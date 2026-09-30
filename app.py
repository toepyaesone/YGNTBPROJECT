import streamlit as st
import pandas as pd
from supabase import create_client, Client

# ==========================================
# 1. PAGE & SUPABASE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Consultation Data Management",
    page_icon="🏥",
    layout="wide"
)

# Fetch Supabase configuration from Streamlit secrets
SUPABASE_URL = st.secrets.get("SUPABASE_URL", "https://kocihpxevlowqbguhstf.supabase.co")
SUPABASE_KEY = st.secrets.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtvY2locHhldmxvd3FiZ3Voc3RmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk5OTc3ODksImV4cCI6MjA4NTU3Mzc4OX0.cvA4PSXK3pb0xALwGVdYl8_u2ljYJJBN9f-XRVrrDm0")

TABLE_NAME = "Consultation"
PRIMARY_KEY = "patientid"

# Base unauthenticated client used for login calls
base_supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==========================================
# 2. SESSION STATE & AUTH FUNCTIONS
# ==========================================
if "session" not in st.session_state:
    st.session_state.session = None
if "user_role" not in st.session_state:
    st.session_state.user_role = None


def get_user_client() -> Client:
    """Returns a user-scoped Supabase client embedding the user's JWT token for RLS."""
    if st.session_state.session:
        access_token = st.session_state.session.access_token
        return create_client(
            SUPABASE_URL,
            SUPABASE_KEY,
            options={"headers": {"Authorization": f"Bearer {access_token}"}}
        )
    return base_supabase


