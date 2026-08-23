import os
import requests
import jwt
import secrets
import base64
import streamlit as st
from urllib.parse import urlencode

st.set_page_config(page_title="Gigo Custom Sync Portal", layout="centered")
st.title("Gigo Custom Sync Portal")

# ------------------------------------------------------------------------
# SECRETS RETRIEVAL LAYER (With Runtime Sanitation)
# ------------------------------------------------------------------------
if "XERO_CLIENT_ID" not in st.secrets or "XERO_CLIENT_SECRET" not in st.secrets or "XERO_REDIRECT_URI" not in st.secrets:
    st.error("🚨 CONFIGURATION ERROR: Missing keys inside Streamlit Secrets panel!")
    st.info("Ensure your Secrets text area matches exactly: XERO_CLIENT_ID, XERO_CLIENT_SECRET, XERO_REDIRECT_URI")
    st.stop()

XERO_CLIENT_ID = str(st.secrets["XERO_CLIENT_ID"]).strip()
XERO_CLIENT_SECRET = str(st.secrets["XERO_CLIENT_SECRET"]).strip()
XERO_REDIRECT_URI = str(st.secrets["XERO_REDIRECT_URI"]).strip()

# Initialize dynamic security state seed
if "oauth_state" not in st.session_state:
    st.session_state.oauth_state = secrets.token_hex(8)

# ------------------------------------------------------------------------
# STATE 1: Active User Session Is Open (Successful Login)
# ------------------------------------------------------------------------
if "authenticated_user" in st.session_state:
    current_user = st.session_state.authenticated_user
    st.success(f"🎉 Login Successful! Welcome, {current_user['name']}!")
    
    st.write("---")
    st.subheader("👤 Authenticated Profile Details")
    st.json(current_user)
    
    if st.button("Log Out and Reset"):
        del st.session_state.authenticated_user
        if "xero_tokens" in st.session_state:
            del st.session_state.xero_tokens
        st.session_state.oauth_state = secrets.token_hex(8)
        st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# STATE 2: Incoming Redirection Data Handler from Xero
# ------------------------------------------------------------------------
query_params = st.query_params

if "code" in query_params:
    auth_code = query_params["code"]
    st.query_params.clear()  # Clear query params instantly to prevent duplicate-tab loops

    with st.spinner("Exchanging token handshake with Xero..."):
        token_endpoint = "https://xero.com"
        
        payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': XERO_REDIRECT_URI
        }
        
        # Mandatory requirement: Generate base64-encoded HTTP Basic Auth Header
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
            st.error("❌ Xero API Handshake Rejected!")
            st.warning(f"HTTP Status Code: {response.status_code}")
            st.code(response.text, language="json")
            if st.button("Clear and Try Again"):
                st.rerun()
    st.stop()

# ------------------------------------------------------------------------
# STATE 3: Base Landing Page Display Screen
# ------------------------------------------------------------------------
st.write("Please click the button below to authenticate using Xero Secure Identity.")

oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID,
    "redirect_uri": XERO_REDIRECT_URI,
    "scope": "openid profile email accounting.transactions.read accounting.settings.read offline_access",
    "state": st.session_state.oauth_state
}

base_gateway_url = "https://login.xero.com/identity/connect/authorize"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

# CRITICAL IFRAME BREAKOUT FIX: Injects an absolute native redirect script 
# that forces the top level tab view container window out to the xero authentication target url
st.html(f"""
    <div style="display: flex; justify-content: start; margin-top: 10px;">
        <button onclick="window.top.location.href='{xero_gate_url}'" style="
            padding: 12px 24px; 
            background-color: #00b7e2; 
            color: white; 
            border: none; 
            border-radius: 6px; 
            cursor: pointer; 
            font-weight: bold;
            font-size: 15px;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
        ">
            🔑 Sign Up / Sign In with Xero
        </button>
    </div>
""")

st.write("---")
st.subheader("🔧 Live Redirect Debugger Data")
st.write(f"**Target Redirect URI:** `{XERO_REDIRECT_URI}`")
st.write(f"**Active Client ID:** `{XERO_CLIENT_ID}`")
