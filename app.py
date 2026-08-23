import os
import requests
import jwt
import base64
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Gigo Custom Sync Engine")

# ------------------------------------------------------------------------
# ENVIRONMENT VARIABLES SETUP
# ------------------------------------------------------------------------
XERO_CLIENT_ID = os.getenv("XERO_CLIENT_ID", "").strip()
XERO_CLIENT_SECRET = os.getenv("XERO_CLIENT_SECRET", "").strip()
XERO_REDIRECT_URI = os.getenv("XERO_REDIRECT_URI", "").strip()

# Local memory store to display the user data after login
db_user_store = {}

# ------------------------------------------------------------------------
# 1. ROUTE: Root Landing Page (Renders a standard clean HTML button)
# ------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def landing_page():
    if db_user_store:
        profile_html = "".join([f"<li><b>{k}:</b> {v}</li>" for k, v in db_user_store.items()])
        return f"""
        <html>
            <body style="font-family: Arial, sans-serif; margin: 40px; text-align: center;">
                <h1 style="color: #00b7e2;">🎉 Login Successful!</h1>
                <div style="background: #f4f4f4; padding: 20px; border-radius: 8px; display: inline-block; text-align: left;">
                    <h3>👤 Authenticated User Payload Data</h3>
                    <ul>{profile_html}</ul>
                </div>
                <br/><br/>
                <a href="/clear" style="color: red; text-decoration: none; font-weight: bold;">Log Out and Reset</a>
            </body>
        </html>
        """

    # Build standard clean OAuth configurations
    oauth_params = {
        "response_type": "code",
        "client_id": XERO_CLIENT_ID,
        "redirect_uri": XERO_REDIRECT_URI,
        "scope": "openid profile email accounting.transactions.read",
        "state": "gigo_fastapi_sync"
    }
    
    base_gateway_url = "https://xero.com"
    xero_gate_url = f"{base_gateway_url}?{urlencode(oauth_params)}"

    return f"""
    <html>
        <body style="font-family: Arial, sans-serif; margin: 50px; text-align: center;">
            <h2>Gigo Custom Sync Portal (FastAPI Engine)</h2>
            <p>Please click the button below to authorize using Xero Secure Identity.</p>
            <br/>
            <a href="{xero_gate_url}" target="_self">
                <button style="padding: 12px 24px; background-color: #00b7e2; color: white; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 15px; box-shadow: 0px 4px 6px rgba(0,0,0,0.1);">
                    🔑 Sign Up / Sign In with Xero
                </button>
            </a>
        </body>
    </html>
    """

# ------------------------------------------------------------------------
# 2. ROUTE: Callback Endpoint (Captures the data returning from Xero)
# ------------------------------------------------------------------------
@app.get("/callback")
def auth_callback(code: str = None, error: str = None):
    if error:
        return HTMLResponse(content=f"<h3 style='color:red;'>Xero Authorization Denied: {error}</h3>", status_code=400)
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code.")

    token_endpoint = "https://xero.com"
    
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': XERO_REDIRECT_URI
    }
    
    # Enforce standard Base64 Basic Auth headers for Web Apps
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
        
        global db_user_store
        db_user_store = {
            "xero_id": identity_claims.get("sub"),
            "email": identity_claims.get("email"),
            "name": f"{identity_claims.get('given_name', '')} {identity_claims.get('family_name', '')}".strip() or "User"
        }
        
        return RedirectResponse(url="/")
    else:
        return HTMLResponse(content=f"<h3>❌ Xero API Handshake Rejected!</h3><pre>{response.text}</pre>", status_code=400)

@app.get("/clear")
def clear_session():
    global db_user_store
    db_user_store.clear()
    return RedirectResponse(url="/")

if __name__ == "__main__":
    import uvicorn
    # Starts the FastAPI app locally on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
