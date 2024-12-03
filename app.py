import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from io import BytesIO
from functools import lru_cache
from tqdm import tqdm
import qrcode
import base64

# Reuse the existing journal standardization functions
JOURNAL_REPLACEMENTS = {
    'intl': 'international',
    'int': 'international',
    'natl': 'national',
    'nat': 'national',
    'sci': 'science',
    'med': 'medical',
    'res': 'research',
    'tech': 'technology',
    'eng': 'engineering',
    'phys': 'physics',
    'chem': 'chemistry',
    'bio': 'biology',
    'env': 'environmental',
    'mgmt': 'management',
    'dev': 'development',
    'edu': 'education',
    'univ': 'university',
    'j\\.': 'journal',
    'jr\\.': 'journal',
    'jrnl\\.': 'journal',
    'proc\\.': 'proceedings',
    'rev\\.': 'review',
    'q\\.': 'quarterly',
}

@lru_cache(maxsize=10000)
def standardize_text(text):
    if not isinstance(text, str):
        return ""
    text = text.lower().strip()
    text = text.replace('&', 'and')
    text = re.sub(r'[-:]', ' ', text)
    text = re.sub(r'\([^)]*?(print|online|www|web|issn|doi).*?\)', '', text, flags=re.IGNORECASE)
    for abbr, full in JOURNAL_REPLACEMENTS.items():
        text = re.sub(rf'\b{abbr}\b', full, text, flags=re.IGNORECASE)
    text = re.sub(r'[^\w\s]', ' ', text)
    return ' '.join(text.split())

def read_file(file):
    file_extension = file.name.split('.')[-1].lower()
    if file_extension == 'xlsx':
        return pd.read_excel(file)
    elif file_extension == 'csv':
        return pd.read_csv(file)
    else:
        raise ValueError("Unsupported file format. Please upload either CSV or XLSX file.")

def process_single_file(user_df, ref_df):
    # Preprocess the dataframes
    user_df.iloc[:, 0] = user_df.iloc[:, 0].astype(str).apply(standardize_text)
    ref_df.iloc[:, 0] = ref_df.iloc[:, 0].astype(str).apply(standardize_text)
    
    # Create reference dictionary
    ref_dict = {}
    for journal, impact in zip(ref_df.iloc[:, 0], ref_df.iloc[:, 1]):
        if journal not in ref_dict:
            ref_dict[journal] = []
        ref_dict[journal].append(impact)
    
    ref_journals = ref_df.iloc[:, 0].tolist()
    journal_list = user_df.iloc[:, 0].tolist()
    
    results = []
    for journal in tqdm(journal_list, desc="Processing journals"):
        if pd.isna(journal) or str(journal).strip() == "":
            continue
            
        if journal in ref_dict:
            results.append((journal, journal, 100, ', '.join(map(str, ref_dict[journal]))))
            continue
            
        match = process.extractOne(journal, ref_journals, scorer=fuzz.ratio, score_cutoff=80)
        if match:
            results.append((journal, match[0], match[1], ', '.join(map(str, ref_dict[match[0]]))))
        else:
            results.append((journal, "No match found", 0, ""))
    
    results_df = pd.DataFrame(results, columns=['Journal Name', 'Best Match', 'Match Score', 'Impact Factor'])
    # Sort by Match Score in ascending order (poorest matches first)
    results_df = results_df.sort_values(by='Match Score', ascending=True)
    return results_df

def save_results(df, file_format='xlsx'):
    output = BytesIO()
    if file_format == 'xlsx':
        df.to_excel(output, index=False)
    else:
        df.to_csv(output, index=False)
    output.seek(0)
    return output

# Streamlit app
st.title("Multi-File Journal Impact Factor Processor")

# Add app information
st.markdown("""
### 📚 About This App
This app helps you find impact factors for your journal lists. It can:
- Process multiple Excel/CSV files at once
- Handle journal name variations and abbreviations
- Sort results by match quality (poorest matches first)
- Export results in the same format as your input files

### 🔍 How to Use
1. Upload one or more Excel/CSV files containing journal names
2. Wait for processing to complete
3. Review results (sorted with poorest matches first)
4. Download processed results for each file

### 📊 Match Score Guide
- **100**: Perfect match
- **80-99**: Good match with minor variations
- **0**: No match found
""")

st.write("Upload multiple journal lists to process them simultaneously.")

# Initialize session states
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'processed_results' not in st.session_state:
    st.session_state.processed_results = {}

