import streamlit as st
import pandas as pd
from datetime import timedelta
from supabase import create_client, Client


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Consultation Data",
    page_icon="🩺",
    layout="wide"
)


# ============================================================
# CONFIG
# ============================================================

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

    client = create_client(
        SUPABASE_URL,
        SUPABASE_KEY
    )

    client.postgrest.auth(
        session.access_token
    )

    return client


# ============================================================
# SESSION STATE
# ============================================================

if "session" not in st.session_state:
    st.session_state.session = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None

if "grid_version" not in st.session_state:
    st.session_state.grid_version = 0

if "filter_version" not in st.session_state:
    st.session_state.filter_version = 0


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

        role_result = (
            base_supabase
            .table("user_roles")
            .select("role")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if role_result.data:

            st.session_state.user_role = (
                role_result.data[0].get("role")
                or "viewer"
            )

        else:

            st.session_state.user_role = "viewer"

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
# USER ROLE
# ============================================================

user_role = (
    st.session_state.user_role
    or "viewer"
)

can_edit = user_role in [
    "editor",
    "admin"
]

can_add = user_role == "admin"

can_delete = user_role == "admin"


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🩺 Consultation")

st.sidebar.write(
    f"**Role:** {user_role}"
)

if st.sidebar.button(
    "Logout",
    use_container_width=True
):

    logout_user()


# ============================================================
# RESET FILTERS
# ============================================================

def reset_filters():

    # Create a completely new set of filter widgets
    st.session_state.filter_version += 1

    # Also recreate the data editor
    st.session_state.grid_version += 1


# ============================================================
# UNIQUE FILTER VALUES
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

        values = []

        for row in result.data or []:

            value = row.get(column)

            if value is not None:

                value = str(value).strip()

                if value:
                    values.append(value)

        return sorted(
            set(values),
            key=lambda x: x.lower()
        )

    except Exception:

        return []


# ============================================================
# FILTER SECTION
# ============================================================

st.subheader("🔎 Filters")

filter_version = (
    st.session_state.filter_version
)

col1, col2, col3 = st.columns(3)


# ------------------------------------------------------------
# COLUMN 1
# ------------------------------------------------------------

with col1:

    patientid_filter = st.multiselect(
        "Patient ID",
        get_unique_values("patientid"),
        key=f"patientid_filter_{filter_version}"
    )

    tsp_filter = st.multiselect(
        "TSP",
        get_unique_values("tsp"),
        key=f"tsp_filter_{filter_version}"
    )

    visitno_filter = st.multiselect(
        "Visit No",
        get_unique_values("visitno"),
        key=f"visitno_filter_{filter_version}"
    )


# ------------------------------------------------------------
# COLUMN 2
# ------------------------------------------------------------

with col2:

    srno_filter = st.multiselect(
        "SR No",
        get_unique_values("srno"),
        key=f"srno_filter_{filter_version}"
    )

    approach_filter = st.multiselect(
        "Approach",
        get_unique_values("approach"),
        key=f"approach_filter_{filter_version}"
    )

    team_filter = st.multiselect(
        "Team",
        get_unique_values("team"),
        key=f"team_filter_{filter_version}"
    )


# ------------------------------------------------------------
# COLUMN 3
# ------------------------------------------------------------

with col3:

    year_filter = st.multiselect(
        "Reporting Year",
        get_unique_values("reportingyear"),
        key=f"year_filter_{filter_version}"
    )

    date_from = st.date_input(
        "Date From",
        value=None,
        key=f"date_from_{filter_version}"
    )

    date_to = st.date_input(
        "Date To",
        value=None,
        key=f"date_to_{filter_version}"
    )


st.button(
    "🔄 Reset Filters",
    on_click=reset_filters
)


# ============================================================
# BUILD SUPABASE QUERY
# ============================================================

client = get_user_client()

query = (
    client
    .table(TABLE_NAME)
    .select("*")
)


# ------------------------------------------------------------
# MULTI-VALUE FILTERS
# ------------------------------------------------------------

selected_filters = {
    "patientid": patientid_filter,
    "tsp": tsp_filter,
    "visitno": visitno_filter,
    "srno": srno_filter,
    "approach": approach_filter,
    "team": team_filter,
    "reportingyear": year_filter
}


for column, values in selected_filters.items():

    if values:

        query = query.in_(
            column,
            values
        )


# ============================================================
# DATE FILTER
# ============================================================

if date_from:

    query = query.gte(
        DATE_COLUMN,
        date_from.isoformat()
    )


if date_to:

    # Include the entire selected To date.
    # This also works when the database column is timestamp.
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
        .order(
            PRIMARY_KEY,
            desc=True
        )
        .limit(MAX_ROWS)
        .execute()
    )

    data = result.data or []

