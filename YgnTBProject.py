import datetime
import pandas as pd
import streamlit as st
import functions as fn

st.set_page_config(page_title="Yangon TB Project Dashboard", layout="wide")

# Read API credentials securely from Streamlit secrets or fallback
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://kocihpxevlowqbguhstf.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z")

# Static configuration mappings
CATEGORICAL_COLS = ['Team', 'Tsp', 'Approach', 'Clinic', 'Reasonforexamination', 'Case', 
                    'Bact_status', 'Treatmentreferral', 'MonthDiagnosis11', 'Cxrr', 
                    'CXRresult', 'CXRresult211', 'Genexpertrequested', 'GeneXpertresult', 
                    'TypeofTBTreatment', 'TargetCategory']

COLUMN_UNCODE = ['Team','Sex','VOL','Referralfor','Cough','Fever','Wtloss','Nightsweat','Haemoptysis','Chestpain','Fatigue','Neckglands',
                'TBcontact','MDRTBcontact','TBTreatmenthistory','Smoking','Reasonforexamination','TypeofPatient','PublicHealthCare1',
                'TypeofPatient1','DM1','HT1','DMHT1','RTIAVI1','Generalweakness1','Other1','Cxrr','CXRresult','Sputum_request','Micror',
                'Sputummicroscopyresult','Genexpertrequested','GeneXpertresult','Bact_status','Case','Treatmentreferral','TreatmentRegimen',
                'Placeforreferral','TreatmentOutcome1211','ContactInvestigation111','DOTSupervision111','DOTsupervisiontillTreatmentComp111',
                'Seeing1','Hearing1','Walking1','Cognition1','Selfcare1','Communication1','Disability1','Xray2ndReading11','CXRresult211',
                'TypeofTBTreatment']

COLUMN_PRESERVED_FOR_TARGET = ["ReportingDate", "Team", "Tsp", "TargetCategory", "Group"]

UNCODE_MAPPING = {
    "CXRresult": {"1": "Normal", "2": "TB Active", "3": "TB Suspect", "4": "TB Healed", "5": "Other Abnormal"},
    "CXRresult211": {"1": "Normal", "2": "TB Active", "3": "TB Suspect", "4": "TB Healed", "5": "Other Abnormal"},
    "GeneXpertresult": {"0": "N", "1": "I", "2": "T", "3": "RR", "4": "TI", "5": "Denied", "6": "Missing", "7": "TT"},
    "Placeforreferral": {"1": "NTP", "2": "MMA", "3": "PSI", "4": "MATA", "5": "Other"},
    "TreatmentRegimen": {"1": "IR", "2": "RR", "3": "CR", "4": "MDR", "5": "MR"},
    "TypeofTBTreatment": {"1": "DS-TB", "2": "DR-TB", "3": "TPT"},
    "Sex": {"1": "Male", "2": "Female"},
    "Cxrr": {"1": "Requested", "2": "Not Requested"},
    "Reasonforexamination": {"1": "Diagnosis", "2": "Follow-Up"},
    "VOL": {"1": "Volunteer Referral", "2": "Walk-In"},
    "Referralfor": {"1": "Presumptive", "2": "CI"},
    "Case": {"1": "TB", "2": "No TB"},
    "DM1": {"1": "DM-New", "2": "No DM", "3": "DM-Old"},
    "HT1": {"1": "HT-New", "2": "No DM", "3": "HT-Old"},
    "HIVStatus": {"N": "Negative", "P": "Positive", "U": "Unknown"},
    "Genexpertrequested": {"1": "Requested", "2": "Not Requested"},
    "Bact_status": {"1": "BC", "2": "CD"},
    "Treatmentreferral": {"1": "Registered", "2": "Not Registered"},
    "TypeofPatient1": {"1": "New", "2": "Old"},
    "Team": {"1": "MMA", "5": "MATA"}
}

CRITERIA_INDICATORS = {
    "Examined Cases": {"Reasonforexamination": "Diagnosis"},
    "Notified Cases": {"Reasonforexamination": "Diagnosis", "Case": "TB"},
    "BC Cases": {"Reasonforexamination": "Diagnosis", "Case": "TB", "Bact_status": "BC"}
}

CATEGORY_PHC_CRITERIA = {
    "DM1": {"DM-New": "DM", "DM-Old": "DM"},
    "HT1": {"HT-New": "HT", "HT-Old": "HT"},
    'RTIAVI1': {"Yes": "AVI"},
    'Generalweakness1': {"Yes": "General Weakness"},
    'Other1': {"Yes": "Others"}
}

