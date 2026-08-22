import streamlit as st
import requests
import pandas as pd
import urllib.parse

# 1. Load Configurations from Secrets (Matching your setup perfectly)
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"

# Scopes needed to fetch organization names, invoices, and contacts
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect", page_icon="🔗", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Initialize persistent session memory
if "xero_tokens" not in st.session_state:
    st.session_state.xero_tokens = None
if "xero_tenant_id" not in st.session_state:
    st.session_state.xero_tenant_id = None
if "xero_tenant_name" not in st.session_state:
    st.session_state.xero_tenant_name = None

# --- STATE 2: DETECT AND INTERCEPT OAUTH CALLBACK FROM XERO ---
query_params = st.query_params

if "code" in query_params and st.session_state.xero_tokens is None:
    auth_code = query_params["code"]
    st.info("🔄 Processing authorization callback code from Xero...")
    
    # Post request payload to exchange code for structural access tokens
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
            st.session_state.xero_tokens = tokens  # Dict containing access_token and refresh_token
            
            # Xero Identity Connection discovery (returns a list of accessible organizations)
            connections_url = "https://xero.com"
            conn_headers = {
                "Authorization": f"Bearer {tokens['access_token']}",
                "Content-Type": "application/json"
            }
            
            conn_response = requests.get(connections_url, headers=conn_headers)
            
            if conn_response.status_code == 200:
                connections = conn_response.json()
                if isinstance(connections, list) and len(connections) > 0:
                    # Select the first connected organization tenant
                    st.session_state.xero_tenant_id = connections[0]["tenantId"]
                    st.session_state.xero_tenant_name = connections[0].get("tenantName", "Xero Organization")
                    st.success(f"✅ Successfully linked to: **{st.session_state.xero_tenant_name}**")
                else:
                    st.error("⚠️ Authentication passed, but no linked Xero organizations were found.")
            else:
                st.error(f"❌ Failed connection retrieval: {conn_response.text}")
        else:
            st.error(f"❌ Failed token handshake: {token_response.text}")
            
    except Exception as e:
        st.error(f"An unexpected connection error occurred: {str(e)}")
        
    # Clear callback values cleanly out of the browser URL bar
    st.query_params.clear()

# --- STATE 3: VIEW & FETCH ACCOUNTING PAYLOADS ---
if st.session_state.xero_tokens and st.session_state.xero_tenant_id:
    st.sidebar.markdown(f"### 🏢 Connected Org\n**{st.session_state.xero_tenant_name}**")
    st.sidebar.caption(f"ID: `{st.session_state.xero_tenant_id[:8]}...`")
    
    # Simple log out switch to reset app state
    if st.sidebar.button("🔌 Disconnect from Xero"):
        st.session_state.xero_tokens = None
        st.session_state.xero_tenant_id = None
        st.session_state.xero_tenant_name = None
        st.rerun()

    # User Selection Layout Tabs
    tab1, tab2 = st.tabs(["📋 Recent Invoices", "👥 Contact Directory"])
    
    # Global Request Headers
    api_headers = {
        "Authorization": f"Bearer {st.session_state.xero_tokens['access_token']}",
        "Xero-tenant-id": st.session_state.xero_tenant_id,
        "Accept": "application/json"
    }

    with tab1:
        if st.button("🔄 Pull Invoices", key="inv_btn"):
            with st.spinner("Fetching invoice ledger..."):
                inv_resp = requests.get("https://xero.com", headers=api_headers)
                if inv_resp.status_code == 200:
                    invoices = inv_resp.json().get("Invoices", [])
                    if invoices:
                        # Normalize nested API JSON data structurally into a data frame
                        df_inv = pd.json_normalize(invoices)
                        # Filter columns dynamically for quick visual scanning
                        display_cols = [c for c in ["InvoiceNumber", "Type", "Status", "Total", "AmountDue", "DateString"] if c in df_inv.columns]
                        st.dataframe(df_inv[display_cols], use_container_width=True)
                    else:
                        st.info("No invoice history items found inside this organization profile.")
                else:
                    st.error(f"Error {inv_resp.status_code}: {inv_resp.text}")

    with tab2:
        if st.button("🔄 Pull Contacts", key="cont_btn"):
            with st.spinner("Fetching customer records..."):
                cont_resp = requests.get("https://xero.com", headers=api_headers)
                if cont_resp.status_code == 200:
                    contacts = cont_resp.json().get("Contacts", [])
                    if contacts:
                        df_cont = pd.json_normalize(contacts)
                        display_cols = [c for c in ["Name", "EmailAddress", "ContactStatus"] if c in df_cont.columns]
                        st.dataframe(df_cont[display_cols], use_container_width=True)
                    else:
                        st.info("No active contacts saved in this company profile.")
                else:
                    st.error(f"Error {cont_resp.status_code}: {cont_resp.text}")

# --- STATE 1: INITIAL UNLINKED INTERFACE ---
else:
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
    
    # Create two columns to handle the user flow smoothly
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # The primary login action button
        st.markdown(
            f'<a href="{auth_redirect_url}" target="_blank" style="display: inline-block; padding: 0.6em 1.3em; color: white; background-color: #00b7e2; border-radius: 6px; text-decoration: none; font-weight: bold; font-size: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">🔐 Launch Xero Login</a>',
            unsafe_allow_html=True
        )
        
    with col2:
        # A manual sync button for Window 1 to pick up changes if it feels stuck
        if st.button("🔄 Sync & Refresh App Data"):
            st.rerun()

    # Clear instructions to prevent user confusion across tabs
    st.markdown("""
    ---
    💡 **What to expect next:**
    1. Clicking the launch button opens Xero's secure login portal in a **new tab**.
    2. Log in and select your **Demo Company (Global)**.
    3. Once authorized, that new tab will load your active data hub. You can safely close this original idle window!
    """)
