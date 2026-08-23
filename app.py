import os
import secrets
import requests
import jwt
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# App Credentials Configuration
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI")

# Mock Local Memory Store 
if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}

# Session Controller Title Block
st.title("Gigo Connect Auth Portal")

# 1. EARLY EXIT: If user session cookie exists, run dashboard layout instantly
if "authenticated_user" in st.session_state:
    current_user = st.session_state.authenticated_user
    st.success(f"Welcome back: {current_user['name']} ({current_user['email']})")
    if st.button("Log Out"):
        del st.session_state.authenticated_user
        if "xero_tokens" in st.session_state:
            del st.session_state.xero_tokens
        st.experimental_rerun()
    st.stop()  # Strictly stops Streamlit executing past this threshold line

# 2. CALLBACK DECODER LAYER: Check for incoming URL callback query parameters
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
        response = requests.post(token_endpoint, data=payload, auth=(XERO_CLIENT_ID, XERO_CLIENT_SECRET))
        
        if response.status_code == 200:
            token_data = response.json()
            identity_claims = jwt.decode(token_data.get("id_token"), options={"verify_signature": False})
            
            xero_uid = identity_claims.get("sub")
            user_email = identity_claims.get("email")
            full_name = f"{identity_claims.get('given_name', '')} {identity_claims.get('family_name', '')}".strip() or "User"
            
            # Simple registration lookup layer
            if xero_uid not in st.session_state.mock_db:
                st.session_state.mock_db[xero_uid] = {"email": user_email, "name": full_name}
                st.toast(f"Account registered for {user_email}!", icon="🎉")
                
            st.session_state.authenticated_user = {"xero_id": xero_uid, "email": user_email, "name": full_name}
            st.session_state.xero_tokens = {"access_token": token_data.get("access_token"), "refresh_token": token_data.get("refresh_token")}
            st.experimental_rerun()
        else:
            st.error(f"Handshake failed: {response.text}")
            if st.button("Back to Login"):
                st.experimental_rerun()
    st.stop()

# 3. BASE LANDING GATEWAY: Displayed when no active session or code parameter exists
st.write("Please sign in or register an account via Xero to unlock internal tooling dashboards.")
scopes = "openid profile email accounting.transactions"
xero_gate_url = f"https://xero.com{XERO_CLIENT_ID}&redirect_uri={XERO_REDIRECT_URI}&scope={scopes}&state={secrets.token_hex(16)}"

st.markdown(
    f'<a href="{xero_gate_url}" target="_self">'
    f'<button style="padding:10px 20px; background-color:#00b7e2; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">'
    f'Sign Up / Sign In with Xero'
    f'</button></a>', 
    unsafe_allow_html=True
)
