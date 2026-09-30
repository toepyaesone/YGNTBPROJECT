import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Consultation Data",
    page_icon="🩺",
    layout="wide"
)

SUPABASE_URL = st.secrets.get("SUPABASE_URL", "")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "")

TABLE_NAME = "Consultation"
PRIMARY_KEY = "patientid"
DATE_COLUMN = "date"
MAX_ROWS = 1000


# ============================================================
# SUPABASE
# ============================================================

base_supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


def get_user_client():
    """Return Supabase client using current user's access token."""

    session = st.session_state.get("session")

    if not session:
        return base_supabase

    client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

    try:
        client.postgrest.auth(session.access_token)
    except Exception:
        pass

    return client


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "session": None,
    "user_role": None,
    "grid_version": 0,
    "filter_version": 0,
    "last_sync_message": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# LOGIN
# ============================================================

def login_user(email, password):

    try:
        response = base_supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        session = response.session

        if not session:
            return False, "Login failed."

        st.session_state.session = session

        # Get user role
        role_response = (
            base_supabase
            .table("user_roles")
            .select("role")
            .eq("user_id", session.user.id)
            .limit(1)
            .execute()
        )

        if role_response.data:
            st.session_state.user_role = (
                role_response.data[0].get("role") or "viewer"
            )
        else:
            st.session_state.user_role = "viewer"

        return True, "Login successful."

    except Exception as e:
        return False, str(e)


def logout_user():

    try:
        base_supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.session = None
    st.session_state.user_role = None
    st.session_state.grid_version += 1
    st.rerun()


# ============================================================
# LOGIN SCREEN
# ============================================================

if not st.session_state.session:

    st.title("🩺 Consultation Data")

    with st.form("login_form"):

        email = st.text_input("Email")

        password = st.text_input(
            "Password",
            type="password"
        )

        login = st.form_submit_button(
            "Login",
            use_container_width=True
        )

    if login:

        success, message = login_user(
            email,
            password
        )

        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    st.stop()


# ============================================================
# USER INFORMATION
# ============================================================

session = st.session_state.session
user_role = st.session_state.user_role or "viewer"

st.sidebar.success(
    f"Logged in\n\nRole: **{user_role}**"
)

if st.sidebar.button(
    "Logout",
    use_container_width=True
):
    logout_user()


can_edit = user_role in ["editor", "admin"]
can_delete = user_role == "admin"


# ============================================================
# FILTER DEFINITIONS
# ============================================================

FILTERS = {
    "Patient ID": "patientid",
    "TSP": "tsp",
    "Visit No": "visitno",
    "SR No": "srno",
    "Approach": "approach",
    "Team": "team",
    "Reporting Year": "reportingyear"
}


# ============================================================
# RESET FILTERS
# ============================================================

def reset_filters():

    # Change widget namespace.
    # This forces Streamlit to create completely new widgets.
    st.session_state.filter_version += 1

    # Remove old widget values.
    old_keys = [
        "f_patientid",
        "f_tsp",
        "f_visitno",
        "f_srno",
        "f_approach",
        "f_team",
        "f_year",
        "f_date_from",
        "f_date_to"
    ]

    for key in old_keys:
        st.session_state.pop(key, None)

    # Also refresh the data grid.
    st.session_state.grid_version += 1


filter_version = st.session_state.filter_version


# ============================================================
# UNIQUE FILTER VALUES
# ============================================================

@st.cache_data(ttl=60)
def get_unique_values(column):

    try:

        response = (
            base_supabase
            .table(TABLE_NAME)
            .select(column)
            .execute()
        )

        values = []

        for row in response.data or []:

            value = row.get(column)

            if value is not None and str(value).strip() != "":
                values.append(str(value))

        return sorted(
            list(set(values)),
            key=lambda x: x.lower()
        )

    except Exception:
        return []


# ============================================================
# FILTER UI
# ============================================================

st.subheader("🔎 Filters")

col1, col2, col3 = st.columns(3)

with col1:

    patientid_values = st.multiselect(
        "Patient ID",
        get_unique_values("patientid"),
        key=f"f_patientid_{filter_version}"
    )

    tsp_values = st.multiselect(
        "TSP",
        get_unique_values("tsp"),
        key=f"f_tsp_{filter_version}"
    )

    visitno_values = st.multiselect(
        "Visit No",
        get_unique_values("visitno"),
        key=f"f_visitno_{filter_version}"
    )


