import re
import base64
import logging
import requests
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from urllib.parse import urlencode

# --- 1. CONFIGURATION CORE CREDENTIALS (STREAMLIT SECRETS) ---
try:
    XERO_CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
    XERO_CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
    XERO_REDIRECT_URI = st.secrets["XERO_REDIRECT_URI"]
except KeyError:
    st.error("⚠️ Missing API configuration variables! Please configure XERO_CLIENT_ID, XERO_CLIENT_SECRET, and XERO_REDIRECT_URI inside your Streamlit Cloud Secrets dashboard panel.")
    st.stop()

XERO_SCOPES = "openid profile email accounting.transactions.read accounting.contacts.read"

# --- 2. SYSTEM INITIALIZATION & LOGGING CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="Gigo Connect — ML Ledger Platform")

# Maintain state tracking properties through application reruns
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "xero_tenant_id" not in st.session_state:
    st.session_state.xero_tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

st.title("📊 Unsupervised Xero ML Bookkeeping & Analytics Engine") 
st.caption("An anti-GIGO system designed to ingest, clean, and cluster unlabeled financial text notifications.") 
# --- 3. XERO OAUTH 2.0 HANDSHAKE PIPELINE GATEWAY ---
if not st.session_state.access_token:
    query_params = st.query_params
    
    if "code" not in query_params:
        st.info("💡 Your application is currently disconnected from Xero.")
        
        params = {
            "response_type": "code",
            "client_id": XERO_CLIENT_ID,
            "redirect_uri": XERO_REDIRECT_URI,
            "scope": XERO_SCOPES,
            "state": "gigo_secure_state"
        }
        auth_url = f"https://xero.com?{urlencode(params)}"
        st.link_button("🔌 Connect Live Xero Demo Company Ledger", auth_url, type="primary")
        st.stop()
    else:
        auth_code = query_params["code"]
        b64_credentials = base64.b64encode(f"{XERO_CLIENT_ID}:{XERO_CLIENT_SECRET}".encode()).decode()
        headers = {"Authorization": f"Basic {b64_credentials}", "Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "authorization_code", "code": auth_code, "redirect_uri": XERO_REDIRECT_URI}
        
        token_response = requests.post("https://xero.com", headers=headers, data=data)
        if token_response.status_code == 200:
            st.session_state.access_token = token_response.json()["access_token"]
            
            # Map Active Tenant ID Organization profile
            t_headers = {"Authorization": f"Bearer {st.session_state.access_token}", "Content-Type": "application/json"}
            conn_res = requests.get("https://xero.com", headers=t_headers)
            
            if conn_res.status_code == 200 and conn_res.json():
                # 🛡️ FIX: Added index [0] to parse the first dict list connection from Xero cleanly
                connections_list = conn_res.json()
                st.session_state.xero_tenant_id = connections_list[0]["tenantId"]
                st.session_state.tenant_name = connections_list[0]["tenantName"]
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Xero authenticated successfully, but could not read organization connection parameters.")
                st.stop()
        else:
            st.error(f"OAuth Exchange Error: {token_response.text}")
            st.stop()

# --- 4. DATA CORE PIPELINE EXTRACTION ROUTINES ---
st.success(f"🔒 Secure Core Pipeline Connection Active. Linked to Ledger: **{st.session_state.tenant_name}**")
if st.button("🔌 Disconnect Ledger / Sign Out"):
    st.session_state.access_token = None
    st.session_state.xero_tenant_id = None
    st.session_state.tenant_name = None
    st.rerun()

api_headers = {
    "Authorization": f"Bearer {st.session_state.access_token}",
    "Xero-tenant-id": st.session_state.xero_tenant_id,
    "Accept": "application/json"
}

with st.spinner("🧠 Syncing live ledger data into Anti-GIGO engine pipelines..."):
    invoice_res = requests.get("https://xero.com", headers=api_headers)

df_master = None
if invoice_res.status_code == 200:
    raw_invoices = invoice_res.json().get("BankTransactions", [])
    
    if raw_invoices:
        data_records = []
        for inv in raw_invoices:
            amount = float(inv.get('Total', 0.0))
            contact_name = inv.get('Contact', {}).get('Name', 'Unknown Customer')
            reconstructed_text_log = f"Trx of AED {amount} at {contact_name}. Status: {inv.get('Status')}."
            data_records.append({
                "Transaction ID": inv.get("BankTransactionID"),
                "SMS": reconstructed_text_log,
                "Raw Amount": amount
            })
        df_master = pd.DataFrame(data_records)
    else:
        st.warning("⚠️ Connected Xero sandbox has no historical records inside.")
else:
    st.error(f"Failed to fetch ledger rows: {invoice_res.text}")

# --- 5. MACHINE LEARNING PROCESSING CALCULATOR ---
def run_unsupervised_accounting_pipeline(df):
    df_out = df.copy()
    df_out['cleaned_sms'] = df_out['SMS'].fillna("").astype(str).str.strip().str.lower()
    
    if len(df_out) >= 3:
        vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=150)
        tfidf_matrix = vectorizer.fit_transform(df_out['cleaned_sms'])
        
        num_clusters = min(4, len(df_out))
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
        df_out['cluster_label_id'] = kmeans.fit_predict(tfidf_matrix)
        
        def infer_category_label(row):
            text = row['cleaned_sms']
            if any(word in text for word in ['credit', 'received', 'deposited']):
                return "Liquidity Inbound Credits"
            elif any(word in text for word in ['withdrawal', 'atm', 'cash debited', 'debited']):
                return "Cash Counter / ATM Withdrawals"
            elif any(word in text for word in ['trx', 'at', 'supermarket', 'cafe', 'order', 'online']):
                return "Merchant Outlays / POS Card Debits"
            elif any(word in text for word in ['created', 'chequebook', 'requested']):
                return "System Admin / Operational Tasks"
            
            cluster_id = row['cluster_label_id']
            fallback_map = {
                0: "Merchant Outlays / POS Card Debits",
                1: "Liquidity Inbound Credits",
                2: "Cash Counter / ATM Withdrawals",
                3: "System Admin / Operational Tasks"
            }
            return fallback_map.get(cluster_id, "Unclassified Operations")

        df_out['assigned_accounting_category'] = df_out.apply(infer_category_label, axis=1)
        df_out['pipeline_status'] = 'CLUSTER_CONFIRMED'
    else:
        df_out['assigned_accounting_category'] = "System Admin / Operational Tasks"
        df_out['pipeline_status'] = 'CLUSTER_CONFIRMED'
        
    return df_out

