import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz

# Provide the correct GitHub URLs
impact_url = "https://raw.githubusercontent.com/yourusername/yourrepo/main/Impact%20Factor%202024.xlsx"
quartile_url = "https://raw.githubusercontent.com/yourusername/yourrepo/main/scimagojr%202024.csv"

@st.cache_data
def load_reference_data():
    impact_df = pd.read_excel(impact_url)
    quartile_df = pd.read_csv(quartile_url, sep=";", on_bad_lines='skip')

    # Rename columns to standard names
    impact_df.rename(columns={"Name": "Journal Name", "JIF": "Impact Factor"}, inplace=True)
    quartile_df.rename(columns={"Title": "Journal Name", "SJR Best Quartile": "Quartile"}, inplace=True)

    return impact_df, quartile_df

def fuzzy_match(journal_name, reference_list):
    match, score, _ = process.extractOne(
        query=journal_name,
        choices=reference_list,
        scorer=fuzz.WRatio
    )
    return match, score

def process_uploaded_file(user_df, impact_df, quartile_df):
    results = []

    if "Source title" not in user_df.columns:
        st.error("Uploaded file must contain a 'Source title' column.")
        st.stop()

    for journal in user_df["Source title"].dropna():
        match_if, score_if = fuzzy_match(journal, impact_df['Journal Name'].astype(str))
        match_q, score_q = fuzzy_match(journal, quartile_df['Journal Name'].astype(str))

        # Fetch matched rows
        row_if = impact_df[impact_df['Journal Name'] == match_if]
        row_q = quartile_df[quartile_df['Journal Name'] == match_q]

        impact_factor = row_if['Impact Factor'].values[0] if not row_if.empty else None
        quartile = row_q['Quartile'].values[0] if not row_q.empty else None

        results.append({
            "Uploaded Journal Name": journal,
            "Matched Journal (Impact Factor)": match_if,
            "Impact Factor": impact_factor,
            "Matched Journal (Quartile)": match_q,
            "Quartile": quartile,
            "Impact Factor Match Score": score_if,
            "Quartile Match Score": score_q
        })

    final_df = pd.DataFrame(results)
    return final_df

# Streamlit UI
st.title("Impact Factor and Quartile Finder (2024)")

uploaded_file = st.file_uploader("Upload your Journal List file (.csv or .xlsx)", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            user_df = pd.read_csv(uploaded_file)
        else:
            user_df = pd.read_excel(uploaded_file)
        
        impact_df, quartile_df = load_reference_data()
        
        final_df = process_uploaded_file(user_df, impact_df, quartile_df)
        
        st.success("Matching complete!")
        st.dataframe(final_df)

        # Option to download
        st.download_button(
            label="Download results as CSV",
            data=final_df.to_csv(index=False),
            file_name="journal_matching_results.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error processing file: {e}")