with col2:

    srno_values = st.multiselect(
        "SR No",
        get_unique_values("srno"),
        key=f"f_srno_{filter_version}"
    )

    approach_values = st.multiselect(
        "Approach",
        get_unique_values("approach"),
        key=f"f_approach_{filter_version}"
    )

    team_values = st.multiselect(
        "Team",
        get_unique_values("team"),
        key=f"f_team_{filter_version}"
    )


with col3:

    year_values = st.multiselect(
        "Reporting Year",
        get_unique_values("reportingyear"),
        key=f"f_year_{filter_version}"
    )

    date_from = st.date_input(
        "Date From",
        value=None,
        key=f"f_date_from_{filter_version}"
    )

    date_to = st.date_input(
        "Date To",
        value=None,
        key=f"f_date_to_{filter_version}"
    )


st.button(
    "🔄 Reset Filters",
    on_click=reset_filters,
    use_container_width=False
)


# ============================================================
# BUILD QUERY
# ============================================================

client = get_user_client()

query = (
    client
    .table(TABLE_NAME)
    .select("*")
)


# Multiple-value filters

selected_filters = {
    "patientid": patientid_values,
    "tsp": tsp_values,
    "visitno": visitno_values,
    "srno": srno_values,
    "approach": approach_values,
    "team": team_values,
    "reportingyear": year_values
}

for column, values in selected_filters.items():

    if values:
        query = query.in_(
            column,
            values
        )


# Date filters

if date_from:

    query = query.gte(
        DATE_COLUMN,
        date_from.isoformat()
    )


if date_to:

    query = query.lte(
        DATE_COLUMN,
        date_to.isoformat()
    )


# ============================================================
# GET DATA
# ============================================================

try:

    response = (
        query
        .order(PRIMARY_KEY, desc=True)
        .limit(MAX_ROWS)
        .execute()
    )

    data = response.data or []

except Exception as e:

    st.error(
        f"Error loading Consultation data: {e}"
    )

    st.stop()


df = pd.DataFrame(data)


if df.empty:

    st.info("No records found.")

    st.stop()


# ============================================================
# DISPLAY INFORMATION
# ============================================================

st.caption(
    f"Showing {len(df):,} records "
    f"(maximum {MAX_ROWS:,})."
)


# ============================================================
# DATA EDITOR
# ============================================================

st.subheader("📋 Consultation Data")


# Columns that should not be manually edited
disabled_columns = []

if PRIMARY_KEY in df.columns:
    disabled_columns.append(PRIMARY_KEY)

if "updated_at" in df.columns:
    disabled_columns.append("updated_at")


editor_state = st.data_editor(
    df,
    key=f"consultation_grid_{st.session_state.grid_version}",
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic" if can_edit and can_delete else "fixed",
    disabled=disabled_columns if not can_edit else disabled_columns,
    column_config={
        "updated_at": st.column_config.DatetimeColumn(
            "Updated At",
            disabled=True
        )
    }
)


# ============================================================
# PENDING CHANGES
# ============================================================

edited_rows = editor_state.get("edited_rows", {})
added_rows = editor_state.get("added_rows", {})
deleted_rows = editor_state.get("deleted_rows", [])


pending_rows = []


# -----------------------------
# Edited rows
# -----------------------------

for row_index, changes in edited_rows.items():

    if row_index >= len(df):
        continue

    original = df.iloc[row_index]

    row = {
        "Action": "UPDATE",
        "Row": row_index
    }

    row[PRIMARY_KEY] = original.get(PRIMARY_KEY)

    for column, value in changes.items():
        row[column] = value

    pending_rows.append(row)


# -----------------------------
# Added rows
# -----------------------------

for row_index, row_data in added_rows.items():

    row = {
        "Action": "INSERT",
        "Row": row_index
    }

    row.update(row_data)

    pending_rows.append(row)


# -----------------------------
# Deleted rows
# -----------------------------

for row_index in deleted_rows:

    if row_index < len(df):

        original = df.iloc[row_index]

        pending_rows.append({
            "Action": "DELETE",
            "Row": row_index,
            PRIMARY_KEY: original.get(PRIMARY_KEY)
        })


# ============================================================
# SHOW PENDING CHANGES
# ============================================================

