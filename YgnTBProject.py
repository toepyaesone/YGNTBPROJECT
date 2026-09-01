import datetime
import pandas as pd
import streamlit as st

# Import all processing and plotting utilities from functions module
import functions as fn

# Streamlit Page Config
st.set_page_config(
    page_title="YgnTBPro Data Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)

# Custom CSS for KPI Metric Cards
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


@st.cache_data
def load_mock_data():
    """Generates dummy baseline datasets if real data is not loaded."""
    dates = pd.date_range("2025-01-01", "2026-08-31", freq="D")
    df_dash = pd.DataFrame(
        {
            "Date": np.random.choice(dates, 1000),
            "Team": np.random.choice(["Team A", "Team B", "Team C"], 1000),
            "Tsp": np.random.choice(["Kamayut", "Insein", "Thingangyun"], 1000),
            "Approach": np.random.choice(["Mobile", "Static"], 1000),
            "Clinic": np.random.choice(["Clinic 1", "Clinic 2"], 1000),
            "Reasonforexamination": np.random.choice(
                ["Diagnosis", "Follow-up"], 1000
            ),
            "Case": np.random.choice(["TB", "Non-TB"], 1000),
            "Bact_status": np.random.choice(["BC", "CD"], 1000),
            "Treatmentreferral": np.random.choice(
                ["Registered", "Referred"], 1000
            ),
            "Sex": np.random.choice(["Male", "Female"], 1000),
            "Age": np.random.randint(10, 80, 1000),
            "CXRresult": np.random.choice(
                ["TB Suspect", "Normal", "TB Active"], 1000
            ),
            "GeneXpertresult": np.random.choice(["N", "T", "RR"], 1000),
            "VOL": np.random.choice(["Volunteer Referral", "Walk-In"], 1000),
            "Referralfor": np.random.choice(["CI", "Presumptive"], 1000),
            "Placeforreferral": np.random.choice(["Public", "Private"], 1000),
            "Symptom_Cough": np.random.choice(["yes", "no"], 1000),
        }
    )

    reporting_dates = pd.date_range("2025-01-01", "2026-12-31", freq="M")
    df_target = pd.DataFrame(
        {
            "ReportingDate": reporting_dates,
            "Examined Cases Target": [500] * len(reporting_dates),
            "Examined Cases Achievement": np.random.randint(
                400, 600, len(reporting_dates)
            ),
            "Notified Cases Target": [200] * len(reporting_dates),
            "Notified Cases Achievement": np.random.randint(
                150, 250, len(reporting_dates)
            ),
            "BC Cases Target": [100] * len(reporting_dates),
            "BC Cases Achievement": np.random.randint(
                80, 120, len(reporting_dates)
            ),
        }
    )

    return df_dash, df_target


# --- DATA PREPARATION ---
df_dashboard, df_target = load_mock_data()

COLUMN_SYMPTOM = ["Symptom_Cough"]
CRITERIA_INDICATORS = {
    "Examined Cases": {},
    "Notified Cases": {},
    "BC Cases": {},
}

df_slicer = df_dashboard.copy()
df_slicer["Date"] = pd.to_datetime(df_slicer["Date"])

min_date = df_slicer["Date"].min().date()
max_date = df_slicer["Date"].max().date()


# --- SIDEBAR FILTERS ---
st.sidebar.title("🔍 Filter Options")

# Date Pickers
date_range = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    date_from, date_to = date_range
else:
    date_from, date_to = min_date, max_date

# Dynamic Multi-Select Slicers
slicer_selections = {}
for col in fn.COLUMNS_SLICER:
    options = fn.get_options(df_slicer, col)
    slicer_selections[col] = st.sidebar.multiselect(
        label=f"{col}", options=options, default=["All"]
    )


# --- DATA FILTERING ENGINE ---
filtered_df = df_slicer.copy()
target_df = df_target.copy()

filtered_df["Symptom"] = fn.classify_symptomatic(filtered_df, COLUMN_SYMPTOM)

# Date Filtering
if date_from:
    filtered_df = filtered_df[filtered_df["Date"].dt.date >= date_from]
    target_df = target_df[target_df["ReportingDate"].dt.year >= date_from.year]
if date_to:
    filtered_df = filtered_df[filtered_df["Date"].dt.date <= date_to]
    target_df = target_df[target_df["ReportingDate"].dt.year <= date_to.year]

# Slicer Filtering
for col, selected_vals in slicer_selections.items():
    if selected_vals and "All" not in selected_vals:
        if col in filtered_df.columns:
            filtered_df = filtered_df[
                filtered_df[col].astype(str).str.strip().isin(selected_vals)
            ]
        if col in target_df.columns:
            target_df = target_df[
                target_df[col].astype(str).str.strip().isin(selected_vals)
            ]


# --- MAIN CONTENT ---
st.title("YgnTBPro Data Analysis Dashboard")
st.caption(
    "Use the sidebar filters to dynamically update all indicators and visualizations."
)
st.divider()

# Compute Achievements & Targets
achievement = fn.function_indicator_achievement(
    filtered_df, CRITERIA_INDICATORS
)
progress = fn.function_merge_target(
    achievement, target_df, indicators=tuple(CRITERIA_INDICATORS.keys())
)

total_attendant = len(filtered_df)
presumptive_count = achievement["Examined Cases"].sum()
notified_count = achievement["Notified Cases"].sum()
bact_confirmed_count = achievement["BC Cases"].sum()

presumptive_sum = progress["Examined Cases Target"].sum()
notified_sum = progress["Notified Cases Target"].sum()
bact_confirmed_sum = 250


# --- KPI METRIC CARDS ---
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

# 1. Achievement vs Target & Variance Heatmap
c1, c2 = st.columns(2)
with c1:
    fig_ach = fn.plotly_achievement_target_dropdown(
        dataframe=progress,
        achievement_columnList=[
            "Examined Cases Achievement",
            "Notified Cases Achievement",
            "BC Cases Achievement",
        ],
        target_columnList=[
            "Examined Cases Target",
            "Notified Cases Target",
            "BC Cases Target",
        ],
        period="Monthly",
        date_col="ReportingDate",
    )
    st.plotly_chart(fig_ach, use_container_width=True)

with c2:
    fig_var = fn.plotly_variance_heatmap(
        progress, color_scale_range=(0, 200)
    )
    st.plotly_chart(fig_var, use_container_width=True)


# 2. Demographics & Categorical Breakdown
c3, c4 = st.columns(2)
with c3:
    fig_demo = fn.plotly_gender_agegroup(filtered_df, "Sex", "Age", 400)
    st.plotly_chart(fig_demo, use_container_width=True)

with c4:
    fig_stack = fn.plotly_stack_bar(
        filtered_df,
        columns=[
            "Bact_status",
            "Treatmentreferral",
            "TypeofTBTreatment",
        ],
        exclude_blank=True,
        orientation="h",
        title="Distribution of Cases",
    )
    st.plotly_chart(fig_stack, use_container_width=True)


# 3. Heatmap & Sankey Cascade
c5, c6 = st.columns(2)
with c5:
    fig_heat = fn.function_heatmap(
        filtered_df, "CXRresult", "GeneXpertresult"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

with c6:
    colSankey = {
        "VOL": ["Volunteer Referral", "Walk-In"],
        "Referralfor": ["CI", "Presumptive"],
        "Case": ["TB"],
        "Bact_status": ["BC", "CD"],
        "Treatmentreferral": ["Registered"],
    }
    df_sankey = filtered_df[
        filtered_df["Reasonforexamination"] == "Diagnosis"
    ]
    fig_sankey = fn.function_sankey_cascade_log(
        dataframe=df_sankey,
        criteria_dict=colSankey,
        title="TB Cascade: Diagnosis to Registration",
        log_base=10,
    )
    st.plotly_chart(fig_sankey, use_container_width=True)


# 4. Period Breakdowns & Target vs Achievement Grid
st.subheader("--- Target vs Achievement Breakdowns ---")

charts = fn.plotly_target_achievement_allcharts(
    dataframe=progress,
    date_config={"ReportingDate": "Reporting Period"},
    bar_configs=[
        {
            "Examined Cases Target": "Examined Cases Target",
            "Examined Cases Achievement": "Examined Cases Achievement",
        },
        {
            "Notified Cases Target": "Notified Cases Target",
            "Notified Cases Achievement": "Notified Cases Achievement",
        },
        {
            "BC Cases Target": "BC Cases Target",
            "BC Cases Achievement": "BC Cases Achievement",
        },
    ],
    optional_percentage=True,
    percentage_calc={
        "Examined Cases": (
            "Examined Cases Achievement",
            "Examined Cases Target",
        ),
        "Notified Cases": (
            "Notified Cases Achievement",
            "Notified Cases Target",
        ),
        "BC Cases": ("BC Cases Achievement", "BC Cases Target"),
    },
    freq="Month",
)

col_a, col_b, col_c = st.columns(3)
with col_a:
    st.plotly_chart(charts["Examined Cases"], use_container_width=True)
with col_b:
    st.plotly_chart(charts["Notified Cases"], use_container_width=True)
with col_c:
    st.plotly_chart(charts["BC Cases"], use_container_width=True)


# 5. Diagnostic Funnel & Categorical Table
st.subheader("--- Diagnostic Cascade Funnel & Summary ---")

funnel_criteria = {
    "Reasonforexamination": ["Diagnosis"],
    "Cxrr": ["Requested"],
    "CXRresult": ["TB Suspect", "TB Healed", "TB Active"],
    "Genexpertrequested": ["Requested"],
    "GeneXpertresult": ["N", "T", "TT", "TI", "RR"],
    "Bact_status": ["BC"],
    "Case": ["TB"],
    "Treatmentreferral": ["Registered"],
}
funnel_renames = [
    "Screening",
    "CXR Request",
    "CXR Abnormality",
    "Gene Request",
    "Gene Result",
    "Bact Confirmed",
    "Notified TB",
    "Treatment Registered",
]

c7, c8 = st.columns(2)
with c7:
    fig_funnel = fn.plotly_funnel(
        filtered_df, funnel_criteria, funnel_renames, "Symptom"
    )
    st.plotly_chart(fig_funnel, use_container_width=True)

with c8:
    fig_tbl = fn.plotly_table_count_percent(
        df=filtered_df,
        column_list=[
            "Sex",
            "CXRresult",
            "GeneXpertresult",
            "Case",
            "Placeforreferral",
        ],
        optional_exclude_blank=True,
        optional_include_total=True,
    )
    st.plotly_chart(fig_tbl, use_container_width=True)


# Raw Data Preview Expander
with st.expander("📄 View Filtered Raw Data"):
    st.dataframe(filtered_df, use_container_width=True)
