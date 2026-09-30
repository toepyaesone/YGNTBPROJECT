import streamlit as st
import pandas as pd
from supabase import create_client, Client


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Consultation Register",
    page_icon="📋",
    layout="wide"
)


# ============================================================
# 2. SUPABASE CONFIGURATION
# ============================================================

SUPABASE_URL = st.secrets.get(
    "SUPABASE_URL",
    "https://kocihpxevlowqbguhstf.supabase.co"
)

SUPABASE_KEY = st.secrets.get(
    "SUPABASE_KEY",
    "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z"
)

TABLE_NAME = "Consultation"
PRIMARY_KEY = "patientid"

base_supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)


# ============================================================
# 3. SESSION STATE
# ============================================================

if "grid_version" not in st.session_state:
    st.session_state.grid_version = 0

if "session" not in st.session_state:
    st.session_state.session = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None


# ============================================================
# 4. FILTER CONFIGURATION
# ============================================================

FILTER_COLUMNS = {
    "Patient ID": "patientid",
    "Township (TSP)": "tsp",
    "Visit No": "visitno",
    "Serial No": "srno",
    "Approach": "approach",
    "Team": "team",
    "Reporting Year": "reportingyear",
}

DATE_COLUMN = "date"


# ============================================================
# 5. AUTHENTICATION CLIENT
# ============================================================

def get_user_client() -> Client:

    if (
        st.session_state.session
        and hasattr(
            st.session_state.session,
            "access_token"
        )
    ):

        client = create_client(
            SUPABASE_URL,
            SUPABASE_KEY
        )

        client.postgrest.auth(
            st.session_state.session.access_token
        )

        return client

    return base_supabase


# ============================================================
# 6. LOGIN
# ============================================================

def login_user(email, password):

    try:

        res = base_supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        st.session_state.session = res.session

        user_client = get_user_client()

        role_res = (
            user_client
            .table("user_roles")
            .select("role")
            .eq("user_id", res.user.id)
            .single()
            .execute()
        )

        if role_res.data:
            st.session_state.user_role = (
                role_res.data.get(
                    "role",
                    "viewer"
                )
            )
        else:
            st.session_state.user_role = "viewer"

        st.success(
            "Authenticated successfully!"
        )

        st.rerun()

    except Exception as e:

        st.error(
            f"Login failed: {e}"
        )


# ============================================================
# 7. LOGOUT
# ============================================================

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
# 8. RESET ALL FILTERS
# ============================================================
#
# IMPORTANT:
# Do NOT assign widget values directly after widgets have
# already been created.
#
# Deleting the widget keys and changing grid_version causes
# Streamlit to recreate them with empty values.
# ============================================================

def reset_filters():

    filter_keys = [
        "filter_patientid",
        "filter_tsp",
        "filter_visitno",
        "filter_srno",
        "filter_approach",
        "filter_team",
        "filter_reportingyear",
        "filter_date_from",
        "filter_date_to",
    ]

    for key in filter_keys:

        st.session_state.pop(
            key,
            None
        )

    st.session_state.grid_version += 1


# ============================================================
# 9. GET UNIQUE VALUES
# ============================================================

def get_unique_values(
    user_client,
    column_name
):

    try:

        response = (
            user_client
            .table(TABLE_NAME)
            .select(column_name)
            .execute()
        )

        if not response.data:
            return []

        values = []

        for row in response.data:

            value = row.get(column_name)

            if value is None:
                continue

            try:

                if pd.isna(value):
                    continue

            except Exception:
                pass

            value = str(value).strip()

            if value:
                values.append(value)

        return sorted(
            list(set(values)),
            key=lambda x: x.lower()
        )

    except Exception as e:

        st.warning(
            f"Could not load `{column_name}`: {e}"
        )

        return []


# ============================================================
# 10. LOGIN SCREEN
# ============================================================

