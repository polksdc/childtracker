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

staff_ref = db.reference("staff")
assignments_ref = db.reference("assignments")
logs_ref = db.reference("logs")
incidents_ref = db.reference("incidents")
memos_ref = db.reference("memos")

def safe_get(ref):
    return ref.get() or {}

# --- DEFAULT STAFF ---
default_staff_list = ["Fernando", "Leticia", "Kayleece", "Daegon", "Ali", "Hunter", "Melissa"]
if not staff_ref.get():
    for name in default_staff_list:
        staff_ref.push({"name": name, "location": "N/A"})
    st.success("✅ Default staff loaded")

# --- LOAD STAFF DATA ---
staff_data_raw = safe_get(staff_ref)
staff_lookup = {v["name"]: v.get("location", "N/A") for v in staff_data_raw.values()}
STAFF = list(staff_lookup.keys())
STAFF.insert(0, "")

# --- LOAD ASSIGNMENTS DATA ---
assignments_raw = safe_get(assignments_ref)
rows = []
for k, v in assignments_raw.items():
    rows.append({
        "id": k,
        "staff": v.get("staff", ""),
        "child": v.get("child", "")
    })
data = pd.DataFrame(rows, columns=["id", "staff", "child"])

#test
# --- PAGE NAVIGATION ---
page = st.sidebar.radio("📂 Navigate", ["👩‍🏫 Staff View", "📊 Admin View", "📝 Memo Management"])

# --- STAFF MANAGEMENT SIDEBAR ---
st.sidebar.divider()
st.sidebar.header("➕ Add New Staff")

new_staff_name = st.sidebar.text_input("Staff Name:")
new_staff_location = st.sidebar.text_input("Staff Location:")

if st.sidebar.button("Add Staff Member"):
    if new_staff_name.strip():
        staff_ref.push({"name": new_staff_name.strip(), "location": new_staff_location.strip() or "N/A"})
        st.sidebar.success(f"Added {new_staff_name}")
        st.rerun()

