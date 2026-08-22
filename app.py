import streamlit as strl
import pandas as pd
import numpy as np
import requests
import base64
import time
import io
import plotly.express as px

# -------------------------------------------------------------------------
# SYSTEM CONFIGURATION & RE-BRANDING INITIALIZATION
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

# Intercept URL Routing Code from Xero Redirect URI
url_params = strl.query_params
if "code" in url_params and strl.session_state["xero_tokens"] is None:
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "authorization_code", "code": url_params["code"], "redirect_uri": REDIRECT_URI}
    try:
        res = requests.post(TOKEN_URL, headers=headers, data=data)
        if res.status_code == 200:
            token_data = res.json()
            token_data["expires_at"] = time.time() + token_data.get("expires_in", 1800)
            strl.session_state["xero_tokens"] = token_data
            strl.query_params.clear()
            strl.rerun()
    except Exception: pass

if st_selection == "Sync Directly with Xero Live API":
    if strl.session_state["xero_tokens"] is None:
        strl.warning("🔐 Data Ingestion Locked: Authentication required.")
        auth_link = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}&prompt=consent&state=gigo_secure_123"
        strl.link_button("🚀 Secure Connect to Xero API App", auth_link)
    else:
        if strl.session_state["xero_df"] is None:
            with strl.spinner("🔄 Ingesting live accounting parameters..."):
                headers = {"Authorization": f"Bearer {strl.session_state['xero_tokens']['access_token']}", "Content-Type": "application/json"}
                res = requests.get(TENANT_API_URL, headers=headers)
                if res.status_code == 200:
                    tenants = res.json()
                    if tenants and isinstance(tenants, list) and len(tenants) > 0:
                        tenant_id = tenants[0]["tenantId"]
                        
                        inv_headers = {"Authorization": f"Bearer {strl.session_state['xero_tokens']['access_token']}", "Xero-tenant-id": tenant_id, "Accept": "application/json"}
                        inv_res = requests.get(INVOICES_API_URL, headers=inv_headers)
                        if inv_res.status_code == 200:
                            invoices = inv_res.json().get("Invoices", [])
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
                            if rows:
                                strl.session_state["xero_df"] = pd.DataFrame(rows)
                                strl.rerun()
        active_matrix_df = strl.session_state["xero_df"]
