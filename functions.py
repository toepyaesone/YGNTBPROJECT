import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

COLUMNS_SLICER = [
    "Team",
    "Tsp",
    "Approach",
    "Clinic",
    "Reasonforexamination",
    "Case",
    "Bact_status",
    "Treatmentreferral",
    "MonthDiagnosis11",
    "Cxrr",
    "CXRresult",
    "CXRresult211",
    "Genexpertrequested",
    "GeneXpertresult",
    "TypeofTBTreatment",
    "TargetCategory",
]


def classify_symptomatic(
    df: pd.DataFrame, symptom_cols, target_val: str = "yes"
) -> pd.Series:
    """Classifies cases into Symptomatic or Asymptomatic based on specified columns."""
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
    """Extracts unique sorted values from a dataframe column for multi-select options."""
    if column_name in df.columns:
        cleaned_values = df[column_name].dropna().astype(str).str.strip()
        unique_vals = sorted(
            list(cleaned_values.replace(["nan", "None", ""], "blank").unique())
        )
        return ["All"] + unique_vals
    return ["All"]


# --- STUB/FALLBACK IMPLEMENTATIONS ---
# Replace these with your actual custom plotting logic if imported from external packages


def function_indicator_achievement(
    df: pd.DataFrame, criteria_indicators: dict
) -> pd.DataFrame:
    """Calculates achievements based on criteria."""
    # Custom business logic goes here
    return pd.DataFrame(
        {
            "Examined Cases": [len(df)],
            "Notified Cases": [
                len(df[df["Case"] == "TB"]) if "Case" in df else 0
            ],
            "BC Cases": [
                len(df[df["Bact_status"] == "BC"]) if "Bact_status" in df else 0
            ],
        }
    )


def function_merge_target(
    achievement_df: pd.DataFrame, target_df: pd.DataFrame, indicators: tuple
) -> pd.DataFrame:
    """Merges achievement calculations with target baseline dataframes."""
    # Return placeholder structured df for rendering charts
    df = target_df.copy() if not target_df.empty else pd.DataFrame()
    df["ReportingDate"] = pd.to_datetime(
        df.get("ReportingDate", pd.date_range("2026-01-01", periods=12, freq="M"))
    )
    df["Examined Cases Target"] = df.get("Examined Cases Target", 500)
    df["Examined Cases Achievement"] = df.get("Examined Cases Achievement", 450)
    df["Notified Cases Target"] = df.get("Notified Cases Target", 200)
    df["Notified Cases Achievement"] = df.get("Notified Cases Achievement", 180)
    df["BC Cases Target"] = df.get("BC Cases Target", 100)
    df["BC Cases Achievement"] = df.get("BC Cases Achievement", 90)
    return df


def plotly_achievement_target_dropdown(
    dataframe, achievement_columnList, target_columnList, period, date_col
):
    fig = go.Figure()
    for col in achievement_columnList:
        if col in dataframe.columns:
            fig.add_trace(
                go.Scatter(
                    x=dataframe[date_col],
                    y=dataframe[col],
                    mode="lines+markers",
                    name=col,
                )
            )
    fig.update_layout(
        title="Achievement vs Target", margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def plotly_variance_heatmap(dataframe, color_scale_range=(0, 200)):
    fig = px.imshow(
        np.random.randint(50, 150, size=(5, 5)),
        labels=dict(x="Indicators", y="Townships", color="Variance %"),
        title="Variance Heatmap",
    )
    return fig


def plotly_gender_agegroup(
    df: pd.DataFrame, sex_col: str, age_col: str, height: int = 400
):
    if sex_col in df.columns and age_col in df.columns:
        fig = px.histogram(
            df,
            x=age_col,
            color=sex_col,
            barmode="group",
            title="Age & Gender Distribution",
        )
    else:
        fig = go.Figure()
        fig.update_layout(title="Age & Gender Distribution (No Data)")
    fig.update_layout(height=height, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def plotly_stack_bar(
    df: pd.DataFrame,
    columns: list,
    exclude_blank: bool = True,
    orientation: str = "h",
    title: str = "Distribution",
):
    fig = go.Figure()
    valid_cols = [c for c in columns if c in df.columns]
    for col in valid_cols:
        counts = df[col].value_counts()
        fig.add_trace(go.Bar(x=counts.values, y=counts.index, name=col, orientation="h"))
    fig.update_layout(
        barmode="stack", title=title, margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def function_heatmap(df: pd.DataFrame, col1: str, col2: str):
    if col1 in df.columns and col2 in df.columns:
        ct = pd.crosstab(df[col1], df[col2])
        fig = px.imshow(
            ct, text_auto=True, title=f"Cross-tabulation: {col1} vs {col2}"
        )
    else:
        fig = go.Figure()
        fig.update_layout(title="Heatmap (Columns missing)")
    return fig


def function_sankey_cascade_log(
    dataframe, criteria_dict, title, log_base=10
):
    fig = go.Figure(
        go.Sankey(
            node=dict(
                pad=15,
                thickness=20,
                line=dict(color="black", width=0.5),
                label=["Diagnosis", "Screened", "CXR", "GeneXpert", "Registered"],
            ),
            link=dict(
                source=[0, 1, 2, 3],
                target=[1, 2, 3, 4],
                value=[80, 60, 40, 20],
            ),
        )
    )
    fig.update_layout(title_text=title, font_size=10)
    return fig


def plotly_target_achievement_allcharts(
    dataframe, date_config, bar_configs, optional_percentage, percentage_calc, freq
):
    charts = {}
    metrics = ["Examined Cases", "Notified Cases", "BC Cases"]
    for m in metrics:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=["Jan", "Feb", "Mar"], y=[100, 120, 140], name="Achievement"
            )
        )
        fig.add_trace(
            go.Bar(x=["Jan", "Feb", "Mar"], y=[110, 110, 110], name="Target")
        )
        fig.update_layout(
            title=f"{m} - Target vs Achievement", barmode="group"
        )
        charts[m] = fig
    return charts


def plotly_funnel(
    df: pd.DataFrame, criteria: dict, renames: list, group_col: str
):
    fig = go.Figure(
        go.Funnel(
            y=renames,
            x=[1000, 800, 600, 500, 400, 300, 200, 180],
            textinfo="value+percent initial",
        )
    )
    fig.update_layout(title="TB Diagnostic & Treatment Cascade Funnel")
    return fig


def plotly_table_count_percent(
    df: pd.DataFrame,
    column_list: list,
    optional_exclude_blank=True,
    optional_include_total=True,
):
    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=["Category", "Count", "Percentage"],
                    fill_color="paleturquoise",
                    align="left",
                ),
                cells=dict(
                    values=[
                        ["Male", "Female", "TB Active"],
                        [120, 90, 45],
                        ["48%", "36%", "16%"],
                    ],
                    fill_color="lavender",
                    align="left",
                ),
            )
        ]
    )
    fig.update_layout(title="Categorical Summary Table")
    return fig
