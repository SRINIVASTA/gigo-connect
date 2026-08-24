import streamlit as st
import requests
import uuid

# 1. Configuration - Replace with your Xero Developer Portal credentials
CLIENT_ID = "YOUR_XERO_CLIENT_ID"
CLIENT_SECRET = "YOUR_XERO_CLIENT_SECRET"
REDIRECT_URI = "https://gigo-connect-hjju63sxucd3un9fqmcvev.streamlit.app/"  # Default Streamlit local URL

# Xero OAuth 2.0 Endpoints
AUTH_URL = "https://xero.com"
TOKEN_URL = "https://xero.com"
CONNECTIONS_URL = "https://xero.com"
INVOICES_URL = "https://xero.com"

# Required Scopes to read data from the Demo Company
# 🔴 Change this in your app.py configuration section
SCOPES = "openid%20profile%20email%20accounting.transactions.read%20accounting.settings.read%20offline_access"

st.set_page_config(page_title="Xero Mock Data Dashboard", layout="wide")
st.title("📊 Xero Demo Data Fetcher")

# Initialize Session State variables
if "auth_token" not in st.session_state:
    st.session_state.auth_token = None
if "tenant_id" not in st.session_state:
    st.session_state.tenant_id = None

# Step 1: Authentication Flow
if not st.session_state.auth_token:
    # Check if returning from Xero authorization redirect
    query_params = st.query_params
    if "code" in query_params:
        auth_code = query_params["code"]
        
        # Exchange authorization code for access token
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
                
                # Clear query parameters to clean up URL
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Failed to fetch token: {e}")
    else:
        # Show Login Button if not authenticated
        st.info("You need to connect to your Xero Developer Account to pull mock data.")
        
        # Generate authorization login URL
        state_key = str(uuid.uuid4())
        login_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPES}&state={state_key}"
        
        # 👇 REPLACE YOUR OLD st.markdown BLOCK WITH THIS:
        st.link_button("🔗 Connect to Xero Demo Company", login_url, type="primary")

# Step 2: Authenticated State - Fetch Connections and Data
else:
    headers = {
        "Authorization": f"Bearer {st.session_state.auth_token}",
        "Content-Type": "application/json"
    }

    # Fetch Tenant ID (Organization) dynamically if missing
    if not st.session_state.tenant_id:
        try:
            conn_response = requests.get(CONNECTIONS_URL, headers=headers)
            conn_response.raise_for_status()
            connections = conn_response.json()
            
            if connections:
                # Target the Demo Company organization linked to your account
                st.session_state.tenant_id = connections[0]["tenantId"]
                st.session_state.tenant_name = connections[0]["tenantName"]
                st.rerun()
            else:
                st.error("No connected organizations found. Please link a Demo Company in your Xero Developer Portal.")
        except Exception as e:
            st.error(f"Failed to fetch Xero connections: {e}")

    # Display Connected Dashboard
    if st.session_state.tenant_id:
        st.success(f"Connected to Connected Organization: **{st.session_state.tenant_name}**")
        
        # Add Xero Tenant ID header for data requests
        headers["Xero-tenant-id"] = st.session_state.tenant_id
        
        # Action Button to Fetch Mock Invoices
        if st.button("🔄 Fetch Mock Invoices"):
            with st.spinner("Pulling data from Xero..."):
                try:
                    data_response = requests.get(INVOICES_URL, headers=headers)
                    data_response.raise_for_status()
                    invoices_data = data_response.json().get("Invoices", [])
                    
                    if invoices_data:
                        st.write(f"### Found {len(invoices_data)} Mock Invoices")
                        
                        # Process and structure data for Streamlit display
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
                        
                        # Render interactive data table
                        st.dataframe(clean_invoices, use_container_width=True)
                    else:
                        st.warning("No invoices found in your Demo Company.")
                        
                except Exception as e:
                    st.error(f"Error fetching data from API: {e}")
                    
        # Log out option
        if st.sidebar.button("Disconnect Xero"):
            st.session_state.auth_token = None
            st.session_state.tenant_id = None
            st.rerun()
