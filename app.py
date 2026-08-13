
import streamlit as st
import pandas as pd
import requests
from pathlib import Path
 
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
        "APPLICANT",
        "CITY",
        "STATE",
        "GENERICNAME",
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
 
for col in df.columns:
    values = sorted(df[col].dropna().astype(str).unique())
 
    if len(values) <= 50:
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
 
# -----------------------------
# Default Filters from R Script
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("Quick Filters")
 
applicant = st.sidebar.text_input(
    "Applicant",
    value="ABBOTT"
)
 
if applicant:
    filtered_df = filtered_df[
        filtered_df["APPLICANT"]
        .fillna("")
        .str.contains(applicant, case=False)
    ]
 
if "PMANUMBER" in filtered_df.columns:
    pma = st.sidebar.text_input("PMA Number")
    if pma:
        filtered_df = filtered_df[
        filtered_df["PMANUMBER"]
        .fillna("")
        .str.contains(pma, case=False, na=False)
        ]
 
if "CITY" in filtered_df.columns:
    city = st.sidebar.text_input(
        "City",
        value="ABBOTT PARK"
    )
 
    if city:
        filtered_df = filtered_df[
            filtered_df["CITY"]
            .fillna("")
            .str.upper()
            .eq(city.upper())
        ]
 
# Original R logic
if "SUPPLEMENTNUMBER" in filtered_df.columns:
    filtered_df = filtered_df[
        filtered_df["SUPPLEMENTNUMBER"].isna()
    ]
 
# Convert date columns to datetime
filtered_df["DATERECEIVED"] = pd.to_datetime(filtered_df["DATERECEIVED"])
filtered_df["DECISIONDATE"] = pd.to_datetime(filtered_df["DECISIONDATE"])

filtered_df["REVIEW TIME (DAYS)"] = ( filtered_df["DECISIONDATE"] - filtered_df["DATERECEIVED"]).dt.days

filtered_df["year"] = filtered_df["DATERECEIVED"].dt.year
# -----------------------------
# Display Results
# -----------------------------
st.subheader("Filtered PMA Records")
 
st.write(f"Records found: {len(filtered_df):,}")
 
st.dataframe(
    filtered_df,
    use_container_width=True,
    height=600
)
 
# -----------------------------
# Build FDA PDF Links
# -----------------------------
st.subheader("FDA PMA Documents")
 
docs = ["A", "B", "C"]
 
if "PMANUMBER" in filtered_df.columns and "year" in filtered_df.columns:
 
    pdf_rows = []
 
    unique_df = (
        filtered_df
        [["PMANUMBER", "year"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
 
    for _, row in unique_df.iterrows():
 
        pma = str(row["PMANUMBER"])
        for year in range(1, 11): # pdf1 ... pdf10
            for doc in docs:
 
                url = (
                   f"https://www.accessdata.fda.gov/"
                   f"cdrh_docs/pdf5/"
                   f"{pma}{doc}.pdf"
             )

                pdf_rows.append({
                    "PMANUMBER": pma,
                "Document": doc,
                "PDF Link": url
            })
 
    pdf_df = pd.DataFrame(pdf_rows)
 
st.dataframe(
    pdf_df,
    use_container_width=True,
    column_config={
        "PDF Link": st.column_config.LinkColumn(
            "PDF Link",
            display_text=r".*/([^/]+\.pdf)$"
        )
    },
    hide_index=True
)
 
# -----------------------------
# Download PDFs
# -----------------------------
st.subheader("Download PDFs")
 
download_dir = Path("downloads")
download_dir.mkdir(exist_ok=True)
 
if st.button("Download All Visible PDFs"):
 
    progress = st.progress(0)
 
    total = len(pdf_rows)
 
    for i, row in enumerate(pdf_rows):
 
        url = row["PDF Link"]
 
        filename = (
            download_dir /
            f"{row['PMANUMBER']}{row['Document']}.pdf"
        )
 
        try:
            r = requests.get(url, timeout=30)
 
            if r.status_code == 200:
                with open(filename, "wb") as f:
                    f.write(r.content)
 
        except Exception:
            pass
 
        progress.progress((i + 1) / total)
 
    st.success(
        f"Download attempt completed. Files saved to {download_dir}"
    )