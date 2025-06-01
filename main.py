import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime

# --- Timestamp Helper ---
def now_timestamp():
    return datetime.datetime.now().strftime("%B %d, %Y %I:%M %p")

# --- Google Sheets Setup ---
@st.cache_resource
def get_gsheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    credentials = Credentials.from_service_account_info(st.secrets["google"], scopes=scopes)
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key("1y9OvIk1X5x2qoMxLJUAxxlUa4ZjlYDIXWzbatRABEzs")

    assignments = spreadsheet.worksheet("assignments")
    meta = spreadsheet.worksheet("meta")
    log = spreadsheet.worksheet("log")
    staff_sheet = spreadsheet.worksheet("staff")
    incidents = spreadsheet.worksheet("incidents")

    return spreadsheet, assignments, meta, log, staff_sheet, incidents

# --- Load Sheets ---
spreadsheet, sheet, meta_sheet, log_sheet, staff_sheet, incident_sheet = get_gsheet()

# --- Daily Reset Logic ---
last_reset_cell = meta_sheet.acell('B1').value
today = datetime.date.today().isoformat()
st.write(f"Today's date: {today}")

if last_reset_cell != today:
    st.warning("New day detected! Resetting assignment sheet...")
    sheet.resize(1)
    sheet.append_row(["staff", "location", "child"])
    meta_sheet.update('B1', [[today]])
else:
    st.success(f"Data loaded for today: {today}")

# --- Load Staff List ---
staff_rows = staff_sheet.get_all_values()
STAFF = [row[0].strip() for row in staff_rows if row and row[0].strip()]
STAFF.insert(0, "")

# --- Allow Adding Staff ---
st.sidebar.subheader("Manage Staff List")
new_staff = st.sidebar.text_input("Add new staff member:")
if st.sidebar.button("Add Staff"):
    if new_staff.strip() and new_staff.strip() not in STAFF:
        staff_sheet.append_row([new_staff.strip()])
        st.rerun()

# --- Load Assignments ---
rows = sheet.get_all_values()
headers = [h.lower() for h in rows[0]] if rows else ['staff', 'location', 'child']
data = pd.DataFrame(rows[1:], columns=headers) if len(rows) > 1 else pd.DataFrame(columns=headers)
data.columns = [col.lower() for col in data.columns]

# --- Main UI ---
st.title("Staff Assignment Manager")

staff = st.selectbox("Select Staff", STAFF)
if not staff:
    st.stop()

staff_data = data[data["staff"] == staff]
locations = staff_data["location"].unique()
location = locations[0] if len(locations) > 0 else ""
new_location = st.text_input("Location:", value=location)

# Auto propagate location to children
if location != new_location:
    for idx, row in enumerate(rows[1:], start=2):
        if row[headers.index("staff")] == staff:
            sheet.update_cell(idx, headers.index("location")+1, new_location)
            log_sheet.append_row([
                now_timestamp(),
                "Location Update",
                staff,
                row[headers.index("child")],
                f"Updated location to {new_location}"
            ])
    location = new_location

rows_with_index = [
    (idx, row) for idx, row in enumerate(rows[1:], start=2)
    if row[headers.index("staff")] == staff
]

# --- Group Care Actions ---
st.subheader("Care Actions (Whole Group)")
care_actions = {
    "Ate": "Meal Confirmed",
    "Hydration": "Hydration Confirmed",
    "Sunscreen": "Sunscreen Applied",
    "Accurate Headcount": "Headcount Confirmed"
}
selected_care_action = st.selectbox("Select Care Action", list(care_actions.keys()), key="care_action_select")

if st.button("Confirm Care Action"):
    timestamp = now_timestamp()
    for _, row_values in rows_with_index:
        child_name = row_values[headers.index("child")]
        log_sheet.append_row([timestamp, selected_care_action, staff, child_name, care_actions[selected_care_action]])
    st.success(f"✅ {selected_care_action} logged for all children under {staff}")
    st.rerun()

# --- Per Child Loop ---
st.subheader("Children")
for i, (sheet_row_num, row_values) in enumerate(rows_with_index):
    child_name = row_values[headers.index("child")]
    with st.expander(f"{child_name}"):
        st.write(f"Assigned to: {staff}")
        st.write(f"Location: {new_location}")

        incident_note = st.text_input(f"Log incident for {child_name}:", key=f"incident_{i}")
        if st.button(f"Save Incident for {child_name}", key=f"save_incident_{i}"):
            incident_sheet.append_row([now_timestamp(), staff, child_name, incident_note])
            st.success("Incident logged!")
            st.rerun()

        # if st.button(f"Snack ✅ for {child_name}", key=f"snack_{i}"):
        #     log_sheet.append_row([now_timestamp(), "SNACK", staff, child_name, "Snack Provided"])
        #     st.success(f"Snack logged for {child_name}")
        #     st.rerun()

        st.write("🔄 Reassign this child:")
        new_staff_for_child = st.selectbox(f"Move {child_name} to another staff:",
                                           [s for s in STAFF if s != ""],
                                           index=STAFF.index(staff), key=f"staff_move_{i}")

        if st.button(f"Confirm Move for {child_name}", key=f"confirm_move_{i}"):
            sheet.delete_rows(sheet_row_num)
            sheet.append_row([new_staff_for_child, new_location, child_name])
            log_sheet.append_row([
                now_timestamp(),
                "Move",
                new_staff_for_child,
                child_name,
                f"Moved from {staff} to {new_staff_for_child}"
            ])
            st.success(f"{child_name} reassigned!")
            st.rerun()

            # --- Checkout Button ---
            # --- Checkout Button With Confirmation ---
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
                    sheet.delete_rows(sheet_row_num)
                    log_sheet.append_row([
                        now_timestamp(),
                        "Checkout",
                        staff,
                        child_name,
                        "Child Checked Out"
                    ])
                    st.success(f"{child_name} checked out successfully.")
                    del st.session_state[f"confirm_checkout_{i}"]
                    st.rerun()
            with col_cancel:
                if st.button("Cancel", key=f"cancel_button_{i}"):
                    st.session_state[f"confirm_checkout_{i}"] = False


