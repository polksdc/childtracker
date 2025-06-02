import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import datetime
from pytz import timezone
import pandas as pd

# --- Timezone Config ---
MT = timezone("US/Mountain")


def today_date():
    return datetime.datetime.now(MT).date().isoformat()

def is_admin():
    return st.experimental_user.email in st.secrets["admin"]["allowed_emails"]
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

# --- Firebase Refs ---
staff_ref = db.reference("staff")
assignments_ref = db.reference("assignments")
logs_ref = db.reference("logs")
incidents_ref = db.reference("incidents")

# --- Load data ---
staff_data = staff_ref.get() or {}
assignments_data = assignments_ref.get() or {}
logs_data = logs_ref.get() or {}
incidents_data = incidents_ref.get() or {}

STAFF = [v["name"] for v in staff_data.values()]

st.title("🚀 CampOps Admin Dashboard")

# --- CHILDREN COUNT & ROSTER PER STAFF ---
st.header("👥 Active Assignments")

# Build assignments dataframe
assignments_rows = []
for k, v in assignments_data.items():
    assignments_rows.append([v.get("staff", ""), v.get("name", ""), v.get("location", "")])

assignments_headers = ["staff", "child", "location"]
assignments_df = pd.DataFrame(assignments_rows, columns=assignments_headers)

if not assignments_df.empty:
    # Child counts
    child_counts = assignments_df["staff"].value_counts().reset_index()
    child_counts.columns = ["staff", "child_count"]
    st.subheader("Total Children Per Staff:")
    st.dataframe(child_counts)

    st.subheader("Active Roster:")
    for staff_member in STAFF:
        staff_children = assignments_df[assignments_df["staff"] == staff_member]
        st.markdown(f"### {staff_member} ({len(staff_children)} children)")
        st.table(staff_children[["child", "location"]].reset_index(drop=True))
else:
    st.write("✅ No current children assigned.")

# --- LOGS REPORTING ---
st.header("📊 Logs Summary")

log_rows = []
for k, v in logs_data.items():
    log_rows.append([
        v.get("timestamp", ""), v.get("action", ""), v.get("staff", ""), v.get("child", ""), v.get("notes", "")
    ])

log_headers = ["timestamp", "action", "staff", "child", "notes"]
logs_df = pd.DataFrame(log_rows, columns=log_headers)

if not logs_df.empty:
    logs_df["parsed_timestamp"] = pd.to_datetime(logs_df["timestamp"], format="%B %d, %Y %I:%M %p", errors="coerce")
    logs_df = logs_df.sort_values(by="parsed_timestamp", ascending=False).drop(columns=["parsed_timestamp"])
    st.dataframe(logs_df)

    st.subheader("Total Log Counts Per Staff:")
    staff_counts = logs_df["staff"].value_counts().reset_index()
    staff_counts.columns = ["staff", "log_count"]
    st.dataframe(staff_counts)
else:
    st.write("✅ No logs found.")

# --- INCIDENTS REPORTING ---
st.header("🚨 Incidents Summary")

incident_rows = []
for k, v in incidents_data.items():
    incident_rows.append([
        v.get("timestamp", ""), v.get("staff", ""), v.get("child", ""), v.get("note", "")
    ])

incident_headers = ["timestamp", "staff", "child", "note"]
incidents_df = pd.DataFrame(incident_rows, columns=incident_headers)

if not incidents_df.empty:
    incidents_df["parsed_timestamp"] = pd.to_datetime(incidents_df["timestamp"], format="%B %d, %Y %I:%M %p",
                                                      errors="coerce")
    incidents_df = incidents_df.sort_values(by="parsed_timestamp", ascending=False).drop(columns=["parsed_timestamp"])
    st.dataframe(incidents_df)
else:
    st.write("✅ No incidents found.")

# --- MEMO MANAGEMENT ---
st.header("📝 Memo Management")

# Get memo data
memos_ref = db.reference("memos")
memos_data = memos_ref.get() or {}

# Select staff + date for memo management
selected_staff = st.selectbox("Select Staff for Memo:", STAFF, key="memo_staff")
selected_date = st.date_input("Select Date", datetime.datetime.now(MT).date(), key="memo_date")

# Find existing memo for selected staff + date
memo_id = None
current_memo = ""

for k, v in memos_data.items():
    if v.get("staff") == selected_staff and v.get("date") == selected_date.isoformat():
        memo_id = k
        current_memo = v.get("memo", "")
        break

# Memo editor
memo_text = st.text_area("Memo Content (Markdown Supported):", value=current_memo, height=400)

# Save/update logic
if st.button("💾 Save Memo"):
    safe_memo = memo_text.replace("\r\n", "\n")
    data = {
        "staff": selected_staff,
        "date": selected_date.isoformat(),
        "memo": safe_memo
    }
    if memo_id:
        memos_ref.child(memo_id).update(data)
        st.success("✅ Memo updated successfully!")
    else:
        memos_ref.push(data)
        st.success("✅ Memo created successfully!")
    st.rerun()

# Delete logic
if memo_id:
    if st.button("🗑️ Delete Memo"):
        memos_ref.child(memo_id).delete()
        st.success("✅ Memo deleted!")
        st.rerun()

# Live preview
st.markdown("---")
st.subheader("📄 Markdown Preview:")
st.markdown(memo_text.replace("\\n", "\n"))
