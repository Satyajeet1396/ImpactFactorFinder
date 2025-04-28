import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font
from io import BytesIO
from functools import lru_cache
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

def prepare_reference_database():
    try:
        sjr_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/627344607132b98637e54f8113b40df0bab0d97f/sorted_journal_rankings.csv"
        sjr_df = pd.read_csv(sjr_url)

        jif_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/main/Impact_Factor_2024.xlsx"
        try:
            jif_df = pd.read_excel(jif_url)
        except Exception:
            data = {
                "Name": [
                    "CA-A CANCER JOURNAL FOR CLINICIANS",
                    "NATURE REVIEWS DRUG DISCOVERY",
                    "LANCET",
                    "NEW ENGLAND JOURNAL OF MEDICINE",
                    "BMJ-British Medical Journal",
                    "NATURE REVIEWS MOLECULAR CELL BIOLOGY",
                    "Nature Reviews Clinical Oncology",
                    "Nature Reviews Materials",
                    "Nature Reviews Disease Primers"
                ],
                "JIF": [
                    503.1, 122.7, 98.4, 96.2, 93.6, 81.3, 81.1, 79.8, 76.9
                ]
            }
            jif_df = pd.DataFrame(data)

        if 'Title' in sjr_df.columns:
            sjr_df = sjr_df.rename(columns={'Title': 'Journal_Title'})
        if 'Name' in jif_df.columns:
            jif_df = jif_df.rename(columns={'Name': 'Journal_Title'})

        sjr_df['Title_std'] = sjr_df['Journal_Title'].astype(str).apply(standardize_text)
        jif_df['Title_std'] = jif_df['Journal_Title'].astype(str).apply(standardize_text)

        merged_df = pd.merge(
            sjr_df, 
            jif_df[['Journal_Title', 'Title_std', 'JIF']], 
            on='Title_std', 
            how='outer',
            suffixes=('', '_jif')
        )

        merged_df['Impact Factor'] = merged_df['JIF']

        return merged_df

    except Exception as e:
        st.error(f"Error preparing reference database: {str(e)}")
        raise e

def process_single_file(user_df, ref_df):
    source_title_col = None
    for col in user_df.columns:
        if 'source title' in str(col).lower():
            source_title_col = col
            break

    if source_title_col is None:
        st.error("No 'Source title' column found. Please ensure your file has a 'Source title' column.")
        return None

    journals = user_df[source_title_col].astype(str).apply(standardize_text)
    ref_journals = ref_df['Title_std'].tolist()

    results = []
    progress_bar = st.progress(0)

    for i, journal in enumerate(journals.tolist()):
        progress = (i + 1) / len(journals)
        progress_bar.progress(min(progress, 1.0))

        if pd.isna(journal) or str(journal).strip() == "":
            results.append(("No journal name", "No match found", 0, "", ""))
            continue

        match_row = ref_df[ref_df['Title_std'] == journal]
        if not match_row.empty:
            impact = match_row.iloc[0].get('Impact Factor', "")
            quartile = match_row.iloc[0].get('SJR Best Quartile', "")
            results.append((journal, match_row.iloc[0].get('Journal_Title', journal), 100, impact, quartile))
            continue

        match = process.extractOne(journal, ref_journals, scorer=fuzz.ratio, score_cutoff=90)
        if match:
            matched_title_std = match[0]
            match_row = ref_df[ref_df['Title_std'] == matched_title_std]
            impact = match_row.iloc[0].get('Impact Factor', "")
            quartile = match_row.iloc[0].get('SJR Best Quartile', "")
            results.append((journal, match_row.iloc[0].get('Journal_Title', journal), match[1], impact, quartile))
        else:
            results.append((journal, "No match found", 0, "", ""))

    progress_bar.empty()

    new_columns = ['Processed Journal Name', 'Best Match', 'Match Score', 'Impact Factor', 'SJR Best Quartile']
    results_df = pd.DataFrame(results, columns=new_columns)

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
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']

            header_fill = PatternFill(start_color='0066CC', end_color='0066CC', fill_type='solid')
            new_columns = df.attrs.get('new_columns', [])

            for cell in worksheet[1]:
                if cell.value in new_columns:
                    cell.fill = header_fill
                    cell.font = Font(color='FFFFFF', bold=True)
    else:
        df.to_csv(output, index=False)

    output.seek(0)
    return output

# --- Streamlit App ---
st.title("Journal Impact Factor and Quartile Finder")

with st.expander("ℹ️ Click here to learn about this app", expanded=False):
    st.markdown("""
    This app helps you find Impact Factors and SJR Quartiles for journals.
    - Upload one or more Excel/CSV files containing a 'Source title' column.
    - The app automatically matches journal names from your files with a comprehensive database.
    - It shows Impact Factor (JIF) and SJR Quartile rankings for each journal.
    - Results are sorted by match quality and can be downloaded as Excel/CSV.
    """)

st.write("Upload journal lists (Excel/CSV) to process.")

if 'processed_files' not in st.session_state:
    st.session_state.processed_files = set()
if 'processed_results' not in st.session_state:
    st.session_state.processed_results = {}

uploaded_files = st.file_uploader("Upload Your Journal Lists", type=["xlsx", "csv"], accept_multiple_files=True)

try:
    with st.spinner("Loading reference database..."):
        ref_df = prepare_reference_database()
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
                mime=mime_type
            )

            st.write(f"Sample results:")
            st.dataframe(data['results_df'].head())

if st.button("Clear All and Process New Files"):
    st.session_state.processed_files.clear()
    st.session_state.processed_results.clear()
    st.rerun()
else:
    st.info("Please upload one or more journal lists to start.")

st.divider()
st.info("Created by Dr. Satyajeet Patil")

with st.expander("🤝 Support Our Research", expanded=False):
    st.markdown("🙏 Your Support Makes a Difference!\nEvery donation, no matter how small, fuels our research journey!", unsafe_allow_html=True)
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
