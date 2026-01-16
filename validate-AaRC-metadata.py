import sys
import pandas as pd
import warnings 
import argparse
import http.client
from urllib.parse import urlparse
import re

# Dictionary to store tested URLs and outcomes (retained for caching functionality)
tested_urls = {}

# Hard-coded lists for ENA and country validations
ENA_TECH_ALLOWED = [
    "BGISEQ", "CAPILLARY", "DNBSEQ", "ELEMENT", "GENAPSYS", "GENEMIND",
    "HELICOS", "ILLUMINA", "ION_TORRENT", "LS454", "OXFORD_NANOPORE",
    "PACBIO_SMRT", "TAPESTRI", "VELA_DIAGNOSTICS", "ULTIMA"
]

ENA_LIB_ALLOWED = [
    "WGS", "WGA", "Targeted-Capture", "AMPLICON", "Hi-C", "RAD-Seq", "GBS", 
    "Synthetic-Long-Read", "OTHER"
]

COUNTRY_ALLOWED = [
    "Afghanistan", "Albania", "Algeria", "American Samoa", "Andorra", "Angola", "Anguilla",
    "Antarctica", "Antigua and Barbuda", "Arctic Ocean", "Argentina", "Armenia", "Aruba",
    "Ashmore and Cartier Islands", "Atlantic Ocean", "Australia", "Austria", "Azerbaijan",
    "Bahamas", "Bahrain", "Baltic Sea", "Baker Island", "Bangladesh", "Barbados",
    "Bassas da India", "Belarus", "Belgium", "Benin", "Bermuda", "Bhutan",
    "Bolivia", "Borneo", "Bosnia and Herzegovina", "Botswana", "Bouvet Island", "Brazil",
    "British Virgin Islands", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "Cambodia",
    "Cameroon", "Canada", "Cape Verde", "Cayman Islands", "Central African Republic", "Chad",
    "Chile", "China", "Christmas Island", "Clipperton Island", "Cocos Islands", "Colombia",
    "Comoros", "Cook Islands", "Coral Sea Islands", "Costa Rica", "Cote d'Ivoire", "Croatia",
    "Cuba", "Curacao", "Cyprus", "Czechia", "Democratic Republic of the Congo", "Denmark",
    "Djibouti", "Dominica", "Dominican Republic", "Ecuador", "Egypt", "El Salvador",
    "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Europa Island",
    "Falkland Islands (Islas Malvinas)", "Faroe Islands", "Fiji", "Finland", "France",
    "French Guiana", "French Polynesia", "French Southern and Antarctic Lands", "Gabon",
    "Gambia", "Gaza Strip", "Georgia", "Germany", "Ghana", "Gibraltar", "Glorioso Islands",
    "Greece", "Greenland", "Grenada", "Guadeloupe", "Guam", "Guatemala", "Guernsey", "Guinea",
    "Guinea-Bissau", "Guyana", "Haiti", "Heard Island and McDonald Islands", "Honduras",
    "Hong Kong", "Howland Island", "Hungary", "Iceland", "India", "Indian Ocean", "Indonesia",
    "Iran", "Iraq", "Ireland", "Isle of Man", "Israel", "Italy", "Jamaica", "Jan Mayen",
    "Japan", "Jarvis Island", "Jersey", "Johnston Atoll", "Jordan", "Juan de Nova Island",
    "Kazakhstan", "Kenya", "Kerguelen Archipelago", "Kingman Reef", "Kiribati", "Kosovo",
    "Kuwait", "Kyrgyzstan", "Laos", "Latvia", "Lebanon", "Lesotho", "Liberia", "Libya",
    "Liechtenstein", "Line Islands", "Lithuania", "Luxembourg", "Macau", "Madagascar",
    "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Martinique",
    "Mauritania", "Mauritius", "Mayotte", "Mediterranean Sea", "Mexico",
    "Micronesia, Federated States of", "Midway Islands", "Moldova", "Monaco", "Mongolia",
    "Montenegro", "Montserrat", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru",
    "Navassa Island", "Nepal", "Netherlands", "New Caledonia", "New Zealand", "Nicaragua",
    "Niger", "Nigeria", "Niue", "Norfolk Island", "North Korea", "North Macedonia",
    "North Sea", "Northern Mariana Islands", "Norway", "Oman", "Pacific Ocean", "Pakistan",
    "Palau", "Palmyra Atoll", "Panama", "Papua New Guinea", "Paracel Islands", "Paraguay",
    "Peru", "Philippines", "Pitcairn Islands", "Poland", "Portugal", "Puerto Rico", "Qatar",
    "Republic of the Congo", "Reunion", "Romania", "Ross Sea", "Russia", "Rwanda",
    "Saint Barthelemy", "Saint Helena", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Martin", "Saint Pierre and Miquelon", "Saint Vincent and the Grenadines", "Samoa",
    "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Serbia", "Seychelles",
    "Sierra Leone", "Singapore", "Sint Maarten", "Slovakia", "Slovenia", "Solomon Islands",
    "Somalia", "South Africa", "South Georgia and the South Sandwich Islands", "South Korea",
    "South Sudan", "Southern Ocean", "Spain", "Spratly Islands", "Sri Lanka",
    "State of Palestine", "Sudan", "Suriname", "Svalbard", "Sweden", "Switzerland", "Syria",
    "Taiwan", "Tajikistan", "Tanzania", "Tasman Sea", "Thailand", "Timor-Leste", "Togo",
    "Tokelau", "Tonga", "Trinidad and Tobago", "Tromelin Island", "Tunisia", "Turkey",
    "Turkmenistan", "Turks and Caicos Islands", "Tuvalu", "Uganda", "Ukraine",
    "United Arab Emirates", "United Kingdom", "Uruguay", "USA", "Uzbekistan", "Vanuatu",
    "Venezuela", "Viet Nam", "Virgin Islands", "Wake Island", "Wallis and Futuna",
    "West Bank", "Western Sahara", "Yemen", "Zambia", "Zimbabwe"
]

