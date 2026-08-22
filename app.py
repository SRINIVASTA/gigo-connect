import streamlit as st
import requests
import pandas as pd

# Load configurations securely from Streamlit Cloud Secrets
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🚀 Gigo Connect: Fully Automated Xero Sync Engine")
st.caption("Machine-to-Machine Integration Node (No Browser Login Required)")

@st.cache_data(show_spinner="Establishing encrypted link directly with Xero Core API...")
def fetch_xero_ledger_data(endpoint_route):
    # Step 1: Request token via direct client_credentials grant
    token_url = "https://xero.com"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    
    # FIX: Explicit User-Agent string bypasses CloudFront's HTTP method restriction block
    token_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        token_res = requests.post(token_url, data=token_payload, headers=token_headers)
        
        if token_res.status_code != 200:
            return {"error": f"Token verification rejected (HTTP {token_res.status_code}): {token_res.text}"}
            
        access_token = token_res.json().get("access_token")
        
        # Step 2: Extract target tenant linkage 
        connections_url = "https://xero.com"
        conn_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        conn_res = requests.get(connections_url, headers=conn_headers)
        
        if conn_res.status_code != 200:
            return {"error": f"Tenant extraction failed: {conn_res.text}"}
            
        connections = conn_res.json()
        if not connections or not isinstance(connections, list):
            return {"error": "No valid organizational connections discovered linked to this credential set."}
            
        # Isolate index dictionary 0 mapping arrays securely
        primary_connection = connections[0]
        tenant_id = primary_connection["tenantId"]
        tenant_name = primary_connection.get("tenantName", "Demo Company (Global)")
        
        # Step 3: Pull real-time data from core endpoint
        data_url = f"https://xero.com{endpoint_route}"
        api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Xero-tenant-id": tenant_id,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        data_res = requests.get(data_url, headers=api_headers)
        if data_res.status_code == 200:
            return {
                "success": True, 
                "tenant_name": tenant_name, 
                "payload": data_res.json().get(endpoint_route, [])
            }
        else:
            return {"error": f"API Endpoint request rejected: {data_res.text}"}
            
    except Exception as network_error:
        return {"error": f"An unhandled background connection fault occurred: {str(network_error)}"}

# --- LIVE UI WORKSPACE PANELS ---
tab1, tab2 = st.tabs(["📋 Live Sales Invoices Ledger", "👥 Customer Contact Profiles"])

with tab1:
    st.subheader("Invoices Ledger")
    if st.button("📥 Synchronize Invoices Now", key="sync_inv"):
        result = fetch_xero_ledger_data("Invoices")
        
        if "error" in result:
            st.error(result["error"])
        else:
            st.success(f"Successfully pulled records from organization: **{result['tenant_name']}**")
            records = result["payload"]
            if records:
                df = pd.json_normalize(records)
                display_cols = [c for c in ["InvoiceNumber", "Type", "Status", "Total", "AmountDue", "DateString"] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.info("No recorded invoices discovered inside this account asset ledger.")

with tab2:
    st.subheader("Contact Master Directory")
    if st.button("📥 Synchronize Contacts Now", key="sync_cont"):
        result = fetch_xero_ledger_data("Contacts")
        
        if "error" in result:
            st.error(result["error"])
        else:
            st.success(f"Successfully pulled records from organization: **{result['tenant_name']}**")
            records = result["payload"]
            if records:
                df = pd.json_normalize(records)
                display_cols = [c for c in ["Name", "EmailAddress", "ContactStatus"] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.info("No saved client contact logs discovered.")
