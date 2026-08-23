import os
import secrets
import requests
import jwt
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Xero Application Credentials
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI")  # e.g., http://localhost:8501/

# ------------------------------------------------------------------------
# LOCAL DATA LOOKUP ENGINE
# ------------------------------------------------------------------------
if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}  # Schema representation: {xero_id: {email, name}}

def find_user_by_xero_id(xero_id):
    return st.session_state.mock_db.get(xero_id)

def find_user_by_email(email):
    for uid, profile in st.session_state.mock_db.items():
        if profile["email"] == email:
            return {"xero_id": uid, **profile}
    return None

def save_new_user(xero_id, email, name):
    st.session_state.mock_db[xero_id] = {"email": email, "name": name}
    return {"xero_id": xero_id, **st.session_state.mock_db[xero_id]}

# ------------------------------------------------------------------------
# UI RENDERING & ROUTER LOGIC
# ------------------------------------------------------------------------
st.title("Gigo Connect Auth Portal")

# Route Block A: User has an active login session running
if "authenticated_user" in st.session_state:
    current_user = st.session_state.authenticated_user
    st.success(f"Successfully authenticated as: {current_user['name']} ({current_user['email']})")
    
    if st.button("Log Out"):
        del st.session_state.authenticated_user
        if "xero_tokens" in st.session_state:
            del st.session_state.xero_tokens
        st.experimental_rerun()

# Route Block B: User does not have a session cookie initialized
else:
    # Check if user was just sent back from Xero with an authorization token
    query_params = st.query_params

    if "code" in query_params:
        # ---> HANDSHAKE ROUTE MODE  SIGN UP NEW VISITOR
                        user_record = save_new_user(xero_uid, user_email, full_name)
                        st.toast(f"Account registered for {user_email}!", icon="🎉")
                    else:
                        # ACTION -> LINK ACCOUNTS FOR INCOMING SIGN IN
                        st.session_state.mock_db[xero_uid] = {"email": user_email, "name": user_record["name"]}
                        user_record = find_user_by_xero_id(xero_uid)
                
                # Initialize state session cookies into memory
                st.session_state.authenticated_user = {
                    "xero_id": xero_uid,
                    "email": user_record["email"],
                    "name": user_record["name"]
                }
                st.session_state.xero_tokens = {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token")
                }
                st.experimental_rerun()
            else:
                st.error(f"Xero token authentication error: {response.text}")
                if st.button("Back to Login Panel"):
                    st.experimental_rerun()

    else:
        # ---> SIGN IN / SIGN UP LANDING SCREEN PANEL '
            f'<button style="padding:10px 20px; background-color:#00b7e2; color:white; '
            f'border:none; border-radius:4px; cursor:pointer; font-weight:bold;">'
            f'Sign Up / Sign In with Xero'
            f'</button></a>', 
            unsafe_allow_html=True
        )
