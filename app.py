import streamlit as st
import requests
import urllib.parse
import pandas as pd

# Load configurations securely from Secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Establish resilient memory caches
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
                st.dataframe(pd.json_normalize(data) if data else "No invoices.")
            else:
                st.error(f"API Error: {r.text}")
                
    with tab2:
        if st.button("📥 Pull Contacts"):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                data = r.json().get("Contacts", [])
                st.dataframe(pd.json_normalize(data) if data else "No contacts.")
            else:
                st.error(f"API Error: {r.text}")

# --- WORKSPACE PATH B: OFFLINE INITIALIZATION & ROBUST FALLBACK ---
else:
    st.info("Application Status: Offline. Start your secure Xero connection sequence below.")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_agentic_stable_v10"
    }
    auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
    
    st.link_button(label="🔐 1. Complete Xero Handshake", url=auth_redirect_url, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🛠️ Secure Connection Panel")
    st.caption("Paste either the **full long URL address string** or just the code block from your address bar after logging in:")
    
    user_input_string = st.text_input("Paste here:", placeholder="https://gigo-connect-.../?code=xxxx... or just the code string")
    
    if st.button("⚡ 2. Finalize Connection Handshake", use_container_width=True):
        if user_input_string:
            # Intelligent agentic parsing filter string
            if "code=" in user_input_string:
                try:
                    parsed_url = urllib.parse.urlparse(user_input_string)
                    url_parameters = urllib.parse.parse_qs(parsed_url.query)
                    extracted_code = url_parameters["code"][0]
                    exchange_code_for_tokens(extracted_code)
                except Exception as parse_err:
                    st.error(f"Could not parse URL text: {str(parse_err)}")
            else:
                # If you pasted just the clean code token string without the URL headers wrapper
                exchange_code_for_tokens(user_input_string)
        else:
            st.error("Please provide a valid code token or landing link address string.")
