import os
import requests
import jwt
import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urlencode

# ------------------------------------------------------------------------
# SECRETS RETRIEVAL LAYER (Streamlit Native Cloud Configurations)
# ------------------------------------------------------------------------
try:
    XERO_CLIENT_ID = st.secrets["XERO_CLIENT_ID"].strip()
    XERO_CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"].strip()
    XERO_REDIRECT_URI = st.secrets["XERO_REDIRECT_URI"].strip()
except KeyError as e:
    st.error(f"Missing configuration setup key inside Streamlit Advanced Secrets: {e}")
    st.info("Ensure your Secrets text area matches the exact naming constraints: XERO_CLIENT_ID, XERO_CLIENT_SECRET, XERO_REDIRECT_URI")
    st.stop()

# ------------------------------------------------------------------------
# LOCAL MEMORY ENGINE DATASTORE
# ------------------------------------------------------------------------
if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}

# Main Title Framework Layout
st.title("Gigo Custom Sync Auth Portal")

# ------------------------------------------------------------------------
# 1. EARLY EXIT ROUTE: Active Login Session Exists
# ------------------------------------------------------------------------
if "authenticated_user" in st.session_state:
    current_user = st.session_state.authenticated_user
    st.success(f"Welcome back: {current_user['name']} ({current_user['email']})")
    
    st.write("---")
    st.subheader("Your Secure Dashboard Workspace")
    st.info("You now have full access to internal workspace systems via Gigo Custom Sync.")
    
    if st.button("Log Out"):
        del st.session_state.authenticated_user
        if "xero_tokens" in st.session_state:
            del st.session_state.xero_tokens
        st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# 2. HANDSHAKE PROCESSING ROUTE: Incoming Token Swap from Xero Callback
# ------------------------------------------------------------------------
query_params = st.query_params

if "code" in query_params:
    auth_code = query_params["code"]
    st.query_params.clear()

    with st.spinner("Processing token authentication handshake..."):
        token_endpoint = "https://xero.com"
        payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': XERO_REDIRECT_URI
        }
        
        response = requests.post(
            token_endpoint, 
            data=payload, 
            auth=(XERO_CLIENT_ID, XERO_CLIENT_SECRET)
        )
        
        if response.status_code == 200:
            token_data = response.json()
            identity_claims = jwt.decode(token_data.get("id_token"), options={"verify_signature": False})
            
            xero_uid = identity_claims.get("sub")
            user_email = identity_claims.get("email")
            first_name = identity_claims.get('given_name', '')
            last_name = identity_claims.get('family_name', '')
            full_name = f"{first_name} {last_name}".strip() or "User"
            
            if xero_uid not in st.session_state.mock_db:
                st.session_state.mock_db[xero_uid] = {"email": user_email, "name": full_name}
                st.toast(f"Account registered for {user_email}!", icon="🎉")
            
            st.session_state.authenticated_user = {
                "xero_id": xero_uid, 
                "email": user_email, 
                "name": full_name
            }
            
            st.session_state.xero_tokens = {
                "access_token": token_data.get("access_token"), 
                "refresh_token": token_data.get("refresh_token")
            }
            st.rerun()
        else:
            st.error(f"Handshake validation rejected: {response.text}")
            if st.button("Back to Portal Screen"):
                st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# 3. BASE SCREEN STATE: Initial Authorization Panel Display
# ------------------------------------------------------------------------
st.write("Please sign in or register an account via Xero to unlock internal tooling dashboards.")

# Construct dynamic URL arguments safely via dictionary mapping
oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID,
    "redirect_uri": XERO_REDIRECT_URI,
    "scope": "openid profile email accounting.transactions",
    "state": "54321"
}

base_gateway_url = "https://xero.com"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

# ------------------------------------------------------------------------
# IFRAME ESCAPE JAVASCRIPT PAYLOAD
# This injects a robust click handler forcing the parent page frame out 
# ------------------------------------------------------------------------
js_escape_button = f"""
<div style="display: flex; justify-content: start;">
    <button id="oauth-btn" style="
        padding: 10px 20px; 
        background-color: #00b7e2; 
        color: white; 
        border: none; 
        border-radius: 4px; 
        cursor: pointer; 
        font-weight: bold;
        font-size: 14px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    ">
        Sign Up / Sign In with Xero
    </button>
</div>

<script>
    document.getElementById("oauth-btn").addEventListener("click", function() {{
        // Force the absolute outer container layout of the web page to redirect
        window.parent.location.href = "{xero_gate_url}";
    }});
</script>
"""

# Render the button cleanly in line using Streamlit's official HTML engine component
components.html(js_escape_button, height=60)