# File uploads
uploaded_files = st.file_uploader("Upload Your Journal Lists (Excel/CSV)", type=["xlsx", "csv"], accept_multiple_files=True, key="file_uploader")
reference_file_url = "https://github.com/Satyajeet1396/ImpactFactorFinder/raw/634e69a8b15cb2e308ffda203213f0b2bfea6085/Impact%20Factor%202024.xlsx"

if uploaded_files:
    # Load reference data once
    ref_df = pd.read_excel(reference_file_url)
    st.write(f"Reference database contains {len(ref_df)} entries")
    
    # Process each file that hasn't been processed yet
    for uploaded_file in uploaded_files:
        file_identifier = f"{uploaded_file.name}_{uploaded_file.size}"
        
        if file_identifier not in st.session_state.processed_files:
            st.write(f"Processing {uploaded_file.name}...")
            
            try:
                # Read and process the file
                user_df = read_file(uploaded_file)
                st.write(f"Found {len(user_df)} entries in {uploaded_file.name}")
                
                with st.spinner(f"Processing {uploaded_file.name}..."):
                    results_df = process_single_file(user_df, ref_df)
                    
                    # Save results to session state
                    output_format = uploaded_file.name.split('.')[-1].lower()
                    output_file = save_results(results_df, output_format)
                    
                    st.session_state.processed_results[file_identifier] = {
                        'results_df': results_df,
                        'output_file': output_file,
                        'output_format': output_format,
                        'filename': uploaded_file.name
                    }
                    
                    # Mark file as processed
                    st.session_state.processed_files.add(file_identifier)
            
            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                continue
    
    # Display results for all processed files
    if st.session_state.processed_results:
        st.write("### Processed Files Results")
        for file_id, data in st.session_state.processed_results.items():
            with st.expander(f"Results for {data['filename']}", expanded=True):
                # Create download button for this file
                output_filename = f"{data['filename'].rsplit('.', 1)[0]}_matched.{data['output_format']}"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if data['output_format'] == 'xlsx' else "text/csv"
                
                st.download_button(
                    label=f"Download Results for {data['filename']}",
                    data=data['output_file'],
                    file_name=output_filename,
                    mime=mime_type,
                    key=f"download_{file_id}"
                )
                
                # Show sample results
                st.write(f"Sample results:")
                st.dataframe(data['results_df'].head())
    
    # Add a button to clear processed files and start fresh
    if st.button("Clear All and Process New Files"):
        st.session_state.processed_files.clear()
        st.session_state.processed_results.clear()
        st.experimental_rerun()
            
else:
    st.info("Please upload one or more journal lists (XLSX or CSV format) to get started.")

st.info("Created by Dr. Satyajeet Patil")
st.info("For more cool apps like this visit: https://patilsatyajeet.wixsite.com/home/python")

# Support section
st.title("Support our Research")
st.write("Scan the QR code below to make a payment to: satyajeet1396@oksbi")

# Generate UPI QR code
upi_url = "upi://pay?pa=satyajeet1396@oksbi&pn=Satyajeet Patil&cu=INR"
qr = qrcode.make(upi_url)

# Save QR code to BytesIO
buffer = BytesIO()
qr.save(buffer, format="PNG")
buffer.seek(0)
qr_base64 = base64.b64encode(buffer.getvalue()).decode()

# Display QR code
st.markdown(
    f"""
    <div style="display: flex; justify-content: center; align-items: center;">
        <img src="data:image/png;base64,{qr_base64}" width="200">
    </div>
    """,
    unsafe_allow_html=True
)

# Buy Me a Coffee button
st.markdown(
    """
    <div style="text-align: center; margin-top: 20px;">
        <a href="https://www.buymeacoffee.com/researcher13" target="_blank">
            <img src="https://img.buymeacoffee.com/button-api/?text=Support our Research&emoji=&slug=researcher13&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" alt="Support our Research"/>
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

st.info("A small donation from you can fuel our research journey, turning ideas into breakthroughs that can change lives!")

# Donation message
st.markdown("""
    <div style='text-align: center; padding: 1rem; background-color: #f0f2f6; border-radius: 10px; margin: 1rem 0;'>
        <h3>🙏 Support Our Work</h3>
        <p>Your support helps us continue developing free tools for the research community.</p>
        <p>Every contribution, no matter how small, makes a difference!</p>
    </div>
    """, unsafe_allow_html=True)
