import streamlit as st
import requests
import uuid
import secrets
import hashlib
import base64
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
REDIRECT_URI = "https://gigo-connect-b9jsvgyo56lnxhi6juansy.streamlit.app/"

# Initialise client configuration layers
config = Configuration(
    oauth2_token=OAuth2Token(
        client_id=CLIENT_ID
    )
)
api_client = ApiClient(configuration=config)

# Helper function to generate structural PKCE safety pairs
def generate_pkce_pair():
    verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(verifier.encode('utf-8')).digest()
    challenge = base64.urlsafe_b64encode(hashed).decode('utf-8').replace('=', '').replace('+', '-').replace('/', '_')
    return verifier, challenge

# ==============================================================================
# 2. UI LAYOUT & MEMORY STATES SETUP
# ==============================================================================
st.set_page_config(page_title="Xero PKCE Dashboard", layout="wide")
st.title("📊 Xero PKCE Native SDK Engine")

if "token_set" not in st.session_state:
    st.session_state.token_set = None
if "xero_tenant_id" not in st.session_state:
    st.session_state.xero_tenant_id = None
if "xero_tenant_name" not in st.session_state:
    st.session_state.xero_tenant_name = None
if "pkce_verifier" not in st.session_state:
    st.session_state.pkce_verifier = None
if "client_secret" not in st.session_state:
    st.session_state.client_secret = None

# ==============================================================================
# STEP 1: AUTHENTICATION FLOW VIA SECURE HANDSHAKE
# ==============================================================================
if not st.session_state.token_set:
    
    # 🔐 Password Prompt for Client Secret
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
        st.stop()

    query_params = st.query_params
    
    if "code" in query_params:
        auth_code = query_params["code"]
        with st.spinner("Exchanging token set via Python SDK PKCE Engine..."):
            try:
                # PKCE Exchange using our state verifier
                response = requests.post(
                    "https://xero.com", 
                    data={
                        "grant_type": "authorization_code",
                        "client_id": CLIENT_ID,
                        "client_secret": st.session_state.client_secret,
                        "code": auth_code,
                        "redirect_uri": REDIRECT_URI,
                        "code_verifier": st.session_state.pkce_verifier
                    }
                )
                response.raise_for_status()
                st.session_state.token_set = response.json()
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"PKCE Token Exchange Failed: {e}")
                st.session_state.client_secret = None  # Reset to let them re-try
    else:
        st.success("✅ Client Secret Loaded Natively into App Memory.")
        st.info("PKCE Authorization initialized. Click below to securely connect.")
        
        if not st.session_state.pkce_verifier:
            verifier, challenge = generate_pkce_pair()
            st.session_state.pkce_verifier = verifier
            st.session_state.pkce_challenge = challenge

        state_key = str(uuid.uuid4())
        
        params = {
            "response_type": "code",
            "client_id": CLIENT_ID,
            "redirect_uri": REDIRECT_URI,
            "scope": "openid profile email accounting.transactions.read accounting.settings.read offline_access",
            "state": state_key,
            "code_challenge": st.session_state.pkce_challenge,
            "code_challenge_method": "S256"
        }
        
        # 🟢 CORRECTED LINK GATEWAY: Targets login.xero.com instead of marketing xero.com
        login_url = f"https://xero.com?{urlencode(params)}"
        
        st.link_button("🔗 Connect via Secure PKCE Engine", login_url, type="primary")

# ==============================================================================
# STEP 2: LIVE ORGANISATION CONTEXT AND DATA FETCHING
# ==============================================================================
else:
    # Build complete configuration layer object
    config = Configuration(
        oauth2_token=OAuth2Token(
            client_id=CLIENT_ID,
            client_secret=st.session_state.client_secret
        )
    )
    api_client = ApiClient(configuration=config)
    api_client.set_oauth2_token(st.session_state.token_set)
    
    identity_instance = IdentityApi(api_client)

    if not st.session_state.xero_tenant_id:
        try:
            with st.spinner("Recovering connected organization context parameters..."):
                connections = identity_instance.get_connections()
                
                if connections and len(connections) > 0:
                    target_connection = connections[0]
                    st.session_state.xero_tenant_id = target_connection.tenant_id
                    st.session_state.xero_tenant_name = target_connection.tenant_name
                    st.rerun()
                else:
                    st.error("No active connected Xero organizations found. Please link a Demo Company.")
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
                            # 🟢 FIXED: Removed the trailing extra parenthesis character typo
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
            st.session_state.pkce_verifier = None
            st.session_state.client_secret = None
            st.rerun()
