import streamlit as st
import requests
import pandas as pd
import urllib.parse

# 1. Load Configurations from Secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://streamlit.app"

# Complete scope credentials required to read your Demo Ledger
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect", page_icon="🔗", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Initialize persistent session tracking structures
if "xero_tokens" not in st.session_state:
    st.session_state.xero_tokens = None
if "xero_tenant_id" not in st.session_state:
    st.session_state.xero_tenant_id = None
if "xero_tenant_name" not in st.session_state:
    st.session_state.xero_tenant_name = None

# Extract current active URL queries
query_params = st.query_params

# --- INTERCEPT CALLBACK: AGENTIC SECURE CHECK ---
if "code" in query_params and st.session_state.xero_tokens is None:
    auth_code = query_params["code"]
    
    st.warning("⚠️ Action Required: Xero has authorized your connection!")
    st.write("Click the button below to process your temporary access tokens and lock in your session data tables.")
    
    if st.button("🚀 Finalize and Load My Dashboard Data", type="primary"):
        with st.spinner("Exchanging secure token handshakes with Xero API infrastructure..."):
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
                token_response = requests.post(token_url, data=payload, headers=headers)
                
                if token_response.status_code == 200:
                    tokens = token_response.json()
                    st.session_state.xero_tokens = tokens
                    
                    # Fetch active organizational associations
                    connections_url = "https://xero.com"
                    conn_headers = {
                        "Authorization": f"Bearer {tokens['access_token']}",
                        "Content-Type": "application/json"
                    }
                    
                    conn_response = requests.get(connections_url, headers=conn_headers)
                    
                    if conn_response.status_code == 200:
                        connections = conn_response.json()
                        
                        if isinstance(connections, list) and len(connections) > 0:
                            # Safely isolate index dict 0 mapping arrays
                            primary_connection = connections[0]
                            st.session_state.xero_tenant_id = primary_connection["tenantId"]
                            st.session_state.xero_tenant_name = primary_connection.get("tenantName", "Demo Company")
                            
                            st.success(f"✅ Success! Connected to: {st.session_state.xero_tenant_name}")
                            
                            # Clean the browser URL bar now that tokens are securely saved
                            st.query_params.clear()
                            st.rerun()
                        else:
                            st.error("❌ Authentication succeeded, but no linked company profiles were found in this account.")
                    else:
                        st.error(f"❌ Connection Discovery Failure: {conn_response.text}")
                else:
                    st.error(f"❌ Token Exchange Failure (HTTP {token_response.status_code}): {token_response.text}")
                    st.info("💡 Tip: Authorization codes expire in under 5 minutes. Try restarting the handshake process.")
                    
            except Exception as e:
                st.error(f"An unexpected networking exception occurred: {str(e)}")

# --- STATE 3: DATA RETRIEVAL ACTIVE HUB ---
if st.session_state.xero_tokens and st.session_state.xero_tenant_id:
    st.sidebar.markdown(f"### 🏢 Active Connection\n**{st.session_state.xero_tenant_name}**")
    st.sidebar.caption(f"Tenant Reference: `{st.session_state.xero_tenant_id[:12]}...`")
    
    if st.sidebar.button("Disconnect Session", type="secondary"):
        st.session_state.xero_tokens = None
        st.session_state.xero_tenant_id = None
        st.session_state.xero_tenant_name = None
        st.query_params.clear()
        st.rerun()

    # Create UI workspace layouts
    tab1, tab2 = st.tabs(["📋 View Sales Invoices", "👥 Customer Contacts"])
    
    api_headers = {
        "Authorization": f"Bearer {st.session_state.xero_tokens['access_token']}",
        "Xero-tenant-id": st.session_state.xero_tenant_id,
        "Accept": "application/json"
    }

    with tab1:
        if st.button("📥 Retrieve Invoices Ledger", key="btn_inv_load"):
            with st.spinner("Extracting transactions..."):
                resp = requests.get("https://xero.com", headers=api_headers)
                if resp.status_code == 200:
                    records = resp.json().get("Invoices", [])
                    if records:
                        df = pd.json_normalize(records)
                        cols = [c for c in ["InvoiceNumber", "Type", "Status", "Total", "AmountDue", "DateString"] if c in df.columns]
                        st.dataframe(df[cols], use_container_width=True)
                    else:
                        st.info("No invoice line items found inside this target company profile.")
                else:
                    st.error(f"API Error ({resp.status_code}): {resp.text}")

    with tab2:
        if st.button("📥 Retrieve Contacts Profile", key="btn_cont_load"):
            with st.spinner("Extracting master records..."):
                resp = requests.get("https://xero.com", headers=api_headers)
                if resp.status_code == 200:
                    records = resp.json().get("Contacts", [])
                    if records:
                        df = pd.json_normalize(records)
                        cols = [c for c in ["Name", "EmailAddress", "ContactStatus"] if c in df.columns]
                        st.dataframe(df[cols], use_container_width=True)
                    else:
                        st.info("No active contacts saved inside this business account profile.")
                else:
                    st.error(f"API Error ({resp.status_code}): {resp.text}")

# --- STATE 1: OFFLINE INITIAL SCREEN ---
elif not ("code" in query_params):
    st.info("Your application context is currently offline. Connect to Xero securely below.")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_secure_state_987"
    }
    encoded_params = urllib.parse.urlencode(params)
    auth_redirect_url = f"https://xero.com?{encoded_params}"
    
    st.page_link(
        page=auth_redirect_url,
        label="🔐 Complete Xero Handshake",
        icon="🔑"
    )
