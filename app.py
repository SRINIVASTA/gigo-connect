import os
import secrets
import requests
import jwt
import streamlit as st
from urllib.parse import urlencode

# 3. BASE SCREEN STATE: Render initial authorization request portal layout
st.write("Please sign in or register an account via Xero to unlock internal tooling dashboards.")

# Use standard urllib dict encoding to build an exploit-proof query structure
oauth_params = {
    "response_type": "code",
    "client_id": XERO_CLIENT_ID.strip(),
    "redirect_uri": XERO_REDIRECT_URI.strip(),
    "scope": "openid profile email accounting.transactions",
    "state": secrets.token_hex(16)
}

# Explicitly attaches to the immutable base identity gateway URL path
base_gateway_url = "https://login.xero.com/identity/connect/authorize"
xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

st.markdown(
    f'<a href="{xero_gate_url}" target="_self">'
    f'<button style="padding:10px 20px; background-color:#00b7e2; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">'
    f'Sign Up / Sign In with Xero'
    f'</button></a>', 
    unsafe_allow_html=True
)

# ------------------------------------------------------------------------
# LOCAL MEMORY ENGINE DATASTORE
# ------------------------------------------------------------------------
if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}

# Main Title Framework Layout
st.title("Gigo Connect Auth Portal")

# 1. EARLY BLOCK: Handle persistent login state instantly if it exists
if "authenticated_user" in st.session_state:
    current_user = st.session_state.authenticated_user
    st.success(f"Welcome back: {current_user['name']} ({current_user['email']})")
    if st.button("Log Out"):
        del st.session_state.authenticated_user
        if "xero_tokens" in st.session_state:
            del st.session_state.xero_tokens
        st.rerun()
    st.stop()

# 2. HANDSHAKE PROCESSING: Process incoming token swap parameters from Xero
query_params = st.query_params

if "code" in query_params:
    auth_code = query_params["code"]
    st.query_params.clear()  # Strip active code query components instantly

    with st.spinner("Processing token authentication handshake..."):
        token_endpoint = "https://xero.com"
        payload = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': XERO_REDIRECT_URI
        }
        
        # Execute direct backend network validation handshake request
        response = requests.post(token_endpoint, data=payload, auth=(XERO_CLIENT_ID, XERO_CLIENT_SECRET))
        
        if response.status_code == 200:
            token_data = response.json()
            identity_claims = jwt.decode(token_data.get("id_token"), options={"verify_signature": False})
            
            xero_uid = identity_claims.get("sub")
            user_email = identity_claims.get("email")
            full_name = f"{identity_claims.get('given_name', '')} {identity_claims.get('family_name', '')}".strip() or "User"
            
            # Registration Mapping Checks
            if xero_uid not in st.session_state.mock_db:
                st.session_state.mock_db[xero_uid] = {"email": user_email, "name": full_name}
                st.toast(f"Account registered for {user_email}!", icon="🎉")
                
            st.session_state.authenticated_user = {"xero_id": xero_uid, "email": user_email, "name": full_name}
            st.session_state.xero_tokens = {"access_token": token_data.get("access_token"), "refresh_token": token_data.get("refresh_token")}
            st.rerun()
        else:
            st.error(f"Handshake validation rejected: {response.text}")
            if st.button("Back to Portal Screen"):
                st.rerun()
    st.stop()

# 3. BASE SCREEN STATE: Render initial authorization request portal layout
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