# --- Add New Child ---
st.subheader("Add Child")
new_child = st.text_input("Child name", key="new_child_global")
if st.button("Add Child"):
    if new_child.strip():
        sheet.append_row([staff, new_location, new_child.strip()])
        log_sheet.append_row([now_timestamp(), "Add", staff, new_child.strip(), "Added"])
        st.rerun()

# # --- Activity Participation (Whole Group) ---
# st.subheader("Activity Participation (Whole Group)")
# activity_actions = {
#     "STEM": "STEM Activity Completed",
#     "SEL": "SEL Activity Completed",
#     "PE": "Physical Education Activity Completed",
#     "ARTS": "Arts & Crafts Completed"
# }
# selected_activity = st.selectbox("Select Activity", list(activity_actions.keys()), key="activity_action_select")
# 
# if st.button("Confirm Activity Participation"):
#     timestamp = now_timestamp()
#     for _, row_values in rows_with_index:
#         child_name = row_values[headers.index("child")]
#         log_sheet.append_row([timestamp, selected_activity, staff, child_name, activity_actions[selected_activity]])
#     st.success(f"✅ {selected_activity} logged for all children under {staff}")
#     st.rerun()

# --- Staff Swap ---
st.header("Shift Change - Staff Swap")
col1, col2 = st.columns(2)
with col1:
    from_staff = st.selectbox("From Staff", [s for s in STAFF if s], key="from_swap")
with col2:
    to_staff = st.selectbox("To Staff", [s for s in STAFF if s], key="to_swap")

if st.button("Swap Roles (move all children)"):
    count = 0
    for idx, row in enumerate(rows[1:], start=2):
        if row[headers.index("staff")] == from_staff:
            sheet.update_cell(idx, headers.index("staff")+1, to_staff)
            log_sheet.append_row([
                now_timestamp(),
                "Role Swap",
                to_staff,
                row[headers.index("child")],
                f"Moved from {from_staff} to {to_staff}"
            ])
            count += 1
    st.success(f"Moved {count} children from {from_staff} to {to_staff}")
    st.rerun()

# --- Full Child History ---
st.header("Child Full History")

incident_rows = incident_sheet.get_all_values()
incident_data = pd.DataFrame(incident_rows[1:], columns=incident_rows[0]) if len(incident_rows) > 1 else pd.DataFrame(columns=["timestamp", "staff", "child", "incident"])

log_rows = log_sheet.get_all_values()
log_data = pd.DataFrame(log_rows[1:], columns=log_rows[0]) if len(log_rows) > 1 else pd.DataFrame(columns=["timestamp", "action", "staff", "child", "log_text"])

all_children = data["child"].dropna().unique().tolist()
selected_child = st.selectbox("Select Child for History:", all_children)

# Incidents First
child_incidents = incident_data[incident_data["child"] == selected_child]
if not child_incidents.empty:
    st.subheader("📋 Incidents")
    for _, row in child_incidents.iterrows():
        st.write(f"🟥 {row['timestamp']} — {row['staff']}: {row['incident']}")
else:
    st.write("✅ No incidents logged.")

# Log After
emoji_map = {
    "Ate": "🍽️", "Hydration": "💧", "Sunscreen": "☀️", "Accurate Headcount": "👥",
    "STEM": "🔬", "SEL": "🧠", "PE": "🏃", "ARTS": "🎨",
    "SNACK": "🍎", "Add": "➕", "Role Swap": "🔄", "Remove": "❌", "Move": "🚚", "Location Update": "📍"
}

# Filter logs to today's date for Activity Log
log_data["parsed_date"] = pd.to_datetime(log_data["timestamp"], format="%B %d, %Y %I:%M %p")
today_only_logs = log_data[log_data["parsed_date"].dt.date == datetime.date.today()]
child_logs = today_only_logs[today_only_logs["child"] == selected_child]
if not child_logs.empty:
    st.subheader("📋 Activity Log")
    for _, row in child_logs.iterrows():
        emoji = emoji_map.get(row['action'], "📝")
        st.write(f"{row['timestamp']} — {emoji} {row['action']} — {row['staff']}: {row['log_text']}")
else:
    st.write("✅ No logs found.")
