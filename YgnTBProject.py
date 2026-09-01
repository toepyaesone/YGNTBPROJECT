import pandas as pd
import streamlit as st

# Import custom processing and plotting functions
try:
    import functions as fn
except ImportError:
    st.error("Could not import 'functions.py'. Ensure it is in the same repository directory.")
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="YgnTBPro Data Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- CUSTOM CSS FOR KPI CARDS ---
st.markdown(
    """
    <style>
    .kpi-card {
        padding: 15px;
        border-radius: 6px;
        color: #2d3748;
        background-color: #f7fafc;
        border-left: 5px solid #2b6cb0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .kpi-title {
        font-size: 11px;
        font-weight: bold;
        text-transform: uppercase;
        color: #4a5568;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: bold;
        margin-top: 4px;
    }
    .kpi-subtext {
        font-size: 11px;
        color: #718096;
        font-weight: bold;
        margin-top: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- CONSTANTS & CONFIGURATIONS ---
COLUMN_UNCODE = [
    'Team', 'Sex', 'VOL', 'Referralfor', 'Cough', 'Fever', 'Wtloss', 'Nightsweat', 
    'Haemoptysis', 'Chestpain', 'Fatigue', 'Neckglands', 'TBcontact', 'MDRTBcontact', 
    'TBTreatmenthistory', 'Smoking', 'Reasonforexamination', 'TypeofPatient', 
    'PublicHealthCare1', 'TypeofPatient1', 'DM1', 'HT1', 'DMHT1', 'RTIAVI1', 
    'Generalweakness1', 'Other1', 'Cxrr', 'CXRresult', 'Sputum_request', 'Micror', 
    'Sputummicroscopyresult', 'Genexpertrequested', 'GeneXpertresult', 'Bact_status', 
    'Case', 'Treatmentreferral', 'TreatmentRegimen', 'Placeforreferral', 
    'TreatmentOutcome1211', 'ContactInvestigation111', 'DOTSupervision111', 
    'DOTsupervisiontillTreatmentComp111', 'Seeing1', 'Hearing1', 'Walking1', 
    'Cognition1', 'Selfcare1', 'Communication1', 'Disability1', 'Xray2ndReading11', 
    'CXRresult211', 'TypeofTBTreatment'
]

COLUMN_SYMPTOM = [
    'Cough', 'Fever', 'Wtloss', 'Nightsweat', 'Haemoptysis', 'Chestpain', 'Fatigue', 'Neckglands'
]

COLUMN_PRESERVED_FOR_TARGET = ["ReportingDate", "Team", "Tsp", "TargetCategory", "Group"]

UNCODE_MAPPING = {
    "CXRresult": {"1": "Normal", "2": "TB Active", "3": "TB Suspect", "4": "TB Healed", "5": "Other Abnormal"},
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
    "DM1": {"1": "TB-DM", "2": "No DM", "3": "TB-DM"},
    "HIVStatus": {"N": "Negative", "P": "Positive", "U": "Unknown"},
    "Genexpertrequested": {"1": "Requested", "2": "Not Requested"},
    "Bact_status": {"1": "BC", "2": "CD"},
    "Treatmentreferral": {"1": "Registered", "2": "Not Registered"},
    "Team": {"1": "MMA", "5": "MATA"}
}

CRITERIA_INDICATORS = {
    "Examined Cases": {"Reasonforexamination": "Diagnosis"},
    "Notified Cases": {"Reasonforexamination": "Diagnosis", "Case": "TB"},
    "BC Cases": {"Reasonforexamination": "Diagnosis", "Case": "TB", "Bact_status": "BC"}
}

COLUMNS_SLICER = [
    'Team', 'Tsp', 'Approach', 'Clinic', 'Reasonforexamination', 'Case', 'Bact_status', 
    'Treatmentreferral', 'MonthDiagnosis11', 'Cxrr', 'CXRresult', 'CXRresult211', 
    'Genexpertrequested', 'GeneXpertresult', 'TypeofTBTreatment', 'TargetCategory'
]


# --- HELPER FUNCTIONS ---
def classify_symptomatic(df: pd.DataFrame, symptom_cols, target_val: str = "yes") -> pd.Series:
    cols = [symptom_cols] if isinstance(symptom_cols, str) else list(symptom_cols)
    valid_cols = [c for c in cols if c in df.columns]
    if not valid_cols:
        return pd.Series("Asymptomatic", index=df.index)
    cleaned_symptoms = (
        df[valid_cols].fillna("").astype(str).apply(lambda col: col.str.strip().str.lower())
    )
    has_symptom_mask = cleaned_symptoms.eq(target_val.lower()).any(axis=1)
    symptom_series = pd.Series("Asymptomatic", index=df.index)
    symptom_series[has_symptom_mask] = "Symptomatic"
    return symptom_series


def get_options(df: pd.DataFrame, column_name: str) -> list:
    if column_name in df.columns:
        cleaned_values = df[column_name].dropna().astype(str).str.strip()
        unique_vals = sorted(list(cleaned_values.replace(["nan", "None", ""], "blank").unique()))
        return ["All"] + unique_vals
    return ["All"]


# --- DATA LOADING & INITIALIZATION ---
@st.cache_data
def load_and_preprocess_data():
    # Import or read raw data frames (Replace with actual data loading logic if needed)
    try:
        from functions import df_dashboard_raw, df_target_raw
    except ImportError:
        # Fallback empty structures if datasets are loaded externally inside functions.py
        df_dashboard_raw = pd.DataFrame()
        df_target_raw = pd.DataFrame()

    # Preprocess Target Data
    if not df_target_raw.empty:
        df_target = fn.switchingRowToColumn(
            df=df_target_raw, 
            column_name="Indicator", 
            preserved_column_list=COLUMN_PRESERVED_FOR_TARGET, 
            value_col="Target"
        )
        df_target = fn.function_uncode(df=df_target, colName=["Team"], mapping=UNCODE_MAPPING)
        df_target = fn.function_reporting_period(df_target, date_col="ReportingDate")
        df_target.rename(columns={"Group": "Clinic"}, inplace=True)
    else:
        df_target = pd.DataFrame()

    # Preprocess Dashboard Data
    if not df_dashboard_raw.empty:
        mapping_TargetCategory = {
            "PPM": ["PPM", "Diagnostic Center"], 
            "Mobile": ["Mobile Visit", "Elderly Care", "Touring"]
        }
        df_dashboard = fn.create_category(
            df_dashboard_raw, 
            source_col="Approach", 
            criteria_mapping=mapping_TargetCategory, 
            output_col="TargetCategory", 
            default=""
        )
        df_dashboard.rename(columns={"EPI11": "Clinic"}, inplace=True)
        df_dashboard = fn.function_uncode(df_dashboard, colName=COLUMN_UNCODE, mapping=UNCODE_MAPPING)
        df_dashboard = fn.function_reporting_period(df_dashboard)
    else:
        df_dashboard = pd.DataFrame()

    return df_dashboard, df_target


df_dashboard, df_target = load_and_preprocess_data()

# Prepare slicer data frame
df_slicer = df_dashboard.copy()
if "Date" in df_slicer.columns:
    df_slicer["Date"] = pd.to_datetime(df_slicer["Date"])
    min_date = df_slicer["Date"].min().date()
    max_date = df_slicer["Date"].max().date()
else:
    min_date = pd.to_datetime("2025-01-01").date()
    max_date = pd.to_datetime("2026-12-31").date()


# --- HELPER: UNIFIED VALUE CLEANER ---
def clean_series(series: pd.Series) -> pd.Series:
    """Utility to safely format values for string comparison."""
    return series.fillna("").astype(str).str.strip()

def get_options(df: pd.DataFrame, column_name: str) -> list:
    if column_name in df.columns:
        cleaned_values = clean_series(df[column_name])
        unique_vals = sorted([v for v in cleaned_values.unique() if v not in ["", "nan", "None"]])
        return ["All"] + unique_vals
    return ["All"]

# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Slicer Controls")

# Parse dates safely
if "Date" in df_slicer.columns:
    df_slicer["Date"] = pd.to_datetime(df_slicer["Date"], errors="coerce")
    valid_dates = df_slicer["Date"].dropna()
    min_date = valid_dates.min().date() if not valid_dates.empty else pd.to_datetime("2025-01-01").date()
    max_date = valid_dates.max().date() if not valid_dates.empty else pd.to_datetime("2026-12-31").date()
else:
    min_date = pd.to_datetime("2025-01-01").date()
    max_date = pd.to_datetime("2026-12-31").date()

date_range = st.sidebar.date_input(
    "Date Range Filter",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    date_from, date_to = date_range
else:
    date_from, date_to = min_date, max_date

slicer_selections = {}
for col in COLUMNS_SLICER:
    if col in df_slicer.columns:
        slicer_selections[col] = st.sidebar.multiselect(
            label=col,
            options=get_options(df_slicer, col),
            default=["All"]
        )

# Reset Button to clear all filters quickly
if st.sidebar.button("🔄 Reset All Filters"):
    st.rerun()

# --- DATA FILTERING ENGINE ---
filtered_df = df_slicer.copy()
target_df = df_target.copy()

if not filtered_df.empty:
    filtered_df['Symptom'] = classify_symptomatic(filtered_df, COLUMN_SYMPTOM)

    # 1. Date Range Filtering
    if "Date" in filtered_df.columns and date_from and date_to:
        filtered_df = filtered_df[
            (filtered_df["Date"].dt.date >= date_from) & 
            (filtered_df["Date"].dt.date <= date_to)
        ]

    if "ReportingDate" in target_df.columns and date_from and date_to:
        target_df["ReportingDate"] = pd.to_datetime(target_df["ReportingDate"], errors="coerce")
        target_df = target_df[
            (target_df['ReportingDate'].dt.year >= date_from.year) & 
            (target_df['ReportingDate'].dt.year <= date_to.year)
        ]

    # 2. Robust Multi-Select Filtering
    for col, selected_vals in slicer_selections.items():
        if selected_vals and "All" not in selected_vals:
            # Clean selection values
            str_selected = [str(v).strip() for v in selected_vals]

            # Filter Dashboard Data
            if col in filtered_df.columns:
                filtered_df = filtered_df[clean_series(filtered_df[col]).isin(str_selected)]

            # Filter Target Data (only if column exists in target_df)
            if col in target_df.columns:
                target_df = target_df[clean_series(target_df[col]).isin(str_selected)]

# --- MAIN HEADER ---
st.title("YgnTBPro Data Analysis Dashboard")
st.caption("Dynamic monitoring dashboard for project metrics, diagnostic funnels, and performance targets.")
st.divider()

if filtered_df.empty:
    st.warning("⚠️ No data matches the selected filter criteria. Please broaden your sidebar selection.")
    st.stop()


# --- CALCULATIONS & KPI METRICS ---
achievement = fn.function_indicator_achievement(filtered_df, CRITERIA_INDICATORS)
progress = fn.function_merge_target(achievement, target_df, indicators=tuple(CRITERIA_INDICATORS.keys()))

total_attendant = len(filtered_df)
presumptive_count = achievement['Examined Cases'].sum() if 'Examined Cases' in achievement else 0
notified_count = achievement['Notified Cases'].sum() if 'Notified Cases' in achievement else 0
bact_confirmed_count = achievement['BC Cases'].sum() if 'BC Cases' in achievement else 0

presumptive_sum = progress['Examined Cases Target'].sum() if 'Examined Cases Target' in progress else 0
notified_sum = progress['Notified Cases Target'].sum() if 'Notified Cases Target' in progress else 0
bact_confirmed_sum = progress['BC Cases Target'].sum() if 'BC Cases Target' in progress else 0

# KPI Cards Layout
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #2b6cb0;">
            <div class="kpi-title">Total Attendant</div>
            <div class="kpi-value" style="color: #2b6cb0;">{total_attendant:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #319795;">
            <div class="kpi-title">Examined Cases</div>
            <div class="kpi-value" style="color: #319795;">{presumptive_count:,}</div>
            <div class="kpi-subtext">Target: {presumptive_sum:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #dd6b20;">
            <div class="kpi-title">Notified Cases</div>
            <div class="kpi-value" style="color: #dd6b20;">{notified_count:,}</div>
            <div class="kpi-subtext">Target: {notified_sum:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color: #805ad5;">
            <div class="kpi-title">BC Cases</div>
            <div class="kpi-value" style="color: #805ad5;">{bact_confirmed_count:,}</div>
            <div class="kpi-subtext">Target: {bact_confirmed_sum:,}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)


# --- DASHBOARD VISUALIZATIONS ---

# Row 1: Achievement & Variance
c1, c2 = st.columns(2)
with c1:
    fig_ach = fn.plotly_achievement_target_dropdown(
        dataframe=progress,
        achievement_columnList=["Examined Cases Achievement", "Notified Cases Achievement", "BC Cases Achievement"],
        target_columnList=["Examined Cases Target", "Notified Cases Target", "BC Cases Target"],
        period="Monthly",
        date_col="ReportingDate"
    )
    st.plotly_chart(fig_ach, use_container_width=True)

with c2:
    fig_var = fn.plotly_variance_heatmap(progress, color_scale_range=(0, 200))
    st.plotly_chart(fig_var, use_container_width=True)

# Row 2: Demographics & Category Stacked Bar
c3, c4 = st.columns(2)
with c3:
    fig_demo = fn.plotly_gender_agegroup(filtered_df, "Sex", "Age", 500)
    st.plotly_chart(fig_demo, use_container_width=True)

with c4:
    fig_stack1 = fn.plotly_stack_bar(
        filtered_df,
        columns=['Bact_status', 'Treatmentreferral', 'TreatmentRegimen', 'DM1', 'HIVStatus', 'TypeofTBTreatment', 'TPTregimen'],
        exclude_blank=True,
        orientation="h",
        title="Distribution of Cases"
    )
    st.plotly_chart(fig_stack1, use_container_width=True)

# Row 3: Stacked Bar Facilities & Diagnostic Heatmap
c5, c6 = st.columns(2)
with c5:
    fig_stack2 = fn.plotly_stack_bar(
        filtered_df,
        columns=["Treatmentreferral", "Tsp", "Approach", "Case", "Sex"],
        exclude_blank=True,
        orientation="h",
        title="Distribution of Cases Across Facilities"
    )
    st.plotly_chart(fig_stack2, use_container_width=True)

with c6:
    fig_heat = fn.function_heatmap(filtered_df, "CXRresult", "GeneXpertresult")
    st.plotly_chart(fig_heat, use_container_width=True)

# Row 4: Sankey Cascade
st.subheader("TB Care Cascade Flow")
col_sankey = {
    "VOL": ["Volunteer Referral", "Walk-In"],
    "Referralfor": ["CI", "Presumptive"],
    "Case": ["TB"],
    "Bact_status": ["BC", "CD"],
    "Treatmentreferral": ["Registered"]
}
df_sankey = filtered_df[filtered_df["Reasonforexamination"] == "Diagnosis"] if "Reasonforexamination" in filtered_df.columns else filtered_df
fig_sankey = fn.function_sankey_cascade_log(
    dataframe=df_sankey,
    criteria_dict=col_sankey,
    title="TB Cascade: Diagnosis to Treatment Registration",
    log_base=10
)
st.plotly_chart(fig_sankey, use_container_width=True)

# Row 5: Target vs Achievement Columns
st.subheader("Target vs Achievement Breakdowns")
charts = fn.plotly_target_achievement_allcharts(
    dataframe=progress,
    date_config={"ReportingDate": "Reporting Period"},
    bar_configs=[
        {"Examined Cases Target": "Examined Cases Target", "Examined Cases Achievement": "Examined Cases Achievement"},
        {"Notified Cases Target": "Notified Cases Target", "Notified Cases Achievement": "Notified Cases Achievement"},
        {"BC Cases Target": "BC Cases Target", "BC Cases Achievement": "BC Cases Achievement"}
    ],
    optional_percentage=True,
    percentage_calc={
        "Examined Cases": ("Examined Cases Achievement", "Examined Cases Target"),
        "Notified Cases": ("Notified Cases Achievement", "Notified Cases Target"),
        "BC Cases": ("BC Cases Achievement", "BC Cases Target")
    },
    freq="Month"
)

col_a, col_b, col_c = st.columns(3)
with col_a:
    if "Examined Cases" in charts:
        st.plotly_chart(charts["Examined Cases"], use_container_width=True)
with col_b:
    if "Notified Cases" in charts:
        st.plotly_chart(charts["Notified Cases"], use_container_width=True)
with col_c:
    if "BC Cases" in charts:
        st.plotly_chart(charts["BC Cases"], use_container_width=True)

# Row 6: Funnel Chart & Summary Table
st.subheader("Diagnostic Cascade & Summary Metrics")
c7, c8 = st.columns(2)

funnel_column_criteria = {
    'Reasonforexamination': ['Diagnosis'],
    'Cxrr': ['Requested'],
    'CXRresult': ['TB Suspect', 'TB Healed', 'TB Active'],
    'Genexpertrequested': ['Requested'],
    'GeneXpertresult': ['N', 'T', 'TT', 'TI', 'RR'],
    'Bact_status': ['BC'],
    'Case': ['TB'],
    'Treatmentreferral': ['Registered']
}
funnel_column_rename = [
    'Screening', 'CXR Request', 'CXR Abnormality', 'Gene Request', 
    'Gene Result', 'Bact Confirmed', 'Notified TB', 'Treatment Registered'
]

with c7:
    fig_funnel = fn.plotly_funnel(filtered_df, funnel_column_criteria, funnel_column_rename, 'Symptom')
    st.plotly_chart(fig_funnel, use_container_width=True)

with c8:
    fig_tbl = fn.plotly_table_count_percent(
        df=filtered_df, 
        column_list=['Sex', 'CXRresult', 'GeneXpertresult', 'Case', 'Placeforreferral'], 
        optional_exclude_blank=True, 
        optional_include_total=True
    )
    st.plotly_chart(fig_tbl, use_container_width=True)

# --- EXPANDABLE DATA PREVIEW ---
with st.expander("📄 View Filtered Raw Data"):
    st.dataframe(filtered_df, use_container_width=True)
