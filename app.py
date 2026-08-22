import streamlit as st
import requests
import urllib.parse
import pandas as pd

# Load configurations from your Streamlit panel secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🔗 Gigo Connect x Xero Integration")

# Setup safe initialization layers
if "xero_tokens" not in st.session_state:
    st.session_state.xero_tokens = None
if "xero_tenant_id" not in st.session_state:
    st.session_state.xero_tenant_id = None
if "xero_tenant_name" not in st.session_state:
    st.session_state.xero_tenant_name = None

# Extract the temporary parameters string from browser
query_params = st.query_params

# --- STATE 2: ERROR-PROOF HANDSHAKE RESOLVER ---
if "code" in query_params and st.session_state.xero_tokens is None:
    auth_code = query_params["code"]
    
    st.success("📥 Temporary authentication code captured from Xero callback context!")
    st.info("Click the button below to exchange this code for live ledger tokens.")
    
    if st.button("🚀 Finalize Handshake & Open Dashboard", type="primary"):
        with st.spinner("Exchanging token parameters..."):
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
                    
                    # Fetch organization listings profile
                    conn_url = "https://xero.com"
                    conn_headers = {
                        "Authorization": f"Bearer {tokens['access_token']}",
                        "Content-Type": "application/json"
                    }
                    conn_res = requests.get(conn_url, headers=conn_headers)
                    
                    if conn_res.status_code == 200:
                        connections = conn_res.json()
                        
                        # AGENTIC PATCH: Robust list validation check against multi-tenant indexing errors
                        if isinstance(connections, list) and len(connections) > 0:
                            # Isolate dictionary item index 0 safely
                            primary_org = connections[0]
                            
                            # Lock items securely to avoid falling into offline resets
                            st.session_state.xero_tokens = tokens
                            st.session_state.xero_tenant_id = primary_org["tenantId"]
                            st.session_state.xero_tenant_name = primary_org.get("tenantName", "Demo Company (Global)")
                            
                            st.toast("Initialization complete!", icon="✅")
                            st.rerun()
                        else:
                            st.error("❌ Authentication succeeded, but no linked company profiles were found inside this account context.")
                            st.write("Raw Connection Object:", connections)
                    else:
                        st.error(f"❌ Tenant Connection lookup failed: {conn_res.text}")
                else:
                    st.error(f"❌ Xero Token Exchange Failure (HTTP {res.status_code}): {res.text}")
                    st.info("💡 Note: Authorization codes from Xero expire after single-use execution or within 5 minutes.")
            except Exception as ex:
                st.error(f"An unexpected networking error occurred: {str(ex)}")

# --- STATE 3: INTERACTIVE ACTIVE DATA HUB ---
if st.session_state.xero_tokens and st.session_state.xero_tenant_id:
    st.sidebar.success(f"🏢 Connected: {st.session_state.xero_tenant_name}")
    st.sidebar.caption(f"ID Reference: `{st.session_state.xero_tenant_id[:12]}...`")
    
    if st.sidebar.button("🔌 Close Active Session", use_container_width=True):
        st.session_state.xero_tokens = None
        st.session_state.xero_tenant_id = None
        st.session_state.xero_tenant_name = None
        st.rerun()
        
    tab1, tab2 = st.tabs(["📋 View Sales Invoices", "👥 Customer Contacts"])
    
    api_headers = {
        "Authorization": f"Bearer {st.session_state.xero_tokens['access_token']}",
        "Xero-tenant-id": st.session_state.xero_tenant_id,
        "Accept": "application/json"
    }
    
    with tab1:
        if st.button("📥 Retrieve Invoices Ledger", key="inv_action"):
            with st.spinner("Extracting transactions payload from Xero..."):
                r = requests.get("https://xero.com", headers=api_headers)
                if r.status_code == 200:
                    records = r.json().get("Invoices", [])
                    if records:
                        df = pd.json_normalize(records)
                        cols = [c for c in ["InvoiceNumber", "Type", "Status", "Total", "AmountDue", "DateString"] if c in df.columns]
                        st.dataframe(df[cols], use_container_width=True)
                    else:
                        st.info("No invoice line records found inside this demo account.")
                else:
                    st.error(f"API Connection Error ({r.status_code}): {r.text}")
                    
    with tab2:
        if st.button("📥 Retrieve Contacts Profile", key="cont_action"):
            with st.spinner("Extracting customer lists..."):
                r = requests.get("https://xero.com", headers=api_headers)
                if r.status_code == 200:
                    records = r.json().get("Contacts", [])
                    if records:
                        df = pd.json_normalize(records)
                        cols = [c for c in ["Name", "EmailAddress", "ContactStatus"] if c in df.columns]
                        st.dataframe(df[cols], use_container_width=True)
                    else:
                        st.info("No active customer contact rows found.")
                else:
                    st.error(f"API Connection Error ({r.status_code}): {r.text}")

# --- STATE 1: INITIAL OFFLINE SCREEN ---
else:
    if "code" not in query_params:
        st.info("System status: Offline. Link your live Xero application setup profiles below.")
        
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
            "state": "gigo_agentic_stable_1"
        }
        auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
        
        st.link_button(
            label="🔐 Complete Xero Handshake",
            url=auth_redirect_url,
            use_container_width=False
        )