# Hard-coded lists for ACCESSION validation
EBI_ARCHIVES = ["INSDC", "ENA", "SRA", "DDBJ"] # Retained, though unused in new ACCESSION logic
NGDC_ARCHIVES = ["GSA"]

# List of special strings to ignore
SPECIAL_STRINGS = ["missing", "not applicable", "AaRC curator"]

def url_exists(url):
    """
    Checks if a URL is accessible using http.client (GET request) and caches the result.
    This function is intended for status-code based checks (< 400).
    """
    url = str(url).strip()
    if url in tested_urls:
        return tested_urls[url]

    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    netloc = parsed_url.netloc
    path = parsed_url.path if parsed_url.path else '/'
    
    # Add query parameters back to the path if they exist
    if parsed_url.query:
        path += '?' + parsed_url.query

    result = False
    conn = None

    try:
        # Determine the connection type (HTTP or HTTPS)
        if scheme == 'https':
            # Use HTTPSConnection
            conn = http.client.HTTPSConnection(netloc, timeout=10)
        elif scheme == 'http':
            # Use HTTPConnection
            conn = http.client.HTTPConnection(netloc, timeout=10)
        else:
            # Scheme not supported for this checker
            tested_urls[url] = False
            return False

        # Use a GET request for better compatibility with APIs/servers
        # Add User-Agent to avoid being blocked by servers (e.g. NGDC) that reject bot-like requests
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        conn.request("GET", path, headers=headers)
        response = conn.getresponse()
        
        # Read the entire response body to allow connection to close properly
        response.read() 
        
        # Check for success (status < 400 includes 2xx success and 3xx redirect)
        result = response.status < 400
        
    except Exception:
        # Catch connection errors, timeouts, invalid host, etc.
        result = False
    finally:
        if conn:
            conn.close()

    tested_urls[url] = result
    return result

def get_url_content(url):
    """
    Retrieves the HTTP status code and content of a URL.
    Returns (status_code, content_string).
    """
    url = str(url).strip()
    parsed_url = urlparse(url)
    scheme = parsed_url.scheme.lower()
    netloc = parsed_url.netloc
    path = parsed_url.path if parsed_url.path else '/'
    
    if parsed_url.query:
        path += '?' + parsed_url.query

    status_code = 0
    content = ""
    conn = None

    try:
        if scheme == 'https':
            conn = http.client.HTTPSConnection(netloc, timeout=5)
        elif scheme == 'http':
            conn = http.client.HTTPConnection(netloc, timeout=5)
        else:
            return (0, "")

        conn.request("GET", path) 
        response = conn.getresponse()
        status_code = response.status
        
        # Read the content and decode it (assuming UTF-8)
        content = response.read().decode('utf-8', errors='ignore')
        
    except Exception:
        status_code = 0
        content = ""
    finally:
        if conn:
            conn.close()

    return (status_code, content)

def accession_mt_exists(accession):
    """
    Validates an NCBI Nucleotide accession using ESummary API by checking
    the XML content for the presence of a DocSum block. Caches the result.
    """
    accession = str(accession).strip()
    # Use a unique prefix to prevent cache key conflicts
    cache_key = f"ACC_MT:{accession}" 
    
    if cache_key in tested_urls:
        return tested_urls[cache_key]

    BASE_URL_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=nucleotide&id="
    full_url = f"{BASE_URL_ESUMMARY}{accession}"

    # Fetch status and content
    status, content = get_url_content(full_url)
    
    # An accession is considered valid if:
    # 1. The request was successful (status < 400).
    # 2. The response content contains the <DocSum> tag (indicating a record was found).
    is_valid = status < 400 and "<DocSum>" in content
    
    tested_urls[cache_key] = is_valid
    return is_valid

def taxid_exists(taxid):
    """
    Checks if an NCBI Taxonomy ID is valid by constructing the API URL and
    using the cached url_exists function to check for existence (status < 400).
    """
    # taxid should now be a clean integer string (e.g., "9823")
    taxid = str(taxid).strip()
    if taxid in tested_urls:
        return tested_urls[taxid]

    # Construct the NCBI API URL
    url = f"https://api.ncbi.nlm.nih.gov/datasets/v2alpha/taxonomy/taxon/{taxid}"
    
    # Use the refactored url_exists function to check for the URL existence
    result = url_exists(url)
    
    # Cache the result under the taxid
    tested_urls[taxid] = result
    return result

def is_valid_biosample_accession_format(accession):
    """
    Uses regex to validate the BioSample accession format based on ENA guidance:
    Starts with SAM, followed by one of [E, D, N, C] (case-insensitive), 
    then an optional single uppercase letter (A or G), and finally one or more digits.
    E.g., SAME12345678, SAMEA115399878, SAMC00000001.
    """
    # Pattern: ^SAM[EDNC][A-Z]?\d+$
    # SAM: Literal 'SAM'
    # [EDNC]: One of E, D, N (INSDC) or C (NGDC)
    # [A-Z]?: Optional single uppercase letter (e.g., A for Assay, G for Group)
    # \d+: One or more digits
    pattern = re.compile(r"^SAM[EDNC][A-Z]?\d+$", re.IGNORECASE)
    return bool(pattern.match(accession.strip()))

