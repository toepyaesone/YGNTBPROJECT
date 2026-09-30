import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==========================================
# 1. PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Consultation Register",
    page_icon="📋",
    layout="wide"
)

# Use st.secrets safely with fallback to empty strings
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://kocihpxevlowqbguhstf.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z")

TABLE_NAME = "Consultation"
PRIMARY_KEY = "patientid"

base_supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize editor version key for reset/discard functionality
if "grid_version" not in st.session_state:
    st.session_state.grid_version = 0


# ==========================================
# 2. SESSION & AUTHENTICATION
# ==========================================
if "session" not in st.session_state:
    st.session_state.session = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

def get_user_client() -> Client:
    """Sets the access token on the client for RLS requests."""
    if st.session_state.session:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.postgrest.auth(st.session_state.session.access_token)
        return client
    return base_supabase


def login_user(email, password):
    try:
        res = base_supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.session = res.session
        
        user_client = get_user_client()
        role_res = user_client.table("user_roles").select("role").eq("user_id", res.user.id).single().execute()
        st.session_state.user_role = role_res.data.get("role", "viewer") if role_res.data else "viewer"
        
        st.success("Authenticated successfully!")
        st.rerun()
    except Exception as e:
        st.error(f"Login failed: {e}")


def logout_user():
    base_supabase.auth.sign_out()
    st.session_state.session = None
    st.session_state.user_role = None
    st.cache_data.clear()
    st.rerun()


# ==========================================
# 3. LOGIN INTERFACE
# ==========================================
if not st.session_state.session:
    st.title("🔐 Login - Consultation Register")
    with st.form("login_form"):
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Log In", type="primary")
        
        if submit_btn:
            if email and password:
                login_user(email, password)
            else:
                st.warning("Please enter email and password.")

