import streamlit as strl
import pandas as pd
import numpy as np
import requests
import re
import base64
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt

# -------------------------------------------------------------------------
# SETUP & CONFIGURATION
# -------------------------------------------------------------------------
strl.set_page_config(page_title="gigo-xero Engine", layout="wide")
strl.title("🛡️ gigo-xero: Live Unsupervised ML Bookkeeping Engine")
strl.caption("Production Data Pipeline with Auto-Refresh & Rate Limit Guards")
strl.divider()

# Load credentials securely from environmental secrets context
CLIENT_ID = strl.secrets.get("XERO_CLIENT_ID", "MISSING_CLIENT_ID")
CLIENT_SECRET = strl.secrets.get("XERO_CLIENT_SECRET", "MISSING_CLIENT_SECRET")
REDIRECT_URI = strl.secrets.get("XERO_REDIRECT_URI", "MISSING_REDIRECT_URI")

if "MISSING" in [CLIENT_ID, CLIENT_SECRET, REDIRECT_URI]:
    strl.error("⚠️ Configuration Error: One or more Xero API credentials are missing from Streamlit Secrets!")
    strl.stop()

# Xero API Authorization Endpoints
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
INVOICES_API_URL = "https://xero.com"

# Added 'offline_access' scope to request refresh tokens that last for 60 days
SCOPES = "openid profile email accounting.transactions accounting.journals offline_access"

# -------------------------------------------------------------------------
# OAUTH 2.0 FLOW & LIVE REFRESH HANDLERS
# -------------------------------------------------------------------------
def get_auth_link():
    """Generates the authorization gateway entry point link."""
    payload_req = requests.Request(
        'GET', AUTH_URL,
        params={
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'scope': SCOPES,
            'state': 'gigo_secure_state_123'
        }
    )
    return payload_req.prepare().url

def exchange_code_for_tokens(auth_code):
    """Exchanges initial authorization codes against Xero server token validation pools."""
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI
    }
    try:
        res = requests.post(TOKEN_URL, headers=headers, data=data)
        if res.status_code == 200:
            token_data = res.json()
            token_data["expires_at"] = time.time() + token_data.get("expires_in", 1800)
            return token_data
    except Exception:
        pass
    return None

def refresh_xero_token():
    """Uses the offline_access refresh token to update an expired session automatically."""
    if "xero_tokens" not in strl.session_state or not strl.session_state.xero_tokens:
        return False
    
    refresh_token = strl.session_state.xero_tokens.get("refresh_token")
    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    try:
        res = requests.post(TOKEN_URL, headers=headers, data=data)
        if res.status_code == 200:
            token_data = res.json()
            token_data["expires_at"] = time.time() + token_data.get("expires_in", 1800)
            strl.session_state.xero_tokens = token_data
            return True
    except Exception:
        pass
    return False

def check_and_ensure_auth():
    """Pre-flight check to verify token health before making any live API requests."""
    tokens = strl.session_state.get("xero_tokens")
    if not tokens:
        return False
    if time.time() > (tokens.get("expires_at", 0) - 60):
        return refresh_xero_token()
    return True

# -------------------------------------------------------------------------
# LIVE API GATEWAY WITH RATE LIMIT PROTECTION GUARDS
# -------------------------------------------------------------------------
def make_rate_guarded_request(url, headers, method="GET", max_retries=3):
    """Executes an API call. If a 429 Rate Limit error occurs, it pauses and retries."""
    for attempt in range(max_retries):
        try:
            if method == "GET":
                res = requests.get(url, headers=headers)
            
            if res.status_code == 429:
                retry_after = int(res.headers.get("Retry-After", 5))
                strl.warning(f"⚠️ Xero API Rate Limit hit. Pausing engine for {retry_after}s before retrying...")
                time.sleep(retry_after)
                continue
                
            return res
        except Exception as e:
            if attempt == max_retries - 1:
                strl.error(f"API Execution Network Failure: {e}")
    return None