def is_valid_age_value(value):
    """
    Validates a single clean string value against the rules for age values:
    - A number (float or integer)
    - A number preceded by ">"
    - Exactly "Inf"
    - Exactly "failed"
    """
    v = str(value).strip()
    
    # Case 1 & 2: Check for special strings (case-sensitive as requested)
    if v in ("Inf", "failed"):
        return True
    
    # Prepare for numeric check
    numeric_part = v
    if v.startswith(">"):
        numeric_part = v[1:].strip() # Remove '>' and strip whitespace
    
    # Check if the remaining part is numeric
    if not numeric_part: # If it was just ">"
        return False

    try:
        float(numeric_part)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_ena_tech(value):
    return str(value).strip() in ENA_TECH_ALLOWED

def is_valid_ena_lib(value):
    return str(value).strip() in ENA_LIB_ALLOWED

def is_valid_country(value):
    """
    Checks if the country part (before the first ':') is in COUNTRY_ALLOWED.
    """
    s_value = str(value).strip()
    
    # Split by ':' and take the first part, then strip whitespace again.
    country_part = s_value.split(":", 1)[0].strip()
    
    return country_part in COUNTRY_ALLOWED

def is_special_string(value):
    """
    Checks if a value is one of the special ignored strings using a case-sensitive match.
    """
    # Compare the stripped input value directly against the list of SPECIAL_STRINGS
    return str(value).strip() in SPECIAL_STRINGS

def get_clean_values(cell_value):
    """
    Splits the cell value by semicolon, strips whitespace, and filters out 
    empty strings and special ignored strings (case-sensitive).
    
    Args:
        cell_value: The raw value from the pandas cell.
        
    Returns:
        A list of cleaned, non-special, non-empty string values.
    """
    # Convert to string, strip, split by semicolon, and strip individual values
    values = [v.strip() for v in str(cell_value).split(";") if v.strip()]
    
    # Filter out special strings
    values = [v for v in values if not is_special_string(v)]
    
    return values

def parse_args():
    """Handles command-line arguments using argparse."""
    parser = argparse.ArgumentParser(
        description="Validate metadata in an Excel file or Google Sheet against 'field_definitions' sheet.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "excel_file",
        nargs="?",
        default="https://docs.google.com/spreadsheets/d/1me-fjDmVRktAGRvThZuA9O1VX9s_ZYwox2jDbtOhEZI/",
        help="Path to the Excel file (e.g., metadata.xlsx) or a Google Sheets URL.\nIf no file is given, the default is the AaRC metadata curation Google Sheet: https://docs.google.com/spreadsheets/d/1me-fjDmVRktAGRvThZuA9O1VX9s_ZYwox2jDbtOhEZI/"
    )
    parser.add_argument(
        "--sheets",
        type=lambda s: [f.strip() for f in s.split(",") if f.strip()],
        default=None,
        help="Optional: Comma-separated list of sheet names to validate (e.g., --sheets canids,capra)."
    )
    parser.add_argument(
        "--skip-urls",
        action="store_true",
        help="Skip external URL and NCBI TaxID validation checks."
    )
    parser.add_argument(
        "--fields",
        type=lambda s: [f.strip() for f in s.split(",") if f.strip()],
        default=None,
        help="Optional: Comma-separated list of column names to validate, e.g., --fields samp_taxon_ID,sample_age."
    )
    parser.add_argument(
        "--txt-reports",
        type=str,
        default=None,
        help="Optional: Prefix for writing tab-delimited reports to files (e.g., 'errors'). Output files will be named <PREFIX>.<SHEET_NAME>.txt"
    )
    parser.add_argument(
        "--xlsx-reports",
        type=str,
        default=None,
        help="Optional: Prefix for writing a single consolidated Excel report (e.g., 'xlsx_errors'). The output file will be named <PREFIX>.xlsx"
    )
    parser.add_argument(
        "--ignore-incomplete",
        action="store_true",
        help="Optional: Do not include incomplete entries in the output (missing required fields)."
    )
    return parser.parse_args()


