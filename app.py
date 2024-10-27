import streamlit as st
import pandas as pd
from rapidfuzz import process
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill

# Standardize journal names
def standardize_text(text):
    if isinstance(text, str):
        text = text.lower()
        text = text.replace('&', 'and')
        text = re.sub(r'[-:]', ' ', text)
    return text

# Load the default Impact Factor database
@st.cache
def load_impact_factor_database():
    url = "https://github.com/Satyajeet1396/ImpactFactorFinder/raw/6ac70dd47398ff3b1fcbbf1e504d9859491f30d9/Impact%20Factor%202024.xlsx"
    return pd.read_excel(url)

# Title of the app
st.title("Impact Factor Finder")
st.write("Upload an Excel file with a column of journal names to find the best matches and their impact factors.")

# Load the default database
df1 = load_impact_factor_database()
df1.iloc[:, 0] = df1.iloc[:, 0].astype(str).apply(standardize_text)

# Upload user file with journal names
user_file = st.file_uploader("Upload your Excel file with Journal Names", type="xlsx")

if user_file:
    # Read the uploaded Excel file
    df2 = pd.read_excel(user_file)
    df2.iloc[:, 0] = df2.iloc[:, 0].astype(str).apply(standardize_text)

    # Initialize results
    results = []

    # Match journal names
    for journal_name in df2.iloc[:, 0]:
        match = df1[df1.iloc[:, 0] == journal_name]
        if not match.empty:
            impact_factor = match.iloc[0, 1]
            results.append([journal_name, journal_name, impact_factor])
        else:
            best_match = process.extractOne(journal_name, df1.iloc[:, 0])
            if best_match and best_match[1] >= 80:
                impact_factor = df1[df1.iloc[:, 0] == best_match[0]].iloc[0, 1]
                results.append([journal_name, best_match[0], impact_factor])

    # Convert results to DataFrame
    results_df = pd.DataFrame(results, columns=['Journal Name', 'Best Match', 'Impact Factor'])

    # Save results to an in-memory file with highlights
    output = BytesIO()
    results_df.to_excel(output, index=False)
    output.seek(0)
    
    # Load workbook and highlight fuzzy matches
    wb = load_workbook(output)
    ws = wb.active
    highlight_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")
    for index, row in results_df.iterrows():
        if row['Journal Name'] != row['Best Match']:
            ws.cell(row=index + 2, column=1).fill = highlight_fill
            ws.cell(row=index + 2, column=2).fill = highlight_fill
            ws.cell(row=index + 2, column=3).fill = highlight_fill
    
    # Save highlighted workbook
    final_output = BytesIO()
    wb.save(final_output)
    final_output.seek(0)

    # Download button
    st.download_button(
        label="Download Matched Excel File",
        data=final_output,
        file_name="matched_journals.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.success("Matching completed! Download your file.")
else:
    st.info("Please upload your Journal Names Excel file to proceed.")
