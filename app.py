import streamlit as st
import requests
import pandas as pd
import urllib.parse

# Load configurations securely from Secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]

# FIX: Using standard desktop loop to force Xero to show your code in giant text on screen
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Establish persistent session memory caches
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None

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
                    primary_connection = connections
                    st.session_state.tokens = token_json
                    st.session_state.tenant_id = primary_connection["tenantId"]
                    st.success("🎉 Connected successfully!")
                    st.rerun()
    except Exception as e:
        st.error(f"Error: {str(e)}")

# --- USER VIEW PANELS ---
if st.session_state.tokens and st.session_state.tenant_id:
    st.sidebar.success("🏢 Connected to Xero")
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
                st.dataframe(pd.json_normalize(data) if data else "No invoices.")
                
    with tab2:
        if st.button("📥 Pull Contacts"):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Contacts", [])
                st.dataframe(pd.json_normalize(data) if data else "No contacts.")

else:
    # AUTOMATIC CHECK: Streamlit tries to grab the code from the URL parameters directly
    if "code" in st.query_params:
        automated_code = st.query_params["code"]
        exchange_code_for_tokens(automated_code)
        
    st.info("Application Status: Offline. Click below to connect.")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_stable_loop"
    }
    auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
    
    st.link_button(label="🔐 Click to Log In & Authenticate", url=auth_redirect_url, use_container_width=True)
    
    st.markdown("---")
    # Backup input box if the redirect gets stuck
    manual_code = st.text_input("Alternatively, if you have your code string, enter it here manually:")
    if st.button("⚡ Force Manual Handshake"):
        if manual_code:
            exchange_code_for_tokens(manual_code)