def login_user(email, password):
    try:
        res = base_supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.session = res.session
        
        # Retrieve user role from user_roles table
        user_client = get_user_client()
        role_res = user_client.table("user_roles").select("role").eq("user_id", res.user.id).single().execute()
        st.session_state.user_role = role_res.data.get("role", "viewer") if role_res.data else "viewer"
        
        st.success("Successfully authenticated!")
        st.rerun()
    except Exception as e:
        st.error(f"Authentication failed: {e}")


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
    st.title("🔐 Login to Consultation System")
    st.caption("Sign in with your Supabase credentials to access record management.")
    
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
    # 4. MAIN DASHBOARD & DATA GRID
    # ==========================================
    user_client = get_user_client()
    user_email = st.session_state.session.user.email
    current_role = st.session_state.user_role

    # Header Bar
    col_hdr, col_logout = st.columns([4, 1])
    with col_hdr:
        st.title("🏥 Consultation Data Management")
        st.caption(f"User: **{user_email}** | Role: `:blue[{current_role.upper()}]`")
    with col_logout:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()

    # Data Fetching
    try:
        response = user_client.table(TABLE_NAME).select("*").order(PRIMARY_KEY, desc=True).execute()
        df = pd.DataFrame(response.data)
    except Exception as e:
        st.error(f"Error fetching data under RLS policy: {e}")
        df = pd.DataFrame()

    # Determine UI Permissions based on Role
    is_read_only = (current_role == "viewer")
    can_add_or_delete = (current_role == "admin")

    st.subheader("Data Records")

    if df.empty:
        st.info("No records found or permission denied by RLS policy.")
    else:
        # Render Interactive Grid
        edited_df = st.data_editor(
            df,
            key="Consultation
    _grid",
            disabled=is_read_only or [PRIMARY_KEY, "created_at", "updated_at"],
            num_rows="dynamic" if can_add_or_delete else "fixed",
            use_container_width=True,
            hide_index=True,
            column_config={
                PRIMARY_KEY: st.column_config.NumberColumn("ID", disabled=True),
                "patient_id": st.column_config.TextColumn("Patient ID", required=True),
                "township": st.column_config.TextColumn("Township", required=True),
                "reg_year": st.column_config.NumberColumn("Reg Year", min_value=2000, max_value=2030, step=1, format="%d"),
                "tb_type": st.column_config.SelectboxColumn(
                    "TB Type",
                    options=["Pulmonary (P)", "Extra-Pulmonary (EP)", "P", "EP"],
                    required=True
                ),
                "treatment_outcome": st.column_config.SelectboxColumn(
                    "Treatment Outcome",
                    options=["Active", "Cured", "Treatment Completed", "Died", "Failed", "Lost to Follow-up"],
                    required=True
                ),
                "remarks": st.column_config.TextColumn("Remarks"),
                "updated_at": st.column_config.DatetimeColumn("Last Modified", disabled=True, format="YYYY-MM-DD HH:mm:ss")
            }
        )

        # Inspect changes captured by Streamlit
        editor_state = st.session_state.get("Consultation
_grid", {})
        edited_rows = editor_state.get("edited_rows", {})
        added_rows = editor_state.get("added_rows", [])
        deleted_row_indices = editor_state.get("deleted_rows", [])

        total_changes = len(edited_rows) + len(added_rows) + len(deleted_row_indices)

        # Change Detection and Sync Bar
        if not is_read_only and total_changes > 0:
            st.warning(f"⚠ Pending changes: **{len(edited_rows)}** updated, **{len(added_rows)}** added, **{len(deleted_row_indices)}** deleted.")

            col_sync, col_discard = st.columns([2, 1])

            with col_sync:
                if st.button("💾 Sync Changes safely", type="primary", use_container_width=True):
                    conflict_occurred = False
                    success_count = 0
                    error_messages = []

                    # --- 1. HANDLE UPDATES WITH OPTIMISTIC CONCURRENCY LOCKING ---
                    if edited_rows:
                        for row_idx, updated_fields in edited_rows.items():
                            row_record = df.iloc[row_idx]
                            row_id = row_record[PRIMARY_KEY]
                            original_updated_at = row_record["updated_at"]

                            # Clean payload
                            cleaned_payload = {
                                k: (None if pd.isna(v) else v) 
                                for k, v in updated_fields.items() 
                                if k != "updated_at"
                            }

                            try:
                                # Update query checking both ID AND original updated_at timestamp
                                res = user_client.table(TABLE_NAME) \
                                    .update(cleaned_payload) \
                                    .eq(PRIMARY_KEY, row_id) \
                                    .eq("updated_at", original_updated_at) \
                                    .execute()

                                # If no rows were modified, timestamp was changed by another user
                                if len(res.data) == 0:
                                    conflict_occurred = True
                                    error_messages.append(
                                        f"❌ **Conflict on Record ID `{row_id}`**: Modified by another user since loading. Changes blocked."
                                    )
                                else:
                                    success_count += 1

                            except Exception as e:
                                error_messages.append(f"Update failed on record `{row_id}`: {e}")

                    # --- 2. HANDLE ADDITIONS ---
                    if added_rows and current_role in ["editor", "admin"]:
                        new_records = [
                            {k: (None if pd.isna(v) or v == "" else v) for k, v in row.items()} 
                            for row in added_rows
                        ]
                        try:
                            user_client.table(TABLE_NAME).insert(new_records).execute()
                            success_count += len(new_records)
                        except Exception as e:
                            error_messages.append(f"Insertion failed: {e}")

                    # --- 3. HANDLE DELETIONS (ADMIN ONLY) ---
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

                    # --- RESULT HANDLING ---
                    if conflict_occurred:
                        st.error("🚨 **Concurrency Conflict Detected!**")
                        for err in error_messages:
                            st.markdown(err)
                        st.info("Click **Refresh Data** below to get the newest data state before editing again.")
                    elif error_messages:
                        st.error("Errors encountered during database sync:")
                        for err in error_messages:
                            st.write(f"- {err}")
                    else:
                        st.success(f"🎉 Successfully synced {success_count} operation(s)!")
                        st.cache_data.clear()
                        st.rerun()

            with col_discard:
                if st.button("❌ Discard Local Changes", use_container_width=True):
                    st.rerun()