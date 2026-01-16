The Python3 script validate-AaRC-metadata.py can be used to validate entries in the AaRC metadata spreadsheet. It can read input either as an Excel file, or directly from a Google Sheets URL. If no input file is given, the default is to read the AaRC metadata curation Google sheet.

By default simply prints identified errors, but with optional flags these can be written to text files or to a multi-sheet Excel file. 

Example command:
python3 ~/sw/validate-AaRC-metadata.py --xlsx-reports output

```
usage: validate-AaRC-metadata.py [-h] [--sheets SHEETS] [--skip-urls] [--fields FIELDS] [--txt-reports TXT_REPORTS] [--xlsx-reports XLSX_REPORTS] [--ignore-incomplete]
                                 [excel_file]

Validate metadata in an Excel file or Google Sheet against 'field_definitions' sheet.

positional arguments:
  excel_file            Path to the Excel file (e.g., metadata.xlsx) or a Google Sheets URL.
                        If no file is given, the default is the AaRC metadata curation Google Sheet: https://docs.google.com/spreadsheets/d/1me-fjDmVRktAGRvThZuA9O1VX9s_ZYwox2jDbtOhEZI/

optional arguments:
  -h, --help            show this help message and exit
  --sheets SHEETS       Optional: Comma-separated list of sheet names to validate (e.g., --sheets canids,capra).
  --skip-urls           Skip external URL and NCBI TaxID validation checks.
  --fields FIELDS       Optional: Comma-separated list of column names to validate, e.g., --fields samp_taxon_ID,sample_age.
  --txt-reports TXT_REPORTS
                        Optional: Prefix for writing tab-delimited reports to files (e.g., 'errors'). Output files will be named <PREFIX>.<SHEET_NAME>.txt
  --xlsx-reports XLSX_REPORTS
                        Optional: Prefix for writing a single consolidated Excel report (e.g., 'xlsx_errors'). The output file will be named <PREFIX>.xlsx
  --ignore-incomplete   Optional: Do not include incomplete entries in the output (missing required fields).
```