# --- 6. DATAFRAME PARSING & INTERFACE LAYOUT RENDER ---
if df_master is not None:
    df_final = run_unsupervised_accounting_pipeline(df_master) 
    
    def extract_currency_float(text): 
        match = re.search(r'(?:AED|aed)\s*([\d,]+\.?\d*)', str(text)) 
        return float(match.group(1).replace(',', '')) if match else 0.0 
        
    df_confirmed = df_final[df_final['pipeline_status'] == 'CLUSTER_CONFIRMED'].copy() 
    df_confirmed['parsed_amount'] = df_confirmed['SMS'].apply(extract_currency_float) 
    
    pivot_summary = df_confirmed.groupby('assigned_accounting_category').agg( 
        transaction_count=('pipeline_status', 'count'), 
        total_volume_aed=('parsed_amount', 'sum'), 
        average_ticket_aed=('parsed_amount', 'mean') 
    ).reset_index() 
    
    col1, col2 = st.columns(2) 
    with col1: 
        st.subheader("General Ledger Metrics Summary") 
        formatted_pivot = pivot_summary.copy() 
        formatted_pivot['total_volume_aed'] = formatted_pivot['total_volume_aed'].map('AED {:,.2f}'.format) 
        formatted_pivot['average_ticket_aed'] = formatted_pivot['average_ticket_aed'].map('AED {:,.2f}'.format) 
        st.dataframe(formatted_pivot, use_container_width=True) 
        
        csv_payload = df_final[['Transaction ID', 'SMS', 'assigned_accounting_category', 'pipeline_status']].to_csv(index=False) 
        st.download_button("💾 Download Final Verified Ledger Spreadsheet", data=csv_payload, file_name="verified_general_ledger.csv", mime="text/csv") 
    
    with col2: 
        st.subheader("Data Analytics Distribution Visualizations") 
        plot_df = pivot_summary[pivot_summary['transaction_count'] > 0].sort_values(by='total_volume_aed', ascending=False) 
        
        if not plot_df.empty and plot_df['total_volume_aed'].sum() > 0: 
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5)) 
            ax1.pie(plot_df['total_volume_aed'], labels=plot_df['assigned_accounting_category'], autopct='%1.1f%%', startangle=140, colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']) 
            ax1.set_title("Total Capital Allocation Share (%)", fontweight='bold') 
            ax2.barh(plot_df['assigned_accounting_category'], plot_df['total_volume_aed'], color='#6366f1') 
            ax2.set_title("Total Category Spending Volume (AED)", fontweight='bold') 
            ax2.grid(axis='x', linestyle='--', alpha=0.5) 
            st.pyplot(fig) 
        else: 
            st.warning("No numeric monetary values parsed to plot dashboard distribution metrics.") 
    
    st.subheader("📋 Live Spreadsheet View Explorer") 
    df_final['Transaction ID'] = df_final['Transaction ID'].astype(str).str.split('.').str.get(0).str.strip() 
    
    st.dataframe( 
        df_final[['Transaction ID', 'SMS', 'assigned_accounting_category', 'pipeline_status']], 
        use_container_width=True, 
        column_config={ 
            "Transaction ID": st.column_config.TextColumn( 
                "Transaction ID", 
                help="Pure static text representation blocking browser data-type coercion" 
            ) 
        } 
    )

# --- 7. IMMUTABLE PORTFOLIO ATTR_FOOTER INTERFACES ---
st.markdown("---")
st.markdown(
    "© 2026 T A Srinivas. All Rights Reserved. Prototype for portfolio display. "
    "For commercial licensing requests, please use the contact channels. | [LinkedIn Profile](https://linkedin.com) | [Contact Me](https://google.com)"
)
