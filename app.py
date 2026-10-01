import streamlit as st
import pandas as pd
from datetime import timedelta
from supabase import create_client, Client


# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="Consultation Data",
    page_icon="🩺",
    layout="wide"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

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
    session = st.session_state.get("session")

    if not session:
        return base_supabase

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client.postgrest.auth(session.access_token)

    return client


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "session": None,
    "user_role": None,
    "grid_version": 0,
    "filter_version": 0,
    "filter_signature": None,
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

        if not response.session:
            return False, "Login failed."

        st.session_state.session = response.session

        user_id = response.session.user.id

        result = (
            base_supabase
            .table("user_roles")
            .select("role")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        st.session_state.user_role = (
            result.data[0].get("role", "viewer")
            if result.data
            else "viewer"
        )

        return True, "Login successful."

    except Exception as e:
        return False, str(e)


# ============================================================
# LOGOUT
# ============================================================

def logout_user():

    try:
        base_supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.session = None
    st.session_state.user_role = None
    st.session_state.grid_version += 1
    st.session_state.filter_version += 1
    st.session_state.filter_signature = None

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

        login_clicked = st.form_submit_button(
            "Login",
            use_container_width=True
        )

    if login_clicked:

        success, message = login_user(email, password)

        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    st.stop()


# ============================================================
# USER ROLE
# ============================================================

user_role = st.session_state.user_role or "viewer"

can_edit = user_role in ("editor", "admin")
can_add = user_role == "admin"
can_delete = user_role == "admin"


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🩺 Consultation")
st.sidebar.write(f"**Role:** {user_role}")

if st.sidebar.button("Logout", use_container_width=True):
    logout_user()


# ============================================================
# FILTER VALUES
# ============================================================

@st.cache_data(ttl=60)
def get_unique_values(column):

    try:
        result = (
            base_supabase
            .table(TABLE_NAME)
            .select(column)
            .execute()
        )

        values = {
            str(row[column]).strip()
            for row in (result.data or [])
            if row.get(column) is not None
            and str(row[column]).strip()
        }

        return sorted(values, key=str.lower)

    except Exception:
        return []


# ============================================================
# FILTERS
# ============================================================

st.subheader("🔎 Filters")

fv = st.session_state.filter_version

col1, col2, col3 = st.columns(3)

with col1:

    patientid_filter = st.multiselect(
        "Patient ID",
        get_unique_values("patientid"),
        key=f"patientid_{fv}"
    )

    tsp_filter = st.multiselect(
        "TSP",
        get_unique_values("tsp"),
        key=f"tsp_{fv}"
    )

    visitno_filter = st.multiselect(
        "Visit No",
        get_unique_values("visitno"),
        key=f"visitno_{fv}"
    )


with col2:

    srno_filter = st.multiselect(
        "SR No",
        get_unique_values("srno"),
        key=f"srno_{fv}"
    )

    approach_filter = st.multiselect(
        "Approach",
        get_unique_values("approach"),
        key=f"approach_{fv}"
    )

    team_filter = st.multiselect(
        "Team",
        get_unique_values("team"),
        key=f"team_{fv}")


with col3:

    year_filter = st.multiselect(
        "Reporting Year",
        get_unique_values("reportingyear"),
        key=f"year_{fv}"
    )

    date_from = st.date_input(
        "Date From",
        value=None,
        key=f"date_from_{fv}"
    )

    date_to = st.date_input(
        "Date To",
        value=None,
        key=f"date_to_{fv}"
    )


# ============================================================
# DETECT FILTER CHANGES
# ============================================================

filter_signature = (
    tuple(patientid_filter),
    tuple(tsp_filter),
    tuple(visitno_filter),
    tuple(srno_filter),
    tuple(approach_filter),
    tuple(team_filter),
    tuple(year_filter),
    date_from,
    date_to,
)

previous_signature = st.session_state.filter_signature

if previous_signature is None:

    st.session_state.filter_signature = filter_signature

elif previous_signature != filter_signature:

    # Important:
    # Create a completely new data editor.
    # This clears ALL unsaved pending changes.
    st.session_state.filter_signature = filter_signature
    st.session_state.grid_version += 1

    st.rerun()


# ============================================================
# RESET FILTERS
# ============================================================

def reset_filters():

    st.session_state.filter_version += 1
    st.session_state.grid_version += 1
    st.session_state.filter_signature = None


st.button(
    "🔄 Reset Filters",
    on_click=reset_filters
)


# ============================================================
# QUERY
# ============================================================

client = get_user_client()

query = (
    client
    .table(TABLE_NAME)
    .select("*")
)

filters = {
    "patientid": patientid_filter,
    "tsp": tsp_filter,
    "visitno": visitno_filter,
    "srno": srno_filter,
    "approach": approach_filter,
    "team": team_filter,
    "reportingyear": year_filter,
}

for column, values in filters.items():

    if values:
        query = query.in_(column, values)


if date_from:
    query = query.gte(
        DATE_COLUMN,
        date_from.isoformat()
    )


if date_to:

    # Include the complete To date.
    next_day = date_to + timedelta(days=1)

    query = query.lt(
        DATE_COLUMN,
        next_day.isoformat()
    )


# ============================================================
# LOAD DATA
# ============================================================

try:

    result = (
        query
        .order(PRIMARY_KEY, desc=True)
        .limit(MAX_ROWS)
        .execute()
    )

    df = pd.DataFrame(result.data or [])

except Exception as e:

    st.error(f"Error loading Consultation data: {e}")
    st.stop()


if df.empty:

    st.info("No records found for the selected filters.")
    st.stop()


st.caption(
    f"Showing {len(df):,} record(s) "
    f"of maximum {MAX_ROWS:,}."
)


# ============================================================
# DATA EDITOR
# ============================================================

st.subheader("📋 Consultation Data")

editor_key = f"consultation_grid_{st.session_state.grid_version}"

disabled_columns = [
    column
    for column in (PRIMARY_KEY, "updated_at")
    if column in df.columns
]

st.data_editor(
    df,
    key=editor_key,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic" if can_add else "fixed",
    disabled=disabled_columns
)


# ============================================================
# EDITOR STATE
# ============================================================

editor_state = st.session_state.get(editor_key, {})

edited_rows = editor_state.get("edited_rows", {})
added_rows = editor_state.get("added_rows", [])
deleted_rows = editor_state.get("deleted_rows", [])

if not isinstance(edited_rows, dict):
    edited_rows = {}

if not isinstance(added_rows, list):
    added_rows = (
        list(added_rows.values())
        if isinstance(added_rows, dict)
        else []
    )

if not isinstance(deleted_rows, list):
    deleted_rows = list(deleted_rows)


# ============================================================
# PENDING CHANGES
# ============================================================

pending_rows = []


# UPDATE
for row_index, changes in edited_rows.items():

    try:
        row_index = int(row_index)

        if row_index >= len(df):
            continue

        row = {
            "Action": "UPDATE",
            PRIMARY_KEY: df.iloc[row_index][PRIMARY_KEY]
        }

        row.update(changes)
        pending_rows.append(row)

    except Exception:
        continue


# INSERT
for row_data in added_rows:

    if isinstance(row_data, dict):

        row = {"Action": "INSERT"}
        row.update(row_data)

        pending_rows.append(row)


# DELETE
for row_index in deleted_rows:

    try:
        row_index = int(row_index)

        if row_index >= len(df):
            continue

        pending_rows.append({
            "Action": "DELETE",
            PRIMARY_KEY: df.iloc[row_index][PRIMARY_KEY]
        })

    except Exception:
        continue


# ============================================================
# PENDING CHANGES DISPLAY
# ============================================================

if pending_rows:

    st.subheader(
        f"📝 Pending Changes ({len(pending_rows)})"
    )

    st.dataframe(
        pd.DataFrame(pending_rows),
        use_container_width=True,
        hide_index=True
    )

else:

    st.caption("No pending changes.")


# ============================================================
# BUTTONS
# ============================================================

col_sync, col_discard = st.columns(2)

with col_sync:

    sync_clicked = st.button(
        "💾 Sync Changes",
        type="primary",
        disabled=not pending_rows or not can_edit,
        use_container_width=True
    )


with col_discard:

    discard_clicked = st.button(
        "↩️ Discard Changes",
        disabled=not pending_rows,
        use_container_width=True
    )


# ============================================================
# DISCARD
# ============================================================

if discard_clicked:

    st.session_state.grid_version += 1
    st.rerun()


# ============================================================
# SYNC
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

            row_index = int(row_index)

            if row_index >= len(df):
                continue

            patient_id = df.iloc[row_index][PRIMARY_KEY]

            if pd.isna(patient_id):
                errors.append(
                    f"UPDATE row {row_index}: missing {PRIMARY_KEY}"
                )
                continue

            update_data = {}

            for column, value in changes.items():

                if column in (PRIMARY_KEY, "updated_at"):
                    continue

                update_data[column] = (
                    None if pd.isna(value) else value
                )

            if not update_data:
                continue

            result = (
                sync_client
                .table(TABLE_NAME)
                .update(update_data)
                .eq(PRIMARY_KEY, patient_id)
                .execute()
            )

            if result.data:
                success_count += 1
            else:
                errors.append(
                    f"UPDATE failed: {patient_id}"
                )

        except Exception as e:

            errors.append(
                f"UPDATE row {row_index}: {e}"
            )


    # --------------------------------------------------------
    # INSERT
    # --------------------------------------------------------

    if added_rows:

        if not can_add:

            errors.append(
                "INSERT failed: Only admin users can add records."
            )

        else:

            for row_index, row_data in enumerate(added_rows):

                try:

                    if not isinstance(row_data, dict):
                        continue

                    insert_data = {}

                    for column, value in row_data.items():

                        if column == "updated_at":
                            continue

                        insert_data[column] = (
                            None if pd.isna(value) else value
                        )

                    # Ignore completely empty rows.
                    if not any(
                        value not in (None, "")
                        for value in insert_data.values()
                    ):
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
                            f"INSERT failed: row {row_index}"
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
                "DELETE failed: Only admin users can delete records."
            )

        else:

            for row_index in deleted_rows:

                try:

                    row_index = int(row_index)

                    if row_index >= len(df):
                        continue

                    patient_id = df.iloc[row_index][PRIMARY_KEY]

                    if pd.isna(patient_id):
                        errors.append(
                            f"DELETE row {row_index}: "
                            f"missing {PRIMARY_KEY}"
                        )
                        continue

                    result = (
                        sync_client
                        .table(TABLE_NAME)
                        .delete()
                        .eq(PRIMARY_KEY, patient_id)
                        .execute()
                    )

                    if result.data:
                        success_count += 1
                    else:
                        errors.append(
                            f"DELETE failed: {patient_id}"
                        )

                except Exception as e:

                    errors.append(
                        f"DELETE row {row_index}: {e}"
                    )


    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    if success_count:

        st.success(
            f"✅ {success_count} change(s) synchronized successfully."
        )

    if errors:

        st.error(
            f"❌ {len(errors)} change(s) failed."
        )

        for error in errors:
            st.warning(error)


    # Refresh editor after Sync.
    st.session_state.grid_version += 1

    # Refresh cached filter values after INSERT/DELETE.
    get_unique_values.clear()

    st.rerun()