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
# SECRETS RETRIEVAL LAYER (Strictly NO Client Secret Required for PKCE)
# ------------------------------------------------------------------------
try:
    # Aggressively strip spaces, line breaks, and lower-case the ID to match PKCE standards
    XERO_CLIENT_ID = str(st.secrets["XERO_CLIENT_ID"]).replace(" ", "").strip().lower()
    XERO_REDIRECT_URI = str(st.secrets["XERO_REDIRECT_URI"]).replace(" ", "").strip()
except KeyError as e:
    st.error(f"🚨 CONFIGURATION ERROR: Missing key in Streamlit Secrets: {e}")
    st.stop()

# Initialize a secure, unique cryptographic verifier string in memory
if "code_verifier" not in st.session_state:
    st.session_state.code_verifier = secrets.token_urlsafe(64)

# ------------------------------------------------------------------------
# STATE 1: Active User Session Is Open (Successful Handshake)
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
    st.query_params.clear()  # Clear params instantly to prevent loop triggers

    with st.spinner("Processing zero-secret PKCE authentication handshake..."):
        token_endpoint = "https://xero.com"
        
        # PKCE payload rules: We pass the client_id and the unhashed code_verifier instead of a secret
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
        
        # Pure frontend/browser POST request without exposing any corporate secrets
        response = requests.post(token_endpoint, data=payload, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            identity_claims = jwt.decode(token_data.get("id_token"), options={"verify_signature": False})
            
            xero_uid = identity_claims.get("sub")
            user_email = identity_claims.get("email")
            first_name = identity_claims.get('given_name', '')
            last_name = identity_claims.get('family_name', '')
            full_name = f"{first_name} {last_name}".strip() or "User"
            
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
            st.error("❌ PKCE Handshake Verification Failed!")
            st.warning(f"HTTP Status Code: {response.status_code}")
            st.code(response.text, language="json")
            if st.button("Reset and Try Again"):
                st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# STATE 3: Base Landing Page Display Screen
# ------------------------------------------------------------------------
st.write("Please click the button below to authenticate using Xero Secure Identity.")

# Cryptographically encode our local verifier string using SHA-256 for Xero
hashed_verifier = hashlib.sha256(st.session_state.code_verifier.encode('utf-8')).digest()
base64_encoded = base64.urlsafe_b64encode(hashed_verifier).decode('utf-8')
code_challenge = base64_encoded.replace('=', '')  # Remove base64 padding characters

oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID,
    "redirect_uri": XERO_REDIRECT_URI,
    "scope": "openid profile email",
    "state": "gigo_pkce_sync",
    "code_challenge": code_challenge,
    "code_challenge_method": "S256"  # Tell Xero to expect a secure SHA-256 challenge string
}

base_gateway_url = "https://xero.com"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

st.link_button(label="🔑 Sign Up / Sign In with Xero", url=xero_gate_url, type="primary")

st.write("---")
st.subheader("🔧 Live Redirect Debugger Data")
st.write(f"**Cleaned Client ID sent to Xero:** `{XERO_CLIENT_ID}`")
st.write(f"**Target Redirect URI:** `{XERO_REDIRECT_URI}`")