# STAFF VIEW
if page == "👩‍🏫 Staff View":
    st.title("SDC Dashboard 😎")
    staff = st.selectbox("Select Staff", STAFF)
    if not staff: st.stop()

    # --- MEMO SIDEBAR ---
    # --- MEMO SIDEBAR ---
    with st.sidebar:
        st.subheader("📋 Today's Memo")
    
        memos_data = safe_get(memos_ref)
        today_iso = today_date()
    
        # Find today's memo for selected staff
        todays_memo = ""
        for v in memos_data.values():
            if v.get("staff") == staff and v.get("date") == today_iso:
                todays_memo = v.get("memo", "")
                break
    
        if todays_memo:
            st.markdown(todays_memo)
        else:
            st.write("✅ No memo assigned today.")

    staff_location = staff_lookup.get(staff, "N/A")
    new_location = st.text_input("Location:", value=staff_location)

    if staff_location != new_location:
        for key, value in staff_data_raw.items():
            if value["name"] == staff:
                staff_ref.child(key).update({"location": new_location})
                logs_ref.push({
                    "timestamp": now_timestamp(),
                    "action": "Location Update",
                    "staff": staff,
                    "child": "[LOCATION UPDATE]",
                    "notes": f"Updated location to {new_location}"
                })
                break
        st.rerun()

    staff_assignments = data[data["staff"] == staff]
    rows_with_index = staff_assignments.to_dict(orient="records")

    st.info("""
    - **KEEP LOCATION UPDATED 🎯**
    - 🧑‍🤝‍🧑 Count heads
    - ☀️ Sunscreen outside every time
    - 💧 Hydrate between transitions
    - ✅ Log everything
    - 📢 Announce changes on walkie
    """)

    with st.expander("🛠️ Whole Group Actions", expanded=True):
        action_options = {
            "Care Actions": {
                "Ate": "Meal Confirmed",
                "Hydration": "Hydration Confirmed",
                "Sunscreen": "Sunscreen Applied",
                "Accurate Headcount": "Headcount Confirmed"
            },
            "Activity Participation": {
                "STEM": "STEM Activity Completed",
                "SEL": "SEL Activity Completed",
                "PE": "Physical Education Activity Completed",
                "ARTS": "Arts & Crafts Completed"
            }
        }
        category = st.radio("Action Type", list(action_options.keys()), key="cat")
        action_dict = action_options[category]
        selected_action = st.selectbox(f"Select {category[:-1]}", list(action_dict.keys()), key="act")

        if st.button(f"Confirm {category[:-1]}"):
            timestamp = now_timestamp()
            for row in rows_with_index:
                logs_ref.push({
                    "timestamp": timestamp,
                    "action": selected_action,
                    "staff": staff,
                    "child": row["child"],
                    "notes": action_dict[selected_action]
                })
            st.success(f"✅ {selected_action} logged for all")
            st.rerun()

    st.subheader("Children", divider="gray")
    st.write(f"🏕️ Total in Center: **{len(data)}**")
    st.write(f"🧑‍🏫 Under {staff}: **{len(rows_with_index)}**")

    for i, row in enumerate(rows_with_index):
        child_name = row["child"]
        child_id = row["id"]
        with st.expander(f"**{child_name}**"):
            st.write(f"Assigned to: {staff}  |  Location: {new_location}")

            incident_note = st.text_input(f"Incident:", key=f"inc_{i}")
            if st.button(f"Save Incident", key=f"btn_inc_{i}"):
                incidents_ref.push({
                    "timestamp": now_timestamp(),
                    "staff": staff,
                    "child": child_name,
                    "note": incident_note
                })
                st.success("Incident logged!")
                st.rerun()

            if st.button(f"Snack ✅", key=f"snack_{i}"):
                logs_ref.push({
                    "timestamp": now_timestamp(),
                    "action": "SNACK",
                    "staff": staff,
                    "child": child_name,
                    "notes": "Snack Provided"
                })
                st.success(f"Snack logged")
                st.rerun()
            
            new_staff_for_child = st.selectbox(
                "Reassign:", 
                [s for s in STAFF if s], 
                index=STAFF.index(staff) if staff in STAFF else 0, 
                key=f"move_{i}"
            )
            if st.button(f"Confirm Move", key=f"btn_move_{i}"):
                assignments_ref.child(child_id).update({"staff": new_staff_for_child, "child": child_name})
                logs_ref.push({
                    "timestamp": now_timestamp(),
                    "action": "Move",
                    "staff": new_staff_for_child,
                    "child": child_name,
                    "notes": f"Moved from {staff} to {new_staff_for_child}"
                })
                st.success(f"Moved to {new_staff_for_child}")
                st.rerun()

            if f"confirm_checkout_{i}" not in st.session_state:
                st.session_state[f"confirm_checkout_{i}"] = False

            if not st.session_state[f"confirm_checkout_{i}"]:
                if st.button(f"✅ Check Out", key=f"checkout_{i}"):
                    st.session_state[f"confirm_checkout_{i}"] = True
            else:
                st.warning("Confirm checkout?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Confirm", key=f"confirm_button_{i}"):
                        assignments_ref.child(child_id).delete()
                        logs_ref.push({
                            "timestamp": now_timestamp(),
                            "action": "Checkout",
                            "staff": staff,
                            "child": child_name,
                            "notes": "Child Checked Out"
                        })
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
            assignments_ref.push({
                "staff": staff,
                "child": new_child.strip()
            })
            logs_ref.push({
                "timestamp": now_timestamp(),
                "action": "Add",
                "staff": staff,
                "child": new_child.strip(),
                "notes": "Added"
            })
            st.rerun()

    with st.expander("🔄 Shift Change - Bulk Move"):
        col1, col2 = st.columns(2)
        with col1:
            from_staff = st.selectbox("From Staff", [s for s in STAFF if s], key="from_swap")
        with col2:
            to_staff = st.selectbox("To Staff", [s for s in STAFF if s], key="to_swap")

        if st.button("Swap Roles"):
            count = 0
            staff_assignments = data[data["staff"] == from_staff]
            for _, row in staff_assignments.iterrows():
                assignments_ref.child(row["id"]).update({
                    "staff": to_staff,
                    "child": row["child"]
                })
                logs_ref.push({
                    "timestamp": now_timestamp(),
                    "action": "Role Swap",
                    "staff": to_staff,
                    "child": row["child"],
                    "notes": f"Moved from {from_staff} to {to_staff}"
                })
                count += 1
            st.success(f"Moved {count} children.")
            st.rerun()



# ADMIN VIEW

