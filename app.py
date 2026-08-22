import streamlit as st
import requests
import pandas as pd
import urllib.parse

# Load configurations securely from your Streamlit panel secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://streamlit.app"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Session state initialization layers
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

def exchange_code_for_tokens(code_string):
    token_url = "https://identity.xero.com/connect/token"
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
            
            # Fetch connected tenant configurations
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

# --- WORKSPACE PATH A: DASHBOARD VIEW ---
if st.session_state.tokens and st.session_state.tenant_id:
    st.sidebar.success(f"🏢 Profile: {st.session_state.tenant_name}")
    if st.sidebar.button("Disconnect Session"):
        st.session_state.tokens = None
        st.session_state.tenant_id = None
        st.rerun()
        
    tab1, tab2 = st.tabs(["📋 Invoices Ledger", "👥 Contact Profiles"])
    api_headers = {
        "Authorization": f"Bearer {st.session_state.tokens['access_token']}",
        "Xero-tenant-id": st.session_state.tenant_id,
        "Accept": "application/json"
    }
    
    with tab1:
        if st.button("📥 Pull Invoices"):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Invoices", [])
                st.dataframe(pd.json_normalize(data) if data else "No invoices found.")
            else:
                st.error(f"API Error: {r.text}")
                
    with tab2:
        if st.button("📥 Pull Contacts"):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Contacts", [])
                st.dataframe(pd.json_normalize(data) if data else "No contacts found.")
            else:
                st.error(f"API Error: {r.text}")

# --- WORKSPACE PATH B: OFFLINE INITIALIZATION & MANUAL FALLBACK ---
else:
    st.info("Application Status: Offline. Start your secure Xero connection sequence below.")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_stable_v6"
    }
    auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
    
    st.link_button(label="🔐 1. Complete Xero Handshake", url=auth_redirect_url, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🛠️ Manual Activation Step")
    st.write("Since Streamlit hides URL tracking variables inside cloud frames, manually extract your authorization string:")
    
    manual_code = st.text_input(
        "Paste the temporary authorization code here:", 
        placeholder="Look for the text after ?code= in your top window address bar..."
    )
    
    if st.button("⚡ 2. Finalize Connection", use_container_width=True):
        if manual_code:
            if "streamlit.app" in manual_code or "http" in manual_code:
                st.error("❌ Wrong string pasted! Do not paste your app URL or domain name. Paste only the temporary code value.")
            else:
                exchange_code_for_tokens(manual_code)
        else:
            st.error("Please provide a valid code string.")
