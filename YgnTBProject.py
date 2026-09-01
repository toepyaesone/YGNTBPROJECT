
import datetime
import pandas as pd
import streamlit as st
import functions as fn

st.set_page_config(page_title="Yangon TB Project Dashboard", layout="wide")

# Cache the dynamic call wrapper to avoid re-fetching on UI interactions
@st.cache_data(ttl=600, show_spinner=False)

with st.spinner("Connecting to Supabase and retrieving dataset..."):
    try:
        # Calling the function by name dynamically
        df_ygntbpro_supabase = fn.functionGetDataFromTable("ygntbpro",SUPABASE_URL,SUPABASE_KEY)
        df_target_supabase = fn.functionGetDataFromTable("target",SUPABASE_URL,SUPABASE_KEY)
    except Exception as err:
        st.error(f"❌ Error during execution: {err}")
        df_ygntbpro_supabase = None
        df_target_supabase = None


if df_ygntbpro_supabase is not None and not df_ygntbpro_supabase.empty:
    st.success(f"✅ Successfully retrieved {len(df_ygntbpro_supabase):,} total records from ygntbpro.")

if df_target_supabase is not None and not df_target_supabase.empty:
    st.success(f"✅ Successfully retrieved {len(df_target_supabase):,} total records from target.")

    df_dashboard = df_ygntbpro_supabase.copy()
    df_target = df_target_supabase.copy()


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
    
    mapping_TargetCategory = {"PPM": ["PPM", "Diagnostic Center"],"Mobile": ["Mobile Visit", "Elderly Care", "Touring"]}
    
    df_target = fn.switchingRowToColumn(df=df_target, column_name="Indicator",preserved_column_list=COLUMN_PRESERVED_FOR_TARGET,value_col="Target")
    df_target = fn.function_uncode(df=df_target,colName=["Team"], mapping=UNCODE_MAPPING)
    df_target = fn.function_reporting_period(df_target,date_col="ReportingDate")
    df_target.rename(columns={"Group":"Clinic"},inplace=True)

    df_dashboard = fn.create_category(df_dashboard,source_col="Approach",criteria_mapping=mapping_TargetCategory,output_col="TargetCategory",default="")
    df_dashboard.rename(columns={"EPI11":"Clinic"},inplace=True)
    df_dashboard = fn.function_uncode(df_dashboard,colName=COLUMN_UNCODE, mapping=UNCODE_MAPPING)
    df_dashboard = fn.function_reporting_period(df_dashboard)
    df_dashboard = fn.create_category_combined(df_dashboard,CATEGORY_PHC_CRITERIA,"PrimaryHealthcare")
    
    # --- Convert Date to datetime format safely ---
    if "Date" in df_dashboard.columns:
        df_dashboard["Date"] = pd.to_datetime(df_dashboard["Date"], errors="coerce")
        
        min_ts = df_dashboard["Date"].min()
        max_ts = df_dashboard["Date"].max()
        
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
    CATEGORICAL_COLS = [
        'Team', 'Tsp', 'Approach', 'Clinic', 'Reasonforexamination', 'Case', 
        'Bact_status', 'Treatmentreferral', 'MonthDiagnosis11', 'Cxrr', 
        'CXRresult', 'CXRresult211', 'Genexpertrequested', 'GeneXpertresult', 
        'TypeofTBTreatment', 'TargetCategory'
    ]
    # Ensure columns actually exist to avoid KeyErrors
    CATEGORICAL_COLS = [col for col in CATEGORICAL_COLS if col in df_dashboard.columns]
    
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
    temp_df = df_dashboard.copy()
    
    if isinstance(date_selection, (tuple, list)) and len(date_selection) == 2:
        start_date, end_date = date_selection
        temp_df = temp_df[(temp_df["Date"].dt.date >= start_date) & (temp_df["Date"].dt.date <= end_date)]
    
    # --- 2. CASCADING CATEGORICAL FILTERS ---
    selected_filters = {}
    
    for col in CATEGORICAL_COLS:
        available_options = sorted(temp_df[col].dropna().astype(str).unique().tolist())
        current_selection = st.session_state.get(f"select_{col}", [])
        
        valid_selection = [val for val in current_selection if val in available_options]
    
        selected = st.sidebar.multiselect(
            label=f"Filter by {col}",
            options=available_options,
            default=valid_selection,
            key=f"select_{col}"
        )
    
        selected_filters[col] = selected
    
        if selected:
            temp_df = temp_df[temp_df[col].astype(str).isin(selected)]
    
    # --- 3. APPLY ALL FILTERS TO FINAL DATAFRAME ---
    filtered_df = df_dashboard.copy()
    
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

    search_term = st.text_input("🔍 Search within filtered records:")
    if search_term:
        filtered_df = filtered_df[
            filtered_df.astype(str)
            .apply(lambda x: x.str.contains(search_term, case=False))
            .any(axis=1)
        ]

    st.dataframe(filtered_df, use_container_width=True)

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Filtered Data CSV",
        data=csv_data,
        file_name="ygntbpro_filtered_data.csv",
        mime="text/csv",
    )

elif df_ygntbpro_supabase is not None and df_ygntbpro_supabase.empty:
    st.warning("⚠️ Connected successfully, but dataset contains no records.")
