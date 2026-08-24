import streamlit as st
import requests
import uuid

# ==============================================================================
# 1. CONFIGURATION (Drawn securely from Streamlit Secrets)
# ==============================================================================
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = st.secrets["XERO_REDIRECT_URI"]

# 🟢 THE REAL FIXED ENDPOINTS - DO NOT SET THESE TO JUST XERO.COM
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
CONNECTIONS_URL = "https://xero.com"
INVOICES_URL = "https://xero.com"

# URL encoded scopes for stable OAuth handshake
SCOPES = "openid%20profile%20email%20accounting.transactions.read%20accounting.settings.read%20offline_access"

# ==============================================================================
# 2. STREAMLIT PAGE SETUP & SESSION MANAGEMENT
# ==============================================================================
st.set_page_config(page_title="Xero Mock Data Dashboard", layout="wide")
st.title("📊 Xero Demo Data Fetcher")

# Initialize session state tracking
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
    
    if "code" in query_params:
        auth_code = query_params["code"]
        
        with st.spinner("Exchanging code for access token..."):
            payload = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": REDIRECT_URI
            }
            try:
                response = requests.post(
                    TOKEN_URL, 
                    data=payload, 
                    auth=(CLIENT_ID, CLIENT_SECRET)
                )
                response.raise_for_status()
                token_data = response.json()
                st.session_state.auth_token = token_data.get("access_token")
                
                # Clear parameters to reset state safely
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Failed to fetch token. Check your Secret keys. Error: {e}")
    else:
        st.info("You need to connect to your Xero Developer Account to pull mock data.")
        
        # Build URL parameters dynamically using secret data values
        state_key = str(uuid.uuid4())
        login_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}&state={state_key}"
        
        # Native layout breakouts bypass frame blocks automatically
        st.link_button("🔗 Connect to Xero Demo Company", login_url, type="primary")

# ==============================================================================
# STEP 2: RECOVERY OF TENANT AND API DATA QUERIES
# ==============================================================================
else:
    headers = {
        "Authorization": f"Bearer {st.session_state.auth_token}",
        "Content-Type": "application/json"
    }

    if not st.session_state.tenant_id:
        try:
            conn_response = requests.get(CONNECTIONS_URL, headers=headers)
            conn_response.raise_for_status()
            connections = conn_response.json()
            
            if connections:
                # Store tenant details safely inside state memory arrays
                st.session_state.tenant_id = connections[0]["tenantId"]
                st.session_state.tenant_name = connections[0]["tenantName"]
                st.rerun()
            else:
                st.error("No active connections found. Please activate your Xero Demo Company.")
        except Exception as e:
            st.error(f"Failed to fetch Xero connections: {e}")

    if st.session_state.tenant_id:
        st.success(f"Connected to Xero Organisation: **{st.session_state.tenant_name}**")
        
        headers["Xero-tenant-id"] = st.session_state.tenant_id
        
        if st.button("🔄 Fetch Mock Invoices"):
            with st.spinner("Pulling data from Xero API..."):
                try:
                    data_response = requests.get(INVOICES_URL, headers=headers)
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
                                "Due Date": inv.get("DueDateString", "N/A"),
                                "Status": inv.get("Status", "N/A"),
                                "Total Amount": inv.get("Total", 0.0),
                                "Amount Due": inv.get("AmountDue", 0.0)
                            })
                        
                        st.dataframe(clean_invoices, use_container_width=True)
                    else:
                        st.warning("No invoices found in your Demo Company environment.")
                        
                except Exception as e:
                    st.error(f"Error fetching data from API: {e}")
                    
        if st.sidebar.button("Disconnect Xero"):
            st.session_state.auth_token = None
            st.session_state.tenant_id = None
            st.session_state.tenant_name = None
            st.rerun()
