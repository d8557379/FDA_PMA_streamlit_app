
import streamlit as st
import pandas as pd
import requests
from pathlib import Path
import io
import zipfile

st.set_page_config(page_title="FDA PMA Explorer", layout="wide")
 
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
st.title("FDA PMA Explorer")
 
# -----------------------------
# Dynamic Filters for Every Column
# -----------------------------
st.sidebar.header("Filters")

filtered_df = df.copy()
filtered_df = filtered_df.sort_values(by="DECISIONDATE", ascending=False)
 
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
 
st.sidebar.markdown("---")
st.sidebar.subheader("Reset Filters")
 
#applicant = st.sidebar.text_input(
#    "Applicant",
#    value='Abbott',
#    placeholder="Type to search applicant..."
#)
# 
#if applicant:
#    filtered_df = filtered_df[
#        filtered_df["APPLICANT"]
#        .fillna("")
#        .str.contains(applicant, case=False)
#    ]
# 
#if "PMANUMBER" in filtered_df.columns:
#    pma = st.sidebar.text_input("PMA Number", placeholder="Type to search PMA number", value='P050042',)
#    if pma:
#        filtered_df = filtered_df[
#        filtered_df["PMANUMBER"]
#        .fillna("")
#        .str.contains(pma, case=False, na=False)
#        ]
 
# Initialize defaults
if "applicant" not in st.session_state:
    st.session_state["applicant"] = "Abbott"

if "pma" not in st.session_state:
    st.session_state["pma"] = "P050042"


# Reset button
if st.sidebar.button("Reset Filters"):
    st.session_state["applicant"] = ""
    st.session_state["pma"] = ""
    st.rerun()


st.sidebar.markdown("---")
st.sidebar.subheader("Quick Filters")

# Quick filter buttons for specific applicants
if st.sidebar.button("Applicant: Abbott"):
    st.session_state["applicant"] = "Abbott"
    st.rerun()

if st.sidebar.button("Applicant: Roche"):
    st.session_state["applicant"] = "Roche"
    st.rerun()

if st.sidebar.button("Applicant: Abbott Laboratories"):
    st.session_state["applicant"] = "Abbott Laboratories"
    st.rerun()

# Use the value from st.session_state for filtering
applicant_filter_value = st.session_state.get("applicant", "")

# NOTE: filtered_df is not defined in this snippet. Assuming it's defined elsewhere.
# For demonstration, let's assume a dummy filtered_df if not present.
# if 'filtered_df' not in locals():
#     filtered_df = pd.DataFrame(columns=["APPLICANT", "PMANUMBER"])

if applicant_filter_value:
    # This part assumes 'filtered_df' is already defined and accessible.
    # If not, this code would raise a NameError.
    # Ensure 'filtered_df' is initialized before this block, e.g., filtered_df = initial_dataframe.
    # For the purpose of indentation, I will re-indent it as if 'filtered_df' exists.
    if 'filtered_df' in locals() or 'filtered_df' in globals(): # Placeholder for context
        filtered_df = filtered_df[
            filtered_df["APPLICANT"]
            .fillna("")
            .str.contains(applicant_filter_value, case=False, na=False)
        ]

# Use the value from st.session_state for filtering
pma_filter_value = st.session_state.get("pma", "")

# This part assumes 'filtered_df' exists and has a 'PMANUMBER' column if the condition is met.
# Also assuming filtered_df is updated by the applicant filter before this block.
if "PMANUMBER" in filtered_df.columns and pma_filter_value:
    filtered_df = filtered_df[
        filtered_df["PMANUMBER"]
        .fillna("")
        .str.contains(pma_filter_value, case=False, na=False)
    ] 
# Convert date columns to datetime
filtered_df["DATERECEIVED"] = pd.to_datetime(filtered_df["DATERECEIVED"])
filtered_df["DECISIONDATE"] = pd.to_datetime(filtered_df["DECISIONDATE"])
filtered_df["SUPPLEMENTCOUNT"] = filtered_df.groupby("PMANUMBER")["SUPPLEMENTNUMBER"].transform("nunique")
filtered_df["REVIEW TIME (DAYS)"] = ( filtered_df["DECISIONDATE"] - filtered_df["DATERECEIVED"]).dt.days

filtered_df["year"] = filtered_df["DATERECEIVED"].dt.year
# Format the datetime objects to display only the date part (YYYY-MM-DD)
filtered_df['DATERECEIVED'] = filtered_df['DATERECEIVED'].dt.strftime('%Y-%m-%d')
filtered_df['DECISIONDATE'] = filtered_df['DECISIONDATE'].dt.strftime('%Y-%m-%d')
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

if "PMANUMBER" in filtered_df.columns and "year" in filtered_df.columns:
 
    pdf_rows = []
 
    unique_df = (
        filtered_df[filtered_df['SUPPLEMENTNUMBER'].isna()] # Filter out rows where SUPPLEMENTNUMBER is blank/NaN
        [["PMANUMBER", "year"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )


    for _, row in unique_df.iterrows():
 
        pma = str(row["PMANUMBER"])
        year2 = str(int(str(row["year"])[-2:]))

        for doc in docs:
            url = (
            f"https://www.accessdata.fda.gov/cdrh_docs/pdf{year2}/"
            f"{pma}{doc}.pdf"
            )
            
            fallback_url = (f"https://www.accessdata.fda.gov/scripts/cdrh/cfdocs/cfpma/pma.cfm?ID={pma}")
            
            pdf_rows.append({
            "PMANUMBER": pma,
            "Document": doc,
            "PDF Link": url,
            "Verified Link": fallback_url
                })
    
    pdf_df = pd.DataFrame(pdf_rows)
    pdf_df['Document Name'] = pdf_df['Document'].map(mapping)
    
st.dataframe(
    pdf_df[['PMANUMBER','Document Name', 'PDF Link', "Verified Link"]].drop_duplicates(),
    width='stretch',
    column_config={
        "PDF Link": st.column_config.LinkColumn(
            "PDF Link",
            display_text=r".*/([^/]+\.pdf)$"
        ),
        "Verified Link": st.column_config.LinkColumn(
            "Verified Link",
            display_text=r".*ID=([^/]+)"
        )
    },
    hide_index=True
)
 
# -----------------------------
# Download PDFs as ZIP
# -----------------------------


st.subheader("Download PDFs")

if st.button("Prepare ZIP of All Visible PDFs"):
	progress = st.progress(0)
	
	zip_buffer = io.BytesIO()
	
	total = len(pdf_rows)
	
	with zipfile.ZipFile(
		zip_buffer,
		mode="w",
		compression=zipfile.ZIP_DEFLATED,
	) as zip_file:
		
		for i, row in enumerate(pdf_rows):
			
			url = row["PDF Link"]
			
			filename = (
				f"{row['PMANUMBER']}"
				f"{row['Document']}.pdf"
			)
			
			try:
				r = requests.get(url, timeout=30)
				
				if r.status_code == 200:
					zip_file.writestr(
						filename,
						r.content,
					)
				
			except Exception:
				pass
			
			progress.progress((i + 1) / total)
			
	zip_buffer.seek(0)
	
	st.success(
		f"ZIP prepared with up to {total} PDFs."
	)
	
	st.download_button(
		label="Download ZIP",
		data=zip_buffer,
		file_name="visible_pma_pdfs.zip",
		mime="application/zip",
	)