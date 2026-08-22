import streamlit as st
import requests
import pandas as pd
import urllib.parse

# 1. Load Configurations from Secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://streamlit.app"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Setup safe state session caches
if "tokens" not in st.session_state:
    st.session_state.tokens = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

# --- AUTOMATED IFRAME BREAKOUT FILTER ---
# Read URL parameters directly from the browser window header
query_params = st.query_params

if "code" in query_params and st.session_state.tokens is None:
    auth_code = query_params["code"]
    
    st.info("🔄 Connection authorized by Xero! Automatically synchronizing your data ledger...")
    
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
            token_json = res.json()
            
            # Fetch connected company profile mappings
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
                    
                    # Store session variables into state memory maps
                    st.session_state.tokens = token_json
                    st.session_state.tenant_id = primary_connection["tenantId"]
                    st.session_state.tenant_name = primary_connection.get("tenantName", "Demo Company")
                    
                    st.success(f"✅ Securely linked to: {st.session_state.tenant_name}")
                    st.query_params.clear() # Wipe parameters to prevent loop refreshes
                    st.rerun()
                else:
                    st.error("❌ No active Xero company links discovered.")
            else:
                st.error(f"Tenant mapping extraction failed: {conn_res.text}")
        else:
            st.error(f"Handshake failed (HTTP {res.status_code}): {res.text}")
    except Exception as e:
        st.error(f"Background connection error: {str(e)}")

# --- USER VIEW PATH A: DASHBOARD SECURE DATA VIEW ---
if st.session_state.tokens and st.session_state.tenant_id:
    st.sidebar.success(f"🏢 Connected Org: {st.session_state.tenant_name}")
    if st.sidebar.button("Disconnect Session"):
        st.session_state.tokens = None
        st.session_state.tenant_id = None
        st.session_state.tenant_name = None
        st.rerun()
        
    tab1, tab2 = st.tabs(["📋 Recent Invoices Ledger", "👥 Customer Contacts"])
    api_headers = {
        "Authorization": f"Bearer {st.session_state.tokens['access_token']}",
        "Xero-tenant-id": st.session_state.tenant_id,
        "Accept": "application/json"
    }
    
    with tab1:
        if st.button("📥 Retrieve Invoices Ledger"):
            with st.spinner("Pulling invoice payload records..."):
                r = requests.get("https://xero.com", headers=api_headers)
                if r.status_code == 200:
                    data = r.json().get("Invoices", [])
                    if data:
                        df = pd.json_normalize(data)
                        display_cols = [c for c in ["InvoiceNumber", "Type", "Status", "Total", "AmountDue", "DateString"] if c in df.columns]
                        st.dataframe(df[display_cols], use_container_width=True)
                    else:
                        st.info("No recorded invoices found.")
                else:
                    st.error(f"API Error: {r.text}")
                
    with tab2:
        if st.button("📥 Retrieve Contacts Profile"):
            with st.spinner("Pulling customer profiles..."):
                r = requests.get("https://xero.com", headers=api_headers)
                if r.status_code == 200:
                    data = r.json().get("Contacts", [])
                    if data:
                        df = pd.json_normalize(data)
                        display_cols = [c for c in ["Name", "EmailAddress", "ContactStatus"] if c in df.columns]
                        st.dataframe(df[display_cols], use_container_width=True)
                    else:
                        st.info("No contacts found.")
                else:
                    st.error(f"API Error: {r.text}")

# --- USER VIEW PATH B: OFFLINE INITIALIZATION GATE ---
else:
    if "code" not in query_params:
        st.info("Application Status: Offline. Securely bridge your Xero application below.")
        
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": "gigo_iframe_breakout_v7"
        }
        auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
        
        # IFRAME BREAKOUT TRIGGER: Forces the button to open Xero outside of Streamlit's hidden framework box
        if st.button("🔐 Complete Xero Handshake Flow", type="primary", use_container_width=True):
            st.markdown(
                f"""
                <meta http-equiv="refresh" content="0; url={auth_redirect_url}">
                <script>window.top.location.href = "{auth_redirect_url}";</script>
                """,
                unsafe_allow_html=True
            )
