import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from fuzzywuzzy import process

# ------------------ PAGE CONFIG ------------------ #
st.set_page_config(page_title="Impact Factor & Quartile Finder", layout="wide")

# ------------------ LINKS TO GITHUB FILES ------------------ #
impact_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/main/Impact%20Factor%202024.xlsx"
quartile_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/main/scimagojr%202024.csv"

# ------------------ LOAD REFERENCE DATA ------------------ #
@st.cache_data
def load_reference_data():
    impact_df = pd.read_excel(impact_url)
    quartile_df_raw = pd.read_csv(quartile_url, sep=";", header=None, on_bad_lines='skip')

    # For Impact Factor file
    impact_df.rename(columns={"Name": "Journal Name", "JIF": "Impact Factor"}, inplace=True)

    # For Quartile file
    # Check number of columns first
    if quartile_df_raw.shape[1] == 13:
        quartile_df_raw.columns = ['Rank', 'SJR', 'Title', 'Type', 'ISSN', 'Country', 'H index', 'Total Docs (3 years)', 'Total Docs (current year)', 'Total References', 'Total Cites (3 years)', 'Citable Docs (3 years)', 'Quartile']
    elif quartile_df_raw.shape[1] == 11:
        quartile_df_raw.columns = ['Rank', 'SJR', 'Title', 'Type', 'ISSN', 'Country', 'H index', 'Total Docs', 'Total Refs', 'Total Cites', 'Quartile']
    elif quartile_df_raw.shape[1] == 5:
        quartile_df_raw.columns = ['Rank', 'ID', 'Title', 'Type', 'ISSN']
        quartile_df_raw['Quartile'] = None  # Add empty Quartile column
    else:
        st.error(f"Unexpected number of columns ({quartile_df_raw.shape[1]}) in Quartile file.")
        st.stop()

    return impact_df, quartile_df_raw

# ------------------ READ UPLOADED FILE ------------------ #
def read_uploaded_file(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file)
    else:
        st.error("Unsupported file type. Please upload a CSV or Excel file.")
        return None

# ------------------ PROCESS UPLOADED JOURNALS ------------------ #
def process_uploaded_file(user_df, impact_df, quartile_df):
    if 'Source title' not in user_df.columns:
        st.error("Uploaded file must contain a 'Source title' column.")
        st.stop()

    results = []

    for journal in user_df['Source title'].dropna().astype(str):
        journal = journal.strip()
        if not journal:
            continue

        # Match with Impact Factor file
        match_if, score_if = fuzzy_match(journal, impact_df['Journal Name'])
        row_if = impact_df.loc[impact_df['Journal Name'] == match_if].squeeze() if match_if else {}

        # Match with Quartile file
        match_q, score_q = fuzzy_match(journal, quartile_df['Title'])
        row_q = quartile_df.loc[quartile_df['Title'] == match_q].squeeze() if match_q else {}

        results.append({
            'Uploaded Journal': journal,
            'Matched Journal (IF)': match_if,
            'Impact Factor': row_if.get('Impact Factor', ''),
            'IF Match Score': score_if,
            'Matched Journal (Quartile)': match_q,
            'Quartile': row_q.get('Quartile', ''),
            'Q Match Score': score_q
        })

    return pd.DataFrame(results)

# ------------------ EXPORT TO EXCEL ------------------ #
def to_excel_with_style(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Matches')
    writer.close()
    return output.getvalue()

# ------------------ HISTOGRAM HELPERS ------------------ #
def plot_histogram(data, column, title, xlabel):
    fig, ax = plt.subplots()
    sns.histplot(data[column].dropna(), kde=True, bins=20, ax=ax)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    return buf, fig

def get_statistics(df, column):
    return df[column].dropna().describe()

# ------------------ STREAMLIT APP ------------------ #
st.title("📚 Journal Impact Factor and Quartile Finder (2024)")

uploaded_file = st.file_uploader(
    "Upload your CSV or Excel file (must have 'Source title' column):",
    type=["csv", "xlsx", "xls"]
)

if uploaded_file:
    user_df = read_uploaded_file(uploaded_file)
    if user_df is not None:
        impact_df, quartile_df = load_reference_data()

        final_df = process_uploaded_file(user_df, impact_df, quartile_df)

        st.success("Matching complete!")
        st.dataframe(final_df)

        # Download matched data
        excel_data = to_excel_with_style(final_df)
        st.download_button(
            "📥 Download Matches as Excel",
            data=excel_data,
            file_name="journal_matches.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Impact Factor histogram
        st.subheader("📈 Impact Factor Distribution")
        buf_if, fig_if = plot_histogram(final_df, 'Impact Factor', 'Impact Factor Distribution', 'Impact Factor')
        st.pyplot(fig_if)
        st.download_button("📥 Download IF Histogram", data=buf_if, file_name="impact_factor_hist.png", mime="image/png")
        st.markdown("**Statistics for Impact Factor**")
        st.dataframe(get_statistics(final_df, 'Impact Factor'))

        # Quartile histogram
        st.subheader("📊 Quartile Distribution")
        final_df['Quartile'] = final_df['Quartile'].astype(str)
        quartile_counts = final_df['Quartile'].value_counts().sort_index()
        fig_q, ax_q = plt.subplots()
        quartile_counts.plot(kind='bar', ax=ax_q)
        ax_q.set_xlabel("Quartile")
        ax_q.set_ylabel("Count")
        ax_q.set_title("Quartile Distribution")
        buf_q = BytesIO()
        fig_q.savefig(buf_q, format="png", bbox_inches="tight")
        buf_q.seek(0)
        st.pyplot(fig_q)
        st.download_button("📥 Download Quartile Histogram", data=buf_q, file_name="quartile_hist.png", mime="image/png")
        st.markdown("**Statistics for Quartile Counts**")
        st.dataframe(quartile_counts)

else:
    st.info("Please upload your file to start matching.")
