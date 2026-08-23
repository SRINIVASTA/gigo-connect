import os
import requests
import jwt
import secrets
import hashlib
import base64
import streamlit as st
from urllib.parse import urlencode

# ------------------------------------------------------------------------
# SECRETS RETRIEVAL LAYER (No Client Secret Required for PKCE)
# ------------------------------------------------------------------------
try:
    XERO_CLIENT_ID = st.secrets["XERO_CLIENT_ID"].strip()
    XERO_REDIRECT_URI = st.secrets["XERO_REDIRECT_URI"].strip()
except KeyError as e:
    st.error(f"🚨 CONFIGURATION ERROR: Missing key in Streamlit Secrets: {e}")
    st.stop()

# Initialize localized PKCE cryptographic verification tokens in memory
if "code_verifier" not in st.session_state:
    # Generate an unguessable high-entropy state verifier string
    st.session_state.code_verifier = secrets.token_urlsafe(64)

if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}

st.title("Gigo Custom Sync Auth Portal")

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
        st.session_state.code_verifier = secrets.token_urlsafe(64)
        st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# 2. HANDSHAKE PROCESSING ROUTE: PKCE Token Exchange Callback Loop
# ------------------------------------------------------------------------
query_params = st.query_params

if "code" in query_params:
    auth_code = query_params["code"]

    with st.spinner("Processing zero-secret PKCE authentication handshake..."):
        token_endpoint = "https://xero.com"
        
        # PKCE requires passing the plaintext verifier string during the POST swap
        payload = {
            'grant_type': 'authorization_code',
            'client_id': XERO_CLIENT_ID,
            'code': auth_code,
            'redirect_uri': XERO_REDIRECT_URI,
            'code_verifier': st.session_state.code_verifier
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Execute direct backend POST without embedding dangerous client secrets
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
            st.error("❌ PKCE Handshake Verification Rejected by Xero!")
            st.write(f"Server Error Log: {response.text}")
            if st.button("Reset Portal"):
                st.query_params.clear()
                st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# 3. BASE SCREEN STATE: Initial PKCE Authorization Trigger Display
# ------------------------------------------------------------------------
st.write("Please sign in or register an account via Xero to unlock internal tooling dashboards.")

# Cryptographically encode the verifier string using SHA-256 for the outbound challenge
hashed_verifier = hashlib.sha256(st.session_state.code_verifier.encode('utf-8')).digest()
base64_encoded = base64.urlsafe_b64encode(hashed_verifier).decode('utf-8')
code_challenge = base64_encoded.replace('=', '') # Strip trailing padding characters

oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID,
    "redirect_uri": XERO_REDIRECT_URI,
    "scope": "openid profile email accounting.transactions.read",
    "state": "pkce_secure_session",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256" # Inform Xero we are using secure SHA-256
}

base_gateway_url = "https://xero.com"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

st.link_button(label="Sign Up / Sign In with Xero (Secure PKCE)", url=xero_gate_url, type="primary")
