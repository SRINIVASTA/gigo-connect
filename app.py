import streamlit as st
import requests
import pandas as pd
import urllib.parse

# 1. Load Configurations directly from your secure Streamlit Secrets panel
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]

# FIXED: Direct matching production URL matching your live deployment domain
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"

# 2026 Mandatory Granular Scopes for Xero App Integrations
SCOPES = "openid profile email app.connections accounting.contacts accounting.invoices offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# --- UTILITY: DEV MODE CLEAR UTILITY ---
if st.sidebar.button("🧼 Reset Cached State", help="Clears lingering session values"):
    st.session_state.tokens = None
    st.session_state.tenant_id = None
    st.session_state.tenant_name = None
    st.rerun()

# Establish resilient memory caches inside the running browser session state
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

def exchange_code_for_tokens(code_string):
    token_url = "https://xero.com"
    payload = {
        "grant_type": "authorization_code",
        "code": code_string.strip(),
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        res = requests.post(token_url, data=payload, headers=headers)
        if res.status_code == 200:
            token_json = res.json()
            
            # Connections endpoint to fetch active organization tenant data
            conn_url = "https://xero.com"
            conn_headers = {
                "Authorization": f"Bearer {token_json['access_token']}",
                "Content-Type": "application/json"
            }
            conn_res = requests.get(conn_url, headers=conn_headers)
            
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
                    st.error("Authentication passed, but no linked Xero organizations were discovered.")
            else:
                st.error(f"Tenant extraction failed: {conn_res.text}")
        else:
            st.error(f"Handshake failed (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        st.error(f"A connection error occurred: {str(e)}")

# --- WORKSPACE PATH A: DASHBOARD SECURE DATA VIEW ---
if st.session_state.tokens and st.session_state.tenant_id:
    st.sidebar.success(f"🏢 Connected Profile: {st.session_state.tenant_name}")
    if st.sidebar.button("Disconnect Session", use_container_width=True):
        st.session_state.tokens = None
        st.session_state.tenant_id = None
        st.session_state.tenant_name = None
        st.rerun()
        
    tab1, tab2 = st.tabs(["📋 Invoices Ledger", "👥 Contact Profiles"])
    api_headers = {
        "Authorization": f"Bearer {st.session_state.tokens['access_token']}",
        "Xero-tenant-id": st.session_state.tenant_id,
        "Accept": "application/json"
    }
    
    with tab1:
        if st.button("📥 Pull Invoices Now", use_container_width=True):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Invoices", [])
                if data:
                    st.dataframe(pd.json_normalize(data), use_container_width=True)
                else:
                    st.info("No recorded invoices found.")
            else:
                st.error(f"API Error: {r.text}")
                
    with tab2:
        if st.button("📥 Pull Contacts Now", use_container_width=True):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Contacts", [])
                if data:
                    st.dataframe(pd.json_normalize(data), use_container_width=True)
                else:
                    st.info("No contacts found.")
            else:
                st.error(f"API Error: {r.text}")

# --- WORKSPACE PATH B: OFFLINE PANEL VIEW ---
else:
    st.info("Application Status: Offline. Start your secure Xero connection sequence below.")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_manual_stable_loop"
    }
    
    # CRITICAL FIX: The absolute OAuth2 URL endpoint mapping
    auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
    
    st.markdown("### Step 1: Copy this link and open it in a private browser tab:")
    st.code(auth_redirect_url, language="text")
    
    st.markdown("---")
    st.subheader("🛠️ Connection Link Dashboard")
    st.caption("Paste the resulting link text string from your address bar right back here:")
    
    manual_input = st.text_input("Paste full address bar URL here:", placeholder="https://streamlit.app?code=...")
    
    if st.button("⚡ 2. Finalize Connection", use_container_width=True):
        if manual_input:
            if "code=" in manual_input:
                try:
                    parsed_url = urllib.parse.urlparse(manual_input)
                    url_parameters = urllib.parse.parse_qs(parsed_url.query)
                    extracted_token = url_parameters["code"][0]
                    exchange_code_for_tokens(extracted_token)
                except Exception as parse_err:
                    st.error(f"Could not parse URL text: {str(parse_err)}")
            else:
                exchange_code_for_tokens(manual_input)
        else:
            st.error("Please provide a valid code token or landing link address string.")
