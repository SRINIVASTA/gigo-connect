import streamlit as st
import requests
import pandas as pd
import urllib.parse
import time

# 1. Secure Environment Mapping from Streamlit Secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "http://localhost:8501/"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration Hub")

# Establish resilient memory caches inside the running browser session state
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None
if "token_expires_at" not in st.session_state:
    st.session_state.token_expires_at = 0

# --- AUTO-RENEWAL ENGINE ---
def get_valid_access_token():
    """Checks the active session clock and silently auto-renews tokens if expired."""
    if not st.session_state.tokens:
        return None
        
    # If token has less than 60 seconds left or is already expired, trigger renewal
    if time.time() >= st.session_state.token_expires_at - 60:
        st.toast("🔄 Access token expired. Auto-refreshing session with Xero Identity Core...", icon="⏳")
        
        token_url = "https://xero.com"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": st.session_state.tokens.get("refresh_token"),
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            res = requests.post(token_url, data=payload, headers=headers)
            if res.status_code == 200:
                new_tokens = res.json()
                st.session_state.tokens = new_tokens
                # Access tokens expire in 30 minutes (1800 seconds)
                st.session_state.token_expires_at = time.time() + new_tokens.get("expires_in", 1800)
                st.toast("🎉 Session renewed successfully!", icon="✅")
            else:
                st.error(f"🚨 Auto-refresh failed: {res.text}. Please re-authenticate.")
                st.session_state.tokens = None
                st.rerun()
        except Exception as e:
            st.error(f"Network error during refresh handshake: {str(e)}")
            
    return st.session_state.tokens.get("access_token")

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
            st.session_state.tokens = token_json
            st.session_state.token_expires_at = time.time() + token_json.get("expires_in", 1800)
            
            # Fetch connected organization configurations
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
    
    # Calculate and display token remaining lifespan in the sidebar
    time_left = max(0, int(st.session_state.token_expires_at - time.time()))
    st.sidebar.caption(f"⏱️ Access Token Lifespan: `{time_left}s` left")
    
    if st.sidebar.button("Disconnect Session", use_container_width=True):
        st.session_state.tokens = None
        st.session_state.tenant_id = None
        st.session_state.tenant_name = None
        st.rerun()
        
    tab1, tab2 = st.tabs(["📋 Invoices Ledger", "👥 Contact Profiles"])
    
    with tab1:
        if st.button("📥 Pull Invoices Now", use_container_width=True):
            # Guard function ensures tokens are valid before launching API calls
            token = get_valid_access_token()
            if token:
                api_headers = {"Authorization": f"Bearer {token}", "Xero-tenant-id": st.session_state.tenant_id, "Accept": "application/json"}
                r = requests.get("https://xero.com", headers=api_headers)
                if r.status_code == 200:
                    data = r.json().get("Invoices", [])
                    st.dataframe(pd.json_normalize(data) if data else "No invoices.", use_container_width=True)
                else:
                    st.error(f"API Error: {r.text}")
                
    with tab2:
        if st.button("📥 Pull Contacts Now", use_container_width=True):
            token = get_valid_access_token()
            if token:
                api_headers = {"Authorization": f"Bearer {token}", "Xero-tenant-id": st.session_state.tenant_id, "Accept": "application/json"}
                r = requests.get("https://xero.com", headers=api_headers)
                if r.status_code == 200:
                    data = r.json().get("Contacts", [])
                    st.dataframe(pd.json_normalize(data) if data else "No contacts.", use_container_width=True)
                else:
                    st.error(f"API Error: {r.text}")

# --- WORKSPACE PATH B: OFFLINE INITIALIZATION & MANUAL PASTE PANEL ---
else:
    st.info("Application Status: Offline. Start your secure Xero connection sequence below.")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_localhost_stable_v12"
    }
    auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
    
    st.link_button(label="🔐 1. Log In and Authorize via Xero Portal", url=auth_redirect_url, use_container_width=True)
    
    st.markdown("---")
    st.subheader("🛠️ Connection Link Dashboard")
    st.caption("Paste the alphanumeric verification URL below to authorize your connection:")
    
    manual_input = st.text_input("Paste full address bar URL here:", placeholder="http://localhost:8501/?code=...")
    
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
            st.error("Please provide a valid link address string.")
