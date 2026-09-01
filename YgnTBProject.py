import datetime
import pandas as pd
import streamlit as st
import functions as fn

st.set_page_config(page_title="Yangon TB Project Dashboard", layout="wide")

# Read API credentials securely from Streamlit secrets or fallback
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://kocihpxevlowqbguhstf.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z")

# Static configuration mappings
CATEGORICAL_COLS = [
    'Team', 'Tsp', 'Approach', 'Clinic', 'Reasonforexamination', 'Case', 
    'Bact_status', 'Treatmentreferral', 'MonthDiagnosis11', 'Cxrr', 
    'CXRresult', 'CXRresult211', 'Genexpertrequested', 'GeneXpertresult', 
    'TypeofTBTreatment', 'TargetCategory'
]

COLUMN_UNCODE = ['Team','Sex','VOL','Referralfor','Cough','Fever','Wtloss','Nightsweat','Haemoptysis','Chestpain','Fatigue','Neckglands',
              'TBcontact','MDRTBcontact','TBTreatmenthistory','Smoking','Reasonforexamination','TypeofPatient','PublicHealthCare1',
              'TypeofPatient1','DM1','HT1','DMHT1','RTIAVI1','Generalweakness1','Other1','Cxrr','CXRresult','Sputum_request','Micror',
              'Sputummicroscopyresult','Genexpertrequested','GeneXpertresult','Bact_status','Case','Treatmentreferral','TreatmentRegimen',
              'Placeforreferral','TreatmentOutcome1211','ContactInvestigation111','DOTSupervision111','DOTsupervisiontillTreatmentComp111',
              'Seeing1','Hearing1','Walking1','Cognition1','Selfcare1','Communication1','Disability1','Xray2ndReading11','CXRresult211',
              'TypeofTBTreatment']

COLUMN_DISABILITY = ["Seeing1","Hearing1","Walking1","Cognition1","Selfcare1","Communication1"]

COLUMN_SYMPTOM = ['Cough','Fever','Wtloss','Nightsweat','Haemoptysis','Chestpain','Fatigue','Neckglands']

COLUMN_PRESERVED_FOR_TARGET = ["ReportingDate","Team","Tsp","TargetCategory","Group"]

UNCODE_DISABILITY = {"1": "No - No Difficulty","2": "Yes - Some Difficulty","3": "Yes - A lot of Difficulty","4": "Yes - Can not do it at all"}

UNCODE_MAPPING = {
    "CXRresult": {
        "1": "Normal",
        "2": "TB Active",
        "3": "TB Suspect",
        "4": "TB Healed",
        "5": "Other Abnormal",
    },
    "CXRresult211": {
        "1": "Normal",
        "2": "TB Active",
        "3": "TB Suspect",
        "4": "TB Healed",
        "5": "Other Abnormal",
    },
    "GeneXpertresult": {
        "0": "N",
        "1": "I",
        "2": "T",
        "3": "RR",
        "4": "TI",
        "5": "Denied",
        "6": "Missing",
        "7": "TT",
    },
    "Placeforreferral": {
        "1": "NTP",
        "2": "MMA",
        "3": "PSI",
        "4": "MATA",
        "5": "Other",
    },
    "TreatmentRegimen": {
        "1": "IR",
        "2": "RR",
        "3": "CR",
        "4": "MDR",
        "5": "MR",
    },
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
    "Genexpertrequested":{"1":"Requested","2":"Not Requested"},
    "Bact_status": {"1": "BC","2": "CD"},
    "Treatmentreferral": {"1": "Registered", "2": "Not Registered"},
    "TypeofPatient1":{"1":"New","2":"Old"},
    "Team":{"1":"MMA", "5":"MATA"}}

UNCODE_DEFAULT = {"1": "Yes", "2": "No"}

MISSING_STRINGS = {"","none","nan","null","n/a","na","<na>","nat","#n/a","-","None","NONE","NaN","NULL","<NA>","N/A","NaT"}

CRITERIA_INDICATORS = {"Examined Cases": {"Reasonforexamination": "Diagnosis"},
                       "Notified Cases": {"Reasonforexamination": "Diagnosis", "Case": "TB"},
                       "BC Cases": {"Reasonforexamination": "Diagnosis","Case": "TB","Bact_status": "BC"}}

CATEGORY_PHC_CRITERIA = {"DM1": {"DM-New": "DM","DM-Old": "DM"},
                         "HT1": {"HT-New": "HT","HT-Old": "HT"},
                         'RTIAVI1':{"Yes":"AVI"}, 
                         'Generalweakness1':{"Yes":"General Weakness"},
                         'Other1':{"Yes":"Others"}}

COLUMN_CI_DOTS = ['Case','Bact_status','Treatmentreferral','TypeofTBTreatment','Age',
                  'HIVStatus','ContactInvestigation111', 'DOTSupervision111', 
                  'DOTStartedDate111','DOTsupervisiontillTreatmentComp111',
                  'Tsp','Ptstsp','VOL','Referralfor','VolunteerName','Organization',
                  'TreatmentOutcome1211','Tx_Outcome_Date','DOTvolName111',
                  'VolunteerGender111','VolunteerOrganization111']


