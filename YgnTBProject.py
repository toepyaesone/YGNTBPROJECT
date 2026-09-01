# import streamlit as st
# import pandas as pd
# import numpy as np
# import requests
# # st.title("My App Linked to GitHub")
# # st.write("Hello from VS Code.")
# # st.write("My Name is Toe Pyae Sone")

import pandas as pd
import requests
import requests.adapters
import streamlit as st
import urllib3.util.connection as urllib3_conn

# Page Configuration
st.set_page_config(page_title="YGN TB Data Viewer", layout="wide")

# Configuration Constants
SUPABASE_URL = "https://kocihpxevlowqbguhstf.supabase.co"
SUPABASE_KEY = "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z"
ALT_CLOUDFLARE_IPS = ["104.16.132.229", "104.18.32.7", "172.67.74.135"]


def _create_censorship_resistant_session(
    host_domain: str, alt_ip: str
) -> requests.Session:
    orig_create_connection = urllib3_conn.create_connection

    def patched_create_connection(address, *args, **kwargs):
        host, port = address
        if host == host_domain:
            host = alt_ip
        return orig_create_connection((host, port), *args, **kwargs)

    session = requests.Session()
    urllib3_conn.create_connection = patched_create_connection
    return session


# Caching prevents full pagination re-runs on every Streamlit state update
@st.cache_data(ttl=600, show_spinner=False)
def functionGetDataFromTable(
    tableName: str, url: str, key: str, page_size: int = 1000
) -> pd.DataFrame:
    endpoint = f"{url.rstrip('/')}/rest/v1/{tableName}?select=*"
    host_domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    headers = {
        "apikey": key.strip(),
        "Authorization": f"Bearer {key.strip()}",
        "Content-Type": "application/json",
    }
    session = None
    for alt_ip in [None] + ALT_CLOUDFLARE_IPS:
        try:
            if alt_ip is None:
                test_session = requests.Session()
            else:
                test_session = _create_censorship_resistant_session(
                    host_domain, alt_ip
                )
            check_res = test_session.get(
                f"{url}/rest/v1/", headers=headers, timeout=5
            )
            if check_res.status_code < 500:
                session = test_session
                break
        except requests.exceptions.RequestException:
            continue

    if session is None:
        st.error(
            "❌ Failed to reach Supabase across all routes. ISP block may require a Cloudflare Worker Relay."
        )
        return None

    all_data = []
    start_index = 0

    try:
        while True:
            page_headers = headers.copy()
            page_headers[
                "Range"
            ] = f"{start_index}-{start_index + page_size - 1}"
            response = session.get(endpoint, headers=page_headers, timeout=15)
            response.raise_for_status()
            chunk = response.json()
            if not chunk:
                break
            all_data.extend(chunk)
            if len(chunk) < page_size:
                break
            start_index += page_size

        return pd.DataFrame(all_data)

    except Exception as err:
        st.error(f"❌ An error occurred during data retrieval: {err}")
        return None


# --- STREAMLIT UI ---

st.title("📊 YGN TB Program - Supabase Data Viewer")

# Trigger button to refresh cache manually if needed
if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

with st.spinner("Connecting to Supabase and fetching records..."):
    df_ygntbpro_supabase = functionGetDataFromTable(
        "ygntbpro", SUPABASE_URL, SUPABASE_KEY
    )

if df_ygntbpro_supabase is not None and not df_ygntbpro_supabase.empty:
    st.success(
        f"✅ Successfully retrieved {len(df_ygntbpro_supabase):,} total records."
    )

    # Key Metrics
    col1, col2 = st.columns(2)
    col1.metric("Total Rows", len(df_ygntbpro_supabase))
    col2.metric("Total Columns", len(df_ygntbpro_supabase.columns))

    st.markdown("---")

    # Display Options
    st.subheader("Data Preview")

    # Search bar across dataframe
    search_term = st.text_input("🔍 Search within records:", "")
    if search_term:
        filtered_df = df_ygntbpro_supabase[
            df_ygntbpro_supabase.astype(str)
            .apply(lambda x: x.str.contains(search_term, case=False))
            .any(axis=1)
        ]
        st.write(f"Found {len(filtered_df)} matching records:")
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.dataframe(df_ygntbpro_supabase, use_container_width=True)

    # Download Option
    csv = df_ygntbpro_supabase.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name="ygntbpro_supabase_data.csv",
        mime="text/csv",
    )

elif df_ygntbpro_supabase is not None and df_ygntbpro_supabase.empty:
    st.warning("⚠️ Connected successfully, but the table 'ygntbpro' is empty.")