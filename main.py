import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import datetime
from pytz import timezone

# --- Timezone Config ---
MT = timezone("US/Mountain")

# --- Timestamp Helper ---
def now_timestamp():
    return datetime.datetime.now(MT).strftime("%B %d, %Y %I:%M %p")

def today_date():
    return datetime.datetime.now(MT).date().isoformat()

# --- Firebase Init ---
if 'firebase_initialized' not in st.session_state:
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
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://group-manager-a55a2-default-rtdb.firebaseio.com'
    })
    st.session_state['firebase_initialized'] = True

# --- DB References ---
staff_ref = db.reference("staff")
assignments_ref = db.reference("assignments")
logs_ref = db.reference("logs")
incidents_ref = db.reference("incidents")
memos_ref = db.reference("memos")
meta_ref = db.reference("meta")

# --- Navigation ---
st.sidebar.title("🧭 Navigation")
page = st.sidebar.radio("Go to:", ["Dashboard", "Center Overview", "Memo Editor"])

# --- Early exit for Dashboard mode (your current code is "Dashboard") ---
if page != "Dashboard":
    st.experimental_set_query_params(page=page)  # preserve page state

# --- Center Overview ---
if page == "Center Overview":
    st.title("🧭 Full Center Overview")

    # Load full assignments data
    assignments_data = assignments_ref.get() or {}
    rows = []
    for k, v in assignments_data.items():
        rows.append({
            "Child": v['name'],
            "Staff": v['staff'],
            "Location": v['location']
        })
    df = pd.DataFrame(rows)

    if df.empty:
        st.info("No active children in the center.")
    else:
        st.write(f"👶 Total children: **{len(df)}**")
        st.dataframe(df.sort_values(by=["Staff", "Location"]))

    st.stop()  # prevent rest of code from running on this page

# --- Memo Editor ---
if page == "Memo Editor":
    st.title("📝 Staff Memo Editor")

    # Load staff list again
    staff_data = staff_ref.get() or {}
    STAFF_MEMO = [v["name"] for v in staff_data.values()]
    STAFF_MEMO.insert(0, "")

    staff_selected = st.selectbox("Select Staff", STAFF_MEMO)
    today = today_date()

    if staff_selected:
        # Load existing memos
        memos_data = memos_ref.get() or {}
        memo_key = None
        memo_text = ""

        for key, memo in memos_data.items():
            if memo.get("staff") == staff_selected and memo.get("date") == today:
                memo_key = key
                memo_text = memo.get("memo", "")
                break

        new_memo = st.text_area("Enter Memo (Markdown supported):", value=memo_text, height=300)

        if st.button("Save Memo"):
            if memo_key:
                memos_ref.child(memo_key).update({"memo": new_memo})
                st.success("Memo updated!")
            else:
                memos_ref.push({
                    "staff": staff_selected,
                    "date": today,
                    "memo": new_memo
                })
                st.success("Memo created!")

    st.stop()  # prevent rest of code from running on this page


# --- Load Staff List ---
staff_data = staff_ref.get() or {}
STAFF = [v["name"] for v in staff_data.values()]
STAFF.insert(0, "")

# --- Load Assignments ---

# --- Load Assignments ---
assignments_data = assignments_ref.get() or {}
rows = []
for k, v in assignments_data.items():
    rows.append({"id": k, "staff": v['staff'], "location": v['location'], "child": v['name']})

# ✅ This is the only change:
data = pd.DataFrame(rows, columns=["id", "staff", "location", "child"])


# --- Main UI ---
st.title("SDC Dashboard :sunglasses:")

staff = st.selectbox("Select Staff", STAFF)
if not staff:
    st.stop()

staff_data = data[data["staff"] == staff]
locations = staff_data["location"].unique()
location = locations[0] if len(locations) > 0 else ""
new_location = st.text_input("Location:", value=location)

if location != new_location:
    for index, row in staff_data.iterrows():
        assignments_ref.child(row["id"]).update({"location": new_location})
        logs_ref.push({
            "timestamp": now_timestamp(),
            "action": "Location Update",
            "staff": staff,
            "child": row["child"],
            "notes": f"Updated location to {new_location}"
        })
    location = new_location

rows_with_index = staff_data.to_dict(orient="records")

st.info(
    """
- **KEEP LOCATION UPDATED 🎯**
- 🧑‍🤝‍🧑 Count actual heads. 
- ☀️ Apply sunscreen for outside. EVERY TIME.
- 💧 Hydrate groups between transitions and during headcount.
- ✅ Use Care Actions to log everything.
- 📢 Announce logs and changes on walkie."""
)

# --- Whole Group Actions ---
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

    category = st.radio("Action Type", list(action_options.keys()), key="category_select")
    action_dict = action_options[category]
    selected_action = st.selectbox(f"Select {category[:-1]}", list(action_dict.keys()), key="action_select")

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
        st.success(f"✅ {selected_action} logged for all children under {staff}")
        st.rerun()