except Exception as e:

    st.error(
        f"Error loading Consultation data: {e}"
    )

    st.stop()


df = pd.DataFrame(data)


# ============================================================
# NO DATA
# ============================================================

if df.empty:

    st.info(
        "No records found for the selected filters."
    )

    st.stop()


# ============================================================
# DATA INFORMATION
# ============================================================

st.caption(
    f"Showing {len(df):,} record(s) "
    f"of maximum {MAX_ROWS:,}."
)


# ============================================================
# DATA EDITOR
# ============================================================

st.subheader("📋 Consultation Data")

editor_key = (
    f"consultation_grid_"
    f"{st.session_state.grid_version}"
)


# ------------------------------------------------------------
# DISABLED COLUMNS
# ------------------------------------------------------------

disabled_columns = []

if PRIMARY_KEY in df.columns:

    disabled_columns.append(
        PRIMARY_KEY
    )

if "updated_at" in df.columns:

    disabled_columns.append(
        "updated_at"
    )


# ------------------------------------------------------------
# DATA EDITOR
# ------------------------------------------------------------

edited_df = st.data_editor(

    df,

    key=editor_key,

    use_container_width=True,

    hide_index=True,

    # Only ADMIN can add/delete rows.
    # Editor can edit existing rows only.
    num_rows=(
        "dynamic"
        if can_add
        else "fixed"
    ),

    disabled=disabled_columns
)


# ============================================================
# GET DATA EDITOR STATE
# ============================================================

editor_state = st.session_state.get(
    editor_key,
    {}
)


# Streamlit:
# edited_rows  -> dict
# added_rows   -> list
# deleted_rows -> list

edited_rows = editor_state.get(
    "edited_rows",
    {}
)

added_rows = editor_state.get(
    "added_rows",
    []
)

deleted_rows = editor_state.get(
    "deleted_rows",
    []
)


# ============================================================
# SAFETY NORMALIZATION
# ============================================================

if not isinstance(
    edited_rows,
    dict
):

    edited_rows = {}


if not isinstance(
    added_rows,
    list
):

    # Compatibility with versions returning dict
    if isinstance(
        added_rows,
        dict
    ):

        added_rows = list(
            added_rows.values()
        )

    else:

        added_rows = []


if not isinstance(
    deleted_rows,
    list
):

    deleted_rows = list(
        deleted_rows
    )


# ============================================================
# PENDING CHANGES
# ============================================================

pending_rows = []


# ------------------------------------------------------------
# UPDATED ROWS
# ------------------------------------------------------------

for row_index, changes in edited_rows.items():

    try:

        row_index = int(row_index)

    except Exception:

        continue


    if row_index >= len(df):
        continue


    original = df.iloc[row_index]

    row = {
        "Action": "UPDATE",
        "Row": row_index,
        PRIMARY_KEY: original.get(
            PRIMARY_KEY
        )
    }


    for column, value in changes.items():

        row[column] = value


    pending_rows.append(row)


# ------------------------------------------------------------
# NEW ROWS
# ------------------------------------------------------------

for row_index, row_data in enumerate(
    added_rows
):

    row = {
        "Action": "INSERT",
        "Row": row_index
    }

    if isinstance(
        row_data,
        dict
    ):

        row.update(row_data)

    pending_rows.append(row)


# ------------------------------------------------------------
# DELETED ROWS
# ------------------------------------------------------------

for row_index in deleted_rows:

    try:

        row_index = int(row_index)

    except Exception:

        continue


    if row_index >= len(df):
        continue


    original = df.iloc[row_index]

    pending_rows.append({

        "Action": "DELETE",

        "Row": row_index,

        PRIMARY_KEY: original.get(
            PRIMARY_KEY
        )

    })


# ============================================================
# PENDING CHANGES DISPLAY
# ============================================================

