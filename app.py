import os
import secrets
import requests
import jwt
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Xero Application Setup Variables
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID")
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET")
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI")  # Must be your Streamlit URL, e.g., http://localhost:8501/

# ------------------------------------------------------------------------
# MOCK LOCAL ENGINE DATABASE
# Replace these methods with your pure MongoDB, PostgreSQL, or local data layers.
# ------------------------------------------------------------------------
if "mock_db" not in st.session_state:
    st.session_state.mock_db = {}  # Format: { xero_id: {"email": "", "name": ""} }

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
# APPLICATION SESSION CONTROLLER
# ------------------------------------------------------------------------
st.title("Gigo Connect Auth Portal")

# Check if user session variable already exists inside browser execution state
if "authenticated_user" in st.session_state:
    user = st.session_state.authenticated_user
    st.success(f"Successfully authenticated as: {user['name']} ({user['email']})")
    
    if st.button("Log Out"):
        del st.session_state.authenticated_user
        if "xero_tokens" in st.session_state:
            del st.session_state.xero_tokens
        st.rerun()

else:
    # Read browser query strings dynamically to detect if Xero sent the user back
    query_params = st.query_params

    if "code" in query_params:
        # ---> STREAMLIT CALLBACK PROCESSING MODE  SIGN UP PROCESS ACTION
                        user_record = save_new_user(xero_uid, user_email, full_name)
                        st.toast(f"Welcome aboard, created account for {user_email}!", icon="🎉")
                    else:
                        # Email exists from prior setups, join identity to the current Xero ID
                        st.session_state.mock_db[xero_uid] = {"email": user_email, "name": user_record["name"]}
                        user_record = find_user_by_xero_id(xero_uid)
                
                # ---> SIGN IN PROCESS ACTION
                # Anchor validation fields into state to flag rendering logic
                st.session_state.authenticated_user = {
                    "xero_id": xero_uid,
                    "email": user_record["email"],
                    "name": user_record["name"]
                }
                
                # Save resource keys safely to perform API tracking downstream
                st.session_state.xero_tokens = {
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token")
                }
                st.rerun()
            else:
                st.error(f"Xero credential verification failed: {response.text}")
                if st.button("Return to Landing Panel"):
                    st.rerun()

    else:
        # ---> STANDARD APP LANDING PANEL MODE '
            f'<button style="padding:10px 20px; background-color:#00b7e2; color:white; '
            f'border:none; border-radius:4px; cursor:pointer; font-weight:bold;">'
            f'Sign Up / Sign In with Xero'
            f'</button></a>', 
            unsafe_allow_html=True
        )
