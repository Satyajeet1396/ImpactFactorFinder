import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
from fuzzywuzzy import process
import base64

# ------------------ CONFIG ------------------ #
st.set_page_config(page_title="Impact Factor & Quartile Finder", layout="wide")

impact_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/6f99aed8fc7d0c558b7cd35ecb022e2500c8aa16/Impact%20Factor%202024.xlsx"
quartile_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/45236668ebf6c9283a7f5e49457fa78681529f26/scimagojr%202024.csv"

# ------------------ LOAD DATA ------------------ #
@st.cache_data
def load_reference_data():
    impact_df = pd.read_excel(impact_url)
    # Read CSV robustly, forcing delimiter and skipping bad lines
    try:
        quartile_df = pd.read_csv(quartile_url, encoding='utf-8', on_bad_lines='skip')
    except:
        quartile_df = pd.read_csv(quartile_url, encoding='latin1', on_bad_lines='skip')

    # Trim whitespace from column names
    impact_df.columns = [col.strip() for col in impact_df.columns]
    quartile_df.columns = [col.strip() for col in quartile_df.columns]

    return impact_df, quartile_df

# ------------------ FUZZY MATCHING ------------------ #
def fuzzy_match(journal_name, reference_list):
    match, score = process.extractOne(journal_name, reference_list)
    return match, score

# ------------------ READ USER FILE ------------------ #
def read_uploaded_file(uploaded_file):
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(('.xlsx', '.xls')):
        return pd.read_excel(uploaded_file)
    else:
        st.error("Unsupported file type. Please upload a CSV or Excel file.")
        return None

# ------------------ PROCESS FILE ------------------ #
def process_uploaded_file(user_df, impact_df, quartile_df):
    journal_col = user_df.columns[0]
    results = []

    for journal in user_df[journal_col].dropna():
        # <-- use "Source title" column from impact_df for matching -->
        match_if, score_if = fuzzy_match(journal, impact_df['Source title'].astype(str))
        match_q, score_q = fuzzy_match(journal, quartile_df['Title'].astype(str))

        # fetch the matched rows
        row_if = impact_df[impact_df['Source title'] == match_if].iloc[0] if not impact_df[impact_df['Source title'] == match_if].empty else {}
        row_q  = quartile_df[quartile_df['Title'] == match_q].iloc[0] if not quartile_df[quartile_df['Title'] == match_q].empty else {}

        results.append({
            'Uploaded Journal': journal,
            'Matched Journal (IF)': match_if,
            'Impact Factor': row_if.get('Impact Factor', ''),
            'IF Match Score': score_if,
            'Matched Journal (Quartile)': match_q,
            'SJR': row_q.get('SJR', ''),
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

# ------------------ HISTOGRAM & STATS ------------------ #
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
st.title("📊 Impact Factor & Quartile Finder (2024)")

uploaded_file = st.file_uploader("Upload CSV or Excel with Journal Names in First Column", type=["csv", "xlsx", "xls"])

if uploaded_file:
    user_df = read_uploaded_file(uploaded_file)
    
    if user_df is not None:
        impact_df, quartile_df = load_reference_data()

        # debug: show actual column names if needed
        # st.write("Impact DF columns:", impact_df.columns.tolist())
        # st.write("Quartile DF columns:", quartile_df.columns.tolist())

        final_df = process_uploaded_file(user_df, impact_df, quartile_df)

        st.success("Matching complete!")
        st.dataframe(final_df)

        # Download Excel
        excel_data = to_excel_with_style(final_df)
        st.download_button(
            "📥 Download Matches as Excel",
            data=excel_data,
            file_name="journal_matches.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Plot IF Histogram
        st.subheader("📈 Impact Factor Distribution")
        buf_if, fig_if = plot_histogram(
            final_df, 'Impact Factor', 'Impact Factor Distribution', 'Impact Factor'
        )
        st.pyplot(fig_if)
        st.download_button(
            "📥 Download IF Histogram",
            data=buf_if,
            file_name="impact_factor_hist.png",
            mime="image/png"
        )
        st.markdown("**Statistics for Impact Factor**")
        st.dataframe(get_statistics(final_df, 'Impact Factor'))

        # Plot Quartile Histogram
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
        st.download_button(
            "📥 Download Quartile Histogram",
            data=buf_q,
            file_name="quartile_hist.png",
            mime="image/png"
        )
        st.markdown("**Statistics for Quartile Counts**")
        st.dataframe(quartile_counts)
else:
    st.info("Please upload a file to begin.")
