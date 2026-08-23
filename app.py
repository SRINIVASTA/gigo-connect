import os
import requests
import jwt
import secrets
import streamlit as st
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
            
            st.query_params.clear()
            st.rerun()
        else:
            st.error(f"Handshake validation rejected by Xero: {response.text}")
            if st.button("Back to Portal Screen"):
                st.query_params.clear()
                st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# 3. BASE SCREEN STATE: Initial Authorization Panel Display
# ------------------------------------------------------------------------
st.write("Please sign in or register an account via Xero to unlock internal tooling dashboards.")

# CRITICAL SECURITY FIX: Generate an absolute unique dynamic state on every render loop
dynamic_state = secrets.token_hex(16)

oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID,
    "redirect_uri": XERO_REDIRECT_URI,
    "scope": "openid profile email",
    "state": dynamic_state
}

base_gateway_url = "https://xero.com"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

st.link_button(
    label="Sign Up / Sign In with Xero", 
    url=xero_gate_url, 
    type="primary"
)
