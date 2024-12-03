# ImpactFactorFinder
# Journal Impact Factor Processor

A powerful Streamlit application that helps researchers match their journal lists with impact factors using fuzzy matching algorithms. The app supports processing multiple files simultaneously and provides an intuitive interface for reviewing and downloading results.

## Features

1. **Multi-File Processing**: Upload and process multiple Excel/CSV files simultaneously
2. **Smart Journal Matching**: Uses fuzzy matching to find the best matches even with slight variations in journal names
3. **Intelligent Text Processing**: 
   - Handles common journal abbreviations
   - Removes irrelevant text (ISSN, DOI, etc.)
   - Case-insensitive matching
4. **Results Organization**:
   - Results sorted by match quality (poorest matches first for easy review)
   - Expandable sections for each processed file
   - Preview of results before download
5. **Export Options**: 
   - Download results in original format (Excel/CSV)
   - Maintains original file format for convenience

## How to Use

1. **Start the App**:
   ```bash
   streamlit run multi_journal_processor.py
   ```

2. **Upload Files**:
   - Click "Browse Files" to select one or more files
   - Supports both Excel (.xlsx) and CSV (.csv) formats
   - Each file should contain a column with journal names

3. **Review Results**:
   - Each file's results are shown in an expandable section
   - Results are sorted with poorest matches first for easy review
   - Preview shows the first few entries of each processed file

4. **Download Results**:
   - Click "Download Results" button for each processed file
   - Results maintain the same format as input (Excel/CSV)
   - Downloaded files include all columns: Journal Name, Best Match, Match Score, Impact Factor

5. **Process New Files**:
   - Click "Clear All and Process New Files" to reset
   - Upload new files to process them

## Match Score Understanding

- **100**: Perfect match found in the database
- **80-99**: Good match with minor variations
- **Below 80**: No match found (shown as "No match found" with score 0)

## Dependencies

- streamlit
- pandas
- rapidfuzz
- openpyxl
- tqdm
- qrcode

## Support

Created by Dr. Satyajeet Patil. For more tools, visit: https://patilsatyajeet.wixsite.com/home/python

To support this work:
- Use the QR code in the app for UPI payments
- Visit the Buy Me a Coffee link in the app

## Note

The reference database is regularly updated with the latest impact factors. The app uses fuzzy matching to handle variations in journal names, making it robust against common differences in spelling, abbreviations, and formatting.

