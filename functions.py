import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import requests
import requests.adapters
import urllib3.util.connection as urllib3_conn

SUPABASE_URL = "https://kocihpxevlowqbguhstf.supabase.co"
SUPABASE_KEY = "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z"
ALT_CLOUDFLARE_IPS = ["104.16.132.229", "104.18.32.7", "172.67.74.135"]

COLUMN_UNCODE = [
        'Team','Sex','VOL','Referralfor','Cough','Fever','Wtloss','Nightsweat','Haemoptysis','Chestpain','Fatigue','Neckglands',
        'TBcontact','MDRTBcontact','TBTreatmenthistory','Smoking','Reasonforexamination','TypeofPatient','PublicHealthCare1',
        'TypeofPatient1','DM1','HT1','DMHT1','RTIAVI1','Generalweakness1','Other1','Cxrr','CXRresult','Sputum_request','Micror',
        'Sputummicroscopyresult','Genexpertrequested','GeneXpertresult','Bact_status','Case','Treatmentreferral','TreatmentRegimen',
        'Placeforreferral','TreatmentOutcome1211','ContactInvestigation111','DOTSupervision111','DOTsupervisiontillTreatmentComp111',
        'Seeing1','Hearing1','Walking1','Cognition1','Selfcare1','Communication1','Disability1','Xray2ndReading11','CXRresult211',
        'TypeofTBTreatment'
    ]

COLUMN_DISABILITY = ["Seeing1","Hearing1","Walking1","Cognition1","Selfcare1","Communication1"]
COLUMN_SYMPTOM = ['Cough','Fever','Wtloss','Nightsweat','Haemoptysis','Chestpain','Fatigue','Neckglands']
COLUMN_PRESERVED_FOR_TARGET = ["ReportingDate","Team","Tsp","TargetCategory","Group"]
    
UNCODE_DISABILITY = {
        "1": "No - No Difficulty",
        "2": "Yes - Some Difficulty",
        "3": "Yes - A lot of Difficulty",
        "4": "Yes - Can not do it at all"
    }
    
