import streamlit as st
import requests
import urllib.parse

# 1. Exact configurations from your setup
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]
REDIRECT_URI = "https://gigo-connect-ry7k6qptubucam3xp4sahf.streamlit.app/"
SCOPES = "openid profile email accounting.transactions accounting.contacts offline_access"

st.set_page_config(page_title="Xero Diagnostics Hub", layout="centered")
st.title("🎛️ Agentic Xero Debugging Console")

# Expose live session variables for full transparency
st.subheader("📋 Core Debugging Variables")
st.write("Is `code` present in URL parameter string?", "code" in st.query_params)
st.write("Raw URL contents detected:", st.query_params.to_dict())

# --- CRITICAL FLOW INTERCEPTOR ---
if "code" in st.query_params:
    auth_code = st.query_params["code"]
    st.success(f"📥 Intercepted Auth Code from Xero: `{auth_code[:10]}...`")
    
    st.markdown("### Step 2: Triggering Code-to-Token Exchange")
    if st.button("⚡ Execute Token Exchange Request", type="primary"):
        token_url = "https://xero.com"
        payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": REDIRECT_URI,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        with st.spinner("Dispatching POST request directly to Xero..."):
            res = requests.post(token_url, data=payload, headers=headers)
            
            st.markdown(f"**Xero Identity Gateway Server Response Status:** `{res.status_code}`")
            try:
                response_json = res.json()
                st.json(response_json)
                
                if res.status_code == 200:
                    st.success("🎉 Access Token received! Your credentials are valid.")
                    st.session_state.xero_tokens = response_json
            except Exception as parse_error:
                st.error(f"Failed to parse response payload: {str(parse_error)}")
                st.text(res.text)

# --- OFFLINE/INITIALIZATION VIEW ---
else:
    st.info("System status: Ready for handshake initialization.")
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": "gigo_agentic_debug_123"
    }
    auth_redirect_url = f"https://xero.com?{urllib.parse.urlencode(params)}"
    
    # Official native Streamlit link button component
    st.link_button(
        label="🔐 Start Xero Handshake",
        url=auth_redirect_url,
        use_container_width=True
    )
