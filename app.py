import os
import requests
import jwt
import secrets
import base64
import streamlit as st
from urllib.parse import urlencode

# ------------------------------------------------------------------------
# DIAGNOSTIC CHECK: Validate Streamlit Secrets Natively
# ------------------------------------------------------------------------
st.title("Gigo Custom Sync Auth Portal")

# Auto-detect if secrets are even visible to the script instance
if not st.secrets.keys():
    st.error("🚨 CRITICAL ERROR: Streamlit Secrets are completely empty!")
    st.info("Go to your Streamlit Cloud Dashboard -> Settings -> Secrets and paste your configuration keys.")
    st.stop()

try:
    XERO_CLIENT_ID = str(st.secrets["XERO_CLIENT_ID"]).strip()
    XERO_CLIENT_SECRET = str(st.secrets["XERO_CLIENT_SECRET"]).strip()
    XERO_REDIRECT_URI = str(st.secrets["XERO_REDIRECT_URI"]).strip()
except Exception as e:
    st.error(f"🚨 CONFIGURATION ERROR: Missing or misnamed key: {e}")
    st.info("Your keys must be named exactly: XERO_CLIENT_ID, XERO_CLIENT_SECRET, and XERO_REDIRECT_URI")
    st.stop()

# ------------------------------------------------------------------------
# LOCAL MEMORY ENGINE DATASTORE
# ------------------------------------------------------------------------
if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}

# ------------------------------------------------------------------------
# 1. EARLY EXIT ROUTE: Active Login Session Exists
# ------------------------------------------------------------------------
if "authenticated_user" in st.session_state:
    current_user = st.session_state.authenticated_user
    st.success(f"Welcome back: {current_user['name']} ({current_user['email']})")
    
    st.write("---")
    st.subheader("Your Secure Dashboard Workspace")
    st.json(current_user)
    
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

    with st.spinner("Processing token authentication handshake..."):
        token_endpoint = "https://xero.com"
        
        payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': XERO_REDIRECT_URI
        }
        
        # Explicit HTTP Basic Auth Header Generation
        raw_auth_string = f"{XERO_CLIENT_ID}:{XERO_CLIENT_SECRET}"
        encoded_auth_bytes = base64.b64encode(raw_auth_string.encode("utf-8"))
        encoded_auth_string = encoded_auth_bytes.decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {encoded_auth_string}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        response = requests.post(token_endpoint, data=payload, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            identity_claims = jwt.decode(token_data.get("id_token"), options={"verify_signature": False})
            
            xero_uid = identity_claims.get("sub")
            user_email = identity_claims.get("email")
            full_name = f"{identity_claims.get('given_name', '')} {identity_claims.get('family_name', '')}".strip() or "User"
            
            if xero_uid not in st.session_state.mock_db:
                st.session_state.mock_db[xero_uid] = {"email": user_email, "name": full_name}
            
            st.session_state.authenticated_user = {
                "xero_id": xero_uid, 
                "email": user_email, 
                "name": full_name
            }
            st.session_state.xero_tokens = {
                "access_token": token_data.get("access_token"), 
                "refresh_token": token_data.get("refresh_token")
            }
            
            st.query_params.clear()
            st.rerun()
        else:
            st.error("❌ Handshake Validation Rejected by Xero!")
            st.write(f"Server Response: {response.text}")
            if st.button("Back to Portal Screen"):
                st.query_params.clear()
                st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# 3. BASE SCREEN STATE: Initial Authorization Panel Display
# ------------------------------------------------------------------------
st.write("Please sign in or register an account via Xero to unlock internal tooling dashboards.")

# Use basic identity validation scopes to ensure absolute compatibility
oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID,
    "redirect_uri": XERO_REDIRECT_URI,
    "scope": "openid profile email",
    "state": "12345678"
}

base_gateway_url = "https://xero.com"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

# Render the button cleanly
st.link_button(label="Sign Up / Sign In with Xero", url=xero_gate_url, type="primary")
