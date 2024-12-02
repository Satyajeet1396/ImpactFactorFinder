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

# Advanced text preprocessing with common journal abbreviations
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

def preprocess_dataframe(df):
    # Store original length
    original_len = len(df)
    
    # Convert to string and standardize
    df.iloc[:, 0] = df.iloc[:, 0].astype(str).apply(standardize_text)
    
    # Remove empty strings but keep duplicates
    df = df[df.iloc[:, 0].str.len() > 0]
    
    # Show how many rows were removed
    removed = original_len - len(df)
    if removed > 0:
        st.write(f"Removed {removed} empty or invalid rows")
        
    return df

def read_file(file):
    # Get the file extension
    file_extension = file.name.split('.')[-1].lower()
    
    if file_extension == 'xlsx':
        return pd.read_excel(file)
    elif file_extension == 'csv':
        return pd.read_csv(file)
    else:
        raise ValueError("Unsupported file format. Please upload either CSV or XLSX file.")

def save_results(df, file_format='xlsx'):
    output = BytesIO()
    if file_format == 'xlsx':
        df.to_excel(output, index=False)
    else:  # csv
        df.to_csv(output, index=False)
    output.seek(0)
    return output

def process_journals(user_file, reference_file, batch_size=1000):
    # Load dataframes and add debugging information
    ref_df = pd.read_excel(reference_file)
    user_df = read_file(user_file)
    
    st.write(f"Original reference file rows: {len(ref_df)}")
    st.write(f"Original user file rows: {len(user_df)}")
    
    # Preprocess dataframes
    ref_df = preprocess_dataframe(ref_df)
    user_df = preprocess_dataframe(user_df)
    
    st.write(f"After preprocessing - reference file rows: {len(ref_df)}")
    st.write(f"After preprocessing - user file rows: {len(user_df)}")

    ref_dict = {}
    for journal, impact in zip(ref_df.iloc[:, 0], ref_df.iloc[:, 1]):
        if journal not in ref_dict:
            ref_dict[journal] = []
        ref_dict[journal].append(impact)
    
    st.write(f"Number of unique journals in reference: {len(ref_dict)}")

    ref_journals = ref_df.iloc[:, 0].tolist()
    journal_list = user_df.iloc[:, 0].tolist()
    
    st.write(f"Number of journals to process: {len(journal_list)}")

    results = []
    for journal in tqdm(journal_list, desc="Matching journals"):
        if pd.isna(journal) or str(journal).strip() == "":
            continue
            
        if journal in ref_dict:
            results.append((journal, journal, 100, ', '.join(map(str, ref_dict[journal]))))
            continue
            
        match = process.extractOne(journal, ref_journals, scorer=fuzz.ratio, score_cutoff=80)
        if match:
            results.append((journal, match[0], match[1], ', '.join(map(str, ref_dict[match[0]]))))
        else:
            # Include unmatched journals with empty impact factor
            results.append((journal, "No match found", 0, ""))
    
    results_df = pd.DataFrame(results, columns=['Journal Name', 'Best Match', 'Match Score', 'Impact Factor'])
    st.write(f"Final results rows: {len(results_df)}")
    return results_df

# Streamlit app
st.title("Enhanced Journal Impact Factor Finder")
st.write("Upload your journal list to find the best matches and their impact factors.")

# File uploads
user_file = st.file_uploader("Upload Your Journal List (Excel/CSV)", type=["xlsx", "csv"])
reference_file_url = "https://github.com/Satyajeet1396/ImpactFactorFinder/raw/634e69a8b15cb2e308ffda203213f0b2bfea6085/Impact%20Factor%202024.xlsx"

if user_file:
    # Get the file extension for the output format
    output_format = user_file.name.split('.')[-1].lower()
    
    with st.spinner("Processing..."):
        results_df = process_journals(user_file, reference_file_url)
        output_file = save_results(results_df, output_format)
    
    st.success("Processing complete! Download your results below:")
    
    # Set appropriate mime type and file extension for download
    if output_format == 'xlsx':
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        file_extension = "xlsx"
    else:
        mime = "text/csv"
        file_extension = "csv"
    
    st.download_button(
        label="Download Results",
        data=output_file,
        file_name=f"matched_journals.{file_extension}",
        mime=mime
    )
    
    st.write("### Sample Results")
    st.dataframe(results_df.head())
else:
    st.info("Please upload your journal list (XLSX or CSV format) to get started.")

st.info("Created by Dr. Satyajeet Patil")
st.info("For more cool apps like this visit: https://patilsatyajeet.wixsite.com/home/python")

# Title of the section
st.title("Support our Research")
st.write("Scan the QR code below to make a payment to: satyajeet1396@oksbi")

# Generate the UPI QR code
upi_url = "upi://pay?pa=satyajeet1396@oksbi&pn=Satyajeet Patil&cu=INR"
qr = qrcode.make(upi_url)

# Save the QR code image to a BytesIO object
buffer = BytesIO()
qr.save(buffer, format="PNG")
buffer.seek(0)

# Convert the image to Base64
qr_base64 = base64.b64encode(buffer.getvalue()).decode()

# Center-align the QR code image using HTML and CSS
st.markdown(
    f"""
    <div style="display: flex; justify-content: center; align-items: center;">
        <img src="data:image/png;base64,{qr_base64}" width="200">
    </div>
    """,
    unsafe_allow_html=True
)

# Display the "Buy Me a Coffee" button as an image link
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

# Add the donation message
st.markdown("""
    <div style='text-align: center; padding: 1rem; background-color: #f0f2f6; border-radius: 10px; margin: 1rem 0;'>
        <h3>🙏 Support Our Work</h3>
        <p>Your support helps us continue developing free tools for the research community.</p>
        <p>Every contribution, no matter how small, makes a difference!</p>
    </div>
    """, unsafe_allow_html=True)