def get_xero_tenants(access_token):
    """Fetches connected tenant instances to isolate your Demo Company."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    res = make_rate_guarded_request("https://xero.com", headers)
    return res.json() if res and res.status_code == 200 else []

def fetch_live_xero_data(access_token, tenant_id):
    """Streams data shapes out of Xero to build your parsing matrices."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Xero-tenant-id": tenant_id,
        "Accept": "application/json"
    }
    res = make_rate_guarded_request(INVOICES_API_URL, headers)
    if res and res.status_code == 200:
        invoices = res.json().get("Invoices", [])
        rows = []
        for inv in invoices:
            rows.append({
                "Transaction ID": inv.get("InvoiceID", f"INV-{inv.get('InvoiceNumber')}"),
                "Raw Description": inv.get("Reference", "") if inv.get("Reference") else f"Invoice to {inv.get('Contact', {}).get('Name', 'Unknown Contact')}",
                "Amount String": f"USD {inv.get('Total', 0.0)}"
            })
        return rows
    return []

# -------------------------------------------------------------------------
# ANOMALY VARIANCE ROWS FOR PIPELINE TESTING
# -------------------------------------------------------------------------
GIGO_ROWS = [
    {"Transaction ID": "", "Raw Description": None, "Amount String": "NaN"},
    {"Transaction ID": "TXN-ERR99", "Raw Description": "SYSTEM ERROR: FAILED TO PARSE INNER JSON NODE", "Amount String": "ERROR_CODE_505"},
    {"Transaction ID": "   ", "Raw Description": "      ", "Amount String": "     "}
]

# -------------------------------------------------------------------------
# INTERACTIVE TERMINAL ENGINE UI (FIXED VIA UNBLOCKABLE NEW-TAB ROUTING)
# -------------------------------------------------------------------------
strl.sidebar.header("🔑 Xero Live Auth Gateway")

if "xero_tokens" not in strl.session_state:
    strl.session_state.xero_tokens = None

try:
    query_params = strl.query_params
    if "code" in query_params:
        incoming_code = query_params["code"]
        with strl.spinner("Verifying secure token exchange with Xero..."):
            tokens = exchange_code_for_tokens(incoming_code)
            if tokens:
                strl.session_state.xero_tokens = tokens
                strl.sidebar.success("Session Verified!")
            else:
                strl.sidebar.error("Token verification handshake failed.")
except Exception:
    pass

if not strl.session_state.xero_tokens:
    strl.warning("🔐 **Application Securely Locked**: Connection to Xero API is required to open this dashboard.")
    
    # CRITICAL FIX: Standard HTML anchor element forced to target a fresh un-sandboxed tab (_blank)
    # This prevents the secure browser layer from timing out or dropping click signals.
    strl.markdown(
        f'<div style="text-align: center; margin-top: 15px; margin-bottom: 15px;">'
        f'<a href="{get_auth_link()}" target="_blank" style="text-decoration: none;">'
        f'<div style="background-color: #1363DF; color: white; padding: 14px 28px; '
        f'text-align: center; border-radius: 6px; font-weight: bold; '
        f'font-size: 16px; border: none; box-shadow: 0px 4px 10px rgba(0,0,0,0.15); display: inline-block;">'
        f'🚀 Secure Connect to Xero API App'
        f'</div></a></div>', 
        unsafe_allow_html=True
    )
    strl.stop()
else:
    if check_and_ensure_auth():
        strl.sidebar.success("📡 Stream Connection Active")
        rem_time = int(strl.session_state.xero_tokens["expires_at"] - time.time())
        strl.sidebar.caption(f"Token Auto-Refresh Pool: Active ({rem_time}s remaining)")
    else:
        strl.sidebar.error("🔄 Session expired. Re-authentication required.")
        strl.session_state.xero_tokens = None
        strl.stop()

    if strl.sidebar.button("🔌 Disconnect Session"):
        strl.session_state.xero_tokens = None
        strl.query_params.clear()
        strl.rerun()

# -------------------------------------------------------------------------
# STREAM DATASETS & COMPILING MACHINE LEARNING LOOPS
# -------------------------------------------------------------------------
access_token = strl.session_state.xero_tokens.get("access_token")
tenants = get_xero_tenants(access_token)
working_df = None

if tenants:
    strl.subheader("🗂️ Active Tenant Dropdown Grid Selector")
    tenant_options = {t.get("tenantName"): t.get("tenantId") for t in tenants}
    selected_tenant_name = strl.selectbox("Select Target Xero Organization Instance:", list(tenant_options.keys()))
    target_tenant_id = tenant_options[selected_tenant_name]
    
    with strl.spinner(f"Extracting live matrix nodes from {selected_tenant_name}..."):
        raw_xero_rows = fetch_live_xero_data(access_token, target_tenant_id)
        if raw_xero_rows:
            working_df = pd.concat([pd.DataFrame(raw_xero_rows), pd.DataFrame(GIGO_ROWS)], ignore_index=True)
        else:
            strl.error("⚠️ Stream Error: No active records returned from this business entity ledger.")
            strl.stop()
