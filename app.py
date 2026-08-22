import streamlit as strl
import pandas as pd
import numpy as np
import requests
import base64
import time
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

# -------------------------------------------------------------------------
# INITIAL SYSTEM LAYER CONFIGURATION
# -------------------------------------------------------------------------
strl.set_page_config(page_title="gigo-xero Engine", layout="wide")
strl.title("🛡️ gigo-xero: Live Unsupervised ML Bookkeeping Engine")
strl.caption("Production Data Ingestion Pipeline with Dual-Channel Routing Control")
strl.divider()

# Core Workspace Cache Layers
if "xero_tokens" not in strl.session_state: strl.session_state["xero_tokens"] = None
if "xero_df" not in strl.session_state: strl.session_state["xero_df"] = None
if "uploaded_df" not in strl.session_state: strl.session_state["uploaded_df"] = None

# LOAD INGESTION AND SUB-CLASSIFICATION CONFIGS FROM TOML
ML_CONFIG = strl.secrets.get("ML_CONFIG", {})
SUB_CLASSIFICATION = strl.secrets.get("SUB_CLASSIFICATION", {})

if not ML_CONFIG or not SUB_CLASSIFICATION:
    strl.error("⚠️ Configuration Error: [ML_CONFIG] or [SUB_CLASSIFICATION] sections missing from secrets.toml!")
    strl.stop()

# Helper Export Converters
def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

def convert_df_to_xlsx(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Clustered Bookkeeping')
    return output.getvalue()

# Ingestion Selector UI
st_selection = strl.radio(
    "Select Target Bookkeeping Data Feed:",
    ["Sync Directly with Xero Live API", "Upload Local Bookkeeping Files (CSV / XLSX)"],
    horizontal=True
)

active_matrix_df = None

if st_selection == "Sync Directly with Xero Live API":
    if strl.session_state["xero_tokens"] is None:
        strl.warning("🔐 Data Ingestion Locked: Authentication required.")
        # Setup dummy URL for visual routing
        auth_link = "https://xero.com"
        strl.link_button("🚀 Secure Connect to Xero API App", auth_link)
    else:
        active_matrix_df = strl.session_state["xero_df"]
else:
    uploaded_file = strl.file_uploader("Drop transaction worksheets here", type=["csv", "xlsx"])
    if uploaded_file is not None:
        try:
            parsed_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            if "Clean Description" not in parsed_df.columns:
                text_match = [col for col in parsed_df.columns if any(x in col.lower() for x in ["desc", "ref", "sms", "text", "particular"])]
                if text_match:
                    parsed_df.rename(columns={text_match[0]: "Clean Description"}, inplace=True)
                else:
                    parsed_df["Clean Description"] = "Manual Data Entry Item"
            strl.session_state["uploaded_df"] = parsed_df
        except Exception as e:
            strl.error(f"File reading exception: {e}")
    active_matrix_df = strl.session_state["uploaded_df"]
# -------------------------------------------------------------------------
# HYBRID AI PIPELINE: TOML RULES + UNSUPERVISED K-MEANS
# -------------------------------------------------------------------------
strl.markdown("---")
strl.subheader("🤖 Unsupervised Clustering Analytics Engine")

if active_matrix_df is not None and not active_matrix_df.empty:
    df_ml = active_matrix_df.copy()
    
    # 1. APPLY ML_CONFIG GARBAGE FILTERS
    garbage_list = ML_CONFIG.get("GARBAGE_FLAGS", [])
    # Drop rows that contain any garbage keywords in their descriptions
    initial_count = len(df_ml)
    df_ml = df_ml[~df_ml['Clean Description'].astype(str).str.contains('|'.join(garbage_list), case=False, na=False)]
    dropped_count = initial_count - len(df_ml)
    
    if dropped_count > 0:
        strl.info(f"🧹 Data Cleansing: Automatically dropped {dropped_count} corrupted system entries based on TOML parameters.")

    strl.subheader(f"📈 Filtered Transaction Extraction Matrix ({len(df_ml)} rows)")
    strl.dataframe(df_ml, use_container_width=True)
    
    num_clusters = strl.slider("Select Target Bookkeeping Clusters (K-Means)", min_value=2, max_value=5, value=3)
    
    with strl.spinner("Running Hybrid Semantic Segmentations..."):
        try:
            # 2. RUN K-MEANS MACHINE LEARNING
            vectorizer = TfidfVectorizer(stop_words='english', max_features=200)
            X = vectorizer.fit_transform(df_ml['Clean Description'].astype(str))
            kmeans = KMeans(n_clusters=num_clusters, random_state=42, n_init=10)
            df_ml['Predicted Cluster Bucket'] = kmeans.fit_predict(X)
            
            # Determine top cluster terms for primary layout headers
            order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]
            terms = vectorizer.get_feature_names_out()
            
            # 3. APPLY SUB_CLASSIFICATION TOKEN PATTERNS
            def assign_sub_class(desc):
                desc_lower = str(desc).lower()
                # Check text strings against your explicit TOML rules
                for class_name, keywords in SUB_CLASSIFICATION.items():
                    if any(kw.lower() in desc_lower for kw in keywords):
                        return class_name
                # Fall back to matching top special company tokens from your TOML config
                if any(x.lower() in desc_lower for x in ML_CONFIG.get("APPLE_TOKENS", [])): return "APPLE DIGITAL ACCESS"
                if any(x.lower() in desc_lower for x in ML_CONFIG.get("DHABI_TOKENS", [])): return "EMIRATES EMIR TAX"
                if any(x.lower() in desc_lower for x in ML_CONFIG.get("CREDIT_TOKENS", [])): return "INCOMING FINANCIAL REVENUE"
                return "Unclassified Transaction"

            # Apply mapping logic across rows
            df_ml['Accounting Sub-Class Label'] = df_ml['Clean Description'].apply(assign_sub_class)
            strl.success("🤖 Hybrid Processing Complete! Applied TOML patterns and K-Means models.")
            
            # 4. RENDER ACCORDIONS WITH AUTO-LABEL HEADERS
            for cluster_id in range(num_clusters):
                top_words = [terms[ind] for ind in order_centroids[cluster_id, :3]]
                human_label = " / ".join(top_words).title()
                
                with strl.expander(f"📁 Cluster Category Group #{cluster_id}: 【 {human_label} 】"):
                    cluster_subset = df_ml[df_ml['Predicted Cluster Bucket'] == cluster_id]
                    
                    # Reorder layout grid columns to put the new dynamic label front and center
                    render_cols = ['Invoice Number', 'Contact Name', 'Clean Description', 'Accounting Sub-Class Label', 'Total Amount', 'Status']
                    valid_cols = [c for c in render_cols if c in cluster_subset.columns]
                    strl.dataframe(cluster_subset[valid_cols], use_container_width=True)
                    
                    # Action buttons
                    col1, col2, _ = strl.columns()
                    with col1:
                        strl.download_button(label="📥 Export to CSV", data=convert_df_to_csv(cluster_subset), file_name=f"cluster_{cluster_id}.csv", mime="text/csv", key=f"dl_csv_{cluster_id}")
                    with col2:
                        strl.download_button(label="📊 Export to Excel", data=convert_df_to_xlsx(cluster_subset), file_name=f"cluster_{cluster_id}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"dl_xlsx_{cluster_id}")
                        
        except Exception as ml_err:
            strl.error(f"Error compiling semantic metadata structure: {ml_err}")
else:
    strl.info("Awaiting data pipeline initialization parameters to apply hybrid TOML validation rules.")
