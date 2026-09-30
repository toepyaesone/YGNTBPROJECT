import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==========================================
# 1. PAGE CONFIGURATION & INITIALIZATION
# ==========================================
st.set_page_config(
    page_title="Consultation Register",
    page_icon="📋",
    layout="wide"
)

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

# ==========================================
# SESSION STATE
# ==========================================
if "grid_version" not in st.session_state:
    st.session_state.grid_version = 0

if "session" not in st.session_state:
    st.session_state.session = None

if "user_role" not in st.session_state:
    st.session_state.user_role = None


# ==========================================
# 2. AUTHENTICATION
# ==========================================
def get_user_client() -> Client:
    """
    Return Supabase client using the logged-in user's
    access token so that RLS policies are respected.
    """

    if (
        st.session_state.session
        and hasattr(st.session_state.session, "access_token")
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
            st.session_state.user_role = role_res.data.get(
                "role",
                "viewer"
            )
        else:
            st.session_state.user_role = "viewer"

        st.success("Authenticated successfully!")
        st.rerun()

    except Exception as e:
        st.error(f"Login failed: {e}")


def logout_user():

    try:
        base_supabase.auth.sign_out()
    except Exception:
        pass

    st.session_state.session = None
    st.session_state.user_role = None
    st.session_state.grid_version += 1

    st.rerun()


# ==========================================
# 3. LOGIN INTERFACE
# ==========================================
if not st.session_state.session:

    st.title("🔐 Login - Consultation Register")

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
                login_user(email, password)

            else:
                st.warning(
                    "Please enter both email and password."
                )


# ==========================================
# 4. MAIN DASHBOARD
# ==========================================
else:

    user_client = get_user_client()

    user_email = st.session_state.session.user.email

    current_role = (
        st.session_state.user_role or "viewer"
    )

    # ======================================
    # HEADER
    # ======================================
    col_hdr, col_logout = st.columns([4, 1])

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


    # ======================================
    # SEARCH / FILTER BAR
    # ======================================

    f_col1, f_col2, f_col3, f_col4 = st.columns(
        [3, 1.3, 1.3, 1]
    )

    with f_col1:

        search_q = st.text_input(
            "🔍 Search",
            placeholder=(
                "Patient ID, Name, Serial No, Township..."
            ),
            key="search_input"
        )

    with f_col2:

        year_filter = st.text_input(
            "📅 Reporting Year",
            placeholder="e.g. 2025",
            key="year_input"
        )

    with f_col3:

        page_size = st.selectbox(
            "Rows per page",
            options=[10, 25, 50, 100],
            index=1,
            key="page_size"
        )

    with f_col4:

        st.write("")

        if st.button(
            "🔄 Reset Filters",
            use_container_width=True
        ):

            st.session_state.search_input = ""
            st.session_state.year_input = ""

            st.session_state.grid_version += 1

            st.rerun()


    # ======================================
    # BUILD SUPABASE QUERY
    # ======================================
    try:

        query = (
            user_client
            .table(TABLE_NAME)
            .select("*")
        )


        # ----------------------------------
        # REPORTING YEAR FILTER
        # ----------------------------------
        yf = year_filter.strip()

        if yf:

            # If reportingyear is a TEXT/VARCHAR column
            #
            # This supports:
            # 2025 -> 2025
            # 202 -> 2020, 2021, 2022...
            #
            query = query.ilike(
                "reportingyear",
                f"%{yf}%"
            )


        # ----------------------------------
        # GENERAL SEARCH
        # ----------------------------------
        sq = search_q.strip()

        if sq:

            # IMPORTANT:
            #
            # These are actual database columns.
            # Change/add column names here if your
            # Consultation table uses different names.
            #
            search_conditions = [
                f"patientid.ilike.%{sq}%",
                f"name.ilike.%{sq}%",
                f"srno.ilike.%{sq}%",
                f"tsp.ilike.%{sq}%"
            ]

            query = query.or_(
                ",".join(search_conditions)
            )


        # ----------------------------------
        # ORDER + LIMIT
        # ----------------------------------
        query = (
            query
            .order(
                PRIMARY_KEY,
                desc=True
            )
            .limit(page_size)
        )


        # ----------------------------------
        # EXECUTE
        # ----------------------------------
        response = query.execute()

        if response.data:

            df = pd.DataFrame(
                response.data
            )

        else:

            df = pd.DataFrame()


    except Exception as e:

        st.error(
            f"Error querying `{TABLE_NAME}` table:\n\n{e}"
        )

        df = pd.DataFrame()


    # ======================================
    # ROLE PERMISSIONS
    # ======================================
    is_read_only = (
        current_role == "viewer"
    )

    can_add_or_delete = (
        current_role == "admin"
    )


    # ======================================
    # DISPLAY DATA
    # ======================================
    if df.empty:

        st.info(
            "No matching records found."
        )

    else:

        st.caption(
            f"Showing **{len(df):,}** record(s). "
            "Double-click a cell to edit."
        )

        # ----------------------------------
        # COLUMN CONFIGURATION
        # ----------------------------------
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


        # ----------------------------------
        # CLEAN COLUMN NAMES
        # ----------------------------------
        df.columns = df.columns.str.strip()

        valid_configs = {
            col: cfg
            for col, cfg in column_configs.items()
            if col in df.columns
        }


        # ----------------------------------
        # DISABLED COLUMNS
        # ----------------------------------
        disabled_columns = [
            col
            for col in [
                PRIMARY_KEY,
                "updated_at"
            ]
            if col in df.columns
        ]


        # ----------------------------------
        # DATA EDITOR
        # ----------------------------------
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


        # ==================================
        # EDITOR STATE
        # ==================================
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

        deleted_row_indices = editor_state.get(
            "deleted_rows",
            []
        )


        total_changes = (
            len(edited_rows)
            + len(added_rows)
            + len(deleted_row_indices)
        )


        # ==================================
        # SYNC / DISCARD
        # ==================================
        if (
            not is_read_only
            and total_changes > 0
        ):

            st.warning(
                f"⚠ Pending changes: "
                f"**{len(edited_rows)}** update(s), "
                f"**{len(added_rows)}** creation(s), "
                f"**{len(deleted_row_indices)}** deletion(s)."
            )

            col_sync, col_discard = st.columns(
                [2, 1]
            )


            # ==================================
            # SYNC
            # ==================================
            with col_sync:

                if st.button(
                    "💾 Sync Consultation Changes",
                    type="primary",
                    use_container_width=True
                ):

                    conflict_occurred = False

                    success_count = 0

                    error_messages = []


                    # ==========================
                    # UPDATE RECORDS
                    # ==========================
                    if edited_rows:

                        for row_idx, updated_fields in edited_rows.items():

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


                            for k, v in updated_fields.items():

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


                                # Optimistic
                                # concurrency check
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
                                        f"Record `{row_id}`: "
                                        f"modified by another user."
                                    )

                                else:

                                    success_count += 1


                            except Exception as e:

                                error_messages.append(
                                    f"Failed updating "
                                    f"`{row_id}`: {e}"
                                )


                    # ==========================
                    # INSERT RECORDS
                    # ==========================
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
                                .insert(new_records)
                                .execute()
                            )

                            success_count += (
                                len(new_records)
                            )

                        except Exception as e:

                            error_messages.append(
                                f"Insertion failed: {e}"
                            )


                    # ==========================
                    # DELETE RECORDS
                    # ==========================
                    if (
                        deleted_row_indices
                        and current_role == "admin"
                    ):

                        deleted_ids = [

                            df.iloc[idx][PRIMARY_KEY]

                            for idx
                            in deleted_row_indices

                            if pd.notna(
                                df.iloc[idx][PRIMARY_KEY]
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


                    # ==========================
                    # RESULTS
                    # ==========================
                    if conflict_occurred:

                        st.error(
                            "🚨 Concurrency Conflict Detected!"
                        )

                        for err in error_messages:
                            st.markdown(err)

                        st.info(
                            "Please refresh the data "
                            "before making further changes."
                        )


                    elif error_messages:

                        st.error(
                            "Errors encountered during sync:"
                        )

                        for err in error_messages:
                            st.write(f"- {err}")


                    else:

                        st.success(
                            f"🎉 Successfully synced "
                            f"{success_count} operation(s)!"
                        )

                        st.session_state.grid_version += 1

                        st.rerun()


            # ==================================
            # DISCARD
            # ==================================
            with col_discard:

                if st.button(
                    "❌ Discard Local Changes",
                    use_container_width=True
                ):

                    st.session_state.grid_version += 1

                    st.rerun()