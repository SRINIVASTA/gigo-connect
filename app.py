import streamlit as st
import requests
import pandas as pd
import urllib.parse
import re

# 1. Secure Credentials loaded dynamically from your Streamlit Secrets Panel
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]

# 2. Hardcoded Xero Subdomain Backend Production Endpoints (No Placeholders)
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
TENANT_API_URL = "https://xero.com"
BANK_TRANSACTIONS_API_URL = "https://xero.com"

# Explicit redirect URL character-for-character cloud deployment matching
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"

# 2026 Mandatory Granular Scopes needed to fetch bank transactions safely
SCOPES = "openid profile email app.connections accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero Analytics", layout="wide")
st.title("🔗 Gigo Connect x Xero Intelligent Data Pipeline")

# --- UTILITY: SESSION CACHE FLUSHER ---
if st.sidebar.button("🧼 Reset App Cache State", help="Clears lingering session values"):
    st.session_state.tokens = None
    st.session_state.tenant_id = None
    st.session_state.tenant_name = None
    st.sidebar.toast("Cache Cleared!", icon="🧼")
    st.rerun()

# Establish browser memory states
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

# --- ML SIMULATION MODEL BLOCK (REPLACE WITH YOUR TRAINED WEIGHTS) ---
def unsupervised_ml_classifier(description_text):
    """
    Simulates your Unsupervised ML model clustering logic.
    Analyzes messy description strings and groups them into cluster fields.
    """
    text_clean = str(description_text).lower()
    
    if any(keyword in text_clean for keyword in ["atm", "withdrawal", "cash"]):
        return "ATM Cash Withdrawals"
    elif any(keyword in text_clean for keyword in ["opened", "created", "notification", "assistance"]):
        return "Administrative Notification"
    elif any(keyword in text_clean for keyword in ["credited", "salary", "deposit", "profit"]):
        return "Direct Cash Bank Credits"
    elif any(keyword in text_clean for keyword in ["debited", "transfer", "cheque", "chq"]):
        return "Direct Cash Bank Debits"
    elif any(keyword in text_clean for keyword in ["cafe", "starbucks", "mcdonalds", "zomato", "talabat", "carrefour", "lulu", "spending", "trx"]):
        return "Merchant Vendor Spending"
    else:
        return "Unclassified System Operations"

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
                    st.rerun()
                else:
                    st.error("Authentication passed, but no linked Xero organizations discovered.")
            else:
                st.error(f"Tenant extraction failed: {conn_res.text}")
        else:
            st.error(f"Handshake failed (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        st.error(f"A connection error occurred: {str(e)}")
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
            raw_json = r.json()
            raw_list = raw_json.get("BankTransactions", [])
            
            if not raw_list:
                st.info("No recorded bank transactions discovered inside your selected Xero workspace context.")
            else:
                st.success(f"⚠️ Live Feed Acquired! Analyzing {len(raw_list)} raw ledger items...")
                
                # STEP 1: [JSON Normalization] -> Flatten nested attributes to structural dataframes
                with st.spinner("🧮 [2/4] Normalizing multi-layered JSON matrix..."):
                    df_raw = pd.json_normalize(raw_list)
                
                # Safeguard: Determine if text column maps to Reference, Narratives, or tracking keys
                desc_col = "Reference" if "Reference" in df_raw.columns else "Contact.Name"
                if desc_col not in df_raw.columns:
                    df_raw[desc_col] = "Xero Bank Log Entry Item"
                    
                # STEP 2: [Your ML Model Block] -> Vector text description categorization clustering
                with st.spinner("🧠 [3/4] Running unsupervised ML categorization clustering..."):
                    df_raw["assigned_accounting_category"] = df_raw[desc_col].apply(unsupervised_ml_classifier)
                
                # Coerce data columns into mathematical floating numbers safely
                df_raw["Total"] = pd.to_numeric(df_raw["Total"], errors="coerce").fillna(0.0)
                
                # STEP 3: [Pandas Aggregation] -> Mathematical grouping and counts
                with st.spinner("📊 [4/4] Computing transaction totals and ticketing weights..."):
                    summary_df = df_raw.groupby("assigned_accounting_category").agg(
                        transaction_count=("Total", "count"),
                        total_volume_raw=("Total", "sum"),
                        average_ticket_raw=("Total", "mean")
                    ).reset_index()
                    
                # STEP 4: Map numeric values to clean AED currency format strings
                summary_df["total_volume_aed"] = summary_df["total_volume_raw"].apply(lambda x: f"AED {x:,.2f}")
                summary_df["average_ticket_aed"] = summary_df["average_ticket_raw"].apply(lambda x: f"AED {x:,.2f}")
                
                # Strip out processing matrix helper values and limit columns to match your exact summary
                final_output_table = summary_df[[
                    "assigned_accounting_category", 
                    "transaction_count", 
                    "total_volume_aed", 
                    "average_ticket_aed"
                ]]
                
                # STEP 5: [Streamlit Output] -> Render structured interactive data table on dashboard UI
                st.markdown("### 📊 Automated ML Ingestion Summary Matrix")
                st.dataframe(final_output_table, use_container_width=True)
                st.toast("Intelligent Ingestion Complete!", icon="🔥")
        else:
            st.error(f"Xero API Error Handshake Refused: {r.text}")

# --- WORKSPACE PATH B: OFFLINE PANEL VIEW ---
else:
    st.info("Application Status: Offline. Start your secure Xero connection sequence below.")
    
    # URL-encode parameter mappings to bypass internal Python encoding bugs
    encoded_redirect = urllib.parse.quote(REDIRECT_URI, safe='')
    encoded_scopes = urllib.parse.quote(SCOPES, safe='')
    
    # Clean raw string construction with un-bypassable consent layout enforcement
    auth_redirect_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={encoded_redirect}&scope={encoded_scopes}&state=gigo_manual_stable_loop&prompt=consent"
    
    st.markdown("### Step 1: Copy this link and open it in a private browser tab:")
    st.code(auth_redirect_url, language="text")
    
    st.markdown("---")
    st.subheader("🛠️ Connection Link Dashboard")
    st.caption("Paste the resulting link text string from your address bar right back here:")
    
    manual_input = st.text_input("Paste full address bar URL here:", placeholder="https://streamlit.app...")
    
    if st.button("⚡ 2. Finalize Connection", use_container_width=True):
        if manual_input:
            if "code=" in manual_input:
                try:
                    parsed_url = urllib.parse.urlparse(manual_input)
                    url_parameters = urllib.parse.parse_qs(parsed_url.query)
                    extracted_token = url_parameters["code"][0]
                    exchange_code_for_tokens(extracted_token)
                except Exception as parse_err:
                    st.error(f"Could not parse URL text string: {str(parse_err)}")
            else:
                exchange_code_for_tokens(manual_input)
        else:
            st.error("Please provide a valid code token or landing link address string.")
