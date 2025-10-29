The Python3 script validate-AaRC medata.py can be used to validate entries in the AaRC metadata spreadsheet. Download the Google spreadsheet as an Excel spreadsheet, and give that as input to the script.

```
usage: validate-AaRC-metadata.py [-h] [--sheets SHEETS] [--skip-urls] [--fields FIELDS] [--write-reports WRITE_REPORTS] excel_file

Validate metadata in an Excel file against 'field_definitions' sheet.

positional arguments:
  excel_file            Path to the Excel file to validate (e.g., metadata.xlsx).

optional arguments:
  -h, --help            show this help message and exit
  --sheets SHEETS       Optional: Comma-separated list of sheet names to validate (e.g., --sheets canids,capra).
  --skip-urls           Skip external URL and NCBI TaxID validation checks.
  --fields FIELDS       Optional: Comma-separated list of column names to validate, e.g., --fields samp_taxon_ID,sample_age.
  --write-reports WRITE_REPORTS
                        Optional: Prefix for writing reports to files (e.g., 'errors'). Output files will be named <PREFIX>.<SHEET_NAME>.txt
                        Optional: Prefix for writing reports to files (e.g., 'errors'). Output files will be named <PREFIX>.<SHEET_NAME>.txt
```

