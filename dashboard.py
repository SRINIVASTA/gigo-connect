import streamlit as st
import requests
import uuid
from urllib.parse import urlencode

# Standard xero-python SDK architecture paths
from xero_python.accounting import AccountingApi
from xero_python.identity import IdentityApi
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.exceptions import ApiException

# ==============================================================================
# 1. APPLICATION CONFIGURATION
# ==============================================================================
CLIENT_ID = "6EF08EA4B68548BDAB9C66AB44820A14"
CLIENT_SECRET = "PASTE_YOUR_REAL_XERO_CLIENT_SECRET_HERE" # 👈 Put your real secret password here!
REDIRECT_URI = "https://gigo-connect-b9jsvgyo56lnxhi6juansy.streamlit.app/"

# Initialise client configuration layers
config = Configuration(
    oauth2_token=OAuth2Token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)
api_client = ApiClient(configuration=config)

# ==============================================================================
# 2. UI LAYOUT & MEMORY STATES Setup
# ==============================================================================
st.set_page_config(page_title="Xero SDK Dashboard", layout="wide")
st.title("📊 Xero Direct Native SDK Engine")

if "token_set" not in st.session_state:
    st.session_state.token_set = None
if "xero_tenant_id" not in st.session_state:
    st.session_state.xero_tenant_id = None
if "xero_tenant_name" not in st.session_state:
    st.session_state.xero_tenant_name = None

# ==============================================================================
# STEP 1: AUTHENTICATION FLOW VIA NATIVE SDK LINK
# ==============================================================================
if not st.session_state.token_set:
    query_params = st.query_params
    
    if "code" in query_params:
        auth_code = query_params["code"]
        with st.spinner("Exchanging token set via Python SDK..."):
            try:
                token_set = api_client.get_oauth2_token_by_code(
                    auth_code, 
                    client_id=CLIENT_ID, 
                    client_secret=CLIENT_SECRET, 
                    redirect_uri=REDIRECT_URI
                )
                st.session_state.token_set = token_set
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"SDK Token Validation Failed: {e}")
    else:
        st.info("Application initialized. Click below to connect directly to your Xero sandbox data.")
        
        state_key = str(uuid.uuid4())
        scopes_string = "openid profile email accounting.transactions.read accounting.settings.read offline_access"
        
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": scopes_string,
            "state": state_key
        }
        
        login_url = f"https://login.xero.com/identity/connect/authorize?{urlencode(params)}"
        st.link_button("🔗 Connect to Xero Demo Company", login_url, type="primary")

# ==============================================================================
# STEP 2: RECOVERY OF LIVE ORG REFERENCES AND TRANSACTION INVOICES
# ==============================================================================
else:
    api_client.set_oauth2_token(st.session_state.token_set)
    identity_instance = IdentityApi(api_client)

    if not st.session_state.xero_tenant_id:
        try:
            with st.spinner("Recovering connected organization context parameters..."):
                connections = identity_instance.get_connections()
                
                # 🟢 SDK FIX: Extract properties using index references from the array model list
                if connections and len(connections) > 0:
                    target_connection = connections[0]
                    st.session_state.xero_tenant_id = target_connection.tenant_id
                    st.session_state.xero_tenant_name = target_connection.tenant_name
                    st.rerun()
                else:
                    st.error("No active Sandbox connections linked to your account profile.")
        except ApiException as e:
            st.error(f"Xero SDK Exception during parameters parsing: {e}")

    # Connected Active State Layout
    if st.session_state.xero_tenant_id:
        st.success(f"Connected to Organisation: **{st.session_state.xero_tenant_name}**")
        accounting_instance = AccountingApi(api_client)
        
        if st.button("🔄 Fetch Live Invoices"):
            with st.spinner("Extracting transactions data objects..."):
                try:
                    api_response = accounting_instance.get_invoices(st.session_state.xero_tenant_id)
                    invoices_list = api_response.invoices
                    
                    if invoices_list:
                        st.write(f"### Found {len(invoices_list)} Invoices")
                        
                        clean_data = []
                        for inv in invoices_list:
                            clean_data.append({
                                "Invoice Code": getattr(inv, "invoice_number", "N/A"),
                                "Contact Client": getattr(inv.contact, "name", "N/A") if inv.contact else "N/A",
                                "Gross Value": getattr(inv, "total", 0.0)
                            })
                        
                        st.dataframe(clean_data, use_container_width=True)
                    else:
                        st.warning("No invoices found in your Demo Company dataset environment.")
                except ApiException as e:
                    st.error(f"Accounting instance read execution failure: {e}")
                    
        if st.sidebar.button("Disconnect Session"):
            st.session_state.token_set = None
            st.session_state.xero_tenant_id = None
            st.session_state.xero_tenant_name = None
            st.rerun()