if not st.session_state.session:

    st.title(
        "🔐 Login - Consultation Register"
    )

    with st.form("login_form"):

        email = st.text_input(
            "Email Address"
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        submit_btn = st.form_submit_button(
            "Log In",
            type="primary"
        )

        if submit_btn:

            if email and password:

                login_user(
                    email,
                    password
                )

            else:

                st.warning(
                    "Please enter both email "
                    "and password."
                )


# ============================================================
# 11. MAIN DASHBOARD
# ============================================================

else:

    user_client = get_user_client()

    user_email = (
        st.session_state.session.user.email
    )

    current_role = (
        st.session_state.user_role
        or "viewer"
    )


    # ========================================================
    # HEADER
    # ========================================================

    col_hdr, col_logout = st.columns(
        [5, 1]
    )

    with col_hdr:

        st.title(
            "📋 Consultation Register Dashboard"
        )

        st.caption(
            f"Logged in: **{user_email}** | "
            f"Role: `:blue[{current_role.upper()}]`"
        )

    with col_logout:

        if st.button(
            "🚪 Logout",
            use_container_width=True
        ):
            logout_user()

    st.divider()


    # ========================================================
    # LOAD FILTER VALUES
    # ========================================================

    filter_values = {}

    for label, column in FILTER_COLUMNS.items():

        filter_values[column] = get_unique_values(
            user_client,
            column
        )


    # ========================================================
    # FILTER PANEL
    # ========================================================

    st.subheader("🔎 Filters")


    # --------------------------------------------------------
    # ROW 1
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        patientid_filter = st.multiselect(
            "Patient ID",
            options=filter_values.get(
                "patientid",
                []
            ),
            key="filter_patientid",
            placeholder="Select Patient ID(s)"
        )

    with col2:

        tsp_filter = st.multiselect(
            "Township (TSP)",
            options=filter_values.get(
                "tsp",
                []
            ),
            key="filter_tsp",
            placeholder="Select Township(s)"
        )

    with col3:

        visitno_filter = st.multiselect(
            "Visit No",
            options=filter_values.get(
                "visitno",
                []
            ),
            key="filter_visitno",
            placeholder="Select Visit No(s)"
        )


    # --------------------------------------------------------
    # ROW 2
    # --------------------------------------------------------

    col4, col5, col6 = st.columns(3)

    with col4:

        srno_filter = st.multiselect(
            "Serial No",
            options=filter_values.get(
                "srno",
                []
            ),
            key="filter_srno",
            placeholder="Select Serial No(s)"
        )

    with col5:

        approach_filter = st.multiselect(
            "Approach",
            options=filter_values.get(
                "approach",
                []
            ),
            key="filter_approach",
            placeholder="Select Approach(es)"
        )

    with col6:

        team_filter = st.multiselect(
            "Team",
            options=filter_values.get(
                "team",
                []
            ),
            key="filter_team",
            placeholder="Select Team(s)"
        )


    # --------------------------------------------------------
    # ROW 3
    # --------------------------------------------------------

    col7, col8, col9 = st.columns(3)

    with col7:

        reportingyear_filter = st.multiselect(
            "Reporting Year",
            options=filter_values.get(
                "reportingyear",
                []
            ),
            key="filter_reportingyear",
            placeholder="Select Year(s)"
        )

    with col8:

        date_from = st.date_input(
            "📅 Date From",
            value=None,
            key="filter_date_from"
        )

    with col9:

        date_to = st.date_input(
            "📅 Date To",
            value=None,
            key="filter_date_to"
        )


    # --------------------------------------------------------
    # FILTER BUTTONS
    # --------------------------------------------------------

    col_filter_status, col_reset = st.columns(
        [5, 1]
    )

    with col_reset:

        st.button(
            "🔄 Reset Filters",
            on_click=reset_filters,
            use_container_width=True
        )


    st.divider()


    # ========================================================
    # BUILD QUERY
    # ========================================================

    try:

        query = (
            user_client
            .table(TABLE_NAME)
            .select("*")
        )


        # ----------------------------------------------------
        # MULTI-VALUE FILTERS
        # ----------------------------------------------------

        if patientid_filter:

            query = query.in_(
                "patientid",
                patientid_filter
            )


        if tsp_filter:

            query = query.in_(
                "tsp",
                tsp_filter
            )


        if visitno_filter:

            query = query.in_(
                "visitno",
                visitno_filter
            )


        if srno_filter:

            query = query.in_(
                "srno",
                srno_filter
            )


        if approach_filter:

            query = query.in_(
                "approach",
                approach_filter
            )


        if team_filter:

            query = query.in_(
                "team",
                team_filter
            )


        if reportingyear_filter:

            query = query.in_(
                "reportingyear",
                reportingyear_filter
            )


        # ----------------------------------------------------
        # DATE FILTER
        # ----------------------------------------------------

        if date_from:

            query = query.gte(
                DATE_COLUMN,
                str(date_from)
            )


        if date_to:

            query = query.lte(
                DATE_COLUMN,
                str(date_to)
            )


        # ----------------------------------------------------
        # ORDER
        # ----------------------------------------------------

        query = (
            query
            .order(
                PRIMARY_KEY,
                desc=True
            )
            .limit(1000)
        )


        response = query.execute()


        if response.data:

            df = pd.DataFrame(
                response.data
            )

        else:

            df = pd.DataFrame()


    except Exception as e:

        st.error(
            f"Error querying `{TABLE_NAME}`:\n\n{e}"
        )

        df = pd.DataFrame()


    # ========================================================
    # FILTER SUMMARY
    # ========================================================

    active_filters = []

    if patientid_filter:
        active_filters.append(
            f"Patient ID ({len(patientid_filter)})"
        )

    if tsp_filter:
        active_filters.append(
            f"TSP: {', '.join(tsp_filter)}"
        )

    if visitno_filter:
        active_filters.append(
            f"Visit No: {', '.join(visitno_filter)}"
        )

    if srno_filter:
        active_filters.append(
            f"SR No ({len(srno_filter)})"
        )

    if approach_filter:
        active_filters.append(
            f"Approach: {', '.join(approach_filter)}"
        )

    if team_filter:
        active_filters.append(
            f"Team: {', '.join(team_filter)}"
        )

    if reportingyear_filter:
        active_filters.append(
            f"Year: {', '.join(reportingyear_filter)}"
        )

    if date_from:
        active_filters.append(
            f"From: {date_from}"
        )

    if date_to:
        active_filters.append(
            f"To: {date_to}"
        )


    if active_filters:

        st.info(
            "🔎 **Active filters:** "
            + " | ".join(active_filters)
        )


    # ========================================================
    # ROLE PERMISSIONS
    # ========================================================

    is_read_only = (
        current_role == "viewer"
    )

    can_add_or_delete = (
        current_role == "admin"
    )


    # ========================================================
    # DISPLAY DATA
    # ========================================================

    if df.empty:

        st.warning(
            "No matching records found."
        )

    else:

        st.caption(
            f"Showing **{len(df):,}** matching record(s)."
        )


        # ====================================================
        # COLUMN CONFIG
        # ====================================================

        column_configs = {

            PRIMARY_KEY:
                st.column_config.TextColumn(
                    "Patient ID",
                    disabled=True
                ),

            "updated_at":
                st.column_config.DatetimeColumn(
                    "Last Modified",
                    disabled=True,
                    format="YYYY-MM-DD HH:mm:ss"
                )
        }


        df.columns = (
            df.columns
            .str.strip()
        )


        valid_configs = {
            col: cfg
            for col, cfg
            in column_configs.items()
            if col in df.columns
        }


        disabled_columns = [
            col
            for col in [
                PRIMARY_KEY,
                "updated_at"
            ]
            if col in df.columns
        ]


        # ====================================================
        # DATA EDITOR
        # ====================================================

        current_grid_key = (
            f"consultation_grid_"
            f"{st.session_state.grid_version}"
        )


        edited_df = st.data_editor(

            df,

            key=current_grid_key,

            disabled=(
                is_read_only
                or disabled_columns
            ),

            num_rows=(
                "dynamic"
                if can_add_or_delete
                else "fixed"
            ),

            use_container_width=True,

            hide_index=True,

            column_config=valid_configs
        )


        # ====================================================
        # GET EDITOR CHANGES
        # ====================================================

        editor_state = st.session_state.get(
            current_grid_key,
            {}
        )


        edited_rows = editor_state.get(
            "edited_rows",
            {}
        )


        added_rows = editor_state.get(
            "added_rows",
            []
        )


        deleted_row_indices = (
            editor_state.get(
                "deleted_rows",
                []
            )
        )


        total_changes = (
            len(edited_rows)
            + len(added_rows)
            + len(deleted_row_indices)
        )


        # ====================================================
        # PENDING CHANGES
        # ====================================================

        if (
            not is_read_only
            and total_changes > 0
        ):

            st.warning(
                f"⚠ **Pending changes:** "
                f"{len(edited_rows)} update(s), "
                f"{len(added_rows)} new record(s), "
                f"{len(deleted_row_indices)} deletion(s)"
            )


            # =================================================
            # SYNC / DISCARD BUTTONS
            # =================================================

            col_sync, col_discard = st.columns(
                [2, 1]
            )


            # -------------------------------------------------
            # SYNC BUTTON
            # -------------------------------------------------

            with col_sync:

                sync_clicked = st.button(
                    "💾 Sync Consultation Changes",
                    type="primary",
                    use_container_width=True
                )


            # -------------------------------------------------
            # DISCARD BUTTON
            # -------------------------------------------------

            with col_discard:

                discard_clicked = st.button(
                    "❌ Discard Local Changes",
                    use_container_width=True
                )


            # =================================================
            # PENDING CHANGE TABLE
            # =================================================

            st.markdown(
                "### 📝 Pending Changes"
            )


            pending_display = []


            # -------------------------------------------------
            # UPDATED ROWS
            # -------------------------------------------------

            for row_idx, changes in (
                edited_rows.items()
            ):

                row_record = df.iloc[
                    row_idx
                ]

                row_id = row_record[
                    PRIMARY_KEY
                ]


                for column, new_value in (
                    changes.items()
                ):

                    try:

                        old_value = row_record[
                            column
                        ]

                    except Exception:

                        old_value = None


                    # Convert timestamps
                    if pd.isna(old_value):
                        old_display = ""
                    else:
                        old_display = str(
                            old_value
                        )


                    if pd.isna(new_value):
                        new_display = ""
                    else:
                        new_display = str(
                            new_value
                        )


                    pending_display.append({

                        "Action": "UPDATE",

                        "Patient ID": str(
                            row_id
                        ),

                        "Field": column,

                        "Previous Value":
                            old_display,

                        "New Value":
                            new_display
                    })


            # -------------------------------------------------
            # NEW ROWS
            # -------------------------------------------------

            for row_number, row in enumerate(
                added_rows,
                start=1
            ):

                row_id = row.get(
                    PRIMARY_KEY,
                    ""
                )


                for column, value in (
                    row.items()
                ):

                    if column == "updated_at":
                        continue


                    if (
                        pd.isna(value)
                        or value == ""
                    ):

                        value_display = ""

                    else:

                        value_display = str(
                            value
                        )


                    pending_display.append({

                        "Action": "INSERT",

                        "Patient ID": str(
                            row_id
                        ),

                        "Field": column,

                        "Previous Value": "",

                        "New Value":
                            value_display
                    })


            # -------------------------------------------------
            # DELETED ROWS
            # -------------------------------------------------

            for row_idx in (
                deleted_row_indices
            ):

                row_record = df.iloc[
                    row_idx
                ]

                row_id = row_record[
                    PRIMARY_KEY
                ]


                pending_display.append({

                    "Action": "DELETE",

                    "Patient ID": str(
                        row_id
                    ),

                    "Field": "Entire Record",

                    "Previous Value":
                        "Existing record",

                    "New Value":
                        "DELETE"
                })


            # -------------------------------------------------
            # SHOW TABLE
            # -------------------------------------------------

            if pending_display:

                pending_df = pd.DataFrame(
                    pending_display
                )


                st.dataframe(
                    pending_df,
                    use_container_width=True,
                    hide_index=True
                )


            # =================================================
            # DISCARD
            # =================================================

            if discard_clicked:

                st.session_state.grid_version += 1

                st.rerun()


            # =================================================
            # SYNC
            # =================================================

            if sync_clicked:

                conflict_occurred = False

                success_count = 0

                error_messages = []


                # =============================================
                # UPDATE
                # =============================================

                if edited_rows:

                    for row_idx, updated_fields in (
                        edited_rows.items()
                    ):

                        row_record = df.iloc[
                            row_idx
                        ]

                        row_id = row_record[
                            PRIMARY_KEY
                        ]

                        original_updated_at = (
                            row_record.get(
                                "updated_at"
                            )
                        )


                        cleaned_payload = {}


                        for k, v in (
                            updated_fields.items()
                        ):

                            if k == "updated_at":
                                continue


                            if pd.isna(v):

                                cleaned_payload[k] = None

                            elif isinstance(
                                v,
                                pd.Timestamp
                            ):

                                cleaned_payload[k] = (
                                    v.isoformat()
                                )

                            else:

                                cleaned_payload[k] = v


                        try:

                            req = (
                                user_client
                                .table(TABLE_NAME)
                                .update(
                                    cleaned_payload
                                )
                                .eq(
                                    PRIMARY_KEY,
                                    row_id
                                )
                            )


                            # Optimistic concurrency
                            if pd.notna(
                                original_updated_at
                            ):

                                req = req.eq(
                                    "updated_at",
                                    str(
                                        original_updated_at
                                    )
                                )


                            res = req.execute()


                            if not res.data:

                                conflict_occurred = True

                                error_messages.append(
                                    f"❌ Conflict on "
                                    f"`{row_id}`."
                                )

                            else:

                                success_count += 1


                        except Exception as e:

                            error_messages.append(
                                f"Update failed for "
                                f"`{row_id}`: {e}"
                            )


                # =============================================
                # INSERT
                # =============================================

                if (
                    added_rows
                    and current_role
                    in ["editor", "admin"]
                ):

                    new_records = []


                    for row in added_rows:

                        cleaned_row = {}


                        for k, v in row.items():

                            if k == "updated_at":
                                continue


                            if (
                                pd.isna(v)
                                or v == ""
                            ):

                                cleaned_row[k] = None

                            elif isinstance(
                                v,
                                pd.Timestamp
                            ):

                                cleaned_row[k] = (
                                    v.isoformat()
                                )

                            else:

                                cleaned_row[k] = v


                        new_records.append(
                            cleaned_row
                        )


                    try:

                        (
                            user_client
                            .table(TABLE_NAME)
                            .insert(
                                new_records
                            )
                            .execute()
                        )

                        success_count += (
                            len(new_records)
                        )


                    except Exception as e:

                        error_messages.append(
                            f"Insertion failed: {e}"
                        )


                # =============================================
                # DELETE
                # =============================================

                if (
                    deleted_row_indices
                    and current_role == "admin"
                ):

                    deleted_ids = [

                        df.iloc[idx][
                            PRIMARY_KEY
                        ]

                        for idx
                        in deleted_row_indices

                        if pd.notna(
                            df.iloc[idx][
                                PRIMARY_KEY
                            ]
                        )
                    ]


                    if deleted_ids:

                        try:

                            (
                                user_client
                                .table(TABLE_NAME)
                                .delete()
                                .in_(
                                    PRIMARY_KEY,
                                    deleted_ids
                                )
                                .execute()
                            )

                            success_count += (
                                len(deleted_ids)
                            )


                        except Exception as e:

                            error_messages.append(
                                f"Deletion failed: {e}"
                            )


                # =============================================
                # SYNC RESULT
                # =============================================

                if conflict_occurred:

                    st.error(
                        "🚨 Concurrency conflict detected."
                    )

                    for err in error_messages:
                        st.write(err)


                elif error_messages:

                    st.error(
                        "Some operations failed."
                    )

                    for err in error_messages:
                        st.write(err)


                else:

                    st.success(
                        f"🎉 Successfully synced "
                        f"{success_count} operation(s)."
                    )

                    st.session_state.grid_version += 1

                    st.rerun()