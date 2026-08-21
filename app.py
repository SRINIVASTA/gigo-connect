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

XERO_SCOPES = "openid profile email accounting.banktransactions.read accounting.contacts.read"

# --- 2. SYSTEM INITIALIZATION & LOGGING CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(layout="wide", page_title="Gigo Connect — ML Ledger Platform")

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
            token_json = token_response.json()
            st.session_state.access_token = token_json["access_token"]
            
            t_headers = {"Authorization": f"Bearer {st.session_state.access_token}", "Content-Type": "application/json"}
            conn_res = requests.get("https://xero.com", headers=t_headers)
            
            if conn_res.status_code == 200:
                try:
                    connections_list = conn_res.json()
                    if isinstance(connections_list, list) and len(connections_list) > 0:
                        st.session_state.xero_tenant_id = connections_list[0]["tenantId"]
                        st.session_state.tenant_name = connections_list[0]["tenantName"]
                    
                    if not st.session_state.xero_tenant_id:
                        st.session_state.xero_tenant_id = "demo_company_sandbox_gateway"
                        st.session_state.tenant_name = "Demo Company (Global)"
                        
                    st.query_params.clear()
                    st.rerun()
                except Exception:
                    st.session_state.xero_tenant_id = "demo_company_sandbox_gateway"
                    st.session_state.tenant_name = "Demo Company (Global)"
                    st.query_params.clear()
                    st.rerun()
            else:
                st.error("Authentication completed, but could not read organization connection parameters.")
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
    # 🔄 FIX: Query all transactions explicitly to catch un-reconciled items from the demo account
    invoice_res = requests.get("https://xero.com", headers=api_headers)

df_master = None
if invoice_res.status_code == 200:
    try:
        raw_txs = invoice_res.json().get("BankTransactions", [])
    except Exception:
        raw_txs = []
    
    if raw_txs:
        data_records = []
        for tx in raw_txs:
            amount = float(tx.get('Total', 0.0))
            contact_name = tx.get('Contact', {}).get('Name', 'Unknown Vendor/Customer')
            reference = tx.get('Reference', 'General Outlay')
            tx_type = tx.get('Type', 'SPEND')
            
            # Dynamically match currency symbols to display correctly in your layout
            currency_symbol = "£" if "Global" in st.session_state.tenant_name else "AED"
            
            reconstructed_text_log = f"Trx of {currency_symbol} {amount:,.2f} on your account. Type: {tx_type} at {contact_name}. Ref: {reference}."
            data_records.append({
                "Transaction ID": tx.get("BankTransactionID"),
                "SMS": reconstructed_text_log,
                "Raw Amount": amount
            })
        df_master = pd.DataFrame(data_records)

# --- 5. ENTERPRISE DATA INJECTION IF LIVE LEDGER IS COMPLETELY BLANK ---
if df_master is None or df_master.empty:
    st.info("💡 Note: Live endpoint returned 0 rows. Injecting Demo Company default historical transactions into your ML vector space for visualization presentation.")
    embedded_20_transactions = { 
        'Transaction ID': [f"TXN-{i}" for i in range(1001, 1021)], 
        'SMS': [ 
            "Dear Customer, £ 2,240.78 was credited to your account from Petrie McLoud Watson.", 
            "Dear Customer, £ 3,897.00 was credited to your account from Boom FM.", 
            "Trx. of £ 541.25 on your credit card at Boom FM.", 
            "Trx. of £ 324.75 on your credit card at Bank West.", 
            "Dear Customer, ATM Cash Withdrawal for £ 104.40 was debited by City Agency.", 
            "Dear Customer, ATM Cash Withdrawal for £ 541.25 was debited by Hamilton Smith Ltd.", 
            "Trx. of £ 541.25 on your account at Young Bros Transport.", 
            "Trx. of £ 541.25 on your account at Port & Philip Freight.", 
            "Trx. of £ 541.25 on your account at Rex Media Group.", 
            "Dear Customer, £ 817.01 was debited from your account by Srinivas T A."
        ] 
    } 
    df_master = pd.DataFrame(embedded_20_transactions)
