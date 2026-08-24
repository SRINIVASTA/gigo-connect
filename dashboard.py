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
# 1. FIXED APPLICATION CONFIGURATION
# ==============================================================================
CLIENT_ID = "6EF08EA4B68548BDAB9C66AB44820A14"
REDIRECT_URI = "https://gigo-connect-b9jsvgyo56lnxhi6juansy.streamlit.app/"

# ==============================================================================
# 2. UI LAYOUT & MEMORY STATES SETUP
# ==============================================================================
st.set_page_config(page_title="Xero Direct Dashboard", layout="wide")
st.title("📊 Xero Direct Data Dashboard")

# Initialize structural properties to manage page states safely
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None
if "client_secret" not in st.session_state:
    st.session_state.client_secret = None

# ==============================================================================
# STEP 1: CLIENT SECRET PASSWORD INPUT & AUTHENTICATION HANDSHAKE
# ==============================================================================
if not st.session_state.auth_token:
    
    # 🟢 ASK FOR CLIENT SECRET LIKE A PASSWORD FIELD ON SCREEN
    if not st.session_state.client_secret:
        st.info("🔐 Security Setup Required")
        input_secret = st.text_input(
            label="Enter your Xero Client Secret:",
            type="password",
            help="Copy Client Secret 1 from your Xero Developer Portal and paste it here safely.",
            placeholder="Pasting your secret masks characters like a password..."
        )
        
        if st.button("Confirm and Save Secret"):
            if input_secret.strip() != "":
                st.session_state.client_secret = input_secret.strip()
                st.rerun()
            else:
                st.warning("Please enter a valid Client Secret string.")
        st.stop() # Freeze the UI here until they enter the password secret

    # Initialize client configuration layers natively using the user's password secret
    config = Configuration(
        oauth2_token=OAuth2Token(
            client_id=CLIENT_ID,
            client_secret=st.session_state.client_secret
        )
    )
    api_client = ApiClient(configuration=config)

    query_params = st.query_params
    
    # Process code if redirected back from Xero gate
    if "code" in query_params:
        auth_code = query_params["code"]
        with st.spinner("Exchanging authorization code for token..."):
            try:
                response = api_client.get_oauth2_token_by_code(
                    auth_code, 
                    client_id=CLIENT_ID, 
                    client_secret=st.session_state.client_secret, 
                    redirect_uri=REDIRECT_URI
                )
                st.session_state.auth_token = response
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Token exchange failed. Double check your Client Secret password. Error: {e}")
                # Reset secret state on failure so they can try re-typing it
                st.session_state.client_secret = None
                if st.button("Reset Secret Input"):
                    st.rerun()
    else:
        st.success("✅ Client Secret Loaded Natively into App Memory.")
        st.info("Click below to connect directly to your secure Xero authorization dashboard screen.")
        
        state_key = str(uuid.uuid4())
        scopes = "openid profile email accounting.transactions.read accounting.settings.read offline_access"
        
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": scopes,
            "state": state_key
        }
        
        login_url = f"https://xero.com?{urlencode(params)}"
        st.link_button("🔗 Connect to Xero Demo Company", login_url, type="primary")

# ==============================================================================
# STEP 2: ORGANISATION TARGETING & DATA FETCHING
# ==============================================================================
else:
    # Setup configuration layers with existing active token sets
    config = Configuration(
        oauth2_token=OAuth2Token(
            client_id=CLIENT_ID,
            client_secret=st.session_state.client_secret
        )
    )
    api_client = ApiClient(configuration=config)
    api_client.set_oauth2_token(st.session_state.auth_token)
    
    identity_instance = IdentityApi(api_client)

    if not st.session_state.tenant_id:
        try:
            with st.spinner("Recovering connected organization context parameters..."):
                connections = identity_instance.get_connections()
                
                if connections and len(connections) > 0:
                    target_connection = connections[0]
                    st.session_state.tenant_id = target_connection.tenant_id
                    st.session_state.tenant_name = target_connection.tenant_name
                    st.rerun()
                else:
                    st.error("No active connected Xero organizations found. Please connect a Demo Company.")
        except ApiException as e:
            st.error(f"Xero SDK Exception during parameters parsing: {e}")

    # Display data dashboard once tenant arrays are extracted successfully
    if st.session_state.tenant_id:
        st.sidebar.markdown(f"🔒 **Connected Org:**\n{st.session_state.tenant_name}")
        st.success(f"Connected Directly to Xero Organisation: **{st.session_state.tenant_name}**")
        
        accounting_instance = AccountingApi(api_client)
        
        if st.button("🔄 Fetch Live Invoices"):
            with st.spinner("Streaming tables from Xero Core Accounting Database..."):
                try:
                    api_response = accounting_instance.get_invoices(st.session_state.tenant_id)
                    invoices_list = api_response.invoices
                    
                    if invoices_list:
                        st.write(f"### Found {len(invoices_list)} Real-Time Invoices")
                        clean_invoices = [
                            {
                                "Invoice ID": getattr(inv, "invoice_number", "N/A"), 
                                "Client Name": getattr(inv.contact, "name", "N/A") if inv.contact else "N/A", 
                                "Invoice Date": getattr(inv, "date", "N/A"),
                                "Gross Value": getattr(inv, "total", 0.0)
                            } 
                            for inv in invoices_list
                        ]
                        st.dataframe(clean_invoices, use_container_width=True)
                    else:
                        st.warning("No invoices found inside your current Xero Demo Company dataset.")
                except ApiException as e:
                    st.error(f"Failed to load invoice transaction datastream: {e}")
                    
        if st.sidebar.button("Disconnect Session & Wipe Memory"):
            st.session_state.auth_token = None
            st.session_state.tenant_id = None
            st.session_state.tenant_name = None
            st.session_state.client_secret = None
            st.rerun()