# OPTIMIZATION 1: Fetch AND pre-process data inside st.cache_data
@st.cache_data(ttl=600, show_spinner=False)
def load_and_preprocess_data():
    df_raw_tb = fn.functionGetDataFromTable("ygntbpro", SUPABASE_URL, SUPABASE_KEY)
    df_raw_target = fn.functionGetDataFromTable("target", SUPABASE_URL, SUPABASE_KEY)

    if df_raw_tb is None or df_raw_tb.empty:
        return None, None

    # Process target dataframe
    df_target = fn.switchingRowToColumn(df=df_raw_target, column_name="Indicator", preserved_column_list=COLUMN_PRESERVED_FOR_TARGET, value_col="Target")
    df_target = fn.function_uncode(df=df_target, colName=["Team"], mapping=UNCODE_MAPPING)
    df_target = fn.function_reporting_period(df_target, date_col="ReportingDate")
    df_target.rename(columns={"Group": "Clinic"}, inplace=True)

    # Process dashboard dataframe
    df_dashboard = fn.create_category(df_raw_tb, source_col="Approach", criteria_mapping=MAPPING_TARGET_CATEGORY, output_col="TargetCategory", default="")
    df_dashboard.rename(columns={"EPI11": "Clinic"}, inplace=True)
    df_dashboard = fn.function_uncode(df_dashboard, colName=COLUMN_UNCODE, mapping=UNCODE_MAPPING)
    df_dashboard = fn.function_reporting_period(df_dashboard)
    df_dashboard = fn.create_category_combined(df_dashboard, CATEGORY_PHC_CRITERIA, "PrimaryHealthcare")

    # Fast datetime parsing
    if "Date" in df_dashboard.columns:
        df_dashboard["Date"] = pd.to_datetime(df_dashboard["Date"], errors="coerce")
    
    return df_dashboard, df_target


# Fetch processed data
with st.spinner("Connecting to Supabase and preparing dataset..."):
    try:
        df_dashboard, df_target = load_and_preprocess_data()
    except Exception as err:
        st.error(f"❌ Error during execution: {err}")
        df_dashboard, df_target = None, None

if df_dashboard is not None and not df_dashboard.empty:
    st.sidebar.header("🔍 Filter Options")

    # Compute date limits efficiently
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

    filtered_df = df_dashboard

    if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
        start_date, end_date = date_selection
        # Optimized inline filtering using query/boolean mask
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= start_date) & 
            (filtered_df["Date"].dt.date <= end_date)
        ]

    # --- 2. SINGLE-PASS CASCADING CATEGORICAL FILTERS ---
    selected_filters = {}
    for col in active_cat_cols:
        # Dynamically compute available options based on currently filtered subset
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
            filtered_df = filtered_df[filtered_df[col].astype(str).isin(selected)]

    # --- 3. DISPLAY PLOTLY CHARTS ---
    # Ensure progress dataset exists before passing to visualization
    achievement = fn.function_indicator_achievement(filtered_df,CRITERIA_INDICATORS)
    progress = fn.function_merge_target(achievement,df_target,indicators=tuple(CRITERIA_INDICATORS.keys()))

    total_attendant = len(filtered_df)


    presumptive_count = achievement['Examined Cases'].sum()
    notified_count = achievement['Notified Cases'].sum()
    bact_confirmed_count = achievement['BC Cases'].sum()

    presumptive_sum_target = progress['Examined Cases Target'].sum()
    notified_sum_target = progress['Notified Cases Target'].sum()
    bact_confirmed_sum_target = progress['BC Cases Target'].sum()

    if date_to.value or date_to.value:
        filtered_progress = progress[progress['ReportingDate'].dt.date.between(date_from.value,date_to.value)]
        
    presumptive_count_target = filtered_progress['Examined Cases Target'].sum()
    notified_count_target = filtered_progress['Notified Cases Target'].sum()
    bact_confirmed_count_target = filtered_progress['BC Cases Target'].sum() 

    presumptive_sub = f"{presumptive_count / presumptive_count_target * 100:.0f}% progress  on {presumptive_count_target:.0f} Targeted <br> ({presumptive_sum_target:.0f} in Total)"
    notified_sub = f"{notified_count / notified_count_target * 100:.0f}% progress on {notified_count_target:.0f} Targeted <br> ({notified_sum_target:.0f} in Total)"
    bact_confirmed_sub = f"{bact_confirmed_count / bact_confirmed_count_target * 100:.0f}% progress on {bact_confirmed_count_target:.0f} Targeted <br> ({bact_confirmed_sum_target:.0f} in Total)"
    
    if "progress" in locals() or "progress" in globals():
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
    
    # OPTIMIZATION 3: Fast String Search across critical columns instead of entire DataFrame
    if search_term:
        searchable_cols = [c for c in ['Team', 'Tsp', 'Clinic', 'Case', 'Bact_status'] if c in filtered_df.columns]
        if not searchable_cols:
            searchable_cols = filtered_df.columns[:10]  # Fallback to first 10 columns
            
        mask = pd.Series(False, index=filtered_df.index)
        for c in searchable_cols:
            mask |= filtered_df[c].astype(str).str.contains(search_term, case=False, na=False)
        display_df = filtered_df[mask]
    else:
        display_df = filtered_df

    st.dataframe(display_df, use_container_width=True)

    # OPTIMIZATION 4: Deferred CSV encoding (only runs when clicked)
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
