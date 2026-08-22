import streamlit as st
import requests
import urllib.parse
import pandas as pd

# 1. Exact configurations from your setup
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Initialize state objects
if "xero_tokens" not in st.session_state:
    st.session_state.xero_tokens = None
if "xero_tenant_id" not in st.session_state:
    st.session_state.xero_tenant_id = None
if "xero_tenant_name" not in st.session_state:
    st.session_state.xero_tenant_name = None

query_params = st.query_params

# --- STATE 2: DETECT AND INTERCEPT CALLBACK ---
if "code" in query_params and st.session_state.xero_tokens is None:
    auth_code = query_params["code"]
    st.warning("⚠️ Action Required: Xero authorized the app query context!")
    
    if st.button("🚀 Finalize and Load My Dashboard Data", type="primary"):
        with st.spinner("Exchanging code for production token metrics..."):
            # CORRECT ENDPOINT: Must go to identity framework, not the main marketing home page
            token_url = "https://xero.com"
            payload = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET
            }
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            
            try:
                res = requests.post(token_url, data=payload, headers=headers)
                if res.status_code == 200:
                    tokens = res.json()
                    st.session_state.xero_tokens = tokens
                    
                    # Discover connected Xero company metrics
                    conn_url = "https://xero.com"
                    conn_headers = {
                        "Authorization": f"Bearer {tokens['access_token']}",
                        "Content-Type": "application/json"
                    }
                    conn_res = requests.get(conn_url, headers=conn_headers)
                    
                    if conn_res.status_code == 200:
                        connections = conn_res.json()
                        if isinstance(connections, list) and len(connections) > 0:
                            st.session_state.xero_tenant_id = connections[0]["tenantId"]
                            st.session_state.xero_tenant_name = connections[0].get("tenantName", "Demo Company")
                            st.success("🎉 Access Token received! Connection complete.")
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error("No organization matching accounts discovered.")
                    else:
                        st.error(f"Tenant mapping lookup failed: {conn_res.text}")
                else:
                    st.error(f"Handshake failed ({res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"Network error processing exchange: {str(e)}")

# --- STATE 3: VIEW ACTIVE DATA HUB ---
if st.session_state.xero_tokens and st.session_state.xero_tenant_id:
    st.sidebar.success(f"🏢 Connected to: {st.session_state.xero_tenant_name}")
    if st.sidebar.button("🔌 Disconnect Session"):
        st.session_state.xero_tokens = None
        st.session_state.xero_tenant_id = None
        st.rerun()
        
    tab1, tab2 = st.tabs(["📋 Pull Invoices", "👥 Pull Contacts"])
    api_headers = {
        "Authorization": f"Bearer {st.session_state.xero_tokens['access_token']}",
        "Xero-tenant-id": st.session_state.xero_tenant_id,
        "Accept": "application/json"
    }
    
    with tab1:
        if st.button("📥 Load System Invoices"):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                invs = r.json().get("Invoices", [])
                st.dataframe(pd.json_normalize(invs) if invs else "No invoices found.")
                
    with tab2:
        if st.button("📥 Load System Contacts"):
            r = requests.get("https://xero.com", headers=api_headers)
            if r.status_code == 200:
                conts = r.json().get("Contacts", [])
                st.dataframe(pd.json_normalize(conts) if conts else "No contacts found.")

# --- STATE 1: INITIAL OFFLINE SCREEN ---
elif "code" not in query_params:
    st.info("System status: Offline. Link your live Xero application setup profiles below.")
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_secure_state_101"
    }
    # CORRECT AUTH LINK: Send user to xero's secure login sub-gateway, not general web URL
    auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
    st.link_button(label="🔐 Start Xero Handshake", url=auth_redirect_url, use_container_width=True)
