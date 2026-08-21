
import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import io
import zipfile

st.set_page_config(page_title="FDA Premarket Approval(PMA) Explorer", layout="wide")
 
# -----------------------------
# Load Data
# -----------------------------
@st.cache_data
def load_data():
    return pd.read_csv(
         r"https://raw.githubusercontent.com/d8557379/FDA_PMA_streamlit_app/main/pma.txt",
        sep="|",
        dtype=str,
        keep_default_na=True,
        encoding="cp1252")
    
df = load_data()
df =df.loc[:, [
        "PMANUMBER",
        "SUPPLEMENTNUMBER",
        "APPLICANT",
        "TRADENAME",
        "PRODUCTCODE",
        "DATERECEIVED",
        "DECISIONDATE",
    ]]

df = df.rename(columns={
    "PMANUMBER": "PMA Number",
    "SUPPLEMENTNUMBER": "Supplement Number",
    "APPLICANT": "Applicant Name",
    "TRADENAME": "Trade Name",
    "PRODUCTCODE": "Product Code",
    "DATERECEIVED": "Date Received",
    "DECISIONDATE": "Decision Date",
    "SUPPLEMENTCOUNT": "Supplement Count",        
})

st.title("FDA Premarket Approval(PMA) Explorer")
 
# -----------------------------
# Dynamic Filters for Every Column
# -----------------------------

st.sidebar.markdown("# Application Setup Note")
st.sidebar.markdown("For demostration purpose, this application has been preselected for **PMA P050042**. Click **Reset Filters** bottom to begin explorering")
st.sidebar.markdown("---")
st.sidebar.subheader("Reset Filters")
 
 
# Initialize defaults
if "Applicant Name" not in st.session_state:
    st.session_state["Applicant Name"] = ""

if "pma" not in st.session_state:
    st.session_state["pma"] = "P050042"


# Reset button
if st.sidebar.button("Reset Filters"):
    st.session_state["Applicant Name"] = ""
    st.session_state["pma"] = ""
    st.rerun()


st.sidebar.subheader("Quick Filters")

# Quick filter buttons for specific applicants
if st.sidebar.button("Applicant Name: Abbott"):
    st.session_state["Applicant Name"] = "Abbott"
    st.rerun()

if st.sidebar.button("Applicant Name: Roche"):
    st.session_state["Applicant Name"] = "Roche"
    st.rerun()

if st.sidebar.button("Applicant Name: Abbott Laboratories"):
    st.session_state["Applicant Name"] = "Abbott Laboratories"
    st.rerun()
st.sidebar.markdown("---")
   
st.sidebar.header("Filters")

filtered_df = df.copy()
filtered_df = filtered_df.sort_values(by="Decision Date", ascending=False)
 
for col in df.columns:
    values = sorted(df[col].dropna().astype(str).unique())
 
    if len(values) <= 100:
        selected = st.sidebar.multiselect(
            col,
            values,
            default=[]
        )
 
        if selected:
            filtered_df = filtered_df[
                filtered_df[col].astype(str).isin(selected)
            ]
 
    else:
        text_filter = st.sidebar.text_input(
            f"{col} contains"
        )
 
        if text_filter:
            filtered_df = filtered_df[
                filtered_df[col]
                .astype(str)
                .str.contains(text_filter, case=False, na=False)
            ]
 
# Use the value from st.session_state for filtering
applicant_filter_value = st.session_state.get("Applicant Name", "")

# NOTE: filtered_df is not defined in this snippet. Assuming it's defined elsewhere.
# For demonstration, let's assume a dummy filtered_df if not present.
# if 'filtered_df' not in locals():
#     filtered_df = pd.DataFrame(columns=["Applicant Name", "PMA Number"])

if applicant_filter_value:
    # This part assumes 'filtered_df' is already defined and accessible.
    # If not, this code would raise a NameError.
    # Ensure 'filtered_df' is initialized before this block, e.g., filtered_df = initial_dataframe.
    # For the purpose of indentation, I will re-indent it as if 'filtered_df' exists.
    if 'filtered_df' in locals() or 'filtered_df' in globals(): # Placeholder for context
        filtered_df = filtered_df[
            filtered_df["Applicant Name"]
            .fillna("")
            .str.contains(applicant_filter_value, case=False, na=False)
        ]

# Use the value from st.session_state for filtering
pma_filter_value = st.session_state.get("pma", "")

# This part assumes 'filtered_df' exists and has a 'PMA Number' column if the condition is met.
# Also assuming filtered_df is updated by the applicant filter before this block.
if "PMA Number" in filtered_df.columns and pma_filter_value:
    filtered_df = filtered_df[
        filtered_df["PMA Number"]
        .fillna("")
        .str.contains(pma_filter_value, case=False, na=False)
    ] 
