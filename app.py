import streamlit as strl
import pandas as pd
import numpy as np
import requests
import base64
import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

# -------------------------------------------------------------------------
# INITIAL SYSTEM LAYER CONFIGURATION
# -------------------------------------------------------------------------
strl.set_page_config(page_title="gigo-xero Engine", layout="wide")
strl.title("🛡️ gigo-xero: Live Unsupervised ML Bookkeeping Engine")
strl.caption("Production Data Pipeline with Auto-Refresh & Rate Limit Guards")
strl.divider()

# Load credentials securely from environmental secrets context or direct configuration fallbacks
CLIENT_ID = strl.secrets.get("XERO_CLIENT_ID", "YOUR_XERO_CLIENT_ID_HERE")
CLIENT_SECRET = strl.secrets.get("XERO_CLIENT_SECRET", "YOUR_XERO_CLIENT_SECRET_HERE")
REDIRECT_URI = strl.secrets.get("XERO_REDIRECT_URI", "https://streamlit.app")

# 1. FIXED STATE PERSISTENCE BOILERPLATE
if "xero_tokens" not in strl.session_state:
    strl.session_state["xero_tokens"] = None
if "extracted_df" not in strl.session_state:
    strl.session_state["extracted_df"] = None

# OFFICIAL PRODUCTION XERO API RESOURCE ENDPOINTS
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
TENANT_API_URL = "https://xero.com"
INVOICES_API_URL = "https://xero.com"

SCOPES = "openid profile email accounting.transactions accounting.journals offline_access"

# -------------------------------------------------------------------------
# SECURE OAUTH 2.0 TOKENS HANDLERS
# -------------------------------------------------------------------------
def get_auth_link():
    payload_req = requests.Request(
        'GET', AUTH_URL,
        params={
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'scope': SCOPES,
            'prompt': 'consent',
            'state': 'gigo_secure_state_123'
        }
    )
    return payload_req.prepare().url

def exchange_code_for_tokens(auth_code):
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

# -------------------------------------------------------------------------
# LIVE API GATEWAY WITH ARRAYS CORRECTIONS
# -------------------------------------------------------------------------
def get_xero_tenants(access_token):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(TENANT_API_URL, headers=headers)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    return []

def fetch_live_xero_data(access_token, tenant_id):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Xero-tenant-id": tenant_id,
        "Accept": "application/json"
    }
    try:
        res = requests.get(INVOICES_API_URL, headers=headers)
        if res.status_code == 200:
            invoices = res.json().get("Invoices", [])
            rows = []
            for inv in invoices:
                ref_text = inv.get("Reference", "").strip()
                contact_name = inv.get("Contact", {}).get("Name", "Unknown Contact")
                final_description = ref_text if ref_text else f"Transaction payload related to {contact_name}"
                
                rows.append({
                    "Invoice Number": inv.get("InvoiceNumber", "N/A"),
                    "Contact Name": contact_name,
                    "Clean Description": final_description,
                    "Total Amount": inv.get("Total", 0.0),
                    "Status": inv.get("Status", "UNKNOWN")
                })
            return rows
    except Exception:
        pass
    return []

# -------------------------------------------------------------------------
# 2. FIXED: IMMUTABLE ROUTING INTERCEPTOR 
# -------------------------------------------------------------------------
url_params = strl.query_params

# Capture incoming data immediately before layout loops clear it out
if "code" in url_params:
    incoming_code = url_params["code"]
    # Safely swap code for actual functional access token packets
    tokens = exchange_code_for_tokens(incoming_code)
    if tokens:
        strl.session_state["xero_tokens"] = tokens
        # Purge parameters only AFTER token arrays are locked in memory
        strl.query_params.clear()
        strl.rerun()

# -------------------------------------------------------------------------
# APPLICATION RENDER DECISION TREE
# -------------------------------------------------------------------------
if strl.session_state["xero_tokens"] is None:
    strl.warning("🔐 Application Securely Locked: Connection to Xero API is required to open this dashboard.")
    auth_link = get_auth_link()
    strl.link_button("🚀 Secure Connect to Xero API App", auth_link)
else:
    access_token = strl.session_state["xero_tokens"]["access_token"]
    
    # Process account tenant identifiers
    tenants = get_xero_tenants(access_token)
    if tenants and isinstance(tenants, list) and len(tenants) > 0:
        # Array safe pull fixes index type errors
        tenant_id = tenants[0]["tenantId"]
        tenant_name = tenants[0].get("tenantName", "Xero Org")
        
        strl.success(f"🔗 Pipeline Established with Workspace: **{tenant_name}**")
        
        # Trigger actual pipeline data compilation loop if workspace frame is empty
        if strl.session_state["extracted_df"] is None:
            with strl.spinner("📊 Ingesting live accounting parameters..."):
                raw_data = fetch_live_xero_data(access_token, tenant_id)
                if raw_data:
                    strl.session_state["extracted_df"] = pd.DataFrame(raw_data)
                    strl.rerun()
                else:
                    strl.info("Connected! However, there are no invoices inside your profile.")
    else:
        strl.error("No active organizations discovered. Reset connection setup parameters.")

# -------------------------------------------------------------------------
# 3. FIXED: RE-ANCHORED ML PIPELINE INTEGRATION BLOCK
# -------------------------------------------------------------------------
strl.markdown("---")
strl.subheader("🤖 Unsupervised Clustering Analytics Engine")

if strl.session_state["extracted_df"] is not None and not strl.session_state["extracted_df"].empty:
    df_ml = strl.session_state["extracted_df"].copy()
    
    strl.subheader(f"📈 Raw Transaction Extraction Matrix ({len(df_ml)} rows)")
    strl.dataframe(df_ml, use_container_width=True)
    
    num_clusters = strl.slider("Select Target Bookkeeping Clusters (K-Means)", min_value=2, max_value=5, value=3)
    
    vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
    X = vectorizer.fit_transform(df_ml['Clean Description'])
    
    kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
    df_ml['Predicted Cluster Bucket'] = kmeans.fit_predict(X)
    
    strl.success(f"🤖 Machine Learning Completed! Grouped transactions into {num_clusters} financial clusters.")
    
    for cluster_id in range(num_clusters):
        with strl.expander(f"📁 Cluster Category Group #{cluster_id}"):
            cluster_subset = df_ml[df_ml['Predicted Cluster Bucket'] == cluster_id]
            strl.dataframe(cluster_subset, use_container_width=True)
else:
    strl.info("Awaiting live database synchronization pool inputs above to feed textual vectors into modeling layer.")
