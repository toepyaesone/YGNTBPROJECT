import pandas as pd
import streamlit as st

import functions  # Import the functions module

st.set_page_config(page_title="YGN TB Data Viewer", layout="wide")


# Cache the dynamic call wrapper to avoid re-fetching on UI interactions
@st.cache_data(ttl=600, show_spinner=False)
def call_function_by_name(
    func_name: str, *args, **kwargs
) -> pd.DataFrame | None:
    """Retrieves a function dynamically by name from functions.py and invokes it."""
    if hasattr(functions, func_name):
        target_func = getattr(functions, func_name)
        return target_func(*args, **kwargs)
    else:
        st.error(f"Function `{func_name}` not found in functions.py.")
        return None


# --- STREAMLIT UI ---

st.title("📊 YGN TB Program - Supabase Data Viewer")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()

target_function_name = "functionGetDataFromTable"
table_name = "ygntbpro"

with st.spinner("Connecting to Supabase and retrieving dataset..."):
    try:
        # Calling the function by name dynamically
        df_ygntbpro_supabase = call_function_by_name(
            target_function_name, tableName=table_name
        )
    except Exception as err:
        st.error(f"❌ Error during execution: {err}")
        df_ygntbpro_supabase = None

if df_ygntbpro_supabase is not None and not df_ygntbpro_supabase.empty:
    st.success(
        f"✅ Successfully retrieved {len(df_ygntbpro_supabase):,} total records."
    )

    col1, col2 = st.columns(2)
    col1.metric("Total Records", len(df_ygntbpro_supabase))
    col2.metric("Total Fields", len(df_ygntbpro_supabase.columns))

    st.markdown("---")
    st.subheader("Data Viewer")

    # Filter functionality
    search_term = st.text_input("🔍 Search table records:")
    if search_term:
        filtered_df = df_ygntbpro_supabase[
            df_ygntbpro_supabase.astype(str)
            .apply(lambda x: x.str.contains(search_term, case=False))
            .any(axis=1)
        ]
        st.dataframe(filtered_df, use_container_width=True)
    else:
        st.dataframe(df_ygntbpro_supabase, use_container_width=True)

    # Download button
    csv_data = df_ygntbpro_supabase.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Data CSV",
        data=csv_data,
        file_name=f"{table_name}_data.csv",
        mime="text/csv",
    )

elif df_ygntbpro_supabase is not None and df_ygntbpro_supabase.empty:
    st.warning(f"⚠️ Connected successfully, but table '{table_name}' contains no records.")