else:
    # ==========================================
    # 4. MAIN CONSULTATION GRID
    # ==========================================
    user_client = get_user_client()
    user_email = st.session_state.session.user.email
    current_role = st.session_state.user_role or "viewer"

    # Header Bar
    col_hdr, col_logout = st.columns([4, 1])
    with col_hdr:
        st.title("📋 Consultation Register Dashboard")
        st.caption(f"Logged in: **{user_email}** | Role: `:blue[{current_role.upper()}]`")
    with col_logout:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()

    st.divider()

    # Filters & Pagination
    f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
    
    with f_col1:
        search_q = st.text_input("🔍 Search (Patient ID, Name, Serial No, Township)", value="")
    with f_col2:
        year_filter = st.text_input("Filter Reporting Year", value="")
    with f_col3:
        page_size = st.selectbox("Rows per page", options=[10, 25, 50, 100], index=1)

    # Query Data
    try:
        query = user_client.table(TABLE_NAME).select("*")
        
        if year_filter.strip():
            # Cast integer/bigint year columns to string search if necessary
            query = query.eq("reportingyear", year_filter.strip())
            
        if search_q.strip():
            sq = search_q.strip()
            # FIX: Explicitly cast bigint/numeric columns (patientid, srno) to text (::text)
            # so Postgres ilike works without type mismatch errors.
            query = query.or_(
                f"patientid::text.ilike.%{sq}%,name.ilike.%{sq}%,srno::text.ilike.%{sq}%,townshipname.ilike.%{sq}%"
            )
            
        response = query.order(PRIMARY_KEY, desc=True).limit(page_size).execute()
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error querying `Consultation` table: {e}")
        df = pd.DataFrame()

    is_read_only = (current_role == "viewer")
    can_add_or_delete = (current_role == "admin")

    if df.empty:
        st.info("No matching records found in `Consultation` table.")
    else:
        st.caption("Double-click any cell to edit. Scroll horizontally to view all columns.")

        # Primary column config schema
        column_configs = {
            PRIMARY_KEY: st.column_config.TextColumn("Patient ID", disabled=True),
            "updated_at": st.column_config.DatetimeColumn("Last Modified", disabled=True, format="YYYY-MM-DD HH:mm:ss"),
        }

        # Normalize column names & filter configs safely
        df.columns = df.columns.str.strip()
        valid_column_configs = {
            col: config for col, config in column_configs.items() if col in df.columns
        }

        # Dynamic session key to allow clearing local editor edits on Discard
        current_grid_key = f"consultation_grid_{st.session_state.grid_version}"

        edited_df = st.data_editor(
            df,
            key=current_grid_key,
            disabled=is_read_only or [col for col in [PRIMARY_KEY, "updated_at"] if col in df.columns],
            num_rows="dynamic" if can_add_or_delete else "fixed",
            use_container_width=True,
            hide_index=True,
            column_config=valid_column_configs
        )

        # Delta capture from editor state
        editor_state = st.session_state.get(current_grid_key, {})
        edited_rows = editor_state.get("edited_rows", {})
        added_rows = editor_state.get("added_rows", [])
        deleted_row_indices = editor_state.get("deleted_rows", [])

        total_changes = len(edited_rows) + len(added_rows) + len(deleted_row_indices)

        # Sync & Discard Action Panel
        if not is_read_only and total_changes > 0:
            st.warning(
                f"⚠ Pending changes: **{len(edited_rows)}** update(s), "
                f"**{len(added_rows)}** creation(s), **{len(deleted_row_indices)}** deletion(s)."
            )

            col_sync, col_discard = st.columns([2, 1])

            with col_sync:
                if st.button("💾 Sync Consultation Changes", type="primary", use_container_width=True):
                    conflict_occurred = False
                    success_count = 0
                    error_messages = []

                    # 1. UPDATES
                    if edited_rows:
                        for row_idx, updated_fields in edited_rows.items():
                            row_record = df.iloc[row_idx]
                            row_id = row_record[PRIMARY_KEY]
                            original_updated_at = row_record.get("updated_at")

                            cleaned_payload = {}
                            for k, v in updated_fields.items():
                                if k == "updated_at":
                                    continue
                                if pd.isna(v):
                                    cleaned_payload[k] = None
                                elif isinstance(v, pd.Timestamp):
                                    cleaned_payload[k] = v.isoformat()
                                else:
                                    cleaned_payload[k] = v

                            try:
                                req = user_client.table(TABLE_NAME).update(cleaned_payload).eq(PRIMARY_KEY, row_id)
                                
                                # Optimistic Concurrency Check
                                if pd.notna(original_updated_at):
                                    req = req.eq("updated_at", str(original_updated_at))
                                    
                                res = req.execute()

                                if len(res.data) == 0:
                                    conflict_occurred = True
                                    error_messages.append(f"❌ **Conflict on `{row_id}`**: Modified by another user.")
                                else:
                                    success_count += 1

                            except Exception as e:
                                error_messages.append(f"Failed updating `{row_id}`: {e}")

                    # 2. INSERTIONS
                    if added_rows and current_role in ["editor", "admin"]:
                        new_records = []
                        for row in added_rows:
                            cleaned_row = {}
                            for k, v in row.items():
                                if k == "updated_at":
                                    continue
                                if pd.isna(v) or v == "":
                                    cleaned_row[k] = None
                                elif isinstance(v, pd.Timestamp):
                                    cleaned_row[k] = v.isoformat()
                                else:
                                    cleaned_row[k] = v
                            new_records.append(cleaned_row)

                        try:
                            user_client.table(TABLE_NAME).insert(new_records).execute()
                            success_count += len(new_records)
                        except Exception as e:
                            error_messages.append(f"Insertion failed: {e}")

                    # 3. DELETIONS
                    if deleted_row_indices and current_role == "admin":
                        deleted_ids = [
                            df.iloc[idx][PRIMARY_KEY]
                            for idx in deleted_row_indices
                            if pd.notna(df.iloc[idx][PRIMARY_KEY])
                        ]
                        if deleted_ids:
                            try:
                                user_client.table(TABLE_NAME).delete().in_(PRIMARY_KEY, deleted_ids).execute()
                                success_count += len(deleted_ids)
                            except Exception as e:
                                error_messages.append(f"Deletion failed: {e}")

                    # REPORT RESULTS
                    if conflict_occurred:
                        st.error("🚨 **Concurrency Conflict Detected!**")
                        for err in error_messages:
                            st.markdown(err)
                        st.info("Please refresh data to merge latest changes.")
                    elif error_messages:
                        st.error("Errors encountered during sync:")
                        for err in error_messages:
                            st.write(f"- {err}")
                    else:
                        st.success(f"🎉 Successfully synced {success_count} operation(s)!")
                        st.cache_data.clear()
                        # Increment grid version to reset editor state after sync
                        st.session_state.grid_version += 1
                        st.rerun()

            with col_discard:
                if st.button("❌ Discard Local Changes", use_container_width=True):
                    # FIX: Incrementing grid_version forces Streamlit to rebuild st.data_editor
                    # with a fresh key, clearing un-synced edits immediately.
                    st.session_state.grid_version += 1
                    st.rerun()