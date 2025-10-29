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
    # Non-existent IDs return status 200, but only an empty <eSummaryResult> or one 
    # without a <DocSum> block.
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
        help="Optional: Comma-separated list of sheet names to validate (e.g., --sheets Data1,Data2)."
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
        help="Optional: Comma-separated list of column names to validate, e.g., --fields col1,col2."
    )
    parser.add_argument(
        "--write-reports",
        type=str,
        default=None,
        help="Optional: Prefix for writing reports to files (e.g., 'errors'). Output files will be named <PREFIX>.<SHEET_NAME>.txt"
    )
    return parser.parse_args()


def main():
    # Use argparse to handle command-line arguments
    args = parse_args()
    excel_file = args.excel_file
    sheet_filters = args.sheets
    skip_urls = args.skip_urls
    selected_fields = args.fields
    report_prefix = args.write_reports # Get the optional prefix

    ignore_sheets = ["README", "summary", "template"]

    try:
        excel_data = pd.ExcelFile(excel_file)

        if "field_definitions" not in excel_data.sheet_names:
            print("Error: 'field_definitions' sheet is missing.")
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
            allowed_values = row.get("Allowed values", None)
            if pd.notnull(field_name) and pd.notnull(value_type):
                validation_rules[field_name] = {
                    "value_type": value_type.strip().upper(),
                    "allowed_values": [val.strip() for val in str(allowed_values).split(";")] if pd.notnull(allowed_values) else None
                }

        for sheet_name in excel_data.sheet_names:
            if sheet_name in ignore_sheets or sheet_name == "field_definitions":
                continue

            if sheet_filters and sheet_name not in sheet_filters:
                continue

            # --- Output Redirection Setup ---
            error_file = sys.stdout
            is_file_opened = False

            if report_prefix:
                report_filename = f"{report_prefix}.{sheet_name}.txt"
                try:
                    error_file = open(report_filename, 'w')
                    is_file_opened = True
                except IOError as e:
                    # Print warning to STDERR so it's visible even if STDOUT is being piped
                    print(f"Warning: Could not open report file '{report_filename}'. Writing to STDOUT instead. Error: {e}", file=sys.stderr)
                    error_file = sys.stdout
                    is_file_opened = False
            # ---------------------------------
            
            # This status message ALWAYS goes to STDOUT
            print(f"Validating sheet: {sheet_name}")

            try:
                sheet_data = pd.read_excel(excel_file, sheet_name=sheet_name)

                if sheet_data.empty:
                    print(f"Sheet '{sheet_name}' is empty. Skipping.", file=sys.stderr) # Print to stderr as a warning
                    continue

                for row_idx, row in sheet_data.iterrows():
                    for col_name, cell_value in row.items():
                        if selected_fields and col_name not in selected_fields:
                            continue

                        if col_name in validation_rules:
                            rule = validation_rules[col_name]
                            value_type = rule["value_type"]
                            allowed_values = rule["allowed_values"]
                            first_column_value = row.iloc[0] if not row.empty else "N/A"

                            if pd.isnull(cell_value):
                                continue

                            if value_type == "FREE TEXT":
                                pass

                            elif value_type == "DEFINED VALUES":
                                values = get_clean_values(cell_value)
                                if not values:
                                    continue
                                invalid_values = [v for v in values if v.strip() not in [av.strip() for av in allowed_values]]
                                if invalid_values:
                                    # Format invalid values with double quotes
                                    formatted_invalid = ', '.join(f'"{v}"' for v in invalid_values)
                                    # Output error to the designated file/stream
                                    print(f"- Invalid value(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}. Expected one of: {', '.join(allowed_values)}.", file=error_file)

                            elif value_type == "NUMBER":
                                values = get_clean_values(cell_value)
                                if not values:
                                    continue
                                invalid_values = []
                                for v in values:
                                    try:
                                        float(v)
                                    except (ValueError, TypeError):
                                        invalid_values.append(v)
                                if invalid_values:
                                    # Format invalid values with double quotes
                                    formatted_invalid = ', '.join(f'"{v}"' for v in invalid_values)
                                    # Output error to the designated file/stream
                                    print(f"- Invalid numeric value(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}. Expected: numeric value(s).", file=error_file)

                            elif value_type == "DOI" and not skip_urls:
                                doi_urls = get_clean_values(cell_value)
                                if not doi_urls:
                                    continue
                                
                                # Fine-grained DOI validation
                                invalid_dois = []
                                prefix_error_message = 'Must start with "doi.org/", "www.doi.org/", "https://doi.org/", or "https://www.doi.org/"'
                                url_unreachable_message = 'URL could not be reached/resolved'

                                for original_url in doi_urls:
                                    resolved_url_for_check = None
                                    is_prefixed_correctly = False

                                    # Check for valid HTTPS prefixes
                                    if original_url.startswith("https://doi.org/") or original_url.startswith("https://www.doi.org/"):
                                        is_prefixed_correctly = True
                                        resolved_url_for_check = original_url
                                    # Check for scheme-less prefix (doi.org/ or www.doi.org/)
                                    elif original_url.startswith("doi.org/") or original_url.startswith("www.doi.org/"):
                                        is_prefixed_correctly = True
                                        # Prepend https:// to make it a valid URL for the check
                                        resolved_url_for_check = "https://" + original_url
                                    
                                    if not is_prefixed_correctly:
                                        # First check failed: Report prefix error
                                        invalid_dois.append(f'"{original_url}" ({prefix_error_message})')
                                        continue
                                    
                                    # First check passed, now test URL existence
                                    if not url_exists(resolved_url_for_check):
                                        # Second check failed: Report URL unreachable error
                                        invalid_dois.append(f'"{original_url}" ({url_unreachable_message})')

                                if invalid_dois:
                                    # Output accumulated, detailed errors
                                    formatted_invalid = '; '.join(invalid_dois)
                                    # Output error to the designated file/stream
                                    print(f"- Invalid DOI value(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}.", file=error_file)

                            elif value_type == "ACCESSION" and not skip_urls:
                                accession_values = get_clean_values(cell_value)
                                
                                if not accession_values:
                                    continue
                                
                                INSDC_PREFIXES = ("SAME", "SAMN", "SAMD")
                                NGDC_PREFIXES = ("SAMC",)

                                invalid_accessions = []
                                for accession in accession_values:
                                    accession_upper = accession.upper()
                                    base_url = None
                                    archive_group = None
                                    
                                    if accession_upper.startswith(INSDC_PREFIXES):
                                        base_url = "https://www.ebi.ac.uk/biosamples/samples/"
                                        archive_group = "EBI BioSamples"
                                    elif accession_upper.startswith(NGDC_PREFIXES):
                                        base_url = "https://ngdc.cncb.ac.cn/biosample/browse/"
                                        # NGDC (formerly GSA)
                                        archive_group = "NGDC BioSample" 
                                    else:
                                        expected_prefixes = ', '.join(INSDC_PREFIXES + NGDC_PREFIXES)
                                        unrecognized_error = f'"{accession}" (Unrecognized accession prefix. Expected one of: {expected_prefixes})'
                                        invalid_accessions.append(unrecognized_error)
                                        continue # Move to next accession

                                    full_url = f"{base_url}{accession}"
                                    if not url_exists(full_url):
                                        # Report the specific accession and the URL that failed
                                        invalid_accessions.append(f'"{accession}" (Unresolved in {archive_group} at {full_url})')
                                
                                if invalid_accessions:
                                    # Output accumulated, detailed errors
                                    formatted_invalid = '; '.join(invalid_accessions)
                                    print(f"- Invalid accession(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}.", file=error_file)

                            elif value_type == "ACCESSION_MT" and not skip_urls:
                                accession_values = get_clean_values(cell_value)
                                
                                if not accession_values:
                                    continue
                                
                                invalid_accessions = []
                                # Use the dedicated function for ESummary content validation.
                                
                                for accession in accession_values:
                                    if not accession_mt_exists(accession):
                                        # Report the specific accession and the URL that failed
                                        invalid_accessions.append(f'"{accession}" (Unresolved in NCBI Nucleotide database via E-utilities content check)')
                                
                                if invalid_accessions:
                                    # Output accumulated, detailed errors
                                    formatted_invalid = '; '.join(invalid_accessions)
                                    print(f"- Invalid accession(s) (NCBI Nucleotide) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}.", file=error_file)


                            elif value_type == "ONTOLOGY_ENA_TECH":
                                values = get_clean_values(cell_value)
                                if not values:
                                    continue
                                invalid_values = [v for v in values if not is_valid_ena_tech(v)]
                                if invalid_values:
                                    # Format invalid values with double quotes
                                    formatted_invalid = ', '.join(f'"{v}"' for v in invalid_values)
                                    # Output error to the designated file/stream
                                    print(f"- Invalid value(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}. Expected one of: {', '.join(ENA_TECH_ALLOWED)}.", file=error_file)

                            elif value_type == "ONTOLOGY_ENA_LIB":
                                values = get_clean_values(cell_value)
                                if not values:
                                    continue
                                invalid_values = [v for v in values if not is_valid_ena_lib(v)]
                                if invalid_values:
                                    # Format invalid values with double quotes
                                    formatted_invalid = ', '.join(f'"{v}"' for v in invalid_values)
                                    # Output error to the designated file/stream
                                    print(f"- Invalid value(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}. Expected one of: {', '.join(ENA_LIB_ALLOWED)}.", file=error_file)

                            elif value_type == "ONTOLOGY_COUNTRY":
                                values = get_clean_values(cell_value)
                                if not values:
                                    continue
                                invalid_values = [v for v in values if not is_valid_country(v)]
                                if invalid_values:
                                    # Format invalid values with double quotes
                                    formatted_invalid = ', '.join(f'"{v}"' for v in invalid_values)
                                    # Output error to the designated file/stream
                                    print(f"- Invalid value(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}. Expected one of the countries listed here: https://www.ncbi.nlm.nih.gov/genbank/collab/country/", file=error_file)

                            elif value_type == "ONTOLOGY_UBERON" and not skip_urls:
                                values = get_clean_values(cell_value)
                                if not values:
                                    continue

                                invalid_uberon_terms = []
                                for entry in values:
                                    parts = [p.strip() for p in entry.split(",", 1)]

                                    if len(parts) != 2:
                                        # Use double quotes around the entry and for the expected format
                                        invalid_uberon_terms.append(f'"{entry}" (Incorrect format. Expected "term, UBERON:ID")')
                                        continue

                                    uberon_id_raw = parts[1].strip() 
                                    
                                    if not uberon_id_raw.startswith("UBERON:"):
                                        # Use double quotes around the entry
                                        invalid_uberon_terms.append(f'"{entry}" (Second part does not start with "UBERON:")')
                                        continue
                                    
                                    # Replace ":" with "_" to get the PURL suffix
                                    purl_suffix = uberon_id_raw.replace(":", "_")
                                    purl_url = f"http://purl.obolibrary.org/obo/{purl_suffix}"

                                    if not url_exists(purl_url):
                                        # Use double quotes around the entry
                                        invalid_uberon_terms.append(f'"{entry}" (UBERON term did not resolve at {purl_url})')
                                
                                if invalid_uberon_terms:
                                    # The terms are already formatted with quotes, so just join them
                                    # Output error to the designated file/stream
                                    print(f"- Invalid UBERON term(s) on row {row_idx + 1} ({first_column_value}), column '{col_name}': {'; '.join(invalid_uberon_terms)}.", file=error_file)
                            
                            elif value_type == "TAXID" and not skip_urls:
                                raw_taxids = get_clean_values(cell_value)
                                
                                taxids = []
                                for raw_id in raw_taxids:
                                    # Remove ".0" suffix if present, which occurs when pandas reads integers 
                                    # as floats due to NaN values in the column.
                                    if raw_id.endswith(".0"):
                                        taxids.append(raw_id[:-2])
                                    else:
                                        taxids.append(raw_id)
                                        
                                if not taxids:
                                    continue
                                invalid_taxids = [taxid for taxid in taxids if not taxid_exists(taxid)]
                                if invalid_taxids:
                                    # Format invalid values with double quotes
                                    formatted_invalid = ', '.join(f'"{taxid}"' for taxid in invalid_taxids)
                                    # Output error to the designated file/stream
                                    print(f"- Invalid NCBI Taxonomy ID on row {row_idx + 1} ({first_column_value}), column '{col_name}': {formatted_invalid}.", file=error_file)

            finally:
                # Close the file handle if we opened one
                if is_file_opened:
                    error_file.close()

            # This separator ALWAYS goes to STDOUT
            print("-" * 40)

    except FileNotFoundError:
        print(f"Error: The file '{excel_file}' was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading the Excel file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