UNCODE_MAPPING = {
        "CXRresult": {
            "1": "Normal", "2": "TB Active", "3": "TB Suspect", "4": "TB Healed", "5": "Other Abnormal"
        },
        "CXRresult211": {
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
        "DM1": {"1": "DM-New", "2": "No DM", "3": "DM-Old"},
        "HT1": {"1": "HT-New", "2": "No DM", "3": "HT-Old"},
        "HIVStatus": {"N": "Negative", "P": "Positive", "U": "Unknown"},
        "Genexpertrequested": {"1": "Requested", "2": "Not Requested"},
        "Bact_status": {"1": "BC", "2": "CD"},
        "Treatmentreferral": {"1": "Registered", "2": "Not Registered"},
        "TypeofPatient1": {"1": "New", "2": "Old"},
        "Team": {"1": "MMA", "5": "MATA"}
    }
    
UNCODE_DEFAULT = {"1": "Yes", "2": "No"}
MISSING_STRINGS = {"", "none", "nan", "null", "n/a", "na", "<na>", "nat", "#n/a", "-", "None", "NONE", "NaN", "NULL", "<NA>", "N/A", "NaT"}
    
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
    
COLUMN_CI_DOTS = [
        'Case','Bact_status','Treatmentreferral','TypeofTBTreatment','Age',
        'HIVStatus','ContactInvestigation111', 'DOTSupervision111', 
        'DOTStartedDate111','DOTsupervisiontillTreatmentComp111',
        'Tsp','Ptstsp','VOL','Referralfor','VolunteerName','Organization',
        'TreatmentOutcome1211','Tx_Outcome_Date','DOTvolName111',
        'VolunteerGender111','VolunteerOrganization111'
    ]
    
mapping_TargetCategory = {"PPM": ["PPM", "Diagnostic Center"], "Mobile": ["Mobile Visit", "Elderly Care", "Touring"]}


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


def functionGetDataFromTable(
    tableName: str,
    url: str = SUPABASE_URL,
    key: str = SUPABASE_KEY,
    page_size: int = 1000,
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
        raise ConnectionError("Failed to reach Supabase across all routes.")

    all_data = []
    start_index = 0

    while True:
        page_headers = headers.copy()
        page_headers["Range"] = f"{start_index}-{start_index + page_size - 1}"
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


def normalize(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() in MISSING_STRINGS:
        return ""
    try:
        f = float(s)
        return str(int(f)) if f.is_integer() else str(f)
    except (ValueError, TypeError):
        return s


def clean_missing(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    non_datetime_cols = [
        col for col in df.columns if not pd.api.types.is_datetime64_any_dtype(df[col])
    ]
    for col in non_datetime_cols:
        df[col] = df[col].astype(str).str.strip()
    df[non_datetime_cols] = df[non_datetime_cols].replace(
        {s: "" for s in MISSING_STRINGS}
    )
    return df


def function_uncode(df: pd.DataFrame, colName=None, mapping=None) -> pd.DataFrame:
    df = clean_missing(df)
    mapping = mapping or {}
    if colName is None:
        columns = list(colName)
        print("No columns specified for uncode. Please provide a column name or list of column names.")
    elif isinstance(colName, str):
        columns = [colName]
    else:
        columns = list(colName)
    for col in columns:
        if col not in df.columns or pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        if col in mapping:
            mp = {normalize(k): v for k, v in mapping[col].items()}
        elif col in COLUMN_DISABILITY:
            mp = UNCODE_DISABILITY
        else:
            mp = UNCODE_DEFAULT
        df[col] = df[col].apply(lambda x: mp.get(normalize(x), x if x else ""))
    return df


def switchingRowToColumn(df, column_name, preserved_column_list, value_col=None):
    if value_col:
        df_reshaped = df.pivot_table(
            index=preserved_column_list,
            columns=column_name,
            values=value_col,
            aggfunc="first",
        ).reset_index()
    else:
        df_reshaped = (
            df.groupby(preserved_column_list + [column_name])
            .size()
            .unstack(fill_value=0)
            .reset_index()
        )
    df_reshaped.columns.name = None
    return df_reshaped


def function_reporting_period(df, date_col="Date", cutoff=25):
    df = df.copy()
    d = pd.to_datetime(df[date_col])
    df["ReportingDate"] = np.where(
        d.dt.day > cutoff,
        (d + pd.DateOffset(months=1)).dt.to_period("M").dt.to_timestamp(),
        d.dt.to_period("M").dt.to_timestamp(),
    )
    return df


def create_category(
    df, source_col, criteria_mapping, output_col="COLUMN_NEW", default=""
):
    df = df.copy()
    source = df[source_col]
    conditions = [
        source.isin(source_values) for source_values in criteria_mapping.values()
    ]
    choices = list(criteria_mapping.keys())
    df[output_col] = np.select(conditions, choices, default=default)
    return df


def function_indicator_achievement(
    dataframe, criteria_indicator, group_columns=None
):
    df = dataframe.copy()
    if group_columns is None:
        group_columns = ["ReportingDate", "Team", "TargetCategory", "Tsp", "Clinic"]

    for indicator, rules in criteria_indicator.items():
        flag = pd.Series(True, index=df.index)
        for column, value in rules.items():
            if column not in df.columns:
                raise KeyError(
                    f"Column '{column}' required for "
                    f"indicator '{indicator}' was not found."
                )
            flag &= (
                df[column]
                .fillna("")
                .astype(str)
                .str.strip()
                .eq(str(value).strip())
            )
        df[indicator] = flag.astype(int)
    indicator_columns = list(criteria_indicator.keys())
    summary = df.groupby(group_columns, as_index=False)[indicator_columns].sum()
    return summary


def function_merge_target(
    achievement, target, indicators=("Examined Cases", "Notified Cases", "BC Cases")
):
    keys = ["ReportingDate", "Team", "TargetCategory", "Tsp", "Clinic"]
    indicators = list(indicators)
    missing_ach = [c for c in keys + indicators if c not in achievement.columns]
    missing_tar = [c for c in keys + indicators if c not in target.columns]
    if missing_ach:
        raise KeyError(f"Missing columns in achievement: {missing_ach}")
    if missing_tar:
        raise KeyError(f"Missing columns in target: {missing_tar}")
    ach = achievement[keys + indicators].copy()
    tar = target[keys + indicators].copy()
    ach["ReportingDate"] = pd.to_datetime(ach["ReportingDate"], errors="coerce")
    tar["ReportingDate"] = pd.to_datetime(tar["ReportingDate"], errors="coerce")
    min_year = ach["ReportingDate"].dt.year.min()
    max_year = ach["ReportingDate"].dt.year.max()
    tar = tar[tar["ReportingDate"].dt.year.between(min_year, max_year)].copy()
    for col in indicators:
        tar[col] = pd.to_numeric(tar[col], errors="coerce").round().astype("Int64")
        ach[col] = pd.to_numeric(ach[col], errors="coerce").round().astype("Int64")
    tar = tar.rename(columns={c: f"{c} Target" for c in indicators})
    ach = ach.rename(columns={c: f"{c} Achievement" for c in indicators})
    return tar.merge(ach, on=keys, how="left")


def plotly_achievement_target_dropdown(
    dataframe: pd.DataFrame,
    achievement_columnList: list,
    target_columnList: list,
    period: str = "Monthly",
    date_col: str = "Date",
) -> go.Figure:
    df_clean = dataframe.copy()
    df_clean[date_col] = pd.to_datetime(df_clean[date_col])
    df_clean["Year"] = df_clean[date_col].dt.year

    periods_config = {
        "Monthly": {
            "label": "Monthly",
            "freq": "MS",
            "date_fmt": "%b %Y",
            "divisor": 12,
        },
        "Quarterly": {
            "label": "Quarterly",
            "freq": "QS",
            "date_fmt": "Q%q %Y",
            "divisor": 4,
        },
        "Semiannually": {
            "label": "Semiannually",
            "freq": "6MS",
            "date_fmt": "%b %Y",
            "divisor": 2,
        },
        "Annually": {
            "label": "Annually",
            "freq": "YS",
            "date_fmt": "%Y",
            "divisor": 1,
        },
    }

    shared_colors = ["#2ca02c", "#ff7f0e", "#d9381e", "#9467bd", "#17becf"]

    annual_targets = df_clean.groupby("Year")[target_columnList].sum()
    frames_data = {}

    for p_key, p_cfg in periods_config.items():
        agg_df = (
            df_clean.set_index(date_col)
            .resample(p_cfg["freq"])[achievement_columnList]
            .sum()
            .reset_index()
        )
        agg_df["Year"] = agg_df[date_col].dt.year

        if p_key == "Quarterly":
            agg_df["Period_Label"] = agg_df[date_col].dt.to_period("Q").astype(str)
        elif p_key == "Semiannually":
            agg_df["Period_Label"] = (
                agg_df[date_col].dt.year.astype(str)
                + "S"
                + (agg_df[date_col].dt.month.gt(6).astype(int) + 1).astype(str)
            )
        else:
            agg_df["Period_Label"] = agg_df[date_col].dt.strftime(p_cfg["date_fmt"])

        period_targets = {}
        for t_col in target_columnList:
            yearly_t = agg_df["Year"].map(annual_targets[t_col])
            period_targets[t_col] = (yearly_t / p_cfg["divisor"]).mean()

        frames_data[p_key] = {
            "agg_df": agg_df,
            "period_targets": period_targets,
        }

    def get_log_axis_config(agg_df, period_targets):
        target_vals = list(period_targets.values())
        bar_vals = agg_df[achievement_columnList].values.flatten()
        all_vals = [v for v in np.append(bar_vals, target_vals) if v > 0]

        if not all_vals:
            min_exp, max_exp = 0, 4
        else:
            min_val, max_val = min(all_vals), max(all_vals)
            min_exp = int(np.floor(np.log10(min_val)))
            max_exp = int(np.ceil(np.log10(max_val * 1.3)))

        power_ticks = [10**i for i in range(min_exp, max_exp + 1)]
        power_texts = [f"{v:,.0f}" for v in power_ticks]

        return dict(
            type="log",
            tickmode="array",
            tickvals=power_ticks,
            ticktext=power_texts,
            range=[min_exp - 0.2, max_exp],
            gridcolor="#e5e5e5",
            side="left",
        )

    def build_chart_elements(selected_period):
        p_data = frames_data[selected_period]
        agg_df = p_data["agg_df"]
        p_targets = p_data["period_targets"]

        traces = []
        for i, ach_col in enumerate(achievement_columnList):
            color = shared_colors[i % len(shared_colors)]
            traces.append(
                go.Bar(
                    x=agg_df["Period_Label"],
                    y=agg_df[ach_col],
                    name=ach_col,
                    marker_color=color,
                    text=agg_df[ach_col],
                    texttemplate="%{text:,.0f}",
                    textposition="auto",
                    hovertemplate=f"<b>%{{x}}</b><br>{ach_col}: %{{y:,.2f}}<extra></extra>",
                )
            )

        shapes = []
        annotations = []
        for j, t_col in enumerate(target_columnList):
            t_val = p_targets[t_col]
            color = shared_colors[j % len(shared_colors)]

            shapes.append(
                dict(
                    type="line",
                    xref="paper",
                    x0=0,
                    x1=1,
                    yref="y",
                    y0=t_val,
                    y1=t_val,
                    line=dict(color=color, width=2.5, dash="dash"),
                )
            )

            annotations.append(
                dict(
                    xref="paper",
                    x=0.99,
                    y=np.log10(t_val),
                    yref="y",
                    text=f"<b>🎯 {t_col} ({t_val:,.0f})</b>",
                    showarrow=False,
                    font=dict(color=color, size=11),
                    xanchor="right",
                    yanchor="bottom",
                    bgcolor="rgba(255, 255, 255, 0.8)",
                )
            )

        yaxis_config = get_log_axis_config(agg_df, p_targets)

        return traces, shapes, annotations, yaxis_config

    initial_traces, initial_shapes, initial_annotations, initial_yaxis = (
        build_chart_elements(period)
    )
    fig = go.Figure(data=initial_traces)

    dropdown_buttons = []
    for p_key, p_cfg in periods_config.items():
        p_traces, p_shapes, p_annotations, p_yaxis = build_chart_elements(p_key)

        dropdown_buttons.append(
            dict(
                label=p_cfg["label"],
                method="update",
                args=[
                    {
                        "x": [t.x for t in p_traces],
                        "y": [t.y for t in p_traces],
                        "text": [t.text for t in p_traces],
                    },
                    {
                        "title.text": f"Achievement vs Target ({p_key})",
                        "shapes": p_shapes,
                        "annotations": p_annotations,
                        "yaxis": p_yaxis,
                    },
                ],
            )
        )

    fig.update_layout(
        title=dict(
            text=f"Achievement vs Target ({period})",
            font=dict(size=18),
            x=0.50,
            y=0.95,
        ),
        xaxis_title="Reporting Period",
        yaxis_title="Number of Cases",
        template="plotly_white",
        hovermode="x unified",
        barmode="group",
        bargap=0.2,
        bargroupgap=0.1,
        shapes=initial_shapes,
        annotations=initial_annotations,
        yaxis=initial_yaxis,
        margin=dict(t=80, b=40, l=80, r=80),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0.0
        ),
        updatemenus=[
            dict(
                type="dropdown",
                active=list(periods_config.keys()).index(period),
                x=1.0,
                xanchor="right",
                y=1.15,
                yanchor="top",
                showactive=True,
                buttons=dropdown_buttons,
            )
        ],
    )

    return fig


def plotly_variance_heatmap(
    df: pd.DataFrame,
    indicators: list = ["Examined Cases", "Notified Cases", "BC Cases"],
    date_column: str = "ReportingDate",
    color_scale_range: tuple = None,
):
    data = df.copy()
    data[date_column] = pd.to_datetime(data[date_column])

    records = []

    for ind in indicators:
        t_col, a_col = f"{ind} Target", f"{ind} Achievement"

        if t_col in data.columns and a_col in data.columns:
            achieve_data = data[data[a_col] > 0]

            if achieve_data.empty:
                continue

            date_bounds = (
                achieve_data.groupby(["Tsp", "Clinic"])[date_column]
                .agg(min_date="min", max_date="max")
                .reset_index()
            )

            ind_df = data[["Tsp", "Clinic", date_column, t_col, a_col]].merge(
                date_bounds, on=["Tsp", "Clinic"], how="inner"
            )

            filtered_df = ind_df[
                (ind_df[date_column] >= ind_df["min_date"])
                & (ind_df[date_column] <= ind_df["max_date"])
            ]

            summary = filtered_df.groupby(
                ["Tsp", "Clinic", "min_date", "max_date"], as_index=False
            ).agg({t_col: "sum", a_col: "sum"})

            summary["Location"] = summary["Tsp"] + " | " + summary["Clinic"]
            summary["Indicator"] = ind
            summary["Target"] = summary[t_col]
            summary["Achievement"] = summary[a_col]

            summary["Progress_Pct"] = np.where(
                summary["Target"] > 0,
                (summary["Achievement"] / summary["Target"]) * 100,
                0.0,
            )

            summary["Period"] = (
                summary["min_date"].dt.strftime("%b %d, %Y")
                + " - "
                + summary["max_date"].dt.strftime("%b %d, %Y")
            )

            records.append(
                summary[
                    [
                        "Location",
                        "Indicator",
                        "Target",
                        "Achievement",
                        "Progress_Pct",
                        "Period",
                    ]
                ]
            )

    if not records:
        raise ValueError(
            "No valid achievement data found across the specified indicators."
        )

    combined_df = pd.concat(records, ignore_index=True)

    pct_matrix = combined_df.pivot(
        index="Location", columns="Indicator", values="Progress_Pct"
    )
    target_matrix = combined_df.pivot(
        index="Location", columns="Indicator", values="Target"
    )
    achieve_matrix = combined_df.pivot(
        index="Location", columns="Indicator", values="Achievement"
    )
    period_matrix = combined_df.pivot(
        index="Location", columns="Indicator", values="Period"
    )

    ordered_cols = [ind for ind in indicators if ind in pct_matrix.columns]

    pct_matrix = pct_matrix.reindex(columns=ordered_cols).fillna(0)
    target_matrix = target_matrix.reindex(columns=ordered_cols).fillna(0)
    achieve_matrix = achieve_matrix.reindex(columns=ordered_cols).fillna(0)
    period_matrix = period_matrix.reindex(columns=ordered_cols).fillna("N/A")

    if (
        color_scale_range is not None
        and isinstance(color_scale_range, (tuple, list))
        and len(color_scale_range) == 2
    ):
        z_min, z_max = color_scale_range
    else:
        z_min = float(pct_matrix.values.min())
        z_max = float(pct_matrix.values.max())

    text_matrix = []
    hover_matrix = []

    for loc in pct_matrix.index:
        row_text = []
        row_hover = []
        for ind in pct_matrix.columns:
            tgt = (
                int(target_matrix.loc[loc, ind])
                if loc in target_matrix.index and ind in target_matrix.columns
                else 0
            )
            ach = (
                int(achieve_matrix.loc[loc, ind])
                if loc in achieve_matrix.index and ind in achieve_matrix.columns
                else 0
            )
            pct = (
                pct_matrix.loc[loc, ind]
                if loc in pct_matrix.index and ind in pct_matrix.columns
                else 0.0
            )
            prd = (
                period_matrix.loc[loc, ind]
                if loc in period_matrix.index and ind in period_matrix.columns
                else "N/A"
            )

            cell_str = f" A:{ach:,} | T:{tgt:,}<br><b>{pct:.1f}%</b>"
            row_text.append(cell_str)

            hover_str = (
                f"<b>Location:</b> {loc}<br>"
                f"<b>Indicator:</b> {ind}<br>"
                f"<b>Active Window:</b> {prd}<br>"
                f"<b>Achievement:</b> {ach:,}<br>"
                f"<b>Target:</b> {tgt:,}<br>"
                f"<b>Progress Rate:</b> {pct:.1f}%"
            )
            row_hover.append(hover_str)

        text_matrix.append(row_text)
        hover_matrix.append(row_hover)

    red_white_green = [
        [0.0, "#D9381E"],
        [0.5, "#FFFFFF"],
        [1.0, "#2E7D32"],
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=pct_matrix.values,
            x=list(pct_matrix.columns),
            y=list(pct_matrix.index),
            text=text_matrix,
            texttemplate="%{text}",
            textfont={"size": 11},
            hoverinfo="text",
            hovertext=hover_matrix,
            colorscale=red_white_green,
            zmin=z_min,
            zmax=z_max,
            colorbar=dict(title="% Target Met"),
        )
    )

    overall_min = combined_df["Period"].str.split(" - ").str[0].min()
    overall_max = combined_df["Period"].str.split(" - ").str[1].max()

    fig.update_layout(
        title=f"<b>Performance Heatmap (Active Data Window: {overall_min} to {overall_max})</b><br>"
        f"<sup>Color gradient (Red-White-Green) scale: {z_min:.1f}% to {z_max:.1f}%</sup>",
        template="plotly_white",
        xaxis_title="Indicator",
        yaxis_title="Tsp | Clinic",
        xaxis=dict(categoryorder="array", categoryarray=ordered_cols),
        height=max(450, len(pct_matrix) * 50),
        margin=dict(l=150, r=40, t=90, b=40),
    )

    return fig


def plotly_target_achievement_allcharts(
    dataframe,
    date_config,
    bar_configs,
    optional_percentage=True,
    percentage_calc=None,
    freq="Month",
):
    df = dataframe.copy()

    date_col = list(date_config)[0]
    date_label = date_config[date_col]

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    f = freq.lower()

    if f in ["month", "m"]:
        period = df[date_col].dt.to_period("M")
        label_format = "%Y-%b"

    elif f in ["quarter", "q"]:
        period = df[date_col].dt.to_period("Q")
        label_format = "%Y-Q%q"

    elif f in ["semi-annual", "semi_annual", "sa"]:
        period = (
            df[date_col].dt.year.astype(str)
            + "-"
            + df[date_col].dt.month.map(lambda x: "S1" if x <= 6 else "S2")
        )
        label_format = None

    elif f in ["annual", "year", "a", "y"]:
        period = df[date_col].dt.to_period("Y")
        label_format = "%Y"

    else:
        raise ValueError("freq must be Month, Quarter, Semi-Annual or Annual")

    df_grouped = df.groupby(period).sum(numeric_only=True).reset_index()

    if label_format:
        df_grouped[date_col] = df_grouped[date_col].dt.strftime(label_format)
    else:
        df_grouped.rename(columns={df_grouped.columns[0]: date_col}, inplace=True)

    charts = {}

    for config in bar_configs:
        target_col = next(
            (
                col
                for col, label in config.items()
                if "target" in col.lower() or "target" in label.lower()
            ),
            None,
        )

        achievement_col = next(
            (col for col in config if col != target_col), None
        )

        if not target_col or not achievement_col:
            raise ValueError(
                f"Could not identify Target/Achievement columns: {config}"
            )

        indicator = (
            achievement_col.replace(" Achievement", "")
            .replace("_Achievement", "")
            .replace("Achievement", "")
            .strip()
        )

        target = pd.to_numeric(df_grouped[target_col], errors="coerce").fillna(0)

        achievement = pd.to_numeric(
            df_grouped[achievement_col], errors="coerce"
        ).fillna(0)

        target_total = target.sum()
        achievement_total = achievement.sum()

        progress_total = (
            achievement_total / target_total * 100 if target_total > 0 else None
        )

        progress_label = (
            f"{progress_total:.0f}%" if progress_total is not None else "N/A"
        )

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=df_grouped[date_col].astype(str),
                y=achievement,
                name=f"Achievement ({achievement_total:,.0f})",
                text=achievement.map(lambda x: f"{x:,.0f}"),
                textposition="inside",
                insidetextanchor="middle",
            )
        )

        fig.add_trace(
            go.Scatter(
                x=df_grouped[date_col].astype(str),
                y=target,
                name=f"Target ({target_total:,.0f})",
                mode="lines+markers+text",
                text=target.map(lambda x: f"{x:,.0f}"),
                textposition="top center",
                line=dict(width=2),
                marker=dict(size=7),
            )
        )

        if (
            optional_percentage
            and percentage_calc
            and indicator in percentage_calc
        ):
            num_col, den_col = percentage_calc[indicator]

            if num_col in df_grouped.columns and den_col in df_grouped.columns:
                num = pd.to_numeric(df_grouped[num_col], errors="coerce")

                den = pd.to_numeric(df_grouped[den_col], errors="coerce")

                pct = pd.Series(pd.NA, index=df_grouped.index, dtype="Float64")

                valid = num.notna() & den.notna() & (num > 0) & (den > 0)

                pct.loc[valid] = (
                    num.loc[valid] / den.loc[valid] * 100
                ).round(0)

                fig.add_trace(
                    go.Scatter(
                        x=df_grouped[date_col].astype(str),
                        y=pct,
                        name=f"Progress ({progress_label})",
                        mode="lines+markers+text",
                        text=pct.map(
                            lambda x: f"{x:.0f}%" if pd.notna(x) else ""
                        ),
                        textposition="top center",
                        line=dict(dash="dash", width=2),
                        marker=dict(size=7),
                        connectgaps=False,
                        yaxis="y2",
                    )
                )

        fig.update_layout(
            title=dict(text=indicator, x=0.5, xanchor="center"),
            height=450,
            barmode="group",
            hovermode="x unified",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            template="plotly_white",
            margin=dict(t=100, b=70, l=60, r=60),
        )

        fig.update_xaxes(title_text=date_label)

        fig.update_yaxes(title_text="Cases", rangemode="tozero")

        if optional_percentage:
            fig.update_layout(
                yaxis2=dict(
                    title="Progress %",
                    overlaying="y",
                    side="right",
                    rangemode="tozero",
                    ticksuffix="%",
                )
            )

        charts[indicator] = fig

    return charts