# ================= CLEANED UP ADMIN VIEW ====================
if page == "📊 Admin View":

    # Load data
    staff_data = safe_get(staff_ref)
    assignments_data = safe_get(assignments_ref)
    logs_data = safe_get(logs_ref)
    incidents_data = safe_get(incidents_ref)
    memos_data = safe_get(memos_ref)
    
    # Build staff lookup
    staff_lookup = {v["name"]: v.get("location", "N/A") for v in staff_data.values()}
    STAFF = list(staff_lookup.keys())
    
    # Assignments Section
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
        assignments_grouped = assignments_df.groupby("staff").size().reset_index(name="Child Count")
    
        with st.expander("📊 Children Count Per Staff", expanded=True):
            st.dataframe(assignments_grouped, use_container_width=True)
    
        st.divider()
    
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
    
    # Logs Section
    st.header("📊 Logs Summary")
    
    log_rows = []
    for k, v in logs_data.items():
        log_rows.append([
            v.get("timestamp", ""),
            v.get("action", ""),
            v.get("staff", ""),
            v.get("child", ""),
            v.get("notes", "")
        ])
    
    logs_df = pd.DataFrame(log_rows, columns=["timestamp", "action", "staff", "child", "notes"])
    
    if logs_df.empty:
        st.success("✅ No logs found.")
    else:
        logs_df["parsed_timestamp"] = pd.to_datetime(logs_df["timestamp"], format="%B %d, %Y %I:%M %p", errors="coerce")
        logs_df = logs_df.sort_values(by="parsed_timestamp", ascending=False)
    
        with st.expander("📄 Full Logs (Latest First)", expanded=True):
            st.dataframe(
                logs_df.drop(columns=["parsed_timestamp"]),
                use_container_width=True,
                height=500
            )
    
        log_counts = logs_df["staff"].value_counts().reset_index()
        log_counts.columns = ["staff", "log_count"]
    
        with st.expander("📈 Log Counts Per Staff", expanded=False):
            st.dataframe(log_counts, use_container_width=True)
    
    st.divider()
    
    # Incidents Section
    st.header("🚨 Incidents Summary")
    
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
if page == "📝 Memo Management":

    st.title("Memo Management")

    selected_staff = st.selectbox("Staff for Memo:", STAFF)
    selected_date = st.date_input("Date", datetime.datetime.now(MT).date())
    memos_data = safe_get(memos_ref)

    memo_id, current_memo = None, ""
    for k, v in memos_data.items():
        if v.get("staff") == selected_staff and v.get("date") == selected_date.isoformat():
            memo_id, current_memo = k, v.get("memo", "")
            break

    col1, col2 = st.columns(2)

    with col1:
        memo_text = st.text_area("Memo Content:", value=current_memo, height=400)
        if st.button("Save Memo"):
            safe_memo = memo_text.replace("\r\n", "\n")
            data = {"staff": selected_staff, "date": selected_date.isoformat(), "memo": safe_memo}
            (memos_ref.child(memo_id).update if memo_id else memos_ref.push)(data)
            st.success("✅ Memo saved")
            st.rerun()

        if memo_id and st.button("Delete Memo"):
            memos_ref.child(memo_id).delete()
            st.success("✅ Memo deleted")
            st.rerun()

    with col2:
        st.markdown("### Live Preview:")
        st.markdown(memo_text or "*No content yet...*", unsafe_allow_html=True)

        # Bulk Memo Section
    st.subheader("📝 Bulk Memo Update")
    
    # Allow selecting date for the bulk memo
    bulk_memo_date = st.date_input("Select Date to Apply Bulk Memo:", datetime.datetime.now(MT).date(), key="bulk_date")
    
    # Text area for the memo content
    bulk_memo_text = st.text_area("Bulk Memo Content:", height=200, key="bulk_memo")
    
    # Apply button logic
    if st.button("Apply Memo to All Staff"):
        safe_bulk = bulk_memo_text.replace("\r\n", "\n")
        for staff_member in [s for s in STAFF if s]:  # skip empty string ""
            # Check if memo already exists
            memo_exists = None
            for k, v in memos_data.items():
                if v.get("staff") == staff_member and v.get("date") == bulk_memo_date.isoformat():
                    memo_exists = k
                    break
            data = {"staff": staff_member, "date": bulk_memo_date.isoformat(), "memo": safe_bulk}
            (memos_ref.child(memo_exists).update if memo_exists else memos_ref.push)(data)
        st.success("✅ Memo applied to all staff")
        st.rerun()