else:
    strl.error("❌ Profile Error: No organizations or active sandbox accounts found linked to this profile.")
    strl.stop()

if working_df is not None:
    strl.subheader("👀 Raw Ingested Input Snapshot (Live API Stream + Corrupted Variance Rows)")
    strl.dataframe(working_df, use_container_width=True)
    
    # Layer 1: Anti-GIGO Filtration Pipeline
    strl.markdown("### 🛡️ Layer 1: Anti-GIGO Filtration Pipeline")
    initial_count = len(working_df)
    working_df = working_df.dropna(subset=["Raw Description", "Transaction ID"])
    working_df = working_df[
        (working_df["Raw Description"].astype(str).str.strip() != "") & 
        (working_df["Transaction ID"].astype(str).str.strip() != "") & 
        (~working_df["Raw Description"].astype(str).str.contains("SYSTEM ERROR|FAILED TO PARSE", case=False, na=False))
    ]
    strl.warning(f"Anti-GIGO Layer executed: dropped **{initial_count - len(working_df)}** trailing, corrupt or unparseable system nodes.")
    
    if len(working_df) > 0:
        # Layer 2: Regex Currency Extractor
        strl.markdown("### 🔍 Layer 2: Regex Currency Extraction Matrix")
        def extract_monetary_float(text):
            if not isinstance(text, str): text = str(text) if text is not None else ""
            match = re.search(r'[-+]?\d*\.\d+|\d+', text)
            return float(match.group()) if match else 0.0

        working_df["Cleaned Amount"] = working_df["Amount String"].apply(extract_monetary_float)

        # Layer 3: Unsupervised Clustering
        strl.markdown("### 🤖 Layer 3: Unsupervised Text Clustering (TF-IDF Bigrams)")
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(working_df["Raw Description"].astype(str))
        num_clusters = min(5, len(working_df))
        kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init="auto")
        working_df["Cluster ID"] = kmeans.fit_predict(tfidf_matrix)
        
        # Layer 4: Deterministic Post-Cluster Rules Correction Engine
        strl.markdown("### ⚙️ Layer 4: Post-Cluster Rules Correction Engine")
        def deterministic_correction(row):
            desc = str(row["Raw Description"]).upper()
            current_cluster = row["Cluster ID"]
            if any(tok in desc for tok in ["ATM", "CASH", "WITHDRAWAL"]): return "ATM Cash Management"
            if any(tok in desc for tok in ["AWS", "AZURE", "MICROSOFT", "GOOGLE", "GITHUB", "DIGITALOCEAN"]): return "SaaS & Cloud Infrastructure"
            if any(tok in desc for tok in ["MCDONALDS", "STARBUCKS", "SUBWAY", "BURGER"]): return "Merchant Vendor (Food/Dining)"
            return f"Cluster Group {current_cluster} (General Operational)"

        working_df["Final Audited Ledger Category"] = working_df.apply(deterministic_correction, axis=1)
        strl.dataframe(working_df[["Transaction ID", "Raw Description", "Amount String", "Cleaned Amount", "Cluster ID", "Final Audited Ledger Category"]], use_container_width=True)
        
        # Layer 5: Accounting Audit Analytics & Visualizations
        strl.divider()
        strl.subheader("📊 Layer 5: Accounting Audit Analytics & Financial Visualization Plots")
        col1, col2 = strl.columns()
        with col1:
            strl.markdown("**Ledger Spend Category Pivot Summary Table**")
            pivot_table = working_df.groupby("Final Audited Ledger Category").agg(
                Transaction_Count=("Transaction ID", "count"),
                Total_Volume_Processed=("Cleaned Amount", "sum")
            ).reset_index()
            strl.dataframe(pivot_table, use_container_width=True)
        with col2:
            strl.markdown("**Aggregated Ledger Category Volume Weights**")
            fig, ax = plt.subplots(figsize=(6, 3.5))
            working_df.groupby("Final Audited Ledger Category")["Cleaned Amount"].sum().plot(kind="barh", ax=ax, color="#1363DF", edgecolor="black")
            ax.set_xlabel("Processed Value Amount")
            ax.set_ylabel("")
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            plt.tight_layout()
            strl.pyplot(fig)
    else:
        strl.info("All records isolated by Anti-GIGO layers. No clean data shapes remaining.")
