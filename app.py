import os
import requests
import jwt
import secrets
import hashlib
import base64
import streamlit as st
from urllib.parse import urlencode

st.set_page_config(page_title="Gigo Custom Sync Portal", layout="centered")
st.title("Gigo Custom Sync Portal")

# ------------------------------------------------------------------------
# SECRETS VERIFICATION AND ERROR LOGGING
# ------------------------------------------------------------------------
if "XERO_CLIENT_ID" not in st.secrets or "XERO_REDIRECT_URI" not in st.secrets:
    st.error("🚨 CRITICAL ERROR: Streamlit Secrets are misconfigured or blank!")
    st.info("Please make sure your Streamlit Secrets box contains exactly XERO_CLIENT_ID and XERO_REDIRECT_URI.")
    st.stop()

XERO_CLIENT_ID = str(st.secrets["XERO_CLIENT_ID"]).strip()
XERO_REDIRECT_URI = str(st.secrets["XERO_REDIRECT_URI"]).strip()

# Initialize safe local state variables
if "code_verifier" not in st.session_state:
    st.session_state.code_verifier = secrets.token_urlsafe(64)

if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}

# ------------------------------------------------------------------------
# STATE 1: Active User Session Is Open
# ------------------------------------------------------------------------
if "authenticated_user" in st.session_state:
    current_user = st.session_state.authenticated_user
    st.success(f"🎉 Login Successful! Welcome, {current_user['name']}!")
    st.json(current_user)
    
    if st.button("Log Out and Reset"):
        del st.session_state.authenticated_user
        if "xero_tokens" in st.session_state:
            del st.session_state.xero_tokens
        st.session_state.code_verifier = secrets.token_urlsafe(64)
        st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# STATE 2: Incoming Redirection Data Handler from Xero
# ------------------------------------------------------------------------
query_params = st.query_params

if "code" in query_params:
    auth_code = query_params["code"]
    
    st.info("🔄 Authorization code captured from URL! Exchanging tokens now...")

    with st.spinner("Exchanging token handshake..."):
        token_endpoint = "https://identity.xero.com/connect/token"
        
        # PKCE payload protocol rules
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
        
        response = requests.post(token_endpoint, data=payload, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            identity_claims = jwt.decode(token_data.get("id_token"), options={"verify_signature": False})
            
            xero_uid = identity_claims.get("sub")
            user_email = identity_claims.get("email")
            full_name = f"{identity_claims.get('given_name', '')} {identity_claims.get('family_name', '')}".strip() or "User"
            
            st.session_state.authenticated_user = {
                "xero_id": xero_uid, 
                "email": user_email, 
                "name": full_name
            }
            
            st.query_params.clear()
            st.rerun()
        else:
            st.error("❌ Xero API Handshake Rejected!")
            st.warning(f"HTTP Status Code: {response.status_code}")
            st.code(response.text, language="json")
            if st.button("Clear and Try Again"):
                st.query_params.clear()
                st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# STATE 3: Base Landing Page Display Screen
# ------------------------------------------------------------------------
st.write("Please click the button below to authenticate using Xero Secure Identity.")

# Generate PKCE cryptographically hashed token challenge
hashed_verifier = hashlib.sha256(st.session_state.code_verifier.encode('utf-8')).digest()
base64_encoded = base64.urlsafe_b64encode(hashed_verifier).decode('utf-8')
code_challenge = base64_encoded.replace('=', '')

oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID,
    "redirect_uri": XERO_REDIRECT_URI,
    "scope": "openid profile email",
    "state": "gigo_sync_portal_session",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256"
}

base_gateway_url = "https://login.xero.com/identity/connect/authorize"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

st.link_button(label="🔑 Sign Up / Sign In with Xero", url=xero_gate_url, type="primary")

# Print out active URL configuration details below the button to debug live variables
st.write("---")
st.subheader("🔧 Live Redirect Debugger Data")
st.write(f"**Target Redirect URI:** `{XERO_REDIRECT_URI}`")
st.write(f"**Active Client ID:** `{XERO_CLIENT_ID}`")
