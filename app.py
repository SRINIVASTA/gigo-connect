import streamlit as st
import requests
import uuid

# ==============================================================================
# 1. READ SECRETS SAFELY (Drawn securely from Streamlit Cloud Secrets)
# ==============================================================================
try:
    CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
    CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
    REDIRECT_URI = st.secrets["XERO_REDIRECT_URI"]
except KeyError as e:
    st.error(f"Missing configuration key in Streamlit Secrets: {e}")
    st.stop()

# ==============================================================================
# 2. STREAMLIT PAGE SETUP & STATE INITIALIZATION
# ==============================================================================
st.set_page_config(page_title="Xero Mock Data Dashboard", layout="wide")
st.title("📊 Xero Demo Data Fetcher")

# 🟢 CRITICAL INITIALIZATION FIX: Prevents AttributeError
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None
if "tenant_name" not in st.session_state:
    st.session_state.tenant_name = None

# ==============================================================================
# STEP 1: AUTHENTICATION FLOW
# ==============================================================================
if not st.session_state.auth_token:
    query_params = st.query_params
    
    # Process return code payload
    if "code" in query_params:
        auth_code = query_params["code"]
        
        with st.spinner("Exchanging code for access token..."):
            payload = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": REDIRECT_URI
            }
            try:
                # Direct API Call - Direct to production token endpoint
                response = requests.post(
                    "https://identity.xero.com/connect/token", 
                    data=payload, 
                    auth=(CLIENT_ID, CLIENT_SECRET)
                )
                response.raise_for_status()
                token_data = response.json()
                st.session_state.auth_token = token_data.get("access_token")
                
                # Clear URL params
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Failed to fetch token: {e}")
    else:
        st.info("Connect to Xero Demo Company to pull data.")
        
        state_key = str(uuid.uuid4())
        scopes_encoded = "openid%20profile%20email%20accounting.transactions.read%20accounting.settings.read%20offline_access"
        
        # 🟢 SECURE HARDCOUPLED TARGET: Points strictly to login.xero.com
        login_url = f"https://xero.com{CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scopes_encoded}&state={state_key}"

        
        st.link_button("🔗 Connect to Xero Demo Company", login_url, type="primary")

# ==============================================================================
# STEP 2: RECOVERY OF TENANT AND API DATA QUERIES
# ==============================================================================
else:
    headers = {
        "Authorization": f"Bearer {st.session_state.auth_token}",
        "Content-Type": "application/json"
    }

    # Fetch active Demo Organization properties
    if not st.session_state.tenant_id:
        try:
            conn_response = requests.get("https://xero.com", headers=headers)
            conn_response.raise_for_status()
            connections = conn_response.json()
            
            if connections:
                st.session_state.tenant_id = connections[0]["tenantId"]
                st.session_state.tenant_name = connections[0]["tenantName"]
                st.rerun()
            else:
                st.error("No active connections found.")
        except Exception as e:
            st.error(f"Failed to fetch Xero connections: {e}")

    # Render data
    if st.session_state.tenant_id:
        st.success(f"Connected to Xero Organisation: **{st.session_state.tenant_name}**")
        
        headers["Xero-tenant-id"] = st.session_state.tenant_id
        
        if st.button("🔄 Fetch Mock Invoices"):
            with st.spinner("Pulling data from Xero API..."):
                try:
                    data_response = requests.get("https://api.xero.com/api.xro/2.0/Invoices", headers=headers)
                    data_response.raise_for_status()
                    invoices_data = data_response.json().get("Invoices", [])
                    
                    if invoices_data:
                        st.write(f"### Found {len(invoices_data)} Mock Invoices")
                        
                        clean_invoices = []
                        for inv in invoices_data:
                            clean_invoices.append({
                                "Invoice Number": inv.get("InvoiceNumber", "N/A"),
                                "Contact": inv.get("Contact", {}).get("Name", "N/A"),
                                "Date": inv.get("DateString", "N/A"),
                                "Total Amount": inv.get("Total", 0.0),
                            })
                        
                        st.dataframe(clean_invoices, use_container_width=True)
                    else:
                        st.warning("No invoices found.")
                        
                except Exception as e:
                    st.error(f"Error fetching data: {e}")
                    
        # Sidebar logout
        if st.sidebar.button("Disconnect Xero"):
            st.session_state.auth_token = None
            st.session_state.tenant_id = None
            st.session_state.tenant_name = None
            st.rerun()
