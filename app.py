import streamlit as st
import requests
import urllib.parse
import pandas as pd

# 1. Load Configurations securely from Secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]

# MUST perfectly match your Xero Portal Configuration redirect setup string character-for-character
REDIRECT_URI = "https://streamlit.app"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Establish resilient memory caches inside the running browser session
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

def exchange_code_for_tokens(code_string):
    # FIXED: Pointed directly to official identity OAuth API service routing path
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
            
            # FIXED: Pointed to official multi-tenant directory service API path
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
                    st.query_params.clear() 
                    st.rerun()
                else:
                    st.error("Authentication passed, but no linked Xero organizations were discovered.")
            else:
                st.error(f"Tenant extraction failed: {conn_res.text}")
        else:
            st.error(f"Handshake failed (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        st.error(f"A connection error occurred: {str(e)}")

# Read query string keys natively from the browser address bar interface
query_params = st.query_params

# --- INTERCEPT AUTOMATIC CALLBACK HOOK ---
if "code" in query_params and st.session_state.tokens is None:
    automated_code = query_params["code"]
    st.info("🔄 Found authorization parameter! Synchronizing dashboard tables...")
    exchange_code_for_tokens(automated_code)

# --- WORKSPACE PATH A: ACTIVE HUB VIEW ---
if st.session_state.tokens and st.session_state.tenant_id:
    st.sidebar.success(f"🏢 Profile: {st.session_state.tenant_name}")
    if st.sidebar.button("Disconnect Session", use_container_width=True):
        st.session_state.tokens = None
        st.session_state.tenant_id = None
        st.session_state.tenant_name = None
        st.query_params.clear()
        st.rerun()
        
    tab1, tab2 = st.tabs(["📋 Invoices Ledger", "👥 Contact Profiles"])
    api_headers = {
        "Authorization": f"Bearer {st.session_state.tokens['access_token']}",
        "Xero-tenant-id": st.session_state.tenant_id,
        "Accept": "application/json"
    }
    
    with tab1:
        if st.button("📥 Pull Invoices Now", key="pull_inv_btn"):
            with st.spinner("Loading ledger data records..."):
                # FIXED: Pointed to correct accounting endpoints
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
        if st.button("📥 Pull Contacts Now", key="pull_cont_btn"):
            with st.spinner("Loading directory details..."):
                # FIXED: Pointed to correct accounting endpoints and aligned text blocks
                r = requests.get("https://xero.com", headers=api_headers)
                if r.status_code == 200:
                    data = r.json().get("Contacts", [])
                    if data:
                        st.dataframe(pd.json_normalize(data), use_container_width=True)
                    else:
                        st.info("No contacts discovered.")
                else:
                    st.error(f"API Error: {r.text}")

# --- WORKSPACE PATH B: OFFLINE INITIAL GATEWAY ---
else:
    if "code" not in query_params:
        st.info("Application Status: Offline. Start your secure Xero connection sequence below.")
        
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": "gigo_automation_final"
        }
        # FIXED: Core redirect points strictly to the secure login gateway page wrapper
        auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
        
        # SAME-TAB BREAKOUT BUTTON: Forces the browser to load the login page natively outside the iframe wrapper context
        if st.button("🔐 Complete Xero Handshake", type="primary", use_container_width=True):
            st.markdown(
                f"""
                <meta http-equiv="refresh" content="0; url={auth_redirect_url}">
                <script>window.top.location.href = "{auth_redirect_url}";</script>
                """,
                unsafe_allow_html=True
            )
