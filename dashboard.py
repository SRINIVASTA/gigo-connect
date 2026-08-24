import streamlit as st
import uuid
from xero_python.api import accounting_api, identity_api
from xero_python.api_client import ApiClient, Configuration
from xero_python.api_client.oauth2 import OAuth2Token
from xero_python.exceptions import ApiException

# ==============================================================================
# 1. SDK CONFIGURATION INITIALIZATION
# ==============================================================================
# Hardcoded to match your exact requested app profile values 
CLIENT_ID = "6EF08EA4B68548BDAB9C66AB44820A14"
CLIENT_SECRET = "PASTE_YOUR_REAL_XERO_CLIENT_SECRET_HERE" # 👈 Put your password secret here!
REDIRECT_URI = "https://gigo-connect-b9jsvgyo56lnxhi6juansy.streamlit.app/"

# Initialise standard SDK client structures natively
config = Configuration(
    oauth2_token=OAuth2Token(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
)
api_client = ApiClient(configuration=config)

# ==============================================================================
# 2. UI LAYOUT & MEMORY STATES SETUP
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
                # 🟢 SDK handles the authorization token swap natively behind the scenes
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
        
        # Scopes array items map to explicit permissions strings requested
        scopes = ["openid", "profile", "email", "accounting.transactions.read", "accounting.settings.read", "offline_access"]
        state_key = str(uuid.uuid4())
        
        # 🟢 NATIVE SDK BUILDER: Formats parameters perfectly to bypass xero.com6ef0... typo bugs
        login_url = api_client.get_authorization_url(
            client_id=CLIENT_ID,
            redirect_uri=REDIRECT_URI,
            scope=scopes,
            state=state_key
        )
        
        st.link_button("🔗 Connect to Xero Demo Company", login_url, type="primary")

# ==============================================================================
# STEP 2: RECOVERY OF REVENUE METRICS AND LIVE INVOICES
# ==============================================================================
else:
    # Hydrate configuration token profiles back into the client layer framework
    api_client.set_oauth2_token(st.session_state.token_set)
    identity_instance = identity_api.IdentityApi(api_client)

    if not st.session_state.xero_tenant_id:
        try:
            with st.spinner("Recovering connected organization parameters..."):
                connections = identity_instance.get_connections()
                
                if connections and len(connections) > 0:
                    # Select the primary connection mapping layout
                    target_connection = connections[0]
                    st.session_state.xero_tenant_id = target_connection.tenant_id
                    st.session_state.xero_tenant_name = target_connection.tenant_name
                    st.rerun()
                else:
                    st.error("No active connections found. Please check your Demo Company settings.")
        except ApiException as e:
            st.error(f"Xero SDK Parameter Extraction Exception: {e}")

    # Display Active Live Dashboard UI Elements
    if st.session_state.xero_tenant_id:
        st.success(f"Connected to Xero Organisation: **{st.session_state.xero_tenant_name}**")
        accounting_instance = accounting_api.AccountingApi(api_client) #
        
        if st.button("🔄 Fetch Live Invoices"):
            with st.spinner("Extracting invoice records data blocks..."):
                try:
                    # Read records data directly via accounting client components
                    api_response = accounting_instance.get_invoices(st.session_state.xero_tenant_id)
                    invoices_list = api_response.invoices
                    
                    if invoices_list:
                        st.write(f"### Found {len(invoices_list)} Invoices")
                        
                        clean_list = []
                        for inv in invoices_list:
                            clean_list.append({
                                "Invoice Code": getattr(inv, "invoice_number", "N/A"),
                                "Contact Client": getattr(inv.contact, "name", "N/A") if inv.contact else "N/A",
                                "Gross Total": getattr(inv, "total", 0.0)
                            })
                        
                        st.dataframe(clean_list, use_container_width=True)
                    else:
                        st.warning("No invoices found in your Demo Company database.")
                except ApiException as e:
                    st.error(f"Accounting instance read execution failure: {e}")
                    
        if st.sidebar.button("Disconnect Session"):
            st.session_state.token_set = None
            st.session_state.xero_tenant_id = None
            st.session_state.xero_tenant_name = None
            st.rerun()
