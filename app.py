import streamlit as st
import pandas as pd
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions  # <--- ADD THIS IMPORT

# ==========================================
# 1. PAGE & SUPABASE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Consultation Records Grid",
    page_icon="📋",
    layout="wide"
)

# Fetch credentials from Streamlit secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://kocihpxevlowqbguhstf.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "sb_publishable_1MWEplxpyp0YOGW_TxZiMQ_HbvtHP5Z")

TABLE_NAME = "Consultation"
PRIMARY_KEY = "patientid"  # Adjust to "consultation_id" if needed

# Base unauthenticated client for auth calls
base_supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==========================================
# 2. SESSION & AUTH MANAGEMENT
# ==========================================
if "session" not in st.session_state:
    st.session_state.session = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None

def get_user_client() -> Client:
    """Sets the access token on the client for RLS requests."""
    if st.session_state.session:
        # Create a clean client and set the auth session
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.postgrest.auth(st.session_state.session.access_token)
        return client
    return base_supabase

# def get_user_client() -> Client:
#     """Returns a user-scoped Supabase client that embeds the user's Auth JWT for RLS."""
#     if st.session_state.session:
#         access_token = st.session_state.session.access_token
#         return create_client(
#             SUPABASE_URL,
#             SUPABASE_KEY,
#             options={"headers": {"Authorization": f"Bearer {access_token}"}}
#         )
#     return base_supabase


def login_user(email, password):
    try:
        res = base_supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.session = res.session
        
        # Retrieve role from user_roles
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
# 3. LOGIN SCREEN
# ==========================================
if not st.session_state.session:
    st.title("🔐 Login - Consultation Management System")
    with st.form("login_form"):
        email = st.text_input("Email Address")
        password = st.text_input("Password", type="password")
        submit_btn = st.form_submit_button("Log In", type="primary")
        
        if submit_btn:
            if email and password:
                login_user(email, password)
            else:
                st.warning("Please provide both email and password.")

