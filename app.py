import streamlit as st
import pandas as pd
from rapidfuzz import process, fuzz
import re
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from functools import lru_cache
from io import BytesIO

# Cache the standardization function for repeated strings
@lru_cache(maxsize=10000)
def standardize_text(text):
    if isinstance(text, str):
        # Combine all string operations into one pass
        text = re.sub(r'[-:]', ' ', text.lower().replace('&', 'and'))
        # Remove multiple spaces
        text = ' '.join(text.split())
    return text

def batch_fuzzy_match(journal_batch, reference_data):
    """Process a batch of journal names for fuzzy matching"""
    results = []
    reference_journals, impact_factors = reference_data
    
    for journal in journal_batch:
        # Try to find a direct match first
        if journal in impact_factors:
            results.append((journal, journal, 100, impact_factors[journal]))
            continue
            
        # Use fuzzy matching only if necessary
        match = process.extractOne(
            journal, 
            reference_journals,
            scorer=fuzz.ratio,
            score_cutoff=80
        )
        if match:
            results.append((journal, match[0], match[1], impact_factors[match[0]]))
    
    return results

def process_journals(file1, file2, batch_size=1000):
    # Load and preprocess data
    df1 = pd.read_excel(file1)
    df2 = pd.read_excel(file2)
    
    df1.iloc[:, 0] = df1.iloc[:, 0].astype(str).apply(standardize_text)
    df2.iloc[:, 0] = df2.iloc[:, 0].astype(str).apply(standardize_text)
    
    impact_factor_dict = dict(zip(df1.iloc[:, 0], df1.iloc[:, 1]))
    reference_journals = df1.iloc[:, 0].tolist()
    journal_list = df2.iloc[:, 0].tolist()
    
    batches = [
        journal_list[i:i + batch_size] 
        for i in range(0, len(journal_list), batch_size)
    ]
    
    # Process batches
    results = []
    for batch in batches:
        batch_results = batch_fuzzy_match(batch, (reference_journals, impact_factor_dict))
        results.extend(batch_results)
    
    # Create results DataFrame
    results_df = pd.DataFrame(
        results,
        columns=['Journal Name', 'Best Match', 'Match Score', 'Impact Factor']
    )
    return results_df

def save_with_highlights(df):
    # Save results with highlighting
    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    
    wb = load_workbook(output)
    ws = wb.active
    highlight_fill = PatternFill(
        start_color="FFFF00",
        end_color="FFFF00",
        fill_type="solid"
    )
    
    for idx, row in enumerate(df.itertuples(), start=2):
        if row._1 != row._2:  # Compare Journal Name with Best Match
            for col in range(1, 5):  # Highlight all columns
                ws.cell(row=idx, column=col).fill = highlight_fill
    
    final_output = BytesIO()
    wb.save(final_output)
    final_output.seek(0)
    return final_output

# Streamlit app
st.title("Journal Impact Factor Finder")

st.write("Upload two Excel files:")
st.write("1. **Impact Factor Database**: Contains journal names and their impact factors.")
st.write("2. **Journal List**: Contains the journal names you want to match.")

# File upload
file1 = st.file_uploader("Upload Impact Factor Database", type="xlsx")
file2 = st.file_uploader("Upload Journal List", type="xlsx")

if file1 and file2:
    with st.spinner("Processing..."):
        results_df = process_journals(file1, file2, batch_size=1000)
        highlighted_file = save_with_highlights(results_df)
    
    st.success("Processing completed! Download your file below:")
    
    # Download button
    st.download_button(
        label="Download Matched Journals",
        data=highlighted_file,
        file_name="matched_journals.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.write("### Sample Results")
    st.dataframe(results_df.head())
else:
    st.info("Please upload both files to proceed.")


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
