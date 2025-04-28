import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from io import BytesIO
from functools import lru_cache
from tqdm import tqdm
import qrcode
import base64

# --- Standardization replacements ---
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
    # Find 'Source title' column
    source_title_col = None
    for col in user_df.columns:
        if 'source title' in str(col).lower():
            source_title_col = col
            break

    if source_title_col is None:
        st.error("No 'Source title' column found. Please ensure your file has a 'Source title' column.")
        return None

    # Standardize user journals
    journals = user_df[source_title_col].astype(str).apply(standardize_text)

    # Standardize reference database
    ref_df['Title_std'] = ref_df['Title'].astype(str).apply(standardize_text)
    ref_journals = ref_df['Title_std'].tolist()

    results = []
    for journal in tqdm(journals.tolist(), desc="Processing journals"):
        if pd.isna(journal) or str(journal).strip() == "":
            results.append(("No journal name", "No match found", 0, "", ""))
            continue

        # Perfect match
        match_row = ref_df[ref_df['Title_std'] == journal]
        if not match_row.empty:
            impact = match_row.iloc[0]['Impact Factor']
            quartile = match_row.iloc[0]['SJR Best Quartile']
            results.append((journal, journal, 100, impact, quartile))
            continue

        # Approximate match
        match = process.extractOne(journal, ref_journals, scorer=fuzz.ratio, score_cutoff=90)
        if match:
            matched_title_std = match[0]
            match_row = ref_df[ref_df['Title_std'] == matched_title_std]
            impact = match_row.iloc[0]['Impact Factor']
            quartile = match_row.iloc[0]['SJR Best Quartile']
            results.append((journal, match_row.iloc[0]['Title'], match[1], impact, quartile))
        else:
            results.append((journal, "No match found", 0, "", ""))

    # Create DataFrame
    new_columns = ['Processed Journal Name', 'Best Match', 'Match Score', 'Impact Factor', 'SJR Best Quartile']
    results_df = pd.DataFrame(results, columns=new_columns)

    # Matching statistics
    total = len(results_df)
    perfect_matches = len(results_df[results_df['Match Score'] == 100])
    good_matches = len(results_df[(results_df['Match Score'] >= 90) & (results_df['Match Score'] < 100)])
    no_matches = len(results_df[results_df['Match Score'] == 0])

    st.write("### Matching Statistics")
    st.write(f"""
    - Total journals: {total}
    - Perfect matches (100): {perfect_matches} ({perfect_matches/total*100:.1f}%)
    - Good matches (90-99): {good_matches} ({good_matches/total*100:.1f}%)
    - No matches: {no_matches} ({no_matches/total*100:.1f}%)
    """)

    final_df = pd.concat([user_df, results_df], axis=1)
    final_df = final_df.sort_values(by='Match Score', ascending=True)
    final_df.attrs['new_columns'] = new_columns

    return final_df

def save_results(df, file_format='xlsx'):
    output = BytesIO()
    if file_format == 'xlsx':
        writer = pd.ExcelWriter(output, engine='openpyxl')
        df.to_excel(writer, index=False)

        workbook = writer.book
        worksheet = writer.sheets['Sheet1']

        header_fill = PatternFill(start_color='0066CC', end_color='0066CC', fill_type='solid')
        new_columns = df.attrs.get('new_columns', [])

        for cell in worksheet[1]:
            if cell.value in new_columns:
                cell.fill = header_fill
                cell.font = Font(color='FFFFFF', bold=True)

        writer.close()
    else:
        df.to_csv(output, index=False)

    output.seek(0)
    return output

# --- Streamlit App ---
st.title("Multi-File Journal Impact Factor and Quartile Processor")

with st.expander("ℹ️ Click here to learn about this app", expanded=False):
    st.markdown("""
    This app helps you find Impact Factors and SJR Quartiles for journals.
    - Upload one or more Excel/CSV files containing a 'Source title' column.
    - Automatically matches journal names.
    - Shows Impact Factor and Quartile.
    """)