# Convert date columns to datetime
filtered_df["Date Received"] = pd.to_datetime(filtered_df["Date Received"])
filtered_df["Decision Date"] = pd.to_datetime(filtered_df["Decision Date"])
filtered_df["Supplement Count"] = filtered_df.groupby("PMA Number")["Supplement Number"].transform("nunique")
filtered_df["Review Time (Day)"] = ( filtered_df["Decision Date"] - filtered_df["Date Received"]).dt.days

filtered_df["Submission Year"] = filtered_df["Date Received"].dt.year
# Format the datetime objects to display only the date part (YYYY-MM-DD)
filtered_df['Date Received'] = filtered_df['Date Received'].dt.strftime('%Y-%m-%d')
filtered_df['Decision Date'] = filtered_df['Decision Date'].dt.strftime('%Y-%m-%d')



# -----------------------------
# Display Results
# -----------------------------
st.subheader("Filtered PMA Records")
 
st.write(f"Records found: {len(filtered_df):,}")
 
st.dataframe(
    filtered_df,
    height=600,
    width="content",
    hide_index=True
)
 
# -----------------------------
# Build FDA PDF Links
# -----------------------------
st.subheader("FDA PMA Documents")
 
docs = ["A", "B", "C"]
mapping = {'A': 'Approval Order', 'B': 'Summary', 'C': 'Labeling'}

if "PMA Number" in filtered_df.columns and "Submission Year" in filtered_df.columns:
 
    pdf_rows = []
 
    unique_df = (
        filtered_df[filtered_df['Supplement Number'].isna()] # Filter out rows where Supplement Number" is blank/NaN
        [["PMA Number", "Submission Year"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )


    for _, row in unique_df.iterrows():
 
        pma = str(row["PMA Number"])
        
        yr=int(str(row["Submission Year"]))
        if yr < 2002:
            year2 = ""
        else:
            year2 = str(int(str(row["Submission Year"])[-2:]))
        
        

        for doc in docs:
            url = (
            f"https://www.accessdata.fda.gov/cdrh_docs/pdf{year2}/"
            f"{pma}{doc}.pdf"
            )
            
            fallback_url = (f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?ID={pma}")
            
            pdf_rows.append({
            "PMA Number": pma,
            "Document": doc,
            "PDF Link": url,
            "FDA Premarket Approval Page": fallback_url
                })
    
    pdf_df = pd.DataFrame(pdf_rows)
    pdf_df['Document Name'] = pdf_df['Document'].map(mapping)
    
st.dataframe(
    pdf_df[["PMA Number", "Document", "Document Name", "PDF Link", "FDA Premarket Approval Page"]].drop_duplicates(),
    width='stretch',
    column_config={
        "PDF Link": st.column_config.LinkColumn(
            "PDF Link",
            display_text=r".*/([^/]+\.pdf)$"
        ),
        "FDA Premarket Approval Page": st.column_config.LinkColumn(
            "FDA Premarket Approval Page",
            display_text=r".*ID=([^/]+)"
        )
    },
    hide_index=True
)
 
# -----------------------------
# Download PDFs as ZIP
# -----------------------------

# Define the headers to mimic a web browser
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

st.subheader("Download PDFs")

if st.button("Prepare ZIP of All Visible PDFs"):
    progress_text = st.empty()
    progress_bar = st.progress(0)

    zip_buffer = io.BytesIO()
    
    total_pdfs = len(pdf_rows)
    
    if total_pdfs == 0:
        st.warning("No PDFs found to prepare in the ZIP.")
    else:
        with zipfile.ZipFile(
            zip_buffer,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
        ) as zip_file:
            
            for i, row in enumerate(pdf_rows):
                current_progress = (i + 1) / total_pdfs
                progress_text.text(f"Downloading PDF {i + 1} of {total_pdfs}: {row['PMA Number']}{row['Document']}.pdf")
                progress_bar.progress(current_progress)
                
                url = row["PDF Link"]
                
                filename = (
                    f"{row['PMA Number']}"
                    f"{row['Document']}.pdf"
                )
                
                try:
                    r = requests.get(url, timeout=30, headers=headers)
                    
                    if r.status_code == 200:
                        zip_file.writestr(
                            filename,
                            r.content,
                        )
                        st.info(f"Successfully added {filename} to ZIP.")
                    else:
                        st.warning(f"Failed to download {filename} (Status: {r.status_code}).")
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Error downloading {filename} from {url}: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred for {filename}: {e}")
            
        zip_buffer.seek(0)
        progress_text.empty() # Clear progress text
        progress_bar.empty() # Clear progress bar

        st.success(
            f"ZIP prepared with {total_pdfs} PDFs. Click the button below to download."
        )
        
        st.download_button(
            label="Download ZIP",
            data=zip_buffer,
            file_name="pma_pdfs.zip",
            mime="application/zip",
            key="download_zip_button"
        )