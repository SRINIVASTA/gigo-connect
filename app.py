import streamlit as strl
import requests
import pandas as pd
import urllib.parse

# 1. Fetch live production credentials from your secure Streamlit Secrets panel
CLIENT_ID = strl.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = strl.secrets["XERO_CLIENT_SECRET"]

# Production Subdomain Endpoints Mapping 
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
TENANT_API_URL = "https://xero.com"

# Absolute matching production string matching your deployment site domain
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"

# 2026 Mandatory Granular Scopes required for Xero's security engine
SCOPES = "openid profile email app.connections accounting.contacts accounting.invoices offline_access"

strl.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
strl.title("🔗 Gigo Connect x Xero Integration")

# --- UTILITY: DEV MODE CLEAR UTILITY ---
if strl.sidebar.button("🧼 Reset Cached State", help="Clears lingering session values"):
    strl.session_state.tokens = None
    strl.session_state.tenant_id = None
    strl.session_state.tenant_name = None
    strl.rerun()

# Establish resilient memory caches inside the running browser session state
if "tokens" not in strl.session_state:
    strl.session_state.tokens = None
if "tenant_id" not in strl.session_state:
    strl.session_state.tenant_id = None
if "tenant_name" not in strl.session_state:
    strl.session_state.tenant_name = None

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
                    strl.session_state.tokens = token_json
                    strl.session_state.tenant_id = primary_connection["tenantId"]
                    strl.session_state.tenant_name = primary_connection.get("tenantName", "Demo Company")
                    strl.success(f"🎉 Connected successfully to: {strl.session_state.tenant_name}")
                    strl.rerun()
                else:
                    strl.error("Authentication passed, but no linked Xero organizations were discovered.")
            else:
                strl.error(f"Tenant extraction failed: {conn_res.text}")
        else:
            st_text = res.text if hasattr(res, 'text') else str(res)
            strl.error(f"Handshake failed (HTTP {res.status_code}): {st_text}")
    except Exception as e:
        strl.error(f"A connection error occurred: {str(e)}")

# --- WORKSPACE PATH A: DASHBOARD SECURE DATA VIEW ---
if strl.session_state.tokens and strl.session_state.tenant_id:
    strl.sidebar.success(f"🏢 Connected Profile: {strl.session_state.tenant_name}")
    if strl.sidebar.button("Disconnect Session", use_container_width=True):
        strl.session_state.tokens = None
        strl.session_state.tenant_id = None
        strl.session_state.tenant_name = None
        strl.rerun()
        
    tab1, tab2 = strl.tabs(["📋 Invoices Ledger", "👥 Contact Profiles"])
    api_headers = {
        "Authorization": f"Bearer {strl.session_state.tokens['access_token']}",
        "Xero-tenant-id": strl.session_state.tenant_id,
        "Accept": "application/json"
    }
    
    with tab1:
        if strl.button("📥 Pull Invoices Now", use_container_width=True):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Invoices", [])
                if data:
                    strl.dataframe(pd.json_normalize(data), use_container_width=True)
                else:
                    strl.info("No recorded invoices found.")
            else:
                strl.error(f"API Error: {r.text}")
                
    with tab2:
        if strl.button("📥 Pull Contacts Now", use_container_width=True):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Contacts", [])
                if data:
                    strl.dataframe(pd.json_normalize(data), use_container_width=True)
                else:
                    strl.info("No contacts found.")
            else:
                strl.error(f"API Error: {r.text}")

# --- WORKSPACE PATH B: OFFLINE PANEL VIEW ---
else:
    strl.info("Application Status: Offline. Start your secure Xero connection sequence below.")
    
    # URL-encode parameters to prevent Python's built-in string space formatting bug
    encoded_redirect = urllib.parse.quote(REDIRECT_URI, safe='')
    encoded_scopes = urllib.parse.quote(SCOPES, safe='')
    
    # Complete, unbroken URL path query structure string with mandatory consent forcing parameter
    auth_redirect_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={encoded_redirect}&scope={encoded_scopes}&state=gigo_manual_stable_loop&prompt=consent"
    
    strl.markdown("### Step 1: Copy this link and open it in a private browser tab:")
    strl.code(auth_redirect_url, language="text")
    
    strl.markdown("---")
    strl.subheader("🛠️ Connection Link Dashboard")
    strl.caption("Paste the resulting link text string from your address bar right back here:")
    
    manual_input = strl.text_input("Paste full address bar URL here:", placeholder="https://streamlit.app?code=...")
    
    if strl.button("⚡ 2. Finalize Connection", use_container_width=True):
        if manual_input:
            if "code=" in manual_input:
                try:
                    parsed_url = urllib.parse.urlparse(manual_input)
                    url_parameters = urllib.parse.parse_qs(parsed_url.query)
                    
                    # FIX: Safely parse array index dictionary elements to a raw text string
                    extracted_token = url_parameters["code"][0]
                    exchange_code_for_tokens(extracted_token)
                except Exception as parse_err:
                    strl.error(f"Could not parse URL text: {str(parse_err)}")
            else:
                exchange_code_for_tokens(manual_input)
        else:
            strl.error("Please provide a valid code token or landing link address string.")
