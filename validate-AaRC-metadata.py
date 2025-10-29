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
    "Bassas da India", "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan",
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
            conn = http.client.HTTPSConnection(netloc, timeout=5)
        elif scheme == 'http':
            # Use HTTPConnection
            conn = http.client.HTTPConnection(netloc, timeout=5)
        else:
            # Scheme not supported for this checker
            tested_urls[url] = False
            return False

        # Use a GET request for better compatibility with APIs/servers
        conn.request("GET", path) 
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
        description="Validate metadata in an Excel file against 'field_definitions' sheet.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "excel_file",
        help="Path to the Excel file to validate (e.g., metadata.xlsx)."
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
    # Changed from --write-reports to --txt-reports
    parser.add_argument(
        "--txt-reports",
        type=str,
        default=None,
        help="Optional: Prefix for writing tab-delimited reports to files (e.g., 'errors'). Output files will be named <PREFIX>.<SHEET_NAME>.txt"
    )
    # Modified flag for XLSX reports to accept a prefix
    parser.add_argument(
        "--xlsx-reports",
        type=str,
        default=None,
        help="Optional: Prefix for writing a single consolidated Excel report (e.g., 'xlsx_errors'). The output file will be named <PREFIX>.xlsx"
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

    ignore_sheets = ["README", "summary", "template"]

    # Initialize dictionary to collect errors for XLSX output
    all_errors_dfs = {} 

    # Define the fixed header for the tab-delimited and DataFrame output
    REPORT_HEADER = ["Sheet", "Line", "Sample ID", "Field Name", "Error Type", "Observed Value", "Error Details", "Allowed values"]
    
    # --- Define descriptive rules for types where "Allowed values" is typically empty ---
    RULE_DESCRIPTIONS = {
        "NUMBER": "Numeric value (integer or float).",
        "DOI": "DOI format (e.g., doi.org/10.xxxx/xxx) resolving to a valid URL.",
        "ACCESSION": "BioSample prefix required (e.g., SAME, SAMN, SAMD, SAMC) resolving to a valid BioSample entry.",
        "ACCESSION_MT": "Valid NCBI Nucleotide Accession (e.g., OM925842.1) found in NCBI database.",
        "ONTOLOGY_ENA_TECH": f"One of ENA allowed technologies: {', '.join(ENA_TECH_ALLOWED)}",
        "ONTOLOGY_ENA_LIB": f"One of ENA allowed library strategies: {', '.join(ENA_LIB_ALLOWED)}",
        "ONTOLOGY_COUNTRY": "NCBI-approved country (e.g., 'USA' or 'USA: state').",
        "ONTOLOGY_UBERON": "Format: term, UBERON:ID (PURL must resolve).",
        "TAXID": "Valid NCBI Taxonomy ID (integer) found via NCBI API.",
        "FREE TEXT": "Any text is allowed."
    }
    # -------------------------------------------------------------------------------------

    try:
        excel_data = pd.ExcelFile(excel_file)

        if "field_definitions" not in excel_data.sheet_names:
            print("Error: 'field_definitions' sheet is missing.", file=sys.stderr)
            sys.exit(1)

        field_definitions = pd.read_excel(excel_file, sheet_name="field_definitions")
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
                sheet_data = pd.read_excel(excel_file, sheet_name=sheet_name)

                if sheet_data.empty:
                    print(f"INFO: Sheet '{sheet_name}' is empty. Skipping.", file=sys.stderr)
                    continue

                # List to hold errors for the CURRENT sheet
                sheet_errors = [] 

                for row_idx, row in sheet_data.iterrows():
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

                            if value_type == "FREE TEXT":
                                pass # No validation for free text

                            elif value_type == "DEFINED VALUES":
                                values = get_clean_values(cell_value)
                                if not values: continue
                                
                                allowed_set = set([av.strip() for av in allowed_values])
                                
                                for v in values:
                                    if v.strip() not in allowed_set:
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Invalid Numeric Value",
                                            "Observed Value": v,
                                            "Error Details": "Value cannot be parsed as a number.",
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                        sheet_errors.append({
                                            "Sheet": sheet_name,
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
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
                                            "Line": row_idx + 1,
                                            "Sample ID": first_column_value,
                                            "Field Name": col_name,
                                            "Error Type": "Unresolved NCBI TaxID",
                                            "Observed Value": taxid,
                                            "Error Details": "Taxonomy ID could not be found via NCBI API.",
                                            "Allowed values": final_allowed_value
                                        })

                # --- Handle Error Reporting for the current sheet ---
                
                if sheet_errors:
                    
                    # 1. Store for XLSX output if requested (using prefix check)
                    if xlsx_report_prefix:
                        error_df = pd.DataFrame(sheet_errors, columns=REPORT_HEADER)
                        # Ensure sheet name is safe for Excel sheet name limit (31 chars)
                        safe_sheet_name = sheet_name[:31]
                        all_errors_dfs[safe_sheet_name] = error_df
                        print(f"REPORT: Sheet '{sheet_name}' validation complete with {len(sheet_errors)} error(s). Errors stored for XLSX report.", file=sys.stderr)
                    
                    # 2. Handle TXT output if requested
                    if txt_report_prefix:
                        report_filename = f"{txt_report_prefix}.{sheet_name}.txt"
                        report_destination_name = report_filename
                        
                        try:
                            with open(report_filename, 'w') as error_file:
                                print(f"REPORT: Sheet '{sheet_name}' validation complete with {len(sheet_errors)} error(s). Outputting to {report_destination_name}.", file=sys.stderr)
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

    # --- Final step: Write consolidated XLSX report if requested (using prefix) ---
    if xlsx_report_prefix and all_errors_dfs:
        xlsx_filename = f"{xlsx_report_prefix}.xlsx"
        print(f"\nINFO: Writing consolidated XLSX report to {xlsx_filename}...", file=sys.stderr)
        
        try:
            # Use ExcelWriter to manage multiple sheets
            with pd.ExcelWriter(xlsx_filename, engine='xlsxwriter') as writer:
                for sheet_name, df in all_errors_dfs.items():
                    # Write each DataFrame to a sheet named after the input sheet
                    # Sheet names are already trimmed to 31 chars
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            print(f"INFO: XLSX report successfully created: {xlsx_filename}", file=sys.stderr)
        except Exception as e:
            print(f"CRITICAL ERROR: Failed to write XLSX report to {xlsx_filename}. Error: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
