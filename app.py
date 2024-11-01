import streamlit as st
import pandas as pd
from rapidfuzz import process
import re
from io import BytesIO
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
import qrcode
import base64

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

    # Match journal names including the first row
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
            else:
                # Handle cases where no good match is found
                results.append([journal_name, "No Match", "N/A"])

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
    st.success("Note: In the downloaded Excel file, journal names, best matches, and impact factors highlighted in yellow indicate entries that were matched using fuzzy matching. This means the journal name in your file didn’t exactly match any name in the database but was closely matched based on similarity. Direct matches without any modification are left unhighlighted.")
else:
    st.info("Please upload your Journal Names Excel file to proceed.")

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