else:
    # ==========================================
    # 4. MAIN CONSULTATION GRID DASHBOARD
    # ==========================================
    user_client = get_user_client()
    user_email = st.session_state.session.user.email
    current_role = st.session_state.user_role

    # Header Bar
    col_hdr, col_logout = st.columns([4, 1])
    with col_hdr:
        st.title("📋 Consultation Records Management")
        st.caption(f"Logged in as: **{user_email}** | Role: `:blue[{current_role.upper()}]`")
    with col_logout:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()

    st.divider()

    # --- FILTER & PAGINATION CONTROLS ---
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    
    with filter_col1:
        search_query = st.text_input("🔍 Search by Patient Name or Consultation ID", value="")
    
    with filter_col2:
        status_filter = st.selectbox("Filter Status", options=["All", "Scheduled", "In Progress", "Completed", "Cancelled"])
        
    with filter_col3:
        page_size = st.selectbox("Rows per page", options=[10, 25, 50, 100], index=1)

    # Fetch Data from Supabase with RLS
    try:
        query = user_client.table(TABLE_NAME).select("*")
        
        if status_filter != "All":
            query = query.eq("status", status_filter)
            
        if search_query.strip():
            # Search against patient_name or patient_id
            query = query.or_(f"patient_name.ilike.%{search_query}%,patient_id.ilike.%{search_query}%")
            
        response = query.order(PRIMARY_KEY, desc=True).limit(page_size).execute()
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error querying `Consultation` table under RLS: {e}")
        df = pd.DataFrame()

    # Permissions Logic
    is_read_only = (current_role == "viewer")
    can_add_or_delete = (current_role == "admin")

    if df.empty:
        st.info("No matching consultation records found in Supabase.")
    else:
        st.caption("Double-click any cell to edit. Use horizontal scroll to view all columns.")

        # --- DATA EDITOR WITH ADVANCED MULTI-COLUMN CONFIGURATION ---
        edited_df = st.data_editor(
            df,
            key="consultation_grid",
            disabled=is_read_only or [PRIMARY_KEY, "created_at", "updated_at"],
            num_rows="dynamic" if can_add_or_delete else "fixed",
            use_container_width=True,
            hide_index=True,
            column_config={
                # System/Key Identifiers
                PRIMARY_KEY: st.column_config.NumberColumn("ID", disabled=True),
                "consultation_date": st.column_config.DatetimeColumn("Consultation Date", format="YYYY-MM-DD HH:mm"),
                
                # Patient Info
                "patient_id": st.column_config.TextColumn("Patient ID", required=True),
                "patient_name": st.column_config.TextColumn("Patient Name", required=True),
                "doctor_name": st.column_config.TextColumn("Attending Doctor"),
                
                # Clinical Details
                "chief_complaint": st.column_config.TextColumn("Chief Complaint", width="large"),
                "diagnosis": st.column_config.TextColumn("Diagnosis / ICD Code", width="medium"),
                "clinical_notes": st.column_config.TextColumn("Clinical Notes", width="large"),
                "prescription": st.column_config.TextColumn("Prescription / Rx", width="medium"),
                
                # Vitals
                "bp_systolic": st.column_config.NumberColumn("BP Sys (mmHg)", min_value=50, max_value=250),
                "bp_diastolic": st.column_config.NumberColumn("BP Dia (mmHg)", min_value=30, max_value=150),
                "weight_kg": st.column_config.NumberColumn("Weight (kg)", min_value=0.0, max_value=300.0, format="%.1f"),
                
                # Status & Categorical
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Scheduled", "In Progress", "Completed", "Cancelled"],
                    required=True
                ),
                "follow_up_required": st.column_config.CheckboxColumn("Follow-up Needed?"),
                "follow_up_date": st.column_config.DateColumn("Follow-up Date", format="YYYY-MM-DD"),
                
                # Metadata
                "updated_at": st.column_config.DatetimeColumn("Last Modified", disabled=True, format="YYYY-MM-DD HH:mm:ss")
            }
        )

        # Delta state capture
        editor_state = st.session_state.get("consultation_grid", {})
        edited_rows = editor_state.get("edited_rows", {})
        added_rows = editor_state.get("added_rows", [])
        deleted_row_indices = editor_state.get("deleted_rows", [])

        total_changes = len(edited_rows) + len(added_rows) + len(deleted_row_indices)

        # --- SYNC ACTION BAR ---
        if not is_read_only and total_changes > 0:
            st.warning(f"⚠ Pending changes: **{len(edited_rows)}** update(s), **{len(added_rows)}** creation(s), **{len(deleted_row_indices)}** deletion(s).")

            col_sync, col_discard = st.columns([2, 1])

            with col_sync:
                if st.button("💾 Sync Consultation Changes", type="primary", use_container_width=True):
                    conflict_occurred = False
                    success_count = 0
                    error_messages = []

                    # 1. UPDATES WITH OPTIMISTIC LOCKING
                    if edited_rows:
                        for row_idx, updated_fields in edited_rows.items():
                            row_record = df.iloc[row_idx]
                            row_id = row_record[PRIMARY_KEY]
                            original_updated_at = row_record.get("updated_at")

                            # Sanitize values (NaN/NAT -> None for SQL NULL)
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
                                # Update query matching both Primary Key AND original timestamp
                                req = user_client.table(TABLE_NAME).update(cleaned_payload).eq(PRIMARY_KEY, row_id)
                                
                                if pd.notna(original_updated_at):
                                    req = req.eq("updated_at", str(original_updated_at))
                                    
                                res = req.execute()

                                if len(res.data) == 0:
                                    conflict_occurred = True
                                    error_messages.append(f"❌ **Conflict on Consultation ID `{row_id}`**: Modified by another user concurrently.")
                                else:
                                    success_count += 1

                            except Exception as e:
                                error_messages.append(f"Failed updating ID `{row_id}`: {e}")

                    # 2. INSERTIONS
                    if added_rows and current_role in ["editor", "admin"]:
                        new_records = []
                        for row in added_rows:
                            cleaned_row = {}
                            for k, v in row.items():
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

                    # 3. DELETIONS (Admin only)
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

                    # DISPLAY EXECUTION RESULTS
                    if conflict_occurred:
                        st.error("🚨 **Concurrency Conflict Detected!**")
                        for err in error_messages:
                            st.markdown(err)
                        st.info("Click **Discard Local Changes** or filter again to load the freshest state.")
                    elif error_messages:
                        st.error("Errors encountered during sync:")
                        for err in error_messages:
                            st.write(f"- {err}")
                    else:
                        st.success(f"🎉 Successfully synced {success_count} consultation record operation(s)!")
                        st.cache_data.clear()
                        st.rerun()

            with col_discard:
                if st.button("❌ Discard Local Changes", use_container_width=True):
                    st.rerun()