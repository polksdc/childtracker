import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import datetime
from pytz import timezone

# --- CONFIG ---
MT = timezone("US/Mountain")

def now_timestamp():
    return datetime.datetime.now(MT).strftime("%B %d, %Y %I:%M %p")

def today_date():
    return datetime.datetime.now(MT).date().isoformat()

# --- FIREBASE INITIALIZATION ---
firebase_secret = st.secrets["firebase"]
cred = credentials.Certificate({
    "type": firebase_secret["type"],
    "project_id": firebase_secret["project_id"],
    "private_key_id": firebase_secret["private_key_id"],
    "private_key": firebase_secret["private_key"].replace('\\n', '\n'),
    "client_email": firebase_secret["client_email"],
    "client_id": firebase_secret["client_id"],
    "auth_uri": firebase_secret["auth_uri"],
    "token_uri": firebase_secret["token_uri"],
    "auth_provider_x509_cert_url": firebase_secret["auth_provider_x509_cert_url"],
    "client_x509_cert_url": firebase_secret["client_x509_cert_url"]
})

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://group-manager-a55a2-default-rtdb.firebaseio.com'
    })

# --- FIREBASE REFERENCES ---
staff_ref = db.reference("staff")
assignments_ref = db.reference("assignments")
logs_ref = db.reference("logs")
incidents_ref = db.reference("incidents")
memos_ref = db.reference("memos")

# --- HELPER ---
def safe_get(ref):
    return ref.get() or {}

# --- DEFAULT STAFF ---
default_staff_list = ["Fernando", "Leticia", "Kayleece", "Daegon", "Ali", "Hunter", "Melissa"]
if not staff_ref.get():
    for name in default_staff_list:
        staff_ref.push({"name": name, "location": "Class 1"})

# --- HARD CODED LOCATIONS ---
LOCATIONS = ["Big Playground", "School Playground", "Field", "Bathroom", "Class 1", "Class 2", "Class 3", "Pool", "Field Trip", "Bus"]

# --- LOAD STAFF DATA ---
staff_data_raw = safe_get(staff_ref)
staff_lookup = {v["name"]: v.get("location", "Class 1") for v in staff_data_raw.values()}
STAFF = sorted(list(staff_lookup.keys()))

# --- LOAD ASSIGNMENTS ---
assignments_raw = safe_get(assignments_ref)
rows = []
for k, v in assignments_raw.items():
    rows.append({
        "id": k,
        "staff": v.get("staff", ""),
        "child": v.get("child", "")
    })
data = pd.DataFrame(rows, columns=["id", "staff", "child"])

# --- SIDEBAR STAFF MANAGEMENT ---
st.sidebar.header("Manage Staff")
new_staff_name = st.sidebar.text_input("Add Staff Name:")
new_staff_location = st.sidebar.selectbox("Default Location:", LOCATIONS)
if st.sidebar.button("Add Staff Member"):
    if new_staff_name.strip():
        staff_ref.push({"name": new_staff_name.strip(), "location": new_staff_location})
        st.sidebar.success(f"Added {new_staff_name}")
        st.rerun()

# --- PAGE NAVIGATION ---
page = st.sidebar.radio("Navigate", ["Staff View", "Admin View", "Memo Management"])