if pending_rows:

    st.subheader(
        f"📝 Pending Changes "
        f"({len(pending_rows)})"
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

    st.caption(
        "No pending changes."
    )


# ============================================================
# BUTTONS
# ============================================================

col_sync, col_discard = st.columns(2)


with col_sync:

    sync_clicked = st.button(

        "💾 Sync Changes",

        type="primary",

        disabled=(
            not pending_rows
            or not can_edit
        ),

        use_container_width=True

    )


with col_discard:

    discard_clicked = st.button(

        "↩️ Discard Changes",

        disabled=not pending_rows,

        use_container_width=True

    )


# ============================================================
# DISCARD CHANGES
# ============================================================

if discard_clicked:

    # Recreate the data editor.
    # This removes all unsaved changes.
    st.session_state.grid_version += 1

    st.rerun()


# ============================================================
# SYNC CHANGES
# ============================================================

if sync_clicked:

    sync_client = get_user_client()

    success_count = 0
    errors = []


    # ========================================================
    # UPDATE EXISTING RECORDS
    # ========================================================

    for row_index, changes in edited_rows.items():

        try:

            row_index = int(row_index)

            if row_index >= len(df):
                continue


            original = df.iloc[row_index]

            patient_id = original.get(
                PRIMARY_KEY
            )


            if pd.isna(patient_id):

                errors.append(
                    f"UPDATE row {row_index}: "
                    f"missing {PRIMARY_KEY}"
                )

                continue


            # -----------------------------------------------
            # Build UPDATE data
            # -----------------------------------------------

            update_data = {}


            for column, value in changes.items():

                # Never change primary key
                if column == PRIMARY_KEY:
                    continue

                # Database should manage updated_at
                if column == "updated_at":
                    continue


                if pd.isna(value):

                    value = None


                update_data[column] = value


            if not update_data:
                continue


            # -----------------------------------------------
            # UPDATE
            # -----------------------------------------------

            result = (
                sync_client
                .table(TABLE_NAME)
                .update(update_data)
                .eq(
                    PRIMARY_KEY,
                    patient_id
                )
                .execute()
            )


            if result.data:

                success_count += 1

            else:

                errors.append(
                    f"UPDATE failed: "
                    f"{patient_id}"
                )


        except Exception as e:

            errors.append(
                f"UPDATE row {row_index}: {e}"
            )


    # ========================================================
    # INSERT NEW RECORDS
    # ========================================================

    if added_rows:

        if not can_add:

            errors.append(
                "INSERT failed: "
                "Only admin users can add records."
            )

        else:

            for row_index, row_data in enumerate(
                added_rows
            ):

                try:

                    if not isinstance(
                        row_data,
                        dict
                    ):
                        continue


                    insert_data = {}


                    for column, value in row_data.items():

                        # Skip auto-generated fields
                        if column == "updated_at":
                            continue


                        if pd.isna(value):

                            value = None


                        insert_data[column] = value


                    # ---------------------------------------
                    # Check empty row
                    # ---------------------------------------

                    has_data = any(

                        value not in [
                            None,
                            ""
                        ]

                        for value in insert_data.values()

                    )


                    if not has_data:
                        continue


                    # ---------------------------------------
                    # INSERT
                    # ---------------------------------------

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
                            f"INSERT failed: "
                            f"row {row_index}"
                        )


                except Exception as e:

                    errors.append(
                        f"INSERT row {row_index}: {e}"
                    )


    # ========================================================
    # DELETE
    # ========================================================

    if deleted_rows:

        if not can_delete:

            errors.append(
                "DELETE failed: "
                "Only admin users can delete records."
            )

        else:

            for row_index in deleted_rows:

                try:

                    row_index = int(row_index)

                    if row_index >= len(df):
                        continue


                    original = df.iloc[row_index]

                    patient_id = original.get(
                        PRIMARY_KEY
                    )


                    if pd.isna(patient_id):

                        errors.append(
                            f"DELETE row {row_index}: "
                            f"missing {PRIMARY_KEY}"
                        )

                        continue


                    # ---------------------------------------
                    # DELETE
                    # ---------------------------------------

                    result = (
                        sync_client
                        .table(TABLE_NAME)
                        .delete()
                        .eq(
                            PRIMARY_KEY,
                            patient_id
                        )
                        .execute()
                    )


                    if result.data:

                        success_count += 1

                    else:

                        errors.append(
                            f"DELETE failed: "
                            f"{patient_id}"
                        )


                except Exception as e:

                    errors.append(
                        f"DELETE row {row_index}: {e}"
                    )


    # ========================================================
    # SHOW SYNC RESULT
    # ========================================================

    if success_count > 0:

        st.success(
            f"✅ {success_count} change(s) "
            f"synchronized successfully."
        )


    if errors:

        st.error(
            f"❌ {len(errors)} change(s) failed."
        )

        for error in errors:

            st.warning(error)


    # ========================================================
    # REFRESH
    # ========================================================

    st.session_state.grid_version += 1

    st.rerun()