# --- Per Child Actions ---
st.subheader("Children ", divider="gray")

total_children = len(data)
staff_children = len(rows_with_index)

st.write(f"🏕️ Total in Center: **{total_children}**")
st.write(f"🧑‍🏫 Under {staff}: **{staff_children}**")

for i, row in enumerate(rows_with_index):
    child_name = row["child"]
    child_id = row["id"]

    with st.expander(f"**{child_name}**"):
        st.write(f"Assigned to: {staff}")
        st.write(f"Location: {new_location}")

        incident_note = st.text_input(f"Log incident for {child_name}:", key=f"incident_{i}")
        if st.button(f"Save Incident for {child_name}", key=f"save_incident_{i}"):
            incidents_ref.push({
                "timestamp": now_timestamp(),
                "staff": staff,
                "child": child_name,
                "note": incident_note
            })
            st.success("Incident logged!")
            st.rerun()

        if st.button(f"Snack ✅ for {child_name}", key=f"snack_{i}"):
            logs_ref.push({
                "timestamp": now_timestamp(),
                "action": "SNACK",
                "staff": staff,
                "child": child_name,
                "notes": "Snack Provided"
            })
            st.success(f"Snack logged for {child_name}")
            st.rerun()

        st.write("🔄 Reassign this child:")
        new_staff_for_child = st.selectbox(f"Move {child_name} to another staff:",
                                           [s for s in STAFF if s != ""],
                                           index=STAFF.index(staff), key=f"staff_move_{i}")

        if st.button(f"Confirm Move for {child_name}", key=f"confirm_move_{i}"):
            assignments_ref.child(child_id).update({"staff": new_staff_for_child})
            logs_ref.push({
                "timestamp": now_timestamp(),
                "action": "Move",
                "staff": new_staff_for_child,
                "child": child_name,
                "notes": f"Moved from {staff} to {new_staff_for_child}"
            })
            st.success(f"{child_name} reassigned!")
            st.rerun()

        if f"confirm_checkout_{i}" not in st.session_state:
            st.session_state[f"confirm_checkout_{i}"] = False

        if not st.session_state[f"confirm_checkout_{i}"]:
            if st.button(f"✅ Check Out {child_name}", key=f"checkout_{i}"):
                st.session_state[f"confirm_checkout_{i}"] = True
        else:
            st.warning(f"Confirm checkout for {child_name}?")
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
                    st.success(f"{child_name} checked out successfully.")
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"cancel_button_{i}"):
                    st.session_state[f"confirm_checkout_{i}"] = False

# --- Add Child ---
st.subheader("Add Child")
new_child = st.text_input("Child name", key="new_child_global")
if st.button("Add Child"):
    if new_child.strip():
        assignments_ref.push({
            "name": new_child.strip(),
            "staff": staff,
            "location": new_location
        })
        logs_ref.push({
            "timestamp": now_timestamp(),
            "action": "Add",
            "staff": staff,
            "child": new_child.strip(),
            "notes": "Added"
        })
        st.rerun()

# --- Bulk Move ---
with st.expander("🔄 Shift Change - Bulk Move Children"):
    col1, col2 = st.columns(2)
    with col1:
        from_staff = st.selectbox("From Staff", [s for s in STAFF if s], key="from_swap")
    with col2:
        to_staff = st.selectbox("To Staff", [s for s in STAFF if s], key="to_swap")

    if st.button("Swap Roles (move all children)"):
        count = 0
        for row in data[data["staff"] == from_staff].itertuples():
            assignments_ref.child(row.id).update({"staff": to_staff})
            logs_ref.push({
                "timestamp": now_timestamp(),
                "action": "Role Swap",
                "staff": to_staff,
                "child": row.child,
                "notes": f"Moved from {from_staff} to {to_staff}"
            })
            count += 1
        st.success(f"Moved {count} children from {from_staff} to {to_staff}")
        st.rerun()

with st.sidebar:
    with st.sidebar:
        st.header("📋 Staff Memos:")
        memos_data = memos_ref.get() or {}

        # Build rows like you had before
        memo_rows = []
        for k, v in memos_data.items():
            memo_rows.append([v.get("staff", ""), v.get("date", ""), v.get("memo", "")])

        memo_headers = ["staff", "date", "memo"]
        memo_data = pd.DataFrame(memo_rows, columns=memo_headers) if memo_rows else pd.DataFrame(columns=memo_headers)

        staff_memos = memo_data[(memo_data["staff"] == staff) & (memo_data["date"] == today)]

        if not staff_memos.empty:
            for _, row in staff_memos.iterrows():
                st.markdown(row["memo"])
        else:
            st.write("✅ No memo assigned for today.")

# --- Allow Adding Staff ---
st.sidebar.subheader("Manage Staff List")
new_staff = st.sidebar.text_input("Add new staff member:")
if st.sidebar.button("Add Staff"):
    if new_staff.strip() and new_staff.strip() not in STAFF:
        staff_ref.push({"name": new_staff.strip()})
        st.rerun()