# ======================= STAFF VIEW =======================
if page == "Staff View":
    st.title("SDC Dashboard 😎")
    staff = st.selectbox("Select Staff:", [""] + STAFF)
    if not staff:
        st.stop()

    # MEMOS IN SIDEBAR
    with st.sidebar:
        st.subheader("📋 Today's Memo")
        memos_data = safe_get(memos_ref)
        today_iso = today_date()
        todays_memo = ""
        for v in memos_data.values():
            if v.get("staff") == staff and v.get("date") == today_iso:
                todays_memo = v.get("memo", "")
                break
        st.markdown(todays_memo or "✅ No memo assigned today.")

    staff_location = staff_lookup.get(staff, "Class 1")
    new_location = st.selectbox("Current Location:", LOCATIONS, index=LOCATIONS.index(staff_location) if staff_location in LOCATIONS else 0)

    if staff_location != new_location:
        for key, value in staff_data_raw.items():
            if value["name"] == staff:
                staff_ref.child(key).update({"location": new_location})
                logs_ref.push({"timestamp": now_timestamp(), "action": "Location Update", "staff": staff, "child": "[LOCATION UPDATE]", "notes": f"Updated location to {new_location}"})
                break
        st.rerun()

    staff_assignments = data[data["staff"] == staff]
    rows_with_index = staff_assignments.to_dict(orient="records")

    st.info("""- **KEEP LOCATION UPDATED 🎯**\n- 🧑‍🤝‍🧑 Count heads\n- ☀️ Sunscreen\n- 💧 Hydrate\n- ✅ Log everything\n- 📢 Walkie logs""")

    with st.expander("🛠 Whole Group Actions", expanded=True):
        action_options = {
            "Care Actions": {"Ate": "Meal Confirmed", "Hydration": "Hydration Confirmed", "Sunscreen": "Sunscreen Applied", "Accurate Headcount": "Headcount Confirmed"},
            "Activity Participation": {"STEM": "STEM Activity Completed", "SEL": "SEL Activity Completed", "PE": "Physical Education Activity Completed", "ARTS": "Arts & Crafts Completed"}
        }
        category = st.radio("Action Type", list(action_options.keys()), key="cat")
        action_dict = action_options[category]
        selected_action = st.selectbox("Select Action", list(action_dict.keys()), key="act")
        if st.button("Confirm Action"):
            timestamp = now_timestamp()
            for row in rows_with_index:
                logs_ref.push({"timestamp": timestamp, "action": selected_action, "staff": staff, "child": row["child"], "notes": action_dict[selected_action]})
            st.success("✅ Logged for all")
            st.rerun()

    st.subheader("Children", divider="gray")
    st.write(f"🏕️ Total in Center: **{len(data)}**")
    st.write(f"🧑‍🏫 Under {staff}: **{len(rows_with_index)}**")

    for i, row in enumerate(rows_with_index):
        child_name = row["child"]
        child_id = row["id"]
        with st.expander(f"**{child_name}**"):
            st.write(f"Assigned to: {staff} | Location: {new_location}")

            incident_note = st.text_input("Incident:", key=f"inc_{i}")
            if st.button("Save Incident", key=f"btn_inc_{i}"):
                incidents_ref.push({"timestamp": now_timestamp(), "staff": staff, "child": child_name, "note": incident_note})
                st.success("Incident logged!")
                st.rerun()

            if st.button("Snack ✅", key=f"snack_{i}"):
                logs_ref.push({"timestamp": now_timestamp(), "action": "SNACK", "staff": staff, "child": child_name, "notes": "Snack Provided"})
                st.success("Snack logged")
                st.rerun()

            valid_staff_list = STAFF
            current_index = valid_staff_list.index(staff) if staff in valid_staff_list else 0
            new_staff_for_child = st.selectbox("Reassign:", valid_staff_list, index=current_index, key=f"move_{i}")
            if st.button("Confirm Move", key=f"btn_move_{i}"):
                assignments_ref.child(child_id).update({"staff": new_staff_for_child, "child": child_name})
                logs_ref.push({"timestamp": now_timestamp(), "action": "Move", "staff": new_staff_for_child, "child": child_name, "notes": f"Moved from {staff} to {new_staff_for_child}"})
                st.success("Child reassigned!")
                st.rerun()

            if f"confirm_checkout_{i}" not in st.session_state:
                st.session_state[f"confirm_checkout_{i}"] = False
            if not st.session_state[f"confirm_checkout_{i}"]:
                if st.button("✅ Check Out", key=f"checkout_{i}"):
                    st.session_state[f"confirm_checkout_{i}"] = True
            else:
                st.warning("Confirm checkout?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Confirm", key=f"confirm_button_{i}"):
                        assignments_ref.child(child_id).delete()
                        logs_ref.push({"timestamp": now_timestamp(), "action": "Checkout", "staff": staff, "child": child_name, "notes": "Checked Out"})
                        del st.session_state[f"confirm_checkout_{i}"]
                        st.success("Checked out.")
                        st.rerun()
                with col_cancel:
                    if st.button("Cancel", key=f"cancel_button_{i}"):
                        st.session_state[f"confirm_checkout_{i}"] = False

    st.subheader("➕ Add Child")
    new_child = st.text_input("Child name:", key="new_child_global")
    if st.button("Add Child"):
        if new_child.strip():
            assignments_ref.push({"staff": staff, "child": new_child.strip()})
            logs_ref.push({"timestamp": now_timestamp(), "action": "Add", "staff": staff, "child": new_child.strip(), "notes": "Added"})
            st.rerun()

    # SWAP ROLES
    with st.expander("🔄 Shift Change - Bulk Move"):
        col1, col2 = st.columns(2)
        with col1:
            from_staff = st.selectbox("From Staff:", STAFF, key="from_swap")
        with col2:
            to_staff = st.selectbox("To Staff:", STAFF, key="to_swap")
        if st.button("Swap Roles"):
            count = 0
            staff_assignments = data[data["staff"] == from_staff]
            for _, row in staff_assignments.iterrows():
                assignments_ref.child(row["id"]).update({"staff": to_staff, "child": row["child"]})
                logs_ref.push({"timestamp": now_timestamp(), "action": "Role Swap", "staff": to_staff, "child": row["child"], "notes": f"Moved from {from_staff} to {to_staff}"})
                count += 1
            st.success(f"Moved {count} children.")
            st.rerun()

