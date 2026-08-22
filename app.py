import streamlit as st
import requests
import pandas as pd

# Load client variables safely out of backend keys
CLIENT_ID = st.secrets["XERO_CLIENT_ID"]
CLIENT_SECRET = st.secrets["XERO_CLIENT_SECRET"]

st.set_page_config(page_title="Gigo Connect x Xero", layout="wide")
st.title("🚀 Gigo Connect: Fully Automated Xero Sync Engine")
st.caption("Machine-to-Machine Integration Node (No Browser Login Required)")

# --- AGENTIC BACKGROUND CONNECT LOOP ---
@st.cache_data(show_spinner="Establishing encrypted link directly with Xero Core API...")
def fetch_xero_ledger_data(endpoint_route):
    # Step 1: Request a direct machine-to-machine Token via client_credentials grant
    token_url = "https://xero.com"
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    
    try:
        token_res = requests.post(token_url, data=token_payload, headers=token_headers)
        
        if token_res.status_code != 200:
            return {"error": f"Token verification rejected (HTTP {token_res.status_code}): {token_res.text}"}
            
        access_token = token_res.json().get("access_token")
        
        # Step 2: Get the underlying tenant linkage
        connections_url = "https://xero.com"
        conn_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        conn_res = requests.get(connections_url, headers=conn_headers)
        
        if conn_res.status_code != 200:
            return {"error": f"Tenant extraction failed: {conn_res.text}"}
            
        connections = conn_res.json()
        if not connections or not isinstance(connections, list):
            return {"error": "No valid organizational connections linked to this credential set."}
            
        tenant_id = connections[0]["tenantId"]
        tenant_name = connections[0].get("tenantName", "Xero Shared Ledger")
        
        # Step 3: Fetch the actual ledger data requested by the workspace
        data_url = f"https://xero.com{endpoint_route}"
        api_headers = {
            "Authorization": f"Bearer {access_token}",
            "Xero-tenant-id": tenant_id,
            "Accept": "application/json"
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

# --- LIVE WORKSPACE INTERFACE ---
tab1, tab2 = st.tabs(["📋 Live Sales Invoices Ledger", "👥 Customer Contact Profiles"])

with tab1:
    st.subheader("Invoices Ledger")
    if st.button("📥 Synchronize Invoices Now", key="sync_inv"):
        result = fetch_xero_ledger_data("Invoices")
        
        if "error" in result:
            st.error(result["error"])
            st.info("💡 Troubleshooting Tip: Make sure your app in the Xero Developer Portal is set to a 'Custom Connection' type and linked to your Demo Company.")
        else:
            st.success(f"Successfully pulled records from organization: **{result['tenant_name']}**")
            records = result["payload"]
            if records:
                df = pd.json_normalize(records)
                display_cols = [c for c in ["InvoiceNumber", "Type", "Status", "Total", "AmountDue", "DateString"] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.info("No recorded invoices discovered inside this asset ledger.")

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
                display_cols = [c for c in ["Name", "EmailAddress", "ContactStatus", "UpdatedDateUTC"] if c in df.columns]
                st.dataframe(df[display_cols], use_container_width=True)
            else:
                st.info("No saved client contact logs found.")