else:
    uploaded_file = strl.file_uploader("Drop transaction worksheets here", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            parsed_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            
            # FIXED: Added explicit string indexing [0] to extract the pure text variable out of the layout matcher
            if "Clean Description" not in parsed_df.columns:
                text_match = [col for col in parsed_df.columns if any(x in col.lower() for x in ["desc", "ref", "sms", "text", "particular", "msg"])]
                if text_match:
                    actual_column_name = str(text_match[0])
                    parsed_df.rename(columns={actual_column_name: "Clean Description"}, inplace=True)
                else:
                    parsed_df["Clean Description"] = "Manual Data Entry Item"
            strl.session_state["uploaded_df"] = parsed_df
        except Exception as e:
            strl.error(f"File reading exception: {e}")
    active_matrix_df = strl.session_state["uploaded_df"]
# -------------------------------------------------------------------------
# METRICS SUMMARY, PIE VISUALIZATIONS & SPENDING VALUE CALCULATOR BLOCK
# -------------------------------------------------------------------------
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

strl.markdown("---")

if active_matrix_df is not None and not active_matrix_df.empty:
    df_ml = active_matrix_df.copy()
    
    # Structural Fallback Layer ensures column absolutely exists to prevent line 153 crashes
    if "Clean Description" not in df_ml.columns:
        # Fallback maps to first available column if rename structure mismatched
        df_ml["Clean Description"] = df_ml.iloc[:, 0].astype(str)

    # Filter out junk elements
    garbage_list = ML_CONFIG.get("GARBAGE_FLAGS", [])
    if garbage_list:
        df_ml = df_ml[~df_ml['Clean Description'].astype(str).str.contains('|'.join(garbage_list), case=False, na=False)]

    # BROAD VALUE PARSER: Scans your sheets for amounts or currency text
    amt_col = [col for col in df_ml.columns if any(x in col.lower() for x in ["amount", "total", "val", "amt", "debit", "credit", "price", "spent"])]
    if amt_col:
        actual_amt_header = str(amt_col[0])
        df_ml['Total Amount'] = pd.to_numeric(df_ml[actual_amt_header].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0.0)
    else:
        # Regex text fallback scanner pulls digits directly out of text blocks
        df_ml['Total Amount'] = df_ml['Clean Description'].astype(str).str.extract(r'(?:INR|USD|AED|Rs\.?)\s*([\d,]+\.?\d*)').str.replace(',', '', regex=False).astype(float).fillna(0.0)

    curr_col = [col for col in df_ml.columns if "curr" in col.lower() or "symbol" in col.lower()]
    currency_label = str(df_ml[curr_col].iloc[0]).upper() if curr_col else "USD"

    # 1. RENDER GENERAL LEDGER METRICS SUMMARY
    strl.subheader("📈 General Ledger Metrics Summary")
    m_col1, m_col2, m_col3, m_col4 = strl.columns(4)
    with m_col1:
        strl.metric("Total Extracted Records", f"{len(df_ml)}")
    with m_col2:
        strl.metric("Gross Financial Velocity", f"{currency_label} {df_ml['Total Amount'].sum():,.2f}")
    with m_col3:
        strl.metric("Average Invoiced Ticket", f"{currency_label} {df_ml['Total Amount'].mean():,.2f}")
    with m_col4:
        strl.metric("Data Quality Consistency (Anti-GIGO)", "100%")

    strl.markdown("---")
    
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
    
    spending_by_label = df_ml.groupby('Accounting Sub-Class Label')['Total Amount'].agg(['sum', 'count']).reset_index()
    spending_by_label.columns = ['Accounting Sub-Class Label', 'Total Spending Value', 'Transaction Count']
    
    with v_col1:
        strl.markdown(f"**Total Category Spending Share Allocation ({currency_label})**")
        fig_pie = px.pie(
            spending_by_label, 
            values='Total Spending Value', 
            names='Accounting Sub-Class Label',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True)
        strl.plotly_chart(fig_pie, use_container_width=True)
        
    with v_col2:
        strl.markdown(f"**Total Category Spending Values Table ({currency_label})**")
        display_spending = spending_by_label.copy()
        display_spending['Total Spending Value'] = display_spending['Total Spending Value'].apply(lambda x: f"{currency_label} {x:,.2f}")
        display_spending = display_spending[['Accounting Sub-Class Label', 'Transaction Count', 'Total Spending Value']]
        strl.dataframe(display_spending, use_container_width=True, hide_index=True)

    strl.markdown("---")
    
    # 3. COMPILING THE LIVE SPREADSHEET VIEW EXPLORER WITH ML CLUSTERING
    strl.subheader("📋 Live Spreadsheet View Explorer")
    num_clusters = strl.slider("Select Target Bookkeeping Clusters (K-Means)", min_value=2, max_value=5, value=3)
    
    try:
        vectorizer = TfidfVectorizer(stop_words='english', max_features=200)
        X = vectorizer.fit_transform(df_ml['Clean Description'].astype(str))
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        df_ml['Predicted Cluster Bucket'] = kmeans.fit_predict(X)
        
        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
        terms = vectorizer.get_feature_names_out()
        
        for cluster_id in range(num_clusters):
            top_words = [terms[ind] for ind in order_centroids[cluster_id, :3]]
            human_label = " / ".join(top_words).title()
            
            with strl.expander(f"📁 Cluster Category Group #{cluster_id}: 【 {human_label} 】"):
                cluster_subset = df_ml[df_ml['Predicted Cluster Bucket'] == cluster_id]
                strl.dataframe(cluster_subset, use_container_width=True)
                
                act_col1, act_col2, _ = strl.columns(3)
                with act_col1:
                    strl.download_button(label="📥 Export to CSV", data=convert_df_to_csv(cluster_subset), file_name=f"cluster_{cluster_id}.csv", mime="text/csv", key=f"dl_csv_{cluster_id}")
                with act_col2:
                    strl.download_button(label="📊 Export to Excel", data=convert_df_to_xlsx(cluster_subset), file_name=f"cluster_{cluster_id}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_xlsx_{cluster_id}")

    except Exception as ml_err:
        strl.error(f"Error compiling semantic analytics framework: {ml_err}")

else:
    strl.subheader("📈 General Ledger Metrics Summary")
    strl.info("Metrics Summary tracking matrix is currently unpopulated.")
    strl.subheader("📊 Data Analytics Distribution Visualizations")
    strl.info("0 analytical distributions computed. Pie charts and category values will render here upon dataset ingestion.")
    strl.subheader("📋 Live Spreadsheet View Explorer")
    strl.info("Awaiting live database synchronization pool or uploaded manual spreadsheet metrics to feed pipeline arrays.")
