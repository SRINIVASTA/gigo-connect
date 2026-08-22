import streamlit as strl
import pandas as pd
import numpy as np
import requests
import base64
import time

# -------------------------------------------------------------------------
# SYSTEM CONFIGURATION & CACHE INIT
# -------------------------------------------------------------------------
strl.set_page_config(page_title="gigo-xero Engine", layout="wide")
strl.title("🛡️ gigo-xero: Live Unsupervised ML Bookkeeping Engine")
strl.caption("Production Data Ingestion Pipeline with Dual-Channel Routing Control")
strl.divider()

# Core Workspace Cache Layers
if "xero_tokens" not in strl.session_state: strl.session_state["xero_tokens"] = None
if "xero_df" not in strl.session_state: strl.session_state["xero_df"] = None
if "uploaded_df" not in strl.session_state: strl.session_state["uploaded_df"] = None

# Credentials Fallbacks
CLIENT_ID = strl.secrets.get("XERO_CLIENT_ID", "YOUR_XERO_CLIENT_ID_HERE")
CLIENT_SECRET = strl.secrets.get("XERO_CLIENT_SECRET", "YOUR_XERO_CLIENT_SECRET_HERE")
REDIRECT_URI = strl.secrets.get("XERO_REDIRECT_URI", "https://streamlit.app")

AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
TENANT_API_URL = "https://xero.com"
INVOICES_API_URL = "https://xero.com"
SCOPES = "openid profile email accounting.transactions accounting.journals offline_access"

# -------------------------------------------------------------------------
# OAUTH HANDSHAKE UTILITIES
# -------------------------------------------------------------------------
def get_auth_link():
    return f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}&prompt=consent&state=gigo_secure_123"

def exchange_code_for_tokens(auth_code):
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "authorization_code", "code": auth_code, "redirect_uri": REDIRECT_URI}
    try:
        res = requests.post(TOKEN_URL, headers=headers, data=data)
        if res.status_code == 200:
            token_data = res.json()
            token_data["expires_at"] = time.time() + token_data.get("expires_in", 1800)
            return token_data
    except Exception: pass
    return None

def get_xero_tenants(access_token):
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    res = requests.get(TENANT_API_URL, headers=headers)
    return res.json() if res.status_code == 200 else []

def fetch_live_xero_data(access_token, tenant_id):
    headers = {"Authorization": f"Bearer {access_token}", "Xero-tenant-id": tenant_id, "Accept": "application/json"}
    res = requests.get(INVOICES_API_URL, headers=headers)
    if res.status_code == 200:
        invoices = res.json().get("Invoices", [])
        rows = []
        for inv in invoices:
            ref_text = inv.get("Reference", "").strip()
            contact_name = inv.get("Contact", {}).get("Name", "Unknown Contact")
            rows.append({
                "Invoice Number": inv.get("InvoiceNumber", "N/A"),
                "Contact Name": contact_name,
                "Clean Description": ref_text if ref_text else f"Transaction payload related to {contact_name}",
                "Total Amount": inv.get("Total", 0.0),
                "Status": inv.get("Status", "UNKNOWN")
            })
        return rows
    return []

# Intercept URL Routing Code from Xero Redirect URI
url_params = strl.query_params
if "code" in url_params and strl.session_state["xero_tokens"] is None:
    tokens = exchange_code_for_tokens(url_params["code"])
    if tokens:
        strl.session_state["xero_tokens"] = tokens
        strl.query_params.clear()
        strl.rerun()

# -------------------------------------------------------------------------
# INTERACTIVE DATA INGESTION MATRIX RADIO CONTROL
# -------------------------------------------------------------------------
st_selection = strl.radio(
    "Select Target Bookkeeping Data Feed:",
    ["Sync Directly with Xero Live API", "Upload Local Bookkeeping Files (CSV / XLSX)"],
    horizontal=True
)

# Variable to anchor data for Block 2 handling pipeline
active_matrix_df = None

if st_selection == "Sync Directly with Xero Live API":
    if strl.session_state["xero_tokens"] is None:
        strl.warning("🔐 Data Ingestion Locked: Authentication with Xero platform is required.")
        strl.link_button("🚀 Secure Connect to Xero API App", get_auth_link())
    else:
        if strl.session_state["xero_df"] is None:
            with strl.spinner("🔄 Ingesting live accounting parameters..."):
                tenants = get_xero_tenants(strl.session_state["xero_tokens"]["access_token"])
                if tenants and len(tenants) > 0:
                    tenant_id = tenants[0]["tenantId"]
                    raw_rows = fetch_live_xero_data(strl.session_state["xero_tokens"]["access_token"], tenant_id)
                    if raw_rows:
                        strl.session_state["xero_df"] = pd.DataFrame(raw_rows)
                        strl.rerun()
        active_matrix_df = strl.session_state["xero_df"]

else:  # Upload Local Files Selection Branch
    uploaded_file = strl.file_uploader("Drop transaction worksheets here", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                parsed_df = pd.read_csv(uploaded_file)
            else:
                parsed_df = pd.read_excel(uploaded_file)
            
            # Map common manual headers to our standardized engine schema format if needed
            if "Clean Description" not in parsed_df.columns:
                if "Description" in parsed_df.columns: parsed_df.rename(columns={"Description": "Clean Description"}, inplace=True)
                elif "Reference" in parsed_df.columns: parsed_df.rename(columns={"Reference": "Clean Description"}, inplace=True)
                else: parsed_df["Clean Description"] = "Manual Data Entry Item"
            
            strl.session_state["uploaded_df"] = parsed_df
        except Exception as e:
            strl.error(f"File reading exception raised: {e}")
            
    active_matrix_df = strl.session_state["uploaded_df"]
# -------------------------------------------------------------------------
# MACHINE LEARNING PIPELINE PROCESSING & EVALUATION BLOCK
# -------------------------------------------------------------------------
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

strl.markdown("---")
strl.subheader("🤖 Unsupervised Clustering Analytics Engine")

# Check if either ingestion track has successfully populated data vectors
if active_matrix_df is not None and not active_matrix_df.empty:
    df_ml = active_matrix_df.copy()
    
    # Render operational matrix view grid
    strl.subheader(f"📈 Raw Transaction Extraction Matrix ({len(df_ml)} rows)")
    strl.dataframe(df_ml, use_container_width=True)
    
    # Clustering Hyperparameter Selector
    num_clusters = strl.slider("Select Target Bookkeeping Clusters (K-Means)", min_value=2, max_value=5, value=3)
    
    # ML Feature Extraction Engine
    with strl.spinner("Running Unsupervised Segmentation Matrix..."):
        try:
            # Transform text description metrics into high-density mathematical vectors
            vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
            X = vectorizer.fit_transform(df_ml['Clean Description'].astype(str))
            
            # Fit Unsupervised Machine Learning Model
            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
            df_ml['Predicted Cluster Bucket'] = kmeans.fit_predict(X)
            
            strl.success(f"🤖 Clustering Complete! Groups assembled based on text similarities.")
            
            # Render Split Categorized Bookkeeping Views
            for cluster_id in range(num_clusters):
                with strl.expander(f"📁 Cluster Category Group #{cluster_id}"):
                    cluster_subset = df_ml[df_ml['Predicted Cluster Bucket'] == cluster_id]
                    strl.dataframe(cluster_subset, use_container_width=True)
                    
        except Exception as ml_err:
            strl.error(f"Error parsing textual metadata structure: {ml_err}. Make sure your dataset contains a valid string text column.")
else:
    strl.info("Awaiting live database synchronization pool or uploaded manual spreadsheet metrics to feed pipeline arrays.")
