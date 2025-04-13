import streamlit as st
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
import seaborn as sns
from fuzzywuzzy import process
import base64

# URLs for reference data
impact_factor_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/6f99aed8fc7d0c558b7cd35ecb022e2500c8aa16/Impact%20Factor%202024.xlsx"
quartile_url = "https://raw.githubusercontent.com/Satyajeet1396/ImpactFactorFinder/45236668ebf6c9283a7f5e49457fa78681529f26/scimagojr%202024.csv"

# Load reference data
@st.cache_data
def load_reference_data():
    impact_df = pd.read_excel(impact_factor_url)
    quartile_df = pd.read_csv(quartile_url)
    return impact_df, quartile_df

impact_df, quartile_df = load_reference_data()

# Prepare journal names
impact_df['Journal Name Clean'] = impact_df['Journal Name'].str.lower().str.strip()
quartile_df['Title Clean'] = quartile_df['Title'].str.lower().str.strip()

# Upload user file
st.title("Journal Impact Factor & Quartile Finder")
uploaded_file = st.file_uploader("Upload your journal file (Excel with 'Journal' column)", type=['xlsx'])

if uploaded_file:
    user_df = pd.read_excel(uploaded_file)
    user_df['Journal Clean'] = user_df['Journal'].str.lower().str.strip()

    matched_data = []
    for journal in user_df['Journal Clean']:
        match_if, score_if = process.extractOne(journal, impact_df['Journal Name Clean'])
        match_q, score_q = process.extractOne(journal, quartile_df['Title Clean'])

        impact_info = impact_df[impact_df['Journal Name Clean'] == match_if].iloc[0]
        quartile_info = quartile_df[quartile_df['Title Clean'] == match_q].iloc[0]

        matched_data.append({
            "Original Journal": journal,
            "Matched IF Journal": impact_info['Journal Name'],
            "Impact Factor": impact_info['Impact Factor'],
            "IF Match Score": score_if,
            "Matched Quartile Journal": quartile_info['Title'],
            "SJR": quartile_info['SJR'],
            "H-index": quartile_info['H index'],
            "Quartile": quartile_info['Quartile'],
            "Q Match Score": score_q
        })

    result_df = pd.DataFrame(matched_data)
    st.dataframe(result_df)

    # Download matched results
    def to_excel(df):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        return output.getvalue()

    st.download_button("Download Matched Data", to_excel(result_df), "matched_journals.xlsx")

    # Histogram of Impact Factors
    st.subheader("Impact Factor Distribution")
    fig1, ax1 = plt.subplots()
    sns.histplot(result_df['Impact Factor'].dropna(), kde=True, ax=ax1, bins=20)
    ax1.set_xlabel("Impact Factor")
    ax1.set_ylabel("Frequency")
    ax1.set_title("Distribution of Impact Factors")
    st.pyplot(fig1)

    # Download plot
    buf1 = BytesIO()
    fig1.savefig(buf1, format="png")
    st.download_button("Download IF Histogram", buf1.getvalue(), "impact_factor_histogram.png")

    # Quartile histogram
    st.subheader("Quartile Distribution")
    fig2, ax2 = plt.subplots()
    sns.countplot(data=result_df, x="Quartile", order=sorted(result_df["Quartile"].dropna().unique()), ax=ax2)
    ax2.set_title("Distribution of Quartiles")
    ax2.set_ylabel("Number of Journals")
    st.pyplot(fig2)

    # Download Quartile plot
    buf2 = BytesIO()
    fig2.savefig(buf2, format="png")
    st.download_button("Download Quartile Histogram", buf2.getvalue(), "quartile_histogram.png")

    # Statistics
    st.subheader("Statistical Summary")
    st.write("**Impact Factor Statistics:**")
    st.dataframe(result_df['Impact Factor'].describe())

    st.write("**Quartile Counts:**")
    st.dataframe(result_df['Quartile'].value_counts())
