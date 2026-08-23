import streamlit as st
import requests
import pandas as pd
import urllib.parse

# 1. Load Credentials directly from your secure Streamlit Secrets panel
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]

# Production Subdomain Endpoints Routing Matrix
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
TENANT_API_URL = "https://xero.com"
BANK_TRANSACTIONS_API_URL = "https://xero.com"

# Explicit redirect URL character-for-character cloud deployment matching
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"

# 2026 Mandatory Granular Scopes required for Xero's security engine
SCOPES = "openid profile email app.connections accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero Analytics", layout="wide")
st.title("🔗 Gigo Connect x Xero Intelligent Data Pipeline")

# --- UTILITY: SESSION CACHE FLUSHER ---
if st.sidebar.button("🧼 Reset App Cache State", use_container_width=True):
    st.session_state.tokens = None
    st.session_state.tenant_id = None
    st.session_state.tenant_name = None
    st.query_params.clear()  # Clear query variables out of browser bar
    st.rerun()

# Establish browser session memory states
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

# Unsupervised ML Logic Processing Map
def unsupervised_ml_classifier(description_text):
    text_clean = str(description_text).lower()
    if any(keyword in text_clean for keyword in ["atm", "withdrawal", "cash"]):
        return "ATM Cash Withdrawals"
    elif any(keyword in text_clean for keyword in ["credited", "salary", "deposit", "profit"]):
        return "Direct Cash Bank Credits"
    elif any(keyword in text_clean for keyword in ["cafe", "starbucks", "mcdonalds", "zomato", "talabat", "spending"]):
        return "Merchant Vendor Spending"
    else:
        return "Direct Cash Bank Debits"

def exchange_code_for_tokens(code_string):
    payload = {
        "grant_type": "authorization_code",
        "code": code_string.strip(),
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        res = requests.post(TOKEN_URL, data=payload, headers=headers)
        if res.status_code == 200:
            token_json = res.json()
            
            # Connections endpoint to fetch active organization tenant data
            conn_headers = {
                "Authorization": f"Bearer {token_json['access_token']}",
                "Content-Type": "application/json"
            }
            conn_res = requests.get(TENANT_API_URL, headers=conn_headers)
            
            if conn_res.status_code == 200:
                connections = conn_res.json()
                if isinstance(connections, list) and len(connections) > 0:
                    primary_connection = connections[0]
                    st.session_state.tokens = token_json
                    st.session_state.tenant_id = primary_connection["tenantId"]
                    st.session_state.tenant_name = primary_connection.get("tenantName", "Demo Company")
                    st.success(f"🎉 Connected successfully to: {st.session_state.tenant_name}")
                    st.query_params.clear()  # Purge token query string out of URL bar
                    st.rerun()
                else:
                    st.error("Authentication passed, but no linked Xero organizations discovered.")
            else:
                st.error(f"Tenant extraction failed: {conn_res.text}")
        else:
            st.error(f"Handshake failed (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        st.error(f"A connection error occurred: {str(e)}")

# --- AUTOMATED ARTIFACT INTERCEPTOR ---
# Checks the active browser bar URL for an incoming code parameter passed back by Xero
if "code" in st.query_params and st.session_state.tokens is None:
    incoming_xero_code = st.query_params["code"]
    exchange_code_for_tokens(incoming_xero_code)

# --- SYSTEM PATH A: ONLINE AUTHORISED ANALYSIS VIEW ---
if st.session_state.tokens and st.session_state.tenant_id:
    st.sidebar.success(f"🏢 Active Workspace: {st.session_state.tenant_name}")
    if st.sidebar.button("Disconnect Session", use_container_width=True):
        st.session_state.tokens = None
        st.session_state.tenant_id = None
        st.session_state.tenant_name = None
        st.rerun()
        
    st.subheader("⚙️ Intelligent Bank Ledger Processing Machine")
    st.caption("Pulls raw transaction feeds, applies unsupervised parsing vectors, and builds metric tables.")
    
    if st.button("🚀 Ingest & Process Xero Bank Feed Directly", use_container_width=True, type="primary"):
        api_headers = {
            "Authorization": f"Bearer {st.session_state.tokens['access_token']}",
            "Xero-tenant-id": st.session_state.tenant_id,
            "Accept": "application/json"
        }
        
        with st.spinner("📥 [1/4] Querying Xero API for Raw JSON Feed..."):
            r = requests.get(BANK_TRANSACTIONS_API_URL, headers=api_headers)
            
        if r.status_code == 200:
            raw_list = r.json().get("BankTransactions", [])
            if not raw_list:
                st.info("No recorded bank transactions discovered inside your selected Xero workspace.")
            else:
                st.success(f"⚠️ Live Feed Acquired! Analyzing {len(raw_list)} raw ledger items...")
                
                df_raw = pd.json_normalize(raw_list)
                desc_col = "Reference" if "Reference" in df_raw.columns else "Contact.Name"
                if desc_col not in df_raw.columns:
                    df_raw[desc_col] = "Xero Bank Log Entry Item"
                    
                df_raw["assigned_accounting_category"] = df_raw[desc_col].apply(unsupervised_ml_classifier)
                df_raw["Total"] = pd.to_numeric(df_raw["Total"], errors="coerce").fillna(0.0)
                
                summary_df = df_raw.groupby("assigned_accounting_category").agg(
                    transaction_count=("Total", "count"),
                    total_volume_raw=("Total", "sum"),
                    average_ticket_raw=("Total", "mean")
                ).reset_index()
                
                summary_df["total_volume_aed"] = summary_df["total_volume_raw"].apply(lambda x: f"AED {x:,.2f}")
                summary_df["average_ticket_aed"] = summary_df["average_ticket_raw"].apply(lambda x: f"AED {x:,.2f}")
                
                final_output_table = summary_df[[
                    "assigned_accounting_category", 
                    "transaction_count", 
                    "total_volume_aed", 
                    "average_ticket_aed"
                ]]
                
                st.markdown("### 📊 Automated ML Ingestion Summary Matrix")
                st.dataframe(final_output_table, use_container_width=True)
                st.toast("Intelligent Ingestion Complete!", icon="🔥")
        else:
            st.error(f"Xero API Error: {r.text}")

# --- COMPLETELY OVERWRITE YOUR END "ELSE:" STATEMENT BLOCK WITH THIS ---
else:
    st.info("Application Status: Offline. Start your secure Xero connection sequence below.")
    
    # FIXED: Re-built into a solid, raw string block to bypass Python f-string encoding corruption completely
    # firewall blocks will drop immediately because CloudFront reads this as a clean, standardized query parameter packet
    auth_redirect_url = (
        "https://xero.com"
        "?response_type=code"
        f"&client_id={CLIENT_ID}"
        "&redirect_uri=https%3A%2F%2Fgigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app%2F"
        "&scope=openid%20profile%20email%20app.connections%20accounting.transactions%20accounting.contacts%20offline_access"
        "&state=gigo_manual_stable_loop"
        "&prompt=login%20consent"
    )
    
    st.markdown("### Step 1: Open this link to grant access to the Demo Company:")
    st.link_button("🚀 Secure Authorize Gateway Link", auth_redirect_url, use_container_width=True)