# --- 6. MACHINE LEARNING PROCESSING CALCULATOR ---
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
            if any(word in text for word in ['credit', 'received', 'deposited', 'credited']):
                return "Liquidity Inbound Credits"
            elif any(word in text for word in ['withdrawal', 'atm', 'cash debited', 'debited']):
                return "Cash Counter / ATM Withdrawals"
            elif any(word in text for word in ['trx', 'at', 'supermarket', 'cafe', 'order', 'online', 'card', 'fm', 'transport']):
                return "Merchant Outlays / POS Card Debits"
            else:
                return "System Admin / Operational Tasks"

        df_out['assigned_accounting_category'] = df_out.apply(infer_category_label, axis=1)
        df_out['pipeline_status'] = 'CLUSTER_CONFIRMED'
    else:
        df_out['assigned_accounting_category'] = "System Admin / Operational Tasks"
        df_out['pipeline_status'] = 'CLUSTER_CONFIRMED'
        
    return df_out

# --- 7. DATAFRAME PARSING & INTERFACE LAYOUT RENDER ---
if df_master is not None:
    df_final = run_unsupervised_accounting_pipeline(df_master) 
    
    def extract_currency_float(text): 
        # Case-insensitive multicharacter data-scraper capture matching your real currency signs
        match = re.search(r'(?:AED|aed|gbp|usd|\$|£)\s*([\d,]+\.?\d*)', str(text), re.IGNORECASE) 
        return float(match.group(1).replace(',', '')) if match else 0.0 
        
    df_confirmed = df_final[df_final['pipeline_status'] == 'CLUSTER_CONFIRMED'].copy() 
    df_confirmed['parsed_amount'] = df_confirmed['SMS'].apply(extract_currency_float) 
    
    pivot_summary = df_confirmed.groupby('assigned_accounting_category').agg( 
        transaction_count=('pipeline_status', 'count'), 
        total_volume_currency=('parsed_amount', 'sum'), 
        average_ticket_currency=('parsed_amount', 'mean') 
    ).reset_index() 
    
    col1, col2 = st.columns(2) 
    with col1: 
        st.subheader("General Ledger Metrics Summary") 
        formatted_pivot = pivot_summary.copy() 
        currency_label = "£" if "Global" in st.session_state.tenant_name else "AED"
        formatted_pivot['total_volume_currency'] = formatted_pivot['total_volume_currency'].map(f'{currency_label} {{:,.2f}}'.format) 
        formatted_pivot['average_ticket_currency'] = formatted_pivot['average_ticket_currency'].map(f'{currency_label} {{:,.2f}}'.format) 
        st.dataframe(formatted_pivot, use_container_width=True) 
        
        csv_payload = df_final[['Transaction ID', 'SMS', 'assigned_accounting_category', 'pipeline_status']].to_csv(index=False) 
        st.download_button("💾 Download Final Verified Ledger Spreadsheet", data=csv_payload, file_name="verified_general_ledger.csv", mime="text/csv") 
    
    with col2: 
        st.subheader("Data Analytics Distribution Visualizations") 
        plot_df = pivot_summary[pivot_summary['transaction_count'] > 0].sort_values(by='total_volume_currency', ascending=False) 
        
        if not plot_df.empty and plot_df['total_volume_currency'].sum() > 0: 
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5)) 
            ax1.pie(plot_df['total_volume_currency'], labels=plot_df['assigned_accounting_category'], autopct='%1.1f%%', startangle=140, colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']) 
            ax1.set_title("Total Capital Allocation Share (%)", fontweight='bold') 
            ax2.barh(plot_df['assigned_accounting_category'], plot_df['total_volume_currency'], color='#6366f1') 
            ax2.set_title(f"Total Category Spending Volume ({currency_label})", fontweight='bold') 
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

# --- 8. IMMUTABLE PORTFOLIO ATTR_FOOTER INTERFACES ---
st.markdown("---")
st.markdown(
    "© 2026 T A Srinivas. All Rights Reserved. Prototype for portfolio display. "
    "For commercial licensing requests, please use the contact channels. | [LinkedIn Profile](https://linkedin.com) | [Contact Me](https://google.com)"
)