MAPPING_TARGET_CATEGORY = {"PPM": ["PPM", "Diagnostic Center"], "Mobile": ["Mobile Visit", "Elderly Care", "Touring"]}


@st.cache_data(ttl=600, show_spinner=False)
def load_data():
    df_raw_tb = fn.functionGetDataFromTable("ygntbpro", SUPABASE_URL, SUPABASE_KEY)
    df_raw_target = fn.functionGetDataFromTable("target", SUPABASE_URL, SUPABASE_KEY)

    if df_raw_tb is None or df_raw_tb.empty or df_raw_target is None or df_raw_target.empty:
        return None, None
    else:
        return df_dashboard, df_target


# Fetch processed data
with st.spinner("Connecting to Supabase and preparing dataset..."):
    try:
        df_dashboard, df_target = load_data()
    except Exception as err:
        st.error(f"❌ Error during execution: {err}")
        df_dashboard, df_target = None, None

if df_dashboard is not None and not df_dashboard.empty:
    st.sidebar.header("🔍 Filter Options")

    # Process target dataframe
    df_target = fn.switchingRowToColumn(df=df_raw_target, column_name="Indicator", preserved_column_list=COLUMN_PRESERVED_FOR_TARGET, value_col="Target")
    df_target = fn.function_uncode(df=df_target, colName=["Team"], mapping=UNCODE_MAPPING)
    df_target = fn.function_reporting_period(df_target, date_col="ReportingDate")
    df_target.rename(columns={"Group": "Clinic"}, inplace=True)
        
    if "ReportingDate" in df_target.columns:
        df_target["ReportingDate"] = pd.to_datetime(df_target["ReportingDate"], errors="coerce")

    if "Date" in df_dashboard.columns:
        df_dashboard["Date"] = pd.to_datetime(df_dashboard["Date"], errors="coerce")

    # Process dashboard dataframe
    df_dashboard = fn.create_category(df_raw_tb, source_col="Approach", criteria_mapping=MAPPING_TARGET_CATEGORY, output_col="TargetCategory", default="")
    df_dashboard.rename(columns={"EPI11": "Clinic"}, inplace=True)
    df_dashboard = fn.function_uncode(df_dashboard, colName=COLUMN_UNCODE, mapping=UNCODE_MAPPING)
    df_dashboard = fn.function_reporting_period(df_dashboard)
    df_dashboard = fn.create_category_combined(df_dashboard, CATEGORY_PHC_CRITERIA, "PrimaryHealthcare")



    # Compute date limits
    if "Date" in df_dashboard.columns and df_dashboard["Date"].notna().any():
        min_date = df_dashboard["Date"].min().date()
        max_date = df_dashboard["Date"].max().date()
    else:
        min_date = max_date = datetime.date.today()

    active_cat_cols = [col for col in CATEGORICAL_COLS if col in df_dashboard.columns]

    # Reset button
    if st.sidebar.button("🔄 Reset All Filters"):
        for col in active_cat_cols:
            st.session_state.pop(f"select_{col}", None)
        st.session_state.pop("date_range", None)
        st.rerun()

    # --- 1. DATE RANGE FILTER ---
    date_selection = st.sidebar.date_input(
        label="Select Date Range (From - To)",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        key="date_range"
    )

    filtered_df = df_dashboard.copy()
    filtered_target = df_target.copy() if df_target is not None else pd.DataFrame()

    start_date, end_date = min_date, max_date
    if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
        start_date, end_date = date_selection
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= start_date) & 
            (filtered_df["Date"].dt.date <= end_date)
        ]

    # --- 2. SINGLE-PASS CASCADING CATEGORICAL FILTERS ---
    selected_filters = {}
    for col in active_cat_cols:
        available_options = sorted(filtered_df[col].dropna().astype(str).unique())
        current_selection = st.session_state.get(f"select_{col}", [])
        valid_selection = [val for val in current_selection if val in available_options]

        selected = st.sidebar.multiselect(
            label=f"Filter by {col}",
            options=available_options,
            default=valid_selection,
            key=f"select_{col}"
        )

        if selected:
            # Dynamically filter the achievement data
            filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected)]
            
            # DYNAMIC FIX: Synchronize Target data filtering for shared structural dimensions
            if not filtered_target.empty and col in filtered_target.columns:
                filtered_target = filtered_target[filtered_target[col].astype(str).isin(selected)]

    # --- 3. DYNAMIC METRICS & PLOTLY CHARTS ---
    achievement = fn.function_indicator_achievement(filtered_df, CRITERIA_INDICATORS)
    progress = fn.function_merge_target(achievement, filtered_target, indicators=tuple(CRITERIA_INDICATORS.keys()))

    total_attendant = len(filtered_df)

    presumptive_count = achievement['Examined Cases'].sum() if 'Examined Cases' in achievement else 0
    notified_count = achievement['Notified Cases'].sum() if 'Notified Cases' in achievement else 0
    bact_confirmed_count = achievement['BC Cases'].sum() if 'BC Cases' in achievement else 0

    presumptive_sum_target = progress['Examined Cases Target'].sum() if 'Examined Cases Target' in progress else 0
    notified_sum_target = progress['Notified Cases Target'].sum() if 'Notified Cases Target' in progress else 0
    bact_confirmed_sum_target = progress['BC Cases Target'].sum() if 'BC Cases Target' in progress else 0

    # DYNAMIC FIX: Filter target metrics strictly using the user's active date range selection
    if not progress.empty and "ReportingDate" in progress.columns:
        filtered_progress = progress[progress['ReportingDate'].dt.date.between(start_date, end_date)]
    else:
        filtered_progress = pd.DataFrame()

    presumptive_count_target = filtered_progress['Examined Cases Target'].sum() if 'Examined Cases Target' in filtered_progress else 0
    notified_count_target = filtered_progress['Notified Cases Target'].sum() if 'Notified Cases Target' in filtered_progress else 0
    bact_confirmed_count_target = filtered_progress['BC Cases Target'].sum() if 'BC Cases Target' in filtered_progress else 0 

    # Zero-division safety checks for percentage calculations
    p_pct = (presumptive_count / presumptive_count_target * 100) if presumptive_count_target > 0 else 0
    n_pct = (notified_count / notified_count_target * 100) if notified_count_target > 0 else 0
    b_pct = (bact_confirmed_count / bact_confirmed_count_target * 100) if bact_confirmed_count_target > 0 else 0

    presumptive_sub = f"{p_pct:.0f}% progress on {presumptive_count_target:.0f} Targeted <br> ({presumptive_sum_target:.0f} in Total)"
    notified_sub = f"{n_pct:.0f}% progress on {notified_count_target:.0f} Targeted <br> ({notified_sum_target:.0f} in Total)"
    bact_confirmed_sub = f"{b_pct:.0f}% progress on {bact_confirmed_count_target:.0f} Targeted <br> ({bact_confirmed_sum_target:.0f} in Total)"

    # Metric Display Cards
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Total Attendants", f"{total_attendant:,}")
    m_col2.metric("Presumptive Cases", f"{presumptive_count:,}")
    m_col3.metric("Notified Cases", f"{notified_count:,}")
    m_col4.metric("Bacteriologically Confirmed", f"{bact_confirmed_count:,}")

    # Plotly Visualizations
    if not progress.empty:
        fig_target_achievement = fn.plotly_achievement_target_dropdown(
            dataframe=progress,
            achievement_columnList=["Examined Cases Achievement", "Notified Cases Achievement", "BC Cases Achievement"],
            target_columnList=["Examined Cases Target", "Notified Cases Target", "BC Cases Target"],
            period="Monthly",
            date_col="ReportingDate"
        )
        st.plotly_chart(
            fig_target_achievement,
            use_container_width=True,
            config={
                "toImageButtonOptions": {
                    "format": "png",
                    "filename": "tb_stacked_bar_chart",
                    "height": 600,
                    "width": 800,
                    "scale": 2,
                },
                "displayModeBar": True
            }
        )

    # --- 4. DISPLAY DATA TABLE ---
    st.markdown("---")
    st.subheader("Data Viewer")

    col1, col2 = st.columns(2)
    col1.metric("Filtered Records", len(filtered_df))
    col2.metric("Total Fields", len(filtered_df.columns))

    search_term = st.text_input("🔍 Search within filtered records:")
    
    if search_term:
        searchable_cols = [c for c in ['Team', 'Tsp', 'Clinic', 'Case', 'Bact_status'] if c in filtered_df.columns]
        if not searchable_cols:
            searchable_cols = filtered_df.columns[:10]
            
        mask = pd.Series(False, index=filtered_df.index)
        for c in searchable_cols:
            mask |= filtered_df[c].astype(str).str.contains(search_term, case=False, na=False)
        display_df = filtered_df[mask]
    else:
        display_df = filtered_df

    st.dataframe(display_df, use_container_width=True)

    @st.cache_data
    def convert_df_to_csv(df):
        return df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Download Filtered Data CSV",
        data=convert_df_to_csv(display_df),
        file_name="ygntbpro_filtered_data.csv",
        mime="text/csv",
    )

elif df_dashboard is not None and df_dashboard.empty:
    st.warning("⚠️ Connected successfully, but dataset contains no records.")