def plotly_gender_agegroup(dataframe, sex, age, xaxis_interval=200):
    df = dataframe.copy()

    if xaxis_interval <= 0:
        raise ValueError("xaxis_interval must be greater than 0")

    df[age] = pd.to_numeric(df[age], errors="coerce")

    bins = [-1, 4, 9, 14, 24, 34, 44, 54, 64, float("inf")]

    labels = [
        "0-4",
        "5-9",
        "10-14",
        "15-24",
        "25-34",
        "35-44",
        "45-54",
        "55-64",
        "≥ 65",
    ]

    df["AgeGroup"] = pd.cut(df[age], bins=bins, labels=labels)

    df[sex] = (
        df[sex]
        .astype(str)
        .str.upper()
        .str.strip()
        .replace({"MALE": "M", "FEMALE": "F"})
    )

    tab = pd.crosstab(df["AgeGroup"], df[sex]).reindex(labels, fill_value=0)

    male = -tab.get("M", pd.Series(0, index=labels))

    female = tab.get("F", pd.Series(0, index=labels))

    male_total = abs(male).sum()
    female_total = female.sum()

    ratio = male_total / female_total if female_total > 0 else 0

    max_value = max(abs(male).max(), female.max())

    axis_max = (
        int((max_value + xaxis_interval - 1) // xaxis_interval)
        * xaxis_interval
    )

    tickvals = list(
        range(-axis_max, axis_max + xaxis_interval, xaxis_interval)
    )

    ticktext = [f"{abs(x):,}" for x in tickvals]

    fig = go.Figure()

    fig.add_bar(
        y=labels,
        x=male,
        orientation="h",
        name=f"Male ({male_total:,})",
        text=abs(male),
        textposition="outside",
        cliponaxis=False,
    )

    fig.add_bar(
        y=labels,
        x=female,
        orientation="h",
        name=f"Female ({female_total:,})",
        text=female,
        textposition="outside",
        cliponaxis=False,
    )

    fig.update_layout(
        title="Population Pyramid by Sex and Age Group",
        barmode="relative",
        template="plotly_white",
        xaxis=dict(
            title=f"Ratio - Male ({ratio:.2f} : 1) Female",
            range=[-axis_max * 1.10, axis_max * 1.10],
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
            zeroline=True,
            zerolinewidth=2,
            showgrid=True,
        ),
        yaxis=dict(
            title="Age Group", categoryorder="array", categoryarray=labels
        ),
        legend=dict(orientation="h", y=1.2, x=0.5, xanchor="center"),
        margin=dict(l=70, r=70, t=100, b=70),
    )

    return fig


def plotly_stack_bar(
    dataframe,
    columns,
    exclude_blank=True,
    orientation="v",
    title="100% Stacked Bar Chart",
):
    df = dataframe.copy()

    if isinstance(columns, str):
        columns = [columns]

    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise KeyError(f"Missing columns: {missing}")

    orientation = orientation.lower()

    if orientation not in ["v", "h"]:
        raise ValueError("orientation must be 'v' or 'h'")

    fig = go.Figure()

    for col in columns:
        data = df[col].astype("string").str.strip()

        if exclude_blank:
            data = data[data.notna() & data.ne("")]
        else:
            data = data.fillna("Blank")
            data = data.replace("", "Blank")

        if data.empty:
            continue

        counts = data.value_counts().sort_values(ascending=False)

        total = counts.sum()

        percentages = counts / total * 100

        for category in counts.index:
            count = counts[category]
            percent = percentages[category]

            label = f"{category}<br>{count:,}<br>{percent:.1f}%"

            hover = (
                f"<b>{col}</b>"
                f"<br>Category: {category}"
                f"<br>Total: {count:,}"
                f"<br>Percent: {percent:.1f}%"
                f"<br>Column Total: {total:,}"
                "<extra></extra>"
            )

            text_angle = 0 if percent >= 12 else -90

            if orientation == "v":
                fig.add_trace(
                    go.Bar(
                        x=[col],
                        y=[percent],
                        name=str(category),
                        text=[label],
                        textposition="inside",
                        insidetextanchor="middle",
                        textangle=text_angle,
                        hovertemplate=hover,
                        showlegend=False,
                    )
                )

            else:
                fig.add_trace(
                    go.Bar(
                        y=[col],
                        x=[percent],
                        orientation="h",
                        name=str(category),
                        text=[label],
                        textposition="inside",
                        insidetextanchor="middle",
                        textangle=text_angle,
                        hovertemplate=hover,
                        showlegend=False,
                    )
                )

    fig.update_layout(
        title=dict(text=title, x=0.5, xanchor="center"),
        barmode="stack",
        template="plotly_white",
        hovermode="closest",
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50),
    )

    if orientation == "v":
        fig.update_yaxes(title=None, range=[0, 100], ticksuffix="%")

        fig.update_xaxes(
            title=None, categoryorder="array", categoryarray=columns
        )

    else:
        fig.update_xaxes(title=None, range=[0, 100], ticksuffix="%")

        fig.update_yaxes(
            title=None, categoryorder="array", categoryarray=columns
        )

    return fig