def main():
    # Use argparse to handle command-line arguments
    args = parse_args()
    excel_file = args.excel_file
    sheet_filters = args.sheets
    skip_urls = args.skip_urls
    selected_fields = args.fields
    
    # Updated report arguments: xlsx_report_prefix is now a string (or None)
    txt_report_prefix = args.txt_reports 
    xlsx_report_prefix = args.xlsx_reports
    flag_incomplete = not args.ignore_incomplete

    # Check if input is a Google Sheets URL and convert to export format if so
    if excel_file.startswith(("http://", "https://")) and "docs.google.com/spreadsheets" in excel_file:
        match = re.search(r"/d/([a-zA-Z0-9-_]+)", excel_file)
        if match:
            sheet_id = match.group(1)
            excel_file = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
            print(f"INFO: Detected Google Sheets URL. Fetching as Excel export from: {excel_file}", file=sys.stderr)

    ignore_sheets = ["README", "summary", "template"]

    # Initialize dictionary to collect errors for XLSX output
    all_errors_dfs = {} 
    sheet_stats_list = []

    # Define the fixed header for the tab-delimited and DataFrame output
    REPORT_HEADER = ["Sheet", "Line", "Sample ID", "Field Name", "Error Type", "Observed Value", "Error Details", "Allowed values"]
    
    # --- Define descriptive rules for types where "Allowed values" is typically empty ---
    RULE_DESCRIPTIONS = {
        "NUMBER": "Numeric value (integer or float).",
        "DOI": "DOI format (e.g., doi.org/10.xxxx/xxx) resolving to a valid URL.",
        "ACCESSION": "BioSample prefix required (SAM[EDNC]) and format (e.g., SAMEA115399878) resolving to a valid BioSample entry.",
        "ACCESSION_MT": "Valid NCBI Nucleotide Accession (e.g., OM925842.1) found in NCBI database.",
        "ONTOLOGY_ENA_TECH": f"One of ENA allowed technologies: {', '.join(ENA_TECH_ALLOWED)}",
        "ONTOLOGY_ENA_LIB": f"One of ENA allowed library strategies: {', '.join(ENA_LIB_ALLOWED)}",
        "ONTOLOGY_COUNTRY": "NCBI-approved country (e.g., 'USA' or 'USA: state').",
        "ONTOLOGY_UBERON": "Format: term, UBERON:ID (PURL must resolve).",
        "TAXID": "Valid NCBI Taxonomy ID (integer) found via NCBI API.",
        "AGE": "Sample age value, one of: numeric value (with optional > prefix), 'Inf', or 'failed'.",
        "FREE TEXT": "Any text is allowed.",
        "FREE TEXT OPTIONAL": "Any text is allowed."
    }
    # -------------------------------------------------------------------------------------

    try:
        excel_data = pd.ExcelFile(excel_file)

        if "field_definitions" not in excel_data.sheet_names:
            print("Error: 'field_definitions' sheet is missing.", file=sys.stderr)
            sys.exit(1)

        field_definitions = pd.read_excel(excel_data, sheet_name="field_definitions")
        field_definitions = field_definitions[
            ~field_definitions.iloc[:, 0].isnull() &
            ~field_definitions.iloc[:, 0].astype(str).str.startswith("#")
        ]

        validation_rules = {}
        for _, row in field_definitions.iterrows():
            field_name = row.iloc[0]
            value_type = row["Validation type"]
            allowed_values_raw = row.get("Allowed values", None)

            # Prepare the raw string from the "Allowed values" column for output
            allowed_values_display_str = str(allowed_values_raw).strip()
            # Clean up pandas/None artifacts for display
            if allowed_values_display_str.lower() in ["nan", "none", ""]:
                allowed_values_display_str = ""

            if pd.notnull(field_name) and pd.notnull(value_type):
                validation_rules[field_name] = {
                    "value_type": value_type.strip().upper(),
                    # List of values for validation logic
                    "allowed_values": [val.strip() for val in str(allowed_values_raw).split(";")] if pd.notnull(allowed_values_raw) else None,
                    # Raw string for the output column, or a descriptive rule if empty
                    "allowed_values_display": allowed_values_display_str or RULE_DESCRIPTIONS.get(value_type.strip().upper(), "")
                }

        for sheet_name in excel_data.sheet_names:
            if sheet_name in ignore_sheets or sheet_name == "field_definitions":
                continue

            if sheet_filters and sheet_name not in sheet_filters:
                continue
            
            print(f"INFO: Starting validation for sheet: {sheet_name}", file=sys.stderr)

            try:
                sheet_data = pd.read_excel(excel_data, sheet_name=sheet_name)

                if sheet_data.empty:
                    print(f"INFO: Sheet '{sheet_name}' is empty. Skipping.", file=sys.stderr)
                    continue

                # List to hold errors for the CURRENT sheet
                sheet_errors = [] 
                deferred_incomplete_errors = []

                # Track seen identifiers for duplicate checking
                duplicate_check_cols = ["samp_name", "biosamples_accession", "mt_accession"]
                seen_identifiers = {col: {} for col in duplicate_check_cols}

                # Determine required columns for this sheet (used for incomplete check and stats)
                required_cols = []
                for col in sheet_data.columns:
                    if selected_fields and col not in selected_fields:
                        continue
                    if col in validation_rules:
                        if validation_rules[col]["value_type"] != "FREE TEXT OPTIONAL":
                            required_cols.append(col)

                for row_idx, row in sheet_data.iterrows():
                    
                    # --- Check for Incomplete Entry ---
                    if required_cols:
                        missing_fields = [col for col in required_cols if pd.isnull(row[col])]
                        if missing_fields:
                            # Check curation_complete status
                            is_marked_complete = False
                            if "curation_complete" in sheet_data.columns:
                                val = str(row["curation_complete"])
                                if val.strip().lower() == "yes":
                                    is_marked_complete = True

                            first_column_value = row.iloc[0] if not row.empty else "N/A"
                            
                            if is_marked_complete:
                                sheet_errors.append({
                                    "Sheet": sheet_name,
                                    "Line": row_idx + 2,
                                    "Sample ID": first_column_value,
                                    "Field Name": "-",
                                    "Error Type": "Unintentionally incomplete",
                                    "Observed Value": ";".join(missing_fields),
                                    "Error Details": "curation_complete is set to 'yes', but there are missing fields, as listed here in the Observed Value column.",
                                    "Allowed values": ""
                                })
                            elif flag_incomplete:
                                deferred_incomplete_errors.append({
                                    "Sheet": sheet_name,
                                    "Line": row_idx + 2,
                                    "Sample ID": first_column_value,
                                    "Field Name": "-",
                                    "Error Type": "Incomplete entry",
                                    "Observed Value": ";".join(missing_fields),
                                    "Error Details": "There are missing fields, as listed here in the Observed Value column.",
                                    "Allowed values": ""
                                })

                    # --- Duplicate ID Check ---
                    first_column_value = row.iloc[0] if not row.empty else "N/A"
                    
                    current_samp_name = "N/A"
                    if "samp_name" in sheet_data.columns and pd.notnull(row["samp_name"]):
                        current_samp_name = str(row["samp_name"]).strip()

                    for col in duplicate_check_cols:
                        if selected_fields and col not in selected_fields:
                            continue
                        if col in sheet_data.columns:
                            cell_value = row[col]
                            if pd.notnull(cell_value):
                                clean_vals = get_clean_values(cell_value)
                                for val in clean_vals:
                                    if val in seen_identifiers[col]:
                                        prev_line, prev_samp_name = seen_identifiers[col][val]
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col,
                                            "Error Type": "Duplicate identifier",
                                            "Observed Value": val,
                                            "Error Details": f"The identifier {val} has already been observed, at line {prev_line} (samp_name: {prev_samp_name})",
                                            "Allowed values": ""
                                        })
                                    else:
                                        seen_identifiers[col][val] = (row_idx + 2, current_samp_name)

                    for col_name, cell_value in row.items():
                        if selected_fields and col_name not in selected_fields:
                            continue

                        if col_name in validation_rules:
                            rule = validation_rules[col_name]
                            value_type = rule["value_type"]
                            allowed_values = rule["allowed_values"]
                            # Use the stored display value for the final report column
                            final_allowed_value = rule.get("allowed_values_display", "")

                            first_column_value = row.iloc[0] if not row.empty else "N/A"

                            if pd.isnull(cell_value):
                                continue

                            # --- Validation Logic Starts ---

                            if value_type == "FREE TEXT" or value_type == "FREE TEXT OPTIONAL":
                                pass # No validation for free text

                            elif value_type == "DEFINED VALUES":
                                values = get_clean_values(cell_value)
                                if not values: continue
                                
                                allowed_set = set([av.strip() for av in allowed_values])
                                
                                for v in values:
                                    if v.strip() not in allowed_set:
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid Defined Value",
                                            "Observed Value": v,
                                            "Error Details": "Observed value not in allowed list.",
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "NUMBER":
                                values = get_clean_values(cell_value)
                                if not values: continue
                                
                                for v in values:
                                    try:
                                        float(v)
                                    except (ValueError, TypeError):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid Numeric Value",
                                            "Observed Value": v,
                                            "Error Details": "Value cannot be parsed as a number.",
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "AGE":
                                values = get_clean_values(cell_value)
                                if not values: continue

                                for v in values:
                                    if not is_valid_age_value(v):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid AGE Value",
                                            "Observed Value": v,
                                            "Error Details": "Value must be a number (with optional '>' prefix), 'Inf', or 'failed'.",
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "DOI" and not skip_urls:
                                doi_urls = get_clean_values(cell_value)
                                if not doi_urls: continue
                                
                                url_unreachable_message = 'URL could not be reached/resolved.'

                                for original_url in doi_urls:
                                    resolved_url_for_check = None
                                    is_prefixed_correctly = False

                                    if original_url.startswith("https://doi.org/") or original_url.startswith("https://www.doi.org/"):
                                        is_prefixed_correctly = True
                                        resolved_url_for_check = original_url
                                    elif original_url.startswith("doi.org/") or original_url.startswith("www.doi.org/"):
                                        is_prefixed_correctly = True
                                        resolved_url_for_check = "https://" + original_url
                                    
                                    if not is_prefixed_correctly:
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid DOI Prefix",
                                            "Observed Value": original_url,
                                            "Error Details": "Should start with doi.org, www.doi.org, https://doi.org/ or https://www.doi.org/",
                                            "Allowed values": final_allowed_value
                                        })
                                        continue
                                    
                                    if not url_exists(resolved_url_for_check):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Unresolved DOI URL",
                                            "Observed Value": original_url,
                                            "Error Details": url_unreachable_message,
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "ACCESSION" and not skip_urls:
                                accession_values = get_clean_values(cell_value)
                                if not accession_values: continue
                                
                                INSDC_PREFIXES = ("SAME", "SAMN", "SAMD")
                                NGDC_PREFIXES = ("SAMC",)
                                
                                for accession in accession_values:
                                    
                                    # --- Check format using Regex first ---
                                    if not is_valid_biosample_accession_format(accession):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid BioSample Accession Format",
                                            "Observed Value": accession,
                                            "Error Details": "Accession does not match required SAM[EDNC][A-Z]?####+ format.",
                                            "Allowed values": final_allowed_value
                                        })
                                        continue # Skip URL check if format is bad
                                    # --- End Check ---

                                    accession_upper = accession.upper()
                                    base_url = None
                                    archive_group = None
                                    
                                    if accession_upper.startswith(INSDC_PREFIXES):
                                        base_url = "https://www.ebi.ac.uk/biosamples/samples/"
                                        archive_group = "EBI BioSamples"
                                    elif accession_upper.startswith(NGDC_PREFIXES):
                                        base_url = "https://ngdc.cncb.ac.cn/biosample/browse/"
                                        archive_group = "NGDC BioSample" 
                                    else:
                                        # This should be caught by the regex check, but kept as a fallback.
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Unrecognized BioSample Accession Prefix",
                                            "Observed Value": accession,
                                            "Error Details": f"Unrecognized accession prefix.",
                                            "Allowed values": final_allowed_value
                                        })
                                        continue

                                    full_url = f"{base_url}{accession}"
                                    if not url_exists(full_url):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Unresolved BioSample Accession",
                                            "Observed Value": accession,
                                            "Error Details": f"URL failed to resolve in {archive_group}.",
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "ACCESSION_MT" and not skip_urls:
                                accession_values = get_clean_values(cell_value)
                                if not accession_values: continue
                                
                                for accession in accession_values:
                                    if not accession_mt_exists(accession):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Unresolved NCBI Nucleotide Accession",
                                            "Observed Value": accession,
                                            "Error Details": "Record not found in NCBI Nucleotide database.",
                                            "Allowed values": final_allowed_value
                                        })
                                

                            elif value_type == "ONTOLOGY_ENA_TECH":
                                values = get_clean_values(cell_value)
                                if not values: continue
                                
                                for v in values:
                                    if not is_valid_ena_tech(v):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid ENA Technology",
                                            "Observed Value": v,
                                            "Error Details": "Observed value not in ENA allowed platform list.",
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "ONTOLOGY_ENA_LIB":
                                values = get_clean_values(cell_value)
                                if not values: continue
                                
                                for v in values:
                                    if not is_valid_ena_lib(v):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid ENA Library Strategy",
                                            "Observed Value": v,
                                            "Error Details": "Observed value not in ENA allowed library strategies list.",
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "ONTOLOGY_COUNTRY":
                                values = get_clean_values(cell_value)
                                if not values: continue
                                
                                for v in values:
                                    if not is_valid_country(v):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid Country",
                                            "Observed Value": v,
                                            "Error Details": "Country part is not in NCBI allowed list.",
                                            "Allowed values": final_allowed_value
                                        })

                            elif value_type == "ONTOLOGY_UBERON" and not skip_urls:
                                values = get_clean_values(cell_value)
                                if not values: continue
                                
                                for entry in values:
                                    parts = [p.strip() for p in entry.split(",", 1)]

                                    if len(parts) != 2:
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "UBERON Format Error",
                                            "Observed Value": entry,
                                            "Error Details": 'Incorrect format. Expected: "term, UBERON:ID".',
                                            "Allowed values": final_allowed_value
                                        })
                                        continue

                                    uberon_id_raw = parts[1].strip() 
                                    
                                    if not uberon_id_raw.startswith("UBERON:"):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "UBERON ID Prefix Error",
                                            "Observed Value": entry,
                                            "Error Details": 'ID part does not start with "UBERON:".',
                                            "Allowed values": final_allowed_value
                                        })
                                        continue
                                    
                                    purl_suffix = uberon_id_raw.replace(":", "_")
                                    purl_url = f"http://purl.obolibrary.org/obo/{purl_suffix}"

                                    if not url_exists(purl_url):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Unresolved UBERON Term",
                                            "Observed Value": entry,
                                            "Error Details": f"UBERON term did not resolve at PURL.",
                                            "Allowed values": final_allowed_value
                                        })
                            
                            elif value_type == "TAXID" and not skip_urls:
                                raw_taxids = get_clean_values(cell_value)
                                if not raw_taxids: continue
                                
                                taxids = []
                                for raw_id in raw_taxids:
                                    # Handle pandas reading integers as floats (e.g., 9606.0)
                                    if raw_id.endswith(".0"):
                                        taxids.append(raw_id[:-2])
                                    else:
                                        taxids.append(raw_id)
                                        
                                for taxid in taxids:
                                    if not taxid_exists(taxid):
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 2,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Unresolved NCBI TaxID",
                                            "Observed Value": taxid,
                                            "Error Details": "Taxonomy ID could not be found via NCBI API.",
                                            "Allowed values": final_allowed_value
                                        })

                # Append deferred incomplete errors to the end of the list
                sheet_errors.extend(deferred_incomplete_errors)

                # --- Calculate Statistics for the Sheet ---
                total_entries = len(sheet_data)
                
                # Calculate complete entries: defined as having any value in every field that is not FREE TEXT OPTIONAL
                # (required_cols is already calculated above)
                if required_cols:
                    # Boolean Series indicating if each row is complete
                    is_complete = sheet_data[required_cols].notnull().all(axis=1)
                else:
                    is_complete = pd.Series([True] * total_entries, index=sheet_data.index)
                
                num_complete = is_complete.sum()

                # Determine if rows are marked as curation complete
                if "curation_complete" in sheet_data.columns:
                    cc_series = sheet_data["curation_complete"].astype(str).str.strip().str.lower()
                    is_marked_yes = cc_series == "yes"
                else:
                    is_marked_yes = pd.Series([False] * total_entries, index=sheet_data.index)

                # Calculate unintentionally incomplete
                num_unintentionally_incomplete = 0
                if required_cols:
                    is_incomplete = ~is_complete
                    num_unintentionally_incomplete = (is_incomplete & is_marked_yes).sum()

                # Calculate entries without errors
                lines_with_errors = set(err["Line"] for err in sheet_errors)
                # Boolean Series indicating if each row is clean (no errors)
                is_clean = pd.Series([(i + 2) not in lines_with_errors for i in sheet_data.index], index=sheet_data.index)
                num_clean = is_clean.sum()
                
                # Calculate "Needs completion tickoff"
                # Complete AND Clean AND NOT marked yes
                num_needs_tickoff = (is_complete & is_clean & (~is_marked_yes)).sum()

                # Calculate PASS: Complete AND Clean AND Marked Yes
                num_pass = (is_complete & is_clean & is_marked_yes).sum()

                # Calculate fraction
                frac_pass = (num_pass / total_entries) if total_entries > 0 else 0.0

                sheet_stats_list.append({
                    "Sheet": sheet_name,
                    "Entries": total_entries,
                    "Complete": num_complete,
                    "Unintentionally incomplete": num_unintentionally_incomplete,
                    "Needs completion tickoff": num_needs_tickoff,
                    "Error-free": num_clean,
                    "PASS": num_pass,
                    "PASS fraction": frac_pass,
                    "Total errors": len(sheet_errors),
                })

                # Add "Needs completion tickoff" entries to the error list for reporting
                # (Done after stats calculation so they don't count towards "Total errors" or affect "Clean" status)
                tickoff_rows = sheet_data[is_complete & is_clean & (~is_marked_yes)]
                for idx, row in tickoff_rows.iterrows():
                    first_column_value = row.iloc[0] if not row.empty else "N/A"
                    obs_val = ""
                    if "curation_complete" in sheet_data.columns:
                        val = row["curation_complete"]
                        if pd.notnull(val):
                            obs_val = str(val)
                    
                    sheet_errors.append({
                        "Sheet": sheet_name,
                        "Line": idx + 2,
                        "Sample ID": first_column_value,
                        "Field Name": "curation_complete",
                        "Error Type": "Needs completion tickoff",
                        "Observed Value": obs_val,
                        "Error Details": "Entry is complete and error-free, but curation_complete is not set to 'yes'",
                        "Allowed values": ""
                    })
                
                # Sort errors: "Incomplete entry" last, then by line number
                sheet_errors.sort(key=lambda x: (x["Error Type"] == "Incomplete entry", x["Line"]))

                # --- Handle Error Reporting for the current sheet ---
                
                # 1. Store for XLSX output if requested (using prefix check)
                if xlsx_report_prefix:
                    error_df = pd.DataFrame(sheet_errors, columns=REPORT_HEADER)
                    # Ensure sheet name is safe for Excel sheet name limit (31 chars)
                    safe_sheet_name = sheet_name[:31]
                    all_errors_dfs[safe_sheet_name] = error_df
                    if sheet_errors:
                        print(f"REPORT: Sheet '{sheet_name}' validation complete with {len(sheet_errors)} error(s). Errors stored for XLSX report.", file=sys.stderr)
                    else:
                        print(f"REPORT: Sheet '{sheet_name}' validation passed. Empty error sheet stored for XLSX report.", file=sys.stderr)
                
                # 2. Handle TXT output if requested
                if txt_report_prefix:
                    report_filename = f"{txt_report_prefix}.{sheet_name}.txt"
                    report_destination_name = report_filename
                    
                    try:
                        with open(report_filename, 'w') as error_file:
                            if sheet_errors:
                                print(f"REPORT: Sheet '{sheet_name}' validation complete with {len(sheet_errors)} error(s). Outputting to {report_destination_name}.", file=sys.stderr)
                            else:
                                print(f"REPORT: Sheet '{sheet_name}' validation passed. Outputting empty report to {report_destination_name}.", file=sys.stderr)
                            
                            # Print the header line
                            print('\t'.join(REPORT_HEADER), file=error_file)

                            for err in sheet_errors:
                                # Construct the tab-delimited line
                                line = '\t'.join(str(err.get(h, "")).replace('\t', ' ').replace('\n', ' ') for h in REPORT_HEADER)
                                print(line, file=error_file)
                    except IOError as e:
                        print(f"Warning: Could not open report file '{report_filename}'. Error: {e}", file=sys.stderr)
                        
                # 3. Handle STDOUT (default behavior if no file output flags are used)
                if not txt_report_prefix and not xlsx_report_prefix:
                    if sheet_errors:
                        print(f"REPORT: Sheet '{sheet_name}' validation complete with {len(sheet_errors)} error(s). Outputting to STDOUT.", file=sys.stderr)
                        print('\t'.join(REPORT_HEADER), file=sys.stdout)
                        for err in sheet_errors:
                            line = '\t'.join(str(err.get(h, "")).replace('\t', ' ').replace('\n', ' ') for h in REPORT_HEADER)
                            print(line, file=sys.stdout)
                    else:
                        print(f"INFO: Sheet '{sheet_name}' validation passed. No errors found.", file=sys.stderr)

            except Exception as e:
                print(f"Error reading or processing sheet '{sheet_name}': {e}", file=sys.stderr)


    except FileNotFoundError:
        print(f"Error: The file '{excel_file}' was not found.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading the Excel file: {e}", file=sys.stderr)
        sys.exit(1)

    # --- Process and Output Statistics ---
    STATS_HEADER = ["Sheet", "Entries", "Complete", "Error-free", "PASS", "PASS fraction", "Total errors", "Unintentionally incomplete", "Needs completion tickoff"]
    stats_df = pd.DataFrame(sheet_stats_list, columns=STATS_HEADER)

    if not stats_df.empty:
        # Calculate summary row
        numeric_cols = ["Entries", "Complete", "Unintentionally incomplete", "Needs completion tickoff", "Error-free", "PASS", "Total errors"]
        sums = stats_df[numeric_cols].sum()
        
        total_entries = sums["Entries"]
        total_cc = sums["PASS"]
        total_frac = (total_cc / total_entries) if total_entries > 0 else 0.0
        
        summary_row = pd.DataFrame([{
            "Sheet": "Summary",
            "Entries": int(sums["Entries"]),
            "Complete": int(sums["Complete"]),
            "Unintentionally incomplete": int(sums["Unintentionally incomplete"]),
            "Needs completion tickoff": int(sums["Needs completion tickoff"]),
            "Error-free": int(sums["Error-free"]),
            "PASS": int(sums["PASS"]),
            "PASS fraction": total_frac,
            "Total errors": int(sums["Total errors"])
        }])
        
        stats_df = pd.concat([stats_df, summary_row], ignore_index=True)

    if txt_report_prefix:
        stats_filename = f"{txt_report_prefix}.Validation_statistics.txt"
        try:
            stats_df.to_csv(stats_filename, sep='\t', index=False, float_format='%.2f')
            print(f"REPORT: Validation statistics written to {stats_filename}", file=sys.stderr)
        except IOError as e:
            print(f"Warning: Could not open stats file '{stats_filename}'. Error: {e}", file=sys.stderr)

    if xlsx_report_prefix:
        # Prepend the statistics dataframe to the dictionary so it becomes the first sheet
        new_dfs = {"Validation statistics": stats_df}
        new_dfs.update(all_errors_dfs)
        all_errors_dfs = new_dfs

    if not txt_report_prefix and not xlsx_report_prefix and not stats_df.empty:
        print("\n--- Validation Statistics ---", file=sys.stdout)
        print(stats_df.to_string(index=False, float_format=lambda x: "{:.2f}".format(x)), file=sys.stdout)
        print("-----------------------------\n", file=sys.stdout)

    # --- Final step: Write consolidated XLSX report if requested (using prefix) ---
    if xlsx_report_prefix and all_errors_dfs:
        xlsx_filename = f"{xlsx_report_prefix}.xlsx"
        print(f"\nINFO: Writing consolidated XLSX report to {xlsx_filename}...", file=sys.stderr)
        
        try:
            # Use ExcelWriter to manage multiple sheets
            with pd.ExcelWriter(xlsx_filename, engine='xlsxwriter') as writer:
                workbook = writer.book
                summary_border_fmt = workbook.add_format({'top': 2}) # Thick top border
                legend_header_fmt = workbook.add_format({'bold': True})
                fraction_fmt = workbook.add_format({'num_format': '0.00'})
                summary_fraction_fmt = workbook.add_format({'top': 2, 'num_format': '0.00'})

                for sheet_name, df in all_errors_dfs.items():
                    # Write each DataFrame to a sheet named after the input sheet
                    # Sheet names are already trimmed to 31 chars
                    df.to_excel(writer, sheet_name=sheet_name, index=False)

                    if sheet_name == "Validation statistics" and not df.empty:
                        worksheet = writer.sheets[sheet_name]
                        
                        # Apply number format to "PASS fraction" column
                        pass_frac_col_idx = -1
                        if "PASS fraction" in df.columns:
                            pass_frac_col_idx = df.columns.get_loc("PASS fraction")
                            # Apply format to the column (width=None keeps default)
                            worksheet.set_column(pass_frac_col_idx, pass_frac_col_idx, None, fraction_fmt)

                        # The summary row is the last row of the dataframe
                        # Excel row index = len(df) (since header is row 0)
                        summary_row_idx = len(df)
                        
                        # Apply the border format to the summary row cells
                        for col_idx, value in enumerate(df.iloc[-1]):
                            val_to_write = value if pd.notnull(value) else ""
                            
                            # Use specific format for the fraction column in the summary row
                            if col_idx == pass_frac_col_idx:
                                worksheet.write(summary_row_idx, col_idx, val_to_write, summary_fraction_fmt)
                            else:
                                worksheet.write(summary_row_idx, col_idx, val_to_write, summary_border_fmt)
                        
                        # Add Legend
                        legend_start_row = summary_row_idx + 2
                        legend_content = [
                            ["Column", "Meaning"],
                            ["Sheet", "Name of the sheet validated"],
                            ["Entries", "Total number of rows in the sheet"],
                            ["Complete", "Entries with values in all required columns"],
                            ["Error-free", "Entries with no validation errors"],
                            ["PASS", "Entries that are complete, error-free, and marked 'curation_complete'='yes'"],
                            ["PASS fraction", "Fraction of entries that are PASS"],
                            ["Total errors", "Total count of validation errors found"],
                            ["Unintentionally incomplete", "Entries marked 'curation_complete'='yes' but missing required fields"],
                            ["Needs completion tickoff", "Entries that are complete and error-free and so would PASS, but are not marked 'curation_complete'='yes'"]
                        ]
                        
                        for i, (col_name, meaning) in enumerate(legend_content):
                            if i == 0:
                                worksheet.write(legend_start_row + i, 0, col_name, legend_header_fmt)
                                worksheet.write(legend_start_row + i, 1, meaning, legend_header_fmt)
                            else:
                                worksheet.write(legend_start_row + i, 0, col_name)
                                worksheet.write(legend_start_row + i, 1, meaning)

            print(f"INFO: XLSX report successfully created: {xlsx_filename}", file=sys.stderr)
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to write XLSX report to {xlsx_filename}. Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()