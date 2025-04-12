import streamlit as st
import pandas as pd
from io import BytesIO
from tqdm import tqdm
import base64
from rapidfuzz import process, fuzz

tqdm.pandas()

st.set_page_config(page_title="Journal SJR & Quartile Finder", layout="wide")

st.title("📚 Journal Impact and Quartile Finder (SCImago 2024)")

def standardize_text(s):
    return str(s).strip().lower()

# Load SCImago reference data
@st.cache_data
def load_scimago_data():
    url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/45236668ebf6c9283a7f5e49457fa78681529f26/scimagojr%202024.csv"
    df = pd.read_csv(url, sep=';')
    df['Title'] = df['Title'].astype(str).apply(standardize_text)
    return df

scimago_df = load_scimago_data()
st.success(f"✅ Loaded SCImago data with {len(scimago_df)} journal entries.")

# File upload
uploaded_file = st.file_uploader("📂 Upload your journal list (CSV, XLSX)", type=["csv", "xlsx"])

def read_user_file(file):
    if file.name.endswith(".csv"):
        return pd.read_csv(file)
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(file)
    return None

# Processing function
def process_single_file(user_df, scimago_df):
    source_title_col = None
    for col in user_df.columns:
        if 'source title' in str(col).lower():
            source_title_col = col
            break

    if source_title_col is None:
        st.error("No 'Source title' column found in the input file.")
        return None

    journals = user_df[source_title_col].astype(str).apply(standardize_text)

    scimago_titles = scimago_df['Title'].tolist()
    scimago_sjr_dict = dict(zip(scimago_df['Title'], scimago_df['SJR']))
    scimago_quartile_dict = dict(zip(scimago_df['Title'], scimago_df['SJR Best Quartile']))

    results = []
    for journal in tqdm(journals, desc="Matching journals"):
        if pd.isna(journal) or journal.strip() == "":
            results.append(("No journal name", "No match", 0, "", ""))
            continue

        match = process.extractOne(journal, scimago_titles, scorer=fuzz.ratio, score_cutoff=90)
        if match:
            matched_title = match[0]
            sjr = scimago_sjr_dict.get(matched_title, "")
            quartile = scimago_quartile_dict.get(matched_title, "")
            results.append((journal, matched_title, match[1], sjr, quartile))
        else:
            results.append((journal, "No match", 0, "", ""))

    results_df = pd.DataFrame(results, columns=[
        'Processed Journal Name', 'Best Match', 'Match Score', 'SJR (Impact)', 'SJR Quartile'
    ])

    final_df = pd.concat([user_df, results_df], axis=1)
    final_df = final_df.sort_values(by='Match Score', ascending=True)
    final_df.attrs['new_columns'] = ['Best Match', 'Match Score', 'SJR (Impact)', 'SJR Quartile']
    return final_df

# Excel styling and download
def to_excel_with_style(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Results')
        workbook = writer.book
        worksheet = writer.sheets['Results']
        
        # Highlight key columns
        match_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})
        score_format = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
        quartile_format = workbook.add_format({'bg_color': '#D9E1F2', 'font_color': '#1F4E78'})

        if 'Match Score' in df.columns:
            col_idx = df.columns.get_loc('Match Score')
            worksheet.set_column(col_idx, col_idx, 15, score_format)

        for col_name in ['SJR (Impact)', 'SJR Quartile']:
            if col_name in df.columns:
                col_idx = df.columns.get_loc(col_name)
                worksheet.set_column(col_idx, col_idx, 18, quartile_format)

        worksheet.freeze_panes(1, 0)

    output.seek(0)
    return output

def download_link(data, filename, label):
    b64 = base64.b64encode(data.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">{label}</a>'
    return href

# Main interaction
if uploaded_file:
    user_df = read_user_file(uploaded_file)
    if user_df is not None:
        st.write("### Preview of Uploaded File", user_df.head())

        if st.button("🔍 Match Journals with SCImago Data"):
            final_df = process_single_file(user_df, scimago_df)
            if final_df is not None:
                st.write("### ✅ Matching Results", final_df)

                # Stats
                st.write("### 📊 Match Summary")
                total = len(final_df)
                perfect = (final_df['Match Score'] == 100).sum()
                good = ((final_df['Match Score'] >= 90) & (final_df['Match Score'] < 100)).sum()
                none = (final_df['Match Score'] == 0).sum()
                st.markdown(f"- Total: **{total}** | Perfect: **{perfect}** | Good: **{good}** | No Match: **{none}**")

                # Download
                styled_excel = to_excel_with_style(final_df)
                st.markdown(download_link(styled_excel, "Journal_Match_Results.xlsx", "📥 Download Excel Results"), unsafe_allow_html=True)

    else:
        st.error("Could not read the uploaded file. Please make sure it is a valid CSV or Excel file.")
