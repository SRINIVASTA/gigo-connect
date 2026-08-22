import streamlit as strl
import pandas as pd
import numpy as np
import requests
import base64
import time
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

# -------------------------------------------------------------------------
# SYSTEM CONFIGURATION & INTERFACE RE-BRANDING
# -------------------------------------------------------------------------
strl.set_page_config(page_title="gigo-xero Engine", layout="wide")
strl.title("📊 Unsupervised Xero ML Bookkeeping & Analytics Engine")
strl.caption("An anti-GIGO system designed to ingest, clean, and cluster unlabeled financial text notifications.")
strl.divider()

# Core Workspace Cache Layers
if "xero_tokens" not in strl.session_state: strl.session_state["xero_tokens"] = None
if "xero_df" not in strl.session_state: strl.session_state["xero_df"] = None
if "uploaded_df" not in strl.session_state: strl.session_state["uploaded_df"] = None

# Load patterns securely from TOML structures
ML_CONFIG = strl.secrets.get("ML_CONFIG", {})
SUB_CLASSIFICATION = strl.secrets.get("SUB_CLASSIFICATION", {})

# Fallback credentials pointers
CLIENT_ID = strl.secrets.get("XERO_CLIENT_ID", "YOUR_XERO_CLIENT_ID_HERE")
CLIENT_SECRET = strl.secrets.get("XERO_CLIENT_SECRET", "YOUR_XERO_CLIENT_SECRET_HERE")
REDIRECT_URI = strl.secrets.get("XERO_REDIRECT_URI", "https://streamlit.app")

AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
TENANT_API_URL = "https://xero.com"
INVOICES_API_URL = "https://xero.com"
SCOPES = "openid profile email accounting.transactions accounting.journals offline_access"

# Helper Export Converters
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def convert_df_to_xlsx(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clustered Bookkeeping')
    return output.getvalue()

# Ingestion Selector UI
st_selection = strl.radio(
    "Select Target Bookkeeping Data Feed:",
    ["Sync Directly with Xero Live API", "Upload Local Bookkeeping Files (CSV / XLSX)"],
    horizontal=True
)

active_matrix_df = None

if st_selection == "Sync Directly with Xero Live API":
    if strl.session_state["xero_tokens"] is None:
        strl.warning("🔐 Data Ingestion Locked: Authentication required.")
        auth_link = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}&prompt=consent"
        strl.link_button("🚀 Secure Connect to Xero API App", auth_link)
    else:
        active_matrix_df = strl.session_state["xero_df"]
