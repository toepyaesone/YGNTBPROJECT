import pandas as pd
import streamlit as st
import datetime

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

# target_function_name = "functionGetDataFromTable"
# table_name = "ygntbpro"

with st.spinner("Connecting to Supabase and retrieving dataset..."):
    try:
        # Calling the function by name dynamically
        df_ygntbpro_supabase = call_function_by_name("functionGetDataFromTable", "ygntbpro")
    except Exception as err:
        st.error(f"❌ Error during execution: {err}")
        df_ygntbpro_supabase = None


if df_ygntbpro_supabase is not None and not df_ygntbpro_supabase.empty:
    st.success(f"✅ Successfully retrieved {len(df_ygntbpro_supabase):,} total records.")

    df = df_ygntbpro_supabase.copy()

    # --- BUG FIX: Convert Date to datetime format safely ---
    # Ensure pandas recognizes the column as datetime before extracting .date()
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        
        min_ts = df["Date"].min()
        max_ts = df["Date"].max()
        
        # Fallback to today's date if the entire column happens to be empty or null
        if pd.isna(min_ts) or pd.isna(max_ts):
            min_date = datetime.date.today()
            max_date = datetime.date.today()
        else:
            min_date = min_ts.date()
            max_date = max_ts.date()
    else:
        st.error("❌ Column 'Date' not found in dataset!")
        st.stop()


    st.sidebar.header("🔍 Filter Options")
    
    # Categorical columns for cascading selection
    CATEGORICAL_COLS = ["Tsp", "Team", "Approach", "MonthDiagnosis11"]
    # Ensure columns actually exist to avoid KeyErrors
    CATEGORICAL_COLS = [col for col in CATEGORICAL_COLS if col in df.columns]
    
    # Reset Filters Button
    if st.sidebar.button("🔄 Reset All Filters"):
        for col in CATEGORICAL_COLS:
            if f"select_{col}" in st.session_state:
                st.session_state[f"select_{col}"] = []
        st.session_state["date_range"] = ()
        st.rerun()
    
    # --- 1. DATE RANGE FILTER (From Date to To Date) ---
    date_selection = st.sidebar.date_input(
        label="Select Date Range (From - To)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="date_range"
    )
    
    # Start working DataFrame with Date Range slice
    temp_df = df.copy()
    
    if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
        start_date, end_date = date_selection
        temp_df = temp_df[(temp_df["Date"].dt.date >= start_date) & (temp_df["Date"].dt.date <= end_date)]
    
    # --- 2. CASCADING CATEGORICAL FILTERS ---
    selected_filters = {}
    
    for col in CATEGORICAL_COLS:
        available_options = sorted(temp_df[col].dropna().astype(str).unique().tolist())
        current_selection = st.session_state.get(f"select_{col}", [])
        
        # Keep only valid selections
        valid_selection = [val for val in current_selection if val in available_options]
    
        selected = st.sidebar.multiselect(
            label=f"Filter by {col}",
            options=available_options,
            default=valid_selection,
            key=f"select_{col}"
        )
    
        selected_filters[col] = selected
    
        # Narrow down temp_df for the NEXT column in sequence
        if selected:
            temp_df = temp_df[temp_df[col].astype(str).isin(selected)]
    
    # --- 3. APPLY ALL FILTERS TO FINAL DATAFRAME ---
    filtered_df = df.copy()
    
    # Apply Date Range
    if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
        start_date, end_date = date_selection
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= start_date) & 
            (filtered_df["Date"].dt.date <= end_date)
        ]
    
    # Apply Categorical Filters
    for col, selected_vals in selected_filters.items():
        if selected_vals:
            filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected_vals)]
    
    
    # --- 4. DISPLAY COMBINED RESULTS ---
    st.markdown("---")
    st.subheader("Data Viewer")

    col1, col2 = st.columns(2)
    col1.metric("Filtered Records", len(filtered_df))
    col2.metric("Total Fields", len(filtered_df.columns))

    # Optional sub-filter for exact text matching
    search_term = st.text_input("🔍 Search within filtered records:")
    if search_term:
        filtered_df = filtered_df[
            filtered_df.astype(str)
            .apply(lambda x: x.str.contains(search_term, case=False))
            .any(axis=1)
        ]

    st.dataframe(filtered_df, use_container_width=True)

    # Download button utilizes filtered data instead of raw table
    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Data CSV",
        data=csv_data,
        file_name=f"filtered_data.csv",
        mime="text/csv",
    )

elif df_ygntbpro_supabase is not None and df_ygntbpro_supabase.empty:
    st.warning(f"⚠️ Connected successfully, but table '{table_name}' contains no records.")