def function_sankey_cascade_log(
    dataframe,
    criteria_dict,
    title="TB Cascade of Care",
    width=1000,
    height=500,
    log_base=10,
):
    df = dataframe.copy()
    if "Reasonforexamination" in df.columns and "Referralfor" in df.columns:
        mask = (df["Reasonforexamination"] == "Diagnosis") & (
            df["Referralfor"].isna() | (df["Referralfor"].astype(str).str.strip() == "")
        )
        df.loc[mask, "Referralfor"] = "Presumptive"

    stages = list(criteria_dict.keys())

    node_map = {}

    labels = []
    node_counts = []
    node_colors = []

    colors = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#B279A2"]
    node_id = 0
    for i, stage in enumerate(stages):
        valid_values = criteria_dict[stage]
        for value in valid_values:
            count = df[stage].astype(str).eq(str(value)).sum()
            node_map[(stage, value)] = node_id
            labels.append(
                f"<b>{value}</b><br>{count:,} ({count/len(df)*100:.1f}%)"
            )
            node_counts.append(count)
            node_colors.append(colors[i % len(colors)])
            node_id += 1

    source = []
    target = []
    values = []
    original = []
    percentages = []

    for i in range(len(stages) - 1):
        stage1 = stages[i]
        stage2 = stages[i + 1]
        temp = (
            df[
                df[stage1].isin(criteria_dict[stage1])
                & df[stage2].isin(criteria_dict[stage2])
            ]
            .groupby([stage1, stage2])
            .size()
            .reset_index(name="Count")
        )
        for _, row in temp.iterrows():
            count = row["Count"]
            source_count = df[df[stage1].eq(row[stage1])].shape[0]
            retention = count / source_count * 100 if source_count > 0 else 0
            source.append(node_map[(stage1, row[stage1])])
            target.append(node_map[(stage2, row[stage2])])
            values.append(np.log(count + 1) / np.log(log_base))
            original.append(count)
            percentages.append(retention)

    fig = go.Figure(
        go.Sankey(
            arrangement="snap",
            node=dict(
                pad=30,
                thickness=35,
                label=labels,
                color=node_colors,
                line=dict(color="black", width=1),
            ),
            link=dict(
                source=source,
                target=target,
                value=values,
                customdata=np.column_stack((original, percentages)),
                hovertemplate="<b>%{source.label}</b>"
                "<br>↓<br>"
                "<b>%{target.label}</b>"
                "<br><br>"
                "Patients: <b>%{customdata[0]:,}</b>"
                "<br>"
                "Retention: <b>%{customdata[1]:.1f}%</b>"
                "<extra></extra>",
            ),
        )
    )

    fig.update_layout(
        title=dict(text=title, x=0.5),
        width=width,
        height=height,
        template="plotly_white",
        dragmode="zoom",
        margin=dict(l=30, r=30, t=70, b=30),
    )

    return fig


def function_heatmap(
    dataframe: pd.DataFrame,
    Xaxis: str,
    Yaxis: str,
    exclude_blank: bool = True,
    colorscale: str = "Blues",
) -> go.Figure:
    df = dataframe.copy()

    for col in [Xaxis, Yaxis]:
        if (
            df[col].dtype == "object"
            or isinstance(df[col].dtype, pd.CategoricalDtype)
            or pd.api.types.is_string_dtype(df[col])
        ):
            df[col] = (
                df[col]
                .astype(str)
                .str.strip()
                .replace(r"^\s*$", np.nan, regex=True)
            )

    if exclude_blank:
        df = df.dropna(subset=[Xaxis, Yaxis], how="all")

    df[Xaxis] = df[Xaxis].fillna("Not Done")
    df[Yaxis] = df[Yaxis].fillna("Not Done")

    counts = pd.crosstab(
        df[Yaxis],
        df[Xaxis],
        dropna=False,
        margins=True,
        margins_name="Total",
    )

    row_order = [idx for idx in counts.index if str(idx) not in ["Total", "Not Done"]]
    if "Not Done" in counts.index:
        row_order.insert(0, "Not Done")
    row_order.insert(0, "Total")
    counts = counts.loc[row_order]

    col_order = [col for col in counts.columns if str(col) not in ["Total", "Not Done"]]
    if "Not Done" in counts.columns:
        col_order.append("Not Done")
    col_order.append("Total")
    counts = counts[col_order]

    grand_total = counts.loc["Total", "Total"]

    text_matrix = []
    hover_matrix = []

    z_values = np.log10(counts.values.astype(float) + 1)

    for i, row_label in enumerate(counts.index):
        text_row = []
        hover_row = []
        for j, col_label in enumerate(counts.columns):
            c_val = counts.iloc[i, j]

            is_total_row = str(row_label) == "Total"
            is_total_col = str(col_label) == "Total"

            if is_total_row or is_total_col:
                z_values[i, j] = np.nan

            col_total = counts.iloc[0, j]

            if is_total_row and is_total_col:
                cell_text = f"<b>{c_val}</b><br>(100.0%)"
                hover_text = f"<b>Grand Total</b>: {c_val}"
            elif is_total_row:
                pct = (c_val / grand_total * 100) if grand_total > 0 else 0
                cell_text = f"<b>{c_val}</b><br>({pct:.1f}%)"
                hover_text = (
                    f"<b>Column Total ({col_label})</b>: {c_val} ({pct:.1f}% of total)"
                )
            elif is_total_col:
                pct = (c_val / grand_total * 100) if grand_total > 0 else 0
                cell_text = f"<b>{c_val}</b><br>({pct:.1f}%)"
                hover_text = (
                    f"<b>Row Total ({row_label})</b>: {c_val} ({pct:.1f}% of total)"
                )
            else:
                pct = (c_val / col_total * 100) if col_total > 0 else 0
                cell_text = f"<b>{c_val}</b><br>({pct:.1f}%)"
                hover_text = (
                    f"<b>{Yaxis}</b>: {row_label}<br>"
                    f"<b>{Xaxis}</b>: {col_label}<br>"
                    f"<b>Count</b>: {c_val}<br>"
                    f"<b>Col %</b>: {pct:.1f}%"
                )

            text_row.append(cell_text)
            hover_row.append(hover_text)

        text_matrix.append(text_row)
        hover_matrix.append(hover_row)

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=[str(col) for col in counts.columns],
            y=[str(idx) for idx in counts.index],
            text=text_matrix,
            texttemplate="%{text}",
            hoverinfo="text",
            hovertext=hover_matrix,
            colorscale=colorscale,
            showscale=False,
        )
    )

    fig.update_layout(
        title=f"Heatmap with Totals: {Yaxis} vs {Xaxis}",
        xaxis_title=f"<b>{Xaxis}</b>",
        yaxis_title=f"<b>{Yaxis}</b>",
        template="plotly_white",
        xaxis=dict(side="bottom"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def plotly_table_count_percent(
    df: pd.DataFrame,
    column_list: list,
    optional_exclude_blank: bool = True,
    optional_include_total: bool = True,
):
    table_rows = []

    for col in column_list:
        data = df[col].copy()

        if optional_exclude_blank:
            data = data.dropna()
            if data.dtype == "object" or isinstance(
                data.dtype, pd.CategoricalDtype
            ):
                data = data[
                    ~data.astype(str)
                    .str.strip()
                    .isin(["", "None", "nan", "NaN"])
                ]

        counts = data.value_counts(dropna=not optional_exclude_blank).reset_index()
        counts.columns = ["Category", "Count"]
        total_count = counts["Count"].sum()
        counts["Percent"] = (
            (counts["Count"] / total_count * 100) if total_count > 0 else 0.0
        )

        if optional_include_total:
            table_rows.append(
                {
                    "Column Name": col,
                    "Category": "Total",
                    "Count": total_count,
                    "Percent": 100.0 if total_count > 0 else 0.0,
                    "Is_Total": True,
                }
            )

        for i, row in counts.iterrows():
            col_display = col if (i == 0 and not optional_include_total) else ""

            table_rows.append(
                {
                    "Column Name": col_display,
                    "Category": str(row["Category"]),
                    "Count": row["Count"],
                    "Percent": row["Percent"],
                    "Is_Total": False,
                }
            )

    result_df = pd.DataFrame(table_rows)

    formatted_col_name = [
        f"<b>{r['Column Name']}</b>" for _, r in result_df.iterrows()
    ]
    formatted_category = [
        f"<b>{r['Category']}</b>" if r["Is_Total"] else r["Category"]
        for _, r in result_df.iterrows()
    ]
    formatted_counts = [
        f"<b>{r['Count']:,}</b>" if r["Is_Total"] else f"{r['Count']:,}"
        for _, r in result_df.iterrows()
    ]
    formatted_percent = [
        f"<b>{r['Percent']:.1f}%</b>" if r["Is_Total"] else f"{r['Percent']:.1f}%"
        for _, r in result_df.iterrows()
    ]

    fill_colors = []
    for _, r in result_df.iterrows():
        if r["Is_Total"]:
            fill_colors.append("#E1EBF5")
        else:
            fill_colors.append("#FFFFFF")

    fig = go.Figure(
        data=[
            go.Table(
                header=dict(
                    values=[
                        "<b>Column Name</b>",
                        "<b>Category</b>",
                        "<b>Count</b>",
                        "<b>Percent</b>",
                    ],
                    fill_color="#1F77B4",
                    font=dict(color="white", size=13),
                    align=["left", "left", "right", "right"],
                ),
                cells=dict(
                    values=[
                        formatted_col_name,
                        formatted_category,
                        formatted_counts,
                        formatted_percent,
                    ],
                    fill_color=[fill_colors] * 4,
                    font=dict(color="black", size=12),
                    align=["left", "left", "right", "right"],
                    height=26,
                ),
            )
        ]
    )

    fig.update_layout(
        title="Summary Table: Count and Percent Breakdown",
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig


def plotly_funnel(
    df: pd.DataFrame,
    funnel_column_criteria: dict,
    rename_column: list,
    column_funnel: str,
):
    raw_step_names = list(funnel_column_criteria.keys())

    if len(rename_column) != len(raw_step_names):
        raise ValueError(
            f"Length of `rename_column` ({len(rename_column)}) must match "
            f"the number of stages in `funnel_column_criteria` ({len(raw_step_names)})."
        )

    segments = df[column_funnel].dropna().unique().tolist()
    num_segments = len(segments)

    if num_segments == 0:
        raise ValueError(f"No unique values found in group column: '{column_funnel}'")

    fig = make_subplots(
        rows=1,
        cols=num_segments,
        subplot_titles=[f"<b>{column_funnel}: {seg}</b>" for seg in segments],
        shared_yaxes=True,
    )

    for i, seg in enumerate(segments, start=1):
        seg_df = df[df[column_funnel] == seg]
        raw_counts = []

        for col, criteria in funnel_column_criteria.items():
            criteria_list = criteria if isinstance(criteria, list) else [criteria]
            count = seg_df[col].isin(criteria_list).sum()
            raw_counts.append(count)

        log_counts = np.log10(np.array(raw_counts) + 1).tolist()

        initial_count = (
            raw_counts[0] if len(raw_counts) > 0 and raw_counts[0] > 0 else 1
        )
        pct_initial = [(cnt / initial_count) * 100 for cnt in raw_counts]

        display_text = [
            f"{cnt:,} ({pct:.1f}%)" for cnt, pct in zip(raw_counts, pct_initial)
        ]
        hover_text = [
            f"<b>Stage:</b> {label}<br><b>Raw Count:</b> {cnt:,}<br><b>% of Initial:</b> {pct:.1f}%"
            for label, cnt, pct in zip(rename_column, raw_counts, pct_initial)
        ]

        fig.add_trace(
            go.Funnel(
                name=str(seg),
                y=rename_column,
                x=log_counts,
                text=display_text,
                textinfo="text",
                hoverinfo="text",
                hovertext=hover_text,
            ),
            row=1,
            col=i,
        )

    fig.update_layout(
        title_text=f"<b>Funnel Analysis Grouped by {column_funnel}</b>",
        showlegend=False,
        template="plotly_white",
        margin=dict(l=40, r=40, t=80, b=40),
    )

    fig.update_xaxes(showticklabels=False, title_text="")

    return fig