st.write("Upload journal lists (Excel/CSV) to process.")

if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'processed_results' not in st.session_state:
    st.session_state.processed_results = {}

# Upload user files
uploaded_files = st.file_uploader("Upload Your Journal Lists", type=["xlsx", "csv"], accept_multiple_files=True, key="file_uploader")

# Load reference database
try:
    reference_file_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/627344607132b98637e54f8113b40df0bab0d97f/sorted_journal_rankings.csv"
    ref_df = pd.read_csv(reference_file_url)
    st.success(f"Reference database loaded successfully with {len(ref_df)} journals")
except Exception as e:
    st.error(f"Error loading reference database: {str(e)}")
    st.stop()

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_identifier = f"{uploaded_file.name}_{uploaded_file.size}"

        if file_identifier not in st.session_state.processed_files:
            st.write(f"Processing {uploaded_file.name}...")

            try:
                user_df = read_file(uploaded_file)
                st.write(f"Found {len(user_df)} entries in {uploaded_file.name}")

                with st.spinner(f"Processing {uploaded_file.name}..."):
                    results_df = process_single_file(user_df, ref_df)

                    output_format = uploaded_file.name.split('.')[-1].lower()
                    output_file = save_results(results_df, output_format)

                    st.session_state.processed_results[file_identifier] = {
                        'results_df': results_df,
                        'output_file': output_file,
                        'output_format': output_format,
                        'filename': uploaded_file.name
                    }

                    st.session_state.processed_files.add(file_identifier)

            except Exception as e:
                st.error(f"Error processing {uploaded_file.name}: {str(e)}")
                continue

    if st.session_state.processed_results:
        st.write("### Processed Files Results")
        for file_id, data in st.session_state.processed_results.items():
            with st.expander(f"Results for {data['filename']}", expanded=True):
                output_filename = f"{data['filename'].rsplit('.', 1)[0]}_matched.{data['output_format']}"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if data['output_format'] == 'xlsx' else "text/csv"

                st.download_button(
                    label=f"Download Results for {data['filename']}",
                    data=data['output_file'],
                    file_name=output_filename,
                    mime=mime_type,
                    key=f"download_{file_id}"
                )

                st.write(f"Sample results:")
                st.dataframe(data['results_df'].head())

    if st.button("Clear All and Process New Files"):
        st.session_state.processed_files.clear()
        st.session_state.processed_results.clear()
        st.experimental_rerun()
else:
    st.info("Please upload one or more journal lists to start.")

st.divider()
st.info("Created by Dr. Satyajeet Patil")

with st.expander("🤝 Support Our Research", expanded=False):
    st.markdown("""
    <div style='text-align: center; padding: 1rem; background-color: #f0f2f6; border-radius: 10px; margin: 1rem 0;'>
        <h3>🙏 Your Support Makes a Difference!</h3>
        <p>Every donation, no matter how small, fuels our research journey!</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### UPI Payment")
        upi_url = "upi://pay?pa=satyajeet1396@oksbi&pn=Satyajeet Patil&cu=INR"
        qr = qrcode.make(upi_url)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        buffer.seek(0)
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        st.markdown("Scan to pay: **satyajeet1396@oksbi**")
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center;">
                <img src="data:image/png;base64,{qr_base64}" width="200">
            </div>
            """,
            unsafe_allow_html=True
        )

    with col2:
        st.markdown("#### Buy Me a Coffee")
        st.markdown(
            """
            <div style="display: flex; justify-content: center; align-items: center;">
                <a href="https://www.buymeacoffee.com/researcher13" target="_blank">
                    <img src="https://img.buymeacoffee.com/button-api/?text=Support our Research&emoji=&slug=researcher13&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" alt="Support our Research"/>
                </a>
            </div>
            """,
            unsafe_allow_html=True
        )
