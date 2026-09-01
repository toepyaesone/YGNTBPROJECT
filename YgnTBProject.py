import datetime
import pandas as pd
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output

# Import project functions
from functions import (
    switchingRowToColumn,
    function_uncode,
    function_reporting_period,
    create_category,
    function_indicator_achievement,
    function_merge_target,
    plotly_achievement_target_dropdown,
    plotly_variance_heatmap,
    plotly_gender_agegroup,
    plotly_stack_bar,
    function_heatmap,
    function_sankey_cascade_log,
    plotly_target_achievement_allcharts,
    plotly_funnel,
    plotly_table_count_percent
)

# --- CONSTANTS & CONFIGURATION ---
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
    "CXRresult": {
        "1": "Normal", "2": "TB Active", "3": "TB Suspect", "4": "TB Healed", "5": "Other Abnormal"
    },
    "GeneXpertresult": {
        "0": "N", "1": "I", "2": "T", "3": "RR", "4": "TI", "5": "Denied", "6": "Missing", "7": "TT"
    },
    "Placeforreferral": {
        "1": "NTP", "2": "MMA", "3": "PSI", "4": "MATA", "5": "Other"
    },
    "TreatmentRegimen": {
        "1": "IR", "2": "RR", "3": "CR", "4": "MDR", "5": "MR"
    },
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


# --- DATA PREPROCESSING ---
# Target Dataset Processing
df_target = switchingRowToColumn(
    df=df_target, 
    column_name="Indicator", 
    preserved_column_list=COLUMN_PRESERVED_FOR_TARGET, 
    value_col="Target"
)
df_target = function_uncode(df=df_target, colName=["Team"], mapping=UNCODE_MAPPING)
df_target = function_reporting_period(df_target, date_col="ReportingDate")
df_target.rename(columns={"Group": "Clinic"}, inplace=True)

# Main Dashboard Dataset Processing
mapping_TargetCategory = {
    "PPM": ["PPM", "Diagnostic Center"], 
    "Mobile": ["Mobile Visit", "Elderly Care", "Touring"]
}
df_dashboard = create_category(
    df_dashboard, 
    source_col="Approach", 
    criteria_mapping=mapping_TargetCategory, 
    output_col="TargetCategory", 
    default=""
)
df_dashboard.rename(columns={"EPI11": "Clinic"}, inplace=True)
df_dashboard = function_uncode(df_dashboard, colName=COLUMN_UNCODE, mapping=UNCODE_MAPPING)
df_dashboard = function_reporting_period(df_dashboard)

# Slicer Setup
df_slicer = df_dashboard.copy()
df_slicer["Date"] = pd.to_datetime(df_slicer["Date"])
min_date = pd.to_datetime(df_slicer["Date"].min()).date()
max_date = pd.to_datetime(df_slicer["Date"].max()).date()


# --- HELPER FUNCTIONS ---
def classify_symptomatic(df: pd.DataFrame, symptom_cols, target_val: str = "yes") -> pd.Series:
    """Classifies cases as Symptomatic or Asymptomatic based on specified symptom columns."""
    cols = [symptom_cols] if isinstance(symptom_cols, str) else list(symptom_cols)
    valid_cols = [c for c in cols if c in df.columns]
    
    if not valid_cols:
        return pd.Series("Asymptomatic", index=df.index)
        
    cleaned_symptoms = (
        df[valid_cols]
        .fillna("")
        .astype(str)
        .apply(lambda col: col.str.strip().str.lower())
    )
    has_symptom_mask = cleaned_symptoms.eq(target_val.lower()).any(axis=1)
    
    symptom_series = pd.Series("Asymptomatic", index=df.index)
    symptom_series[has_symptom_mask] = "Symptomatic"
    return symptom_series


def get_options(df: pd.DataFrame, column_name: str) -> list:
    """Extracts unique values for slicer options."""
    if column_name in df.columns:
        cleaned_values = df[column_name].dropna().astype(str).str.strip()
        unique_vals = sorted(
            list(cleaned_values.replace(["nan", "None", ""], "blank").unique())
        )
        return ["All"] + unique_vals
    return ["All"]


# --- WIDGET CONTROLS ---
date_from = widgets.DatePicker(description="From:", value=min_date, style={"description_width": "initial"})
date_to = widgets.DatePicker(description="To:", value=max_date, style={"description_width": "initial"})