# ADMIN VIEW
if page == "Admin View":

    st.title("📊 Admin Panel")

    # Load Firebase data
    staff_data = safe_get(staff_ref)
    assignments_data = safe_get(assignments_ref)
    logs_data = safe_get(logs_ref)
    incidents_data = safe_get(incidents_ref)

    # Build staff lookup again (for safety)
    staff_lookup = {v["name"]: v.get("location", "N/A") for v in staff_data.values()}
    STAFF = sorted(list(staff_lookup.keys()))

    # Active Assignments
    st.header("👥 Active Assignments")

    assignment_rows = []
    for k, v in assignments_data.items():
        assignment_rows.append({
            "id": k,
            "staff": v.get("staff", ""),
            "child": v.get("child", "")
        })

    assignments_df = pd.DataFrame(assignment_rows)

    if assignments_df.empty:
        st.success("✅ No active assignments.")
    else:
        count_by_staff = assignments_df.groupby("staff").size().reset_index(name="Child Count")

        with st.expander("📊 Children Count Per Staff", expanded=True):
            st.dataframe(count_by_staff, use_container_width=True)

        st.subheader("📋 Full Staff Rosters")
        for staff_member in STAFF:
            assigned_children = assignments_df[assignments_df["staff"] == staff_member]
            location = staff_lookup.get(staff_member, "N/A")
            child_count = len(assigned_children)

            st.markdown(f"#### 👤 {staff_member} — Location: {location} — `{child_count} kids`")
            if not assigned_children.empty:
                st.table(assigned_children[["child"]].reset_index(drop=True))
            else:
                st.write("No children assigned.")

    st.divider()

    # Logs View
    st.header("📄 Logs Summary")

    # Date Filter for Logs
    selected_date = st.date_input("Filter Logs by Date:", datetime.datetime.now(MT).date())
    selected_date_str = selected_date.strftime("%B %d, %Y")

    log_rows = []
    for k, v in logs_data.items():
        timestamp = v.get("timestamp", "")
        if selected_date_str in timestamp:  # Only include logs from selected date
            log_rows.append([
                timestamp,
                v.get("action", ""),
                v.get("staff", ""),
                v.get("child", ""),
                v.get("notes", "")
            ])

    logs_df = pd.DataFrame(log_rows, columns=["timestamp", "action", "staff", "child", "notes"])
    
    # Child-specific log view
    st.subheader("👶 Child-Specific Log View")
    # Get unique children from both current assignments and logs
    all_children = set()
    for v in assignments_data.values():
        if v.get("child"):
            all_children.add(v.get("child"))
    for v in logs_data.values():
        if v.get("child") and v.get("child") not in ["[LOCATION UPDATE]", "ALL"]:
            all_children.add(v.get("child"))
    
    selected_child = st.selectbox("Select Child:", [""] + sorted(list(all_children)))
    
    if selected_child:
        child_logs = logs_df[logs_df["child"] == selected_child]
        if not child_logs.empty:
            st.markdown(f"### 📊 Statistics for {selected_child}")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Logs", len(child_logs))
            with col2:
                st.metric("Unique Actions", len(child_logs["action"].unique()))
            with col3:
                st.metric("Staff Interactions", len(child_logs["staff"].unique()))
            
            st.markdown("### 📝 Log History")
            for _, log in child_logs.iterrows():
                with st.expander(f"{log['timestamp']} - {log['action']}"):
                    st.write(f"**Staff:** {log['staff']}")
                    st.write(f"**Action:** {log['action']}")
                    st.write(f"**Notes:** {log['notes']}")
        else:
            st.info(f"No logs found for {selected_child} on {selected_date_str}")

    st.divider()

    # All Logs View
    st.subheader("📄 All Logs")
    if logs_df.empty:
        st.success(f"✅ No logs found for {selected_date_str}")
    else:
        logs_df["parsed_timestamp"] = pd.to_datetime(logs_df["timestamp"], format="%B %d, %Y %I:%M %p", errors="coerce")
        logs_df = logs_df.sort_values(by="parsed_timestamp", ascending=False)

        with st.expander("📄 Full Logs", expanded=True):
            st.dataframe(
                logs_df.drop(columns=["parsed_timestamp"]),
                use_container_width=True,
                height=500
            )

        log_counts = logs_df["staff"].value_counts().reset_index()
        log_counts.columns = ["staff", "log_count"]

        with st.expander("📈 Log Counts Per Staff"):
            st.dataframe(log_counts, use_container_width=True)

    st.divider()

    # Emergency Actions
    with st.expander("🚨 Emergency Actions", expanded=False):
        st.warning("⚠️ These actions are irreversible!")
        
        if "confirm_remove_all" not in st.session_state:
            st.session_state.confirm_remove_all = 0
            
        if st.session_state.confirm_remove_all == 0:
            if st.button("Remove All Children"):
                st.session_state.confirm_remove_all = 1
        elif st.session_state.confirm_remove_all == 1:
            st.error("Are you absolutely sure? This will remove ALL children from the system.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, I'm Sure"):
                    st.session_state.confirm_remove_all = 2
            with col2:
                if st.button("Cancel"):
                    st.session_state.confirm_remove_all = 0
        elif st.session_state.confirm_remove_all == 2:
            st.error("⚠️ FINAL WARNING: This action cannot be undone!")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Confirm Remove All"):
                    # Remove all assignments
                    for key in assignments_data.keys():
                        assignments_ref.child(key).delete()
                    # Log the action
                    logs_ref.push({
                        "timestamp": now_timestamp(),
                        "action": "EMERGENCY",
                        "staff": "ADMIN",
                        "child": "ALL",
                        "notes": "Emergency removal of all children"
                    })
                    st.session_state.confirm_remove_all = 0
                    st.success("✅ All children have been removed from the system")
                    st.rerun()
            with col2:
                if st.button("Cancel Emergency Action"):
                    st.session_state.confirm_remove_all = 0

    st.divider()

    # Incidents View
    st.header("🚨 Incident Reports")

    incident_rows = []
    for k, v in incidents_data.items():
        incident_rows.append([
            v.get("timestamp", ""),
            v.get("staff", ""),
            v.get("child", ""),
            v.get("note", "")
        ])

    incidents_df = pd.DataFrame(incident_rows, columns=["timestamp", "staff", "child", "note"])

    if incidents_df.empty:
        st.success("✅ No incidents found.")
    else:
        incidents_df["parsed_timestamp"] = pd.to_datetime(incidents_df["timestamp"], format="%B %d, %Y %I:%M %p", errors="coerce")
        incidents_df = incidents_df.sort_values(by="parsed_timestamp", ascending=False)

        st.dataframe(
            incidents_df.drop(columns=["parsed_timestamp"]),
            use_container_width=True,
            height=400
        )

