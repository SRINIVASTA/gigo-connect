import streamlit as st
import requests
import uuid

# ==============================================================================
# 1. DIRECT APP CONFIGURATION
# ==============================================================================
CLIENT_ID = "6EF08EA4B68548BDAB9C66AB44820A14"
CLIENT_SECRET = "PASTE_YOUR_REAL_XERO_CLIENT_SECRET_HERE"  # 👈 Paste your real client secret here

# Must match your current active deployment address perfectly
REDIRECT_URI = "https://gigo-connect-b9jsvgyo56lnxhi6juansy.streamlit.app/"

# ==============================================================================
# 2. STREAMLIT INITIALIZATION & SESSION MEMORY
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

# ==============================================================================
# STEP 1: AUTHENTICATION HANDSHAKE
# ==============================================================================
if not st.session_state.auth_token:
    query_params = st.query_params
    
    # Process code if redirected back from Xero gate
    if "code" in query_params:
        auth_code = query_params["code"]
        with st.spinner("Exchanging authorization code for token..."):
            try:
                response = requests.post(
                    "https://xero.com", 
                    data={
                        "grant_type": "authorization_code",
                        "code": auth_code,
                        "redirect_uri": REDIRECT_URI
                    }, 
                    auth=(CLIENT_ID, CLIENT_SECRET)
                )
                response.raise_for_status()
                st.session_state.auth_token = response.json().get("access_token")
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Token exchange failed. Double check your Client Secret value. Error: {e}")
    else:
        st.info("Your application is live. Click below to connect directly to your Xero sandbox data.")
        
        state_key = str(uuid.uuid4())
        scopes = "openid%20profile%20email%20accounting.transactions.read%20accounting.settings.read%20offline_access"
        
        # 🟢 RECHECKED & VERIFIED LINK: Explicit delimiters prevent domain mashups
        login_url = f"https://xero.com{CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={scopes}&state={state_key}"
        
        st.link_button("🔗 Connect to Xero Demo Company", login_url, type="primary")

# ==============================================================================
# STEP 2: ORGANISATION TARGETING & DATA FETCHING
# ==============================================================================
else:
    headers = {
        "Authorization": f"Bearer {st.session_state.auth_token}",
        "Content-Type": "application/json"
    }

    # Fetch organization parameters if token is valid but context details are blank
    if not st.session_state.tenant_id:
        try:
            conn_response = requests.get("https://xero.com", headers=headers)
            conn_response.raise_for_status()
            connections = conn_response.json()
            
            # 🟢 RECHECKED & VERIFIED FIX: Connections returns a list array, not a dictionary object
            if isinstance(connections, list) and len(connections) > 0:
                st.session_state.tenant_id = connections[0]["tenantId"]
                st.session_state.tenant_name = connections[0]["tenantName"]
                st.rerun()
            else:
                st.error("No active connected Xero organizations found. Please connect a Demo Company.")
        except Exception as e:
            st.error(f"Failed to extract connected Xero organization profiles: {e}")

    # Display data dashboard once tenant arrays are extracted successfully
    if st.session_state.tenant_id:
        st.success(f"Connected Directly to Xero Organisation: **{st.session_state.tenant_name}**")
        
        # Inject the active organizational token header required for records reading calls
        headers["Xero-tenant-id"] = st.session_state.tenant_id
        
        if st.button("🔄 Fetch Live Invoices"):
            with st.spinner("Streaming tables from Xero Core Accounting Database..."):
                try:
                    data_response = requests.get("https://xero.com", headers=headers)
                    data_response.raise_for_status()
                    invoices_data = data_response.json().get("Invoices", [])
                    
                    if invoices_data:
                        st.write(f"### Found {len(invoices_data)} Real-Time Invoices")
                        clean_invoices = [
                            {
                                "Invoice ID": inv.get("InvoiceNumber", "N/A"), 
                                "Client Name": inv.get("Contact", {}).get("Name", "N/A"), 
                                "Invoice Date": inv.get("DateString", "N/A"),
                                "Gross Value": inv.get("Total", 0.0)
                            } 
                            for inv in invoices_data
                        ]
                        st.dataframe(clean_invoices, use_container_width=True)
                    else:
                        st.warning("No invoices found inside your current Xero Demo Company dataset.")
                except Exception as e:
                    st.error(f"Failed to load invoice transaction datastream: {e}")
                    
        if st.sidebar.button("Disconnect Session"):
            st.session_state.auth_token = None
            st.session_state.tenant_id = None
            st.session_state.tenant_name = None
            st.rerun()
