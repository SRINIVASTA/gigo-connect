import streamlit as strl
import pandas as pd
import numpy as np
import requests
import base64
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

# -------------------------------------------------------------------------
# INITIAL SYSTEM CONFIGURATION
# -------------------------------------------------------------------------
strl.set_page_config(page_title="gigo-xero Engine", layout="wide")
strl.title("🛡️ gigo-xero: Live Unsupervised ML Bookkeeping Engine")
strl.caption("Production Data Pipeline with Auto-Refresh & Rate Limit Guards")
strl.divider()

# Load credentials securely from environmental secrets context or direct configuration fallbacks
CLIENT_ID = strl.secrets.get("XERO_CLIENT_ID", "YOUR_XERO_CLIENT_ID_HERE")
CLIENT_SECRET = strl.secrets.get("XERO_CLIENT_SECRET", "YOUR_XERO_CLIENT_SECRET_HERE")
REDIRECT_URI = strl.secrets.get("XERO_REDIRECT_URI", "https://streamlit.app")

if "YOUR_XERO" in [CLIENT_ID, CLIENT_SECRET] or "MISSING" in [CLIENT_ID, CLIENT_SECRET]:
    strl.error("⚠️ Configuration Warning: Please hardcode your explicit Xero Client ID and Client Secret keys directly into the app.py file!")
    strl.stop()

# OFFICIAL PRODUCTION XERO API RESOURCE ENDPOINTS
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
TENANT_API_URL = "https://xero.com"
INVOICES_API_URL = "https://xero.com"

# Scope parameters requested to capture dynamic 60-day background refresh pools
SCOPES = "openid profile email accounting.transactions accounting.journals offline_access"

# -------------------------------------------------------------------------
# SECURE OAUTH 2.0 TOKENS HANDLERS
# -------------------------------------------------------------------------
def get_auth_link():
    """Generates the authorization link, explicitly adding prompt=consent to fix bypassing loops."""
    payload_req = requests.Request(
        'GET', AUTH_URL,
        params={
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'scope': SCOPES,
            'prompt': 'consent',  # Forces organization picker selection view
            'state': 'gigo_secure_state_123'
        }
    )
    return payload_req.prepare().url

def exchange_code_for_tokens(auth_code):
    """Exchanges authorization codes against Xero server token validation pools."""
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
# NETWORK LAYER / BACKOFF PROTECTION GATEWAY
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
    res = make_rate_guarded_request(TENANT_API_URL, headers)
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
            ref_text = inv.get("Reference", "").strip()
            contact_name = inv.get("Contact", {}).get("Name", "Unknown Contact")
            final_description = ref_text if ref_text else f"Transaction payload related to {contact_name}"
            
            rows.append({
                "Transaction ID": inv.get("InvoiceID", ""),
                "Invoice Number": inv.get("InvoiceNumber", "N/A"),
                "Contact Name": contact_name,
                "Clean Description": final_description,
                "Sub Total": inv.get("SubTotal", 0.0),
                "Total Tax": inv.get("TotalTax", 0.0),
                "Total Amount": inv.get("Total", 0.0),
                "Status": inv.get("Status", "UNKNOWN")
            })
        return rows
    return []

# -------------------------------------------------------------------------
# EXECUTION MANAGEMENT & NAVIGATION TRACKER
# -------------------------------------------------------------------------
if "xero_tokens" not in strl.session_state:
    strl.session_state.xero_tokens = None

# Monitor current web query strings for incoming auth signals
url_params = strl.query_params

if "code" in url_params and not strl.session_state.xero_tokens:
    auth_code = url_params["code"]
    with strl.spinner("🔄 Exchanging Active Handshake Credentials..."):
        tokens = exchange_code_for_tokens(auth_code)
        if tokens:
            strl.session_state.xero_tokens = tokens
            strl.query_params.clear()  # Purges parameters from UI path address bar
            strl.rerun()

# Streamlit Render Decision Matrix
if not strl.session_state.xero_tokens:
    strl.warning("🔐 Application Securely Locked: Connection to Xero API is required to open this dashboard.")
    auth_link = get_auth_link()
    strl.link_button("🚀 Secure Connect to Xero API App", auth_link)
else:
    if check_and_ensure_auth():
        access_token = strl.session_state.xero_tokens["access_token"]
        
        tenants = get_xero_tenants(access_token)
        if tenants:
            # Safely capture target connected profile indices
            first_tenant = tenants[0] if isinstance(tenants, list) else tenants
            tenant_id = first_tenant["tenantId"]
            tenant_name = first_tenant.get("tenantName", "Xero Account Organization")
            
            strl.success(f"🔗 Pipeline Established with Workspace: **{tenant_name}**")
            
            with strl.spinner("📊 Ingesting live accounting parameters..."):
                raw_data = fetch_live_xero_data(access_token, tenant_id)
                
                if raw_data:
                    df = pd.DataFrame(raw_data)
                    strl.subheader(f"📈 Transaction Extraction Matrix ({len(df)} rows)")
                    strl.dataframe(df, use_container_width=True)
                    
                    # Store data in session state for the ML extension processing module
                    strl.session_state["extracted_df"] = df
                    strl.info("👉 Ready to run the machine learning modeling logic block below!")
                    
                else:
                    strl.info("Connected successfully! However, there are no invoices available inside this specific organization.")
        else:
            strl.error("No organization attachments found. Try clearing your browser session and logging in again.")
# -------------------------------------------------------------------------
# STANDALONE UNSUPERVISED MACHINE LEARNING PROCESSING MODULE
# -------------------------------------------------------------------------
import streamlit as strl
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

strl.markdown("---")
strl.subheader("🤖 Unsupervised Clustering Analytics Engine")

# Check if data exists from the block above
if "extracted_df" in strl.session_state and not strl.session_state["extracted_df"].empty:
    df_ml = strl.session_state["extracted_df"].copy()
    
    # Parameter Controls
    num_clusters = strl.slider("Select Target Bookkeeping Clusters (K-Means)", min_value=2, max_value=5, value=3)
    
    # Text Processing Matrix
    vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
    X = vectorizer.fit_transform(df_ml['Clean Description'])
    
    # Execute Unsupervised Segmentation Modeling
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    df_ml['Predicted Cluster Bucket'] = kmeans.fit_predict(X)
    
    # Output Display
    strl.success(f"🤖 Machine Learning Clustering Finished! Categorized transactions into {num_clusters} semantic groupings.")
    
    for cluster_id in range(num_clusters):
        with strl.expander(f"📁 Cluster Category Group #{cluster_id}"):
            cluster_subset = df_ml[df_ml['Predicted Cluster Bucket'] == cluster_id]
            strl.dataframe(cluster_subset[['Invoice Number', 'Contact Name', 'Clean Description', 'Total Amount', 'Status']], use_container_width=True)
else:
    strl.info("Awaiting live database synchronization pool inputs above to feed textual vectors into modeling layer.")