# MEMO MANAGEMENT

if page == "Memo Management":

    st.title("📝 Memo Management")

    # Load memos again
    memos_data = safe_get(memos_ref)

    selected_staff = st.selectbox("Staff for Memo:", STAFF)
    selected_date = st.date_input("Date", datetime.datetime.now(MT).date())

    # Attempt to prepopulate if memo exists
    memo_id, current_memo = None, ""
    for k, v in memos_data.items():
        if v.get("staff") == selected_staff and v.get("date") == selected_date.isoformat():
            memo_id, current_memo = k, v.get("memo", "")
            break

    col1, col2 = st.columns(2)

    with col1:
        memo_text = st.text_area("Memo Content:", value=current_memo, height=400)
        if st.button("Save Memo"):
            clean_memo = memo_text.replace("\r\n", "\n")
            data = {"staff": selected_staff, "date": selected_date.isoformat(), "memo": clean_memo}
            (memos_ref.child(memo_id).update if memo_id else memos_ref.push)(data)
            st.success("✅ Memo saved!")
            st.rerun()

        if memo_id and st.button("Delete Memo"):
            memos_ref.child(memo_id).delete()
            st.success("✅ Memo deleted.")
            st.rerun()

    with col2:
        st.markdown("### Live Preview:")
        st.markdown(memo_text or "*No memo content yet...*")

    st.divider()
    st.subheader("📝 Bulk Memo Distribution")

    bulk_date = st.date_input("Date for Bulk Memo:", datetime.datetime.now(MT).date(), key="bulk_date")
    bulk_memo = st.text_area("Bulk Memo Content:", height=200, key="bulk_memo")

    if st.button("Apply Memo to All Staff"):
        safe_bulk = bulk_memo.replace("\r\n", "\n")
        for staff_member in STAFF:
            existing = None
            for k, v in memos_data.items():
                if v.get("staff") == staff_member and v.get("date") == bulk_date.isoformat():
                    existing = k
                    break
            data = {"staff": staff_member, "date": bulk_date.isoformat(), "memo": safe_bulk}
            (memos_ref.child(existing).update if existing else memos_ref.push)(data)
        st.success("✅ Bulk memo assigned")
        st.rerun()