if pending_rows:

    st.subheader(
        f"📝 Pending Changes ({len(pending_rows)})"
    )

    pending_df = pd.DataFrame(
        pending_rows
    )

    st.dataframe(
        pending_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.caption("No pending changes.")


# ============================================================
# SYNC / DISCARD
# ============================================================

col_sync, col_discard = st.columns(2)


# ============================================================
# DISCARD
# ============================================================

with col_discard:

    if st.button(
        "↩️ Discard Changes",
        disabled=not pending_rows,
        use_container_width=True
    ):

        st.session_state.grid_version += 1

        st.success(
            "Changes discarded."
        )

        st.rerun()


# ============================================================
# SYNC
# ============================================================

with col_sync:

    sync_clicked = st.button(
        "💾 Sync Changes",
        disabled=not pending_rows or not can_edit,
        type="primary",
        use_container_width=True
    )


# ============================================================
# SYNC PROCESS
# ============================================================

if sync_clicked:

    sync_client = get_user_client()

    success_count = 0
    errors = []


    # --------------------------------------------------------
    # UPDATE
    # --------------------------------------------------------

    for row_index, changes in edited_rows.items():

        try:

            if row_index >= len(df):
                continue

            original = df.iloc[row_index]

            patient_id = original.get(
                PRIMARY_KEY
            )

            if pd.isna(patient_id):
                continue


            # Only update changed columns
            update_data = {}

            for column, value in changes.items():

                if column in [
                    PRIMARY_KEY,
                    "updated_at"
                ]:
                    continue

                if pd.isna(value):
                    value = None

                update_data[column] = value


            if not update_data:
                continue


            # Optimistic concurrency
            old_updated_at = original.get(
                "updated_at"
            )


            update_query = (
                sync_client
                .table(TABLE_NAME)
                .update(update_data)
                .eq(
                    PRIMARY_KEY,
                    patient_id
                )
            )


            if (
                "updated_at" in df.columns
                and pd.notna(old_updated_at)
            ):

                update_query = update_query.eq(
                    "updated_at",
                    str(old_updated_at)
                )


            result = update_query.execute()


            if not result.data:

                errors.append(
                    f"UPDATE {patient_id}: "
                    f"record may have been changed by another user."
                )

            else:

                success_count += 1


        except Exception as e:

            errors.append(
                f"UPDATE row {row_index}: {e}"
            )


    # --------------------------------------------------------
    # INSERT
    # --------------------------------------------------------

    if can_edit:

        for row_index, row_data in added_rows.items():

            try:

                insert_data = {}

                for column, value in row_data.items():

                    if column == "updated_at":
                        continue

                    if pd.isna(value):
                        value = None

                    insert_data[column] = value


                if not insert_data:
                    continue


                result = (
                    sync_client
                    .table(TABLE_NAME)
                    .insert(insert_data)
                    .execute()
                )


                if result.data:

                    success_count += 1

                else:

                    errors.append(
                        f"INSERT row {row_index}: no data returned."
                    )


            except Exception as e:

                errors.append(
                    f"INSERT row {row_index}: {e}"
                )


    # --------------------------------------------------------
    # DELETE
    # --------------------------------------------------------

    if deleted_rows:

        if not can_delete:

            errors.append(
                "Only administrators can delete records."
            )

        else:

            for row_index in deleted_rows:

                try:

                    if row_index >= len(df):
                        continue

                    original = df.iloc[row_index]

                    patient_id = original.get(
                        PRIMARY_KEY
                    )

                    if pd.isna(patient_id):
                        continue


                    delete_query = (
                        sync_client
                        .table(TABLE_NAME)
                        .delete()
                        .eq(
                            PRIMARY_KEY,
                            patient_id
                        )
                    )


                    # Optimistic concurrency
                    old_updated_at = original.get(
                        "updated_at"
                    )

                    if (
                        "updated_at" in df.columns
                        and pd.notna(old_updated_at)
                    ):

                        delete_query = delete_query.eq(
                            "updated_at",
                            str(old_updated_at)
                        )


                    result = delete_query.execute()


                    if result.data:

                        success_count += 1

                    else:

                        errors.append(
                            f"DELETE {patient_id}: "
                            f"record may have been changed by another user."
                        )


                except Exception as e:

                    errors.append(
                        f"DELETE row {row_index}: {e}"
                    )


    # ========================================================
    # SYNC RESULT
    # ========================================================

    if success_count:

        st.success(
            f"Successfully synchronized "
            f"{success_count} change(s)."
        )


    if errors:

        st.error(
            f"{len(errors)} change(s) could not be synchronized."
        )

        for error in errors:
            st.warning(error)


    # Refresh editor
    st.session_state.grid_version += 1

    st.rerun()