slicers = {
    col: widgets.SelectMultiple(
        options=get_options(df_slicer, col),
        value=("All",),
        description=f"{col}:",
        layout=widgets.Layout(width="220px", height="100px"),
    )
    for col in COLUMNS_SLICER
}

dashboard_output = widgets.Output()


# --- DASHBOARD UPDATE CALLBACK ---
def update_dashboard(change=None):
    with dashboard_output:
        clear_output(wait=True)

        filtered_df = df_slicer.copy()
        target_df = df_target.copy()
        filtered_df['Symptom'] = classify_symptomatic(filtered_df, COLUMN_SYMPTOM)

        # Apply Date Filtering
        if date_from.value:
            filtered_df = filtered_df[filtered_df["Date"].dt.date >= date_from.value]
            target_df = target_df[target_df['ReportingDate'].dt.year >= date_from.value.year]
        if date_to.value:
            filtered_df = filtered_df[filtered_df["Date"].dt.date <= date_to.value]
            target_df = target_df[target_df['ReportingDate'].dt.year <= date_to.value.year]

        # Apply Multi-select Slicer Filtering
        for col, slicer_widget in slicers.items():
            selected_vals = slicer_widget.value
            if selected_vals and "All" not in selected_vals:
                if col in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df[col].astype(str).str.strip().isin(selected_vals)]
                if col in target_df.columns:
                    target_df = target_df[target_df[col].astype(str).str.strip().isin(selected_vals)]

        # Indicator Calculations
        achievement = function_indicator_achievement(filtered_df, CRITERIA_INDICATORS)
        progress = function_merge_target(achievement, target_df, indicators=tuple(CRITERIA_INDICATORS.keys()))

        total_attendant = len(filtered_df)
        presumptive_count = achievement['Examined Cases'].sum()
        notified_count = achievement['Notified Cases'].sum()
        bact_confirmed_count = achievement['BC Cases'].sum()

        presumptive_sum = progress['Examined Cases Target'].sum()
        notified_sum = progress['Notified Cases Target'].sum()
        bact_confirmed_sum = progress['BC Cases Target'].sum()

        # Render KPI Cards (HTML)
        kpi_html = f"""
        <div style="display: flex; gap: 15px; font-family: Arial, sans-serif; margin-bottom: 20px;">
            <div style="flex: 1; background-color: #f0f4f8; border-left: 5px solid #2b6cb0; padding: 12px; border-radius: 4px;">
                <span style="font-size: 12px; color: #4a5568; font-weight: bold; text-transform: uppercase;">Total Attendant</span>
                <h2 style="margin: 5px 0 0 0; color: #2b6cb0; font-size: 24px;">{total_attendant:,}</h2>
            </div>
            <div style="flex: 1; background-color: #f7fafc; border-left: 5px solid #319795; padding: 12px; border-radius: 4px;">
                <span style="font-size: 12px; color: #4a5568; font-weight: bold; text-transform: uppercase;">Examined Cases</span>
                <h2 style="margin: 5px 0 0 0; color: #319795; font-size: 24px;">{presumptive_count:,}</h2>
                <div style="font-size: 11px; color: #718096; font-weight: bold; margin-top: 6px;">
                    Target: {presumptive_sum:,}
                </div>
            </div>
            <div style="flex: 1; background-color: #f7fafc; border-left: 5px solid #dd6b20; padding: 12px; border-radius: 4px;">
                <span style="font-size: 12px; color: #4a5568; font-weight: bold; text-transform: uppercase;">Notified Cases</span>
                <h2 style="margin: 5px 0 0 0; color: #dd6b20; font-size: 24px;">{notified_count:,}</h2>
                <div style="font-size: 11px; color: #718096; font-weight: bold; margin-top: 6px;">
                    Target: {notified_sum:,}
                </div>
            </div>
            <div style="flex: 1; background-color: #f7fafc; border-left: 5px solid #805ad5; padding: 12px; border-radius: 4px;">
                <span style="font-size: 12px; color: #4a5568; font-weight: bold; text-transform: uppercase;">BC Cases</span>
                <h2 style="margin: 5px 0 0 0; color: #805ad5; font-size: 24px;">{bact_confirmed_count:,}</h2>
                <div style="font-size: 11px; color: #718096; font-weight: bold; margin-top: 6px;">
                    Target: {bact_confirmed_sum:,}
                </div>
            </div>
        </div>
        """
        display(HTML(kpi_html))

        # Render Visualizations
        plotly_achievement_target_dropdown(
            dataframe=progress,
            achievement_columnList=["Examined Cases Achievement", "Notified Cases Achievement", "BC Cases Achievement"],
            target_columnList=["Examined Cases Target", "Notified Cases Target", "BC Cases Target"],
            period="Monthly",
            date_col="ReportingDate"
        ).show()

        plotly_variance_heatmap(progress, color_scale_range=(0, 200)).show()

        plotly_gender_agegroup(filtered_df, "Sex", "Age", 500).show()

        plotly_stack_bar(
            filtered_df,
            columns=['Bact_status', 'Treatmentreferral', 'TreatmentRegimen', 'DM1', 'HIVStatus', 'TypeofTBTreatment', 'TPTregimen'],
            exclude_blank=True,
            orientation="h",
            title="Distribution of Cases"
        ).show()

        plotly_stack_bar(
            filtered_df,
            columns=["Treatmentreferral", "Tsp", "Approach", "Case", "Sex"],
            exclude_blank=True,
            orientation="h",
            title="Distribution of Cases Across Facilities"
        ).show()

        function_heatmap(filtered_df, "CXRresult", "GeneXpertresult").show()

        col_sankey = {
            "VOL": ["Volunteer Referral", "Walk-In"],
            "Referralfor": ["CI", "Presumptive"],
            "Case": ["TB"],
            "Bact_status": ["BC", "CD"],
            "Treatmentreferral": ["Registered"]
        }
        df_sankey = filtered_df[filtered_df["Reasonforexamination"] == "Diagnosis"]
        function_sankey_cascade_log(
            dataframe=df_sankey,
            criteria_dict=col_sankey,
            title="TB Cascade: Diagnosis to Treatment Registration",
            log_base=10
        ).show()

        # Target vs Achievement Breakdown Charts
        charts = plotly_target_achievement_allcharts(
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

        chart_ExaminedCases = widgets.Output()
        with chart_ExaminedCases:
            display(charts["Examined Cases"])

        chart_NotifiedCases = widgets.Output()
        with chart_NotifiedCases:
            display(charts["Notified Cases"])

        chart_BCCases = widgets.Output()
        with chart_BCCases:
            display(charts["BC Cases"])

        display(widgets.HBox(
            [chart_ExaminedCases, chart_NotifiedCases, chart_BCCases],
            layout=widgets.Layout(gap="40px", margin="10px 0px 20px 0px")
        ))

        # Diagnostic Cascade Funnel & Summary Table
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
        
        plotly_funnel(filtered_df, funnel_column_criteria, funnel_column_rename, 'Symptom').show()

        plotly_table_count_percent(
            df=filtered_df, 
            column_list=['Sex', 'CXRresult', 'GeneXpertresult', 'Case', 'Placeforreferral'], 
            optional_exclude_blank=True, 
            optional_include_total=True
        ).show()


# --- EVENT LISTENERS ---
date_from.observe(update_dashboard, names="value")
date_to.observe(update_dashboard, names="value")
for slicer_widget in slicers.values():
    slicer_widget.observe(update_dashboard, names="value")

# --- LAYOUT INITIALIZATION ---
date_ui = widgets.HBox([date_from, date_to], layout=widgets.Layout(margin="0px 0px 10px 0px"))
slicers_ui = widgets.HBox(list(slicers.values()), layout=widgets.Layout(flex_flow="row wrap", gap="15px"))

dashboard_layout = widgets.VBox([
    widgets.HTML(
        "<h3 style='font-family:Arial;color:#2d3748;margin-bottom:5px;'>YgnTBPro Data Analysis Dashboard</h3>"
        "<p style='font-size:12px;color:#718096;margin-top:0px;'>Hold Down <b>Ctrl</b> (or <b>Cmd</b> on Mac) to select multiple options.</p>"
    ),
    widgets.VBox([date_ui, slicers_ui]),
    widgets.HTML("<hr style='border: 1px solid #e2e8f0; margin: 15px 0;'>"),
    dashboard_output
])

# Trigger initial render
update_dashboard()
display(dashboard_layout)