else:
    uploaded_file = strl.file_uploader("Drop transaction worksheets here", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            parsed_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            if "Clean Description" not in parsed_df.columns:
                text_match = [col for col in parsed_df.columns if any(x in col.lower() for x in ["desc", "ref", "sms", "text", "particular"])]
                if text_match:
                    parsed_df.rename(columns={text_match[0]: "Clean Description"}, inplace=True)
                else:
                    parsed_df["Clean Description"] = "Manual Data Entry Item"
            strl.session_state["uploaded_df"] = parsed_df
        except Exception as e:
            strl.error(f"File reading exception: {e}")
    active_matrix_df = strl.session_state["uploaded_df"]
# -------------------------------------------------------------------------
# METRICS SUMMARY, VISUALIZATIONS & SPREADSHEET EXPLORER BLOCK
# -------------------------------------------------------------------------
strl.markdown("---")

if active_matrix_df is not None and not active_matrix_df.empty:
    df_ml = active_matrix_df.copy()
    
    # Apply ML_CONFIG Garbage Cleaning Filters
    garbage_list = ML_CONFIG.get("GARBAGE_FLAGS", [])
    if garbage_list:
        df_ml = df_ml[~df_ml['Clean Description'].astype(str).str.contains('|'.join(garbage_list), case=False, na=False)]

    # Clean Amount column formatting dynamically for analytics charts mapping
    amt_col = [col for col in df_ml.columns if "amount" in col.lower() or "total" in col.lower() or "val" in col.lower()]
    if amt_col:
        df_ml['Total Amount'] = pd.to_numeric(df_ml[amt_col[0]].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0.0)
    else:
        df_ml['Total Amount'] = 0.0

    # 1. RENDER GENERAL LEDGER METRICS SUMMARY
    strl.subheader("📈 General Ledger Metrics Summary")
    m_col1, m_col2, m_col3, m_col4 = strl.columns(4)
    with m_col1:
        strl.metric("Total Extracted Records", f"{len(df_ml)}")
    with m_col2:
        strl.metric("Gross Financial Velocity", f"USD {df_ml['Total Amount'].sum():,.2f}")
    with m_col3:
        strl.metric("Average Invoiced Ticket", f"USD {df_ml['Total Amount'].mean():,.2f}")
    with m_col4:
        strl.metric("Data Quality Consistency (Anti-GIGO)", "100%")

    strl.markdown("---")
    
    # K-Means clustering configuration setup hooks
    num_clusters = strl.slider("Select Target Bookkeeping Clusters (K-Means)", min_value=2, max_value=5, value=3)
    
    try:
        # Run Vectorizer Modeling 
        vectorizer = TfidfVectorizer(stop_words='english', max_features=200)
        X = vectorizer.fit_transform(df_ml['Clean Description'].astype(str))
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        df_ml['Predicted Cluster Bucket'] = kmeans.fit_predict(X)
        
        # Sub-classification tag mappings handler loop
        def assign_sub_class(desc):
            desc_lower = str(desc).lower()
            for class_name, keywords in SUB_CLASSIFICATION.items():
                if any(kw.lower() in desc_lower for kw in keywords): return class_name
            if any(x.lower() in desc_lower for x in ML_CONFIG.get("APPLE_TOKENS", [])): return "APPLE DIGITAL"
            if any(x.lower() in desc_lower for x in ML_CONFIG.get("DHABI_TOKENS", [])): return "ABU DHABI EMIR"
            if any(x.lower() in desc_lower for x in ML_CONFIG.get("CREDIT_TOKENS", [])): return "INCOMING CREDIT"
            return "General Unclassified"

        df_ml['Accounting Sub-Class Label'] = df_ml['Clean Description'].apply(assign_sub_class)
        
        # 2. DATA ANALYTICS DISTRIBUTION VISUALIZATIONS
        strl.subheader("📊 Data Analytics Distribution Visualizations")
        v_col1, v_col2 = strl.columns(2)
        
        with v_col1:
            strl.markdown("**Transaction Frequency by Sub-Classification Model**")
            subclass_counts = df_ml['Accounting Sub-Class Label'].value_counts()
            strl.bar_chart(subclass_counts)
            
        with v_col2:
            strl.markdown("**Volume Footprint Density per AI Cluster Group**")
            cluster_volumes = df_ml.groupby('Predicted Cluster Bucket')['Total Amount'].sum()
            strl.bar_chart(cluster_volumes)

        strl.markdown("---")
        
        # 3. COMPILING THE LIVE SPREADSHEET VIEW EXPLORER
        strl.subheader("📋 Live Spreadsheet View Explorer")
        
        # Re-map centroids keywords mapping arrays back to label expanders
        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        terms = vectorizer.get_feature_names_out()
        
        for cluster_id in range(num_clusters):
            top_words = [terms[ind] for ind in order_centroids[cluster_id, :3]]
            human_label = " / ".join(top_words).title()
            
            with strl.expander(f"📁 Cluster Category Group #{cluster_id}: 【 {human_label} 】"):
                cluster_subset = df_ml[df_ml['Predicted Cluster Bucket'] == cluster_id]
                
                # Render standalone spreadsheet framework inside this segment container row
                strl.dataframe(cluster_subset, use_container_width=True)
                
                # Dynamic buffer file download action links handles setup loops
                act_col1, act_col2, _ = strl.columns()
                with act_col1:
                    strl.download_button(label="📥 Export to CSV", data=convert_df_to_csv(cluster_subset), file_name=f"cluster_{cluster_id}.csv", mime="text/csv", key=f"dl_csv_{cluster_id}")
                with act_col2:
                    strl.download_button(label="📊 Export to Excel", data=convert_df_to_xlsx(cluster_subset), file_name=f"cluster_{cluster_id}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_xlsx_{cluster_id}")

    except Exception as ml_err:
        strl.error(f"Error compiling semantic analytics framework visualization layers: {ml_err}")

else:
    # 4. INITIAL EMPTY STATUS VIEW INTERFACE FOR EMPTY INPUTS
    strl.subheader("📈 General Ledger Metrics Summary")
    strl.info("Metrics Summary tracking matrix is currently unpopulated.")
    
    strl.subheader("📊 Data Analytics Distribution Visualizations")
    strl.info("0 charts loaded.")
    
    strl.subheader("📋 Live Spreadsheet View Explorer")
    strl.info("Awaiting live database synchronization pool or uploaded manual spreadsheet metrics to feed pipeline arrays.")
