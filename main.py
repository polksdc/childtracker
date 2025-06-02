import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import datetime
from pytz import timezone

# --- Timezone Config ---
MT = timezone("US/Mountain")

# --- Timestamp Helper ---
def now_timestamp():
    return datetime.datetime.now(MT).strftime("%B %d, %Y %I:%M %p")

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
    memos = spreadsheet.worksheet("memos")

    return spreadsheet, assignments, meta, log, staff_sheet, incidents, memos

# Load Sheets
spreadsheet, sheet, meta_sheet, log_sheet, staff_sheet, incident_sheet, memo_sheet = get_gsheet()

# --- UI Styling ---
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Daily Reset Logic ---
last_reset_cell = meta_sheet.acell('B1').value
today = datetime.datetime.now(MT).date().isoformat()

if last_reset_cell != today:
    st.warning("New day detected! Resetting assignment sheet...")
    sheet.resize(1)
    meta_sheet.update('B1', [[today]])
else:
    st.success(f"Data loaded for today: {today}")

# --- Load Staff List ---
staff_rows = staff_sheet.get_all_values()
STAFF = [row[0].strip() for row in staff_rows if row and row[0].strip()]
STAFF.insert(0, "")

# --- Load Assignments ---
rows = sheet.get_all_values()
headers = [h.lower() for h in rows[0]] if rows else ['staff', 'location', 'child']
data = pd.DataFrame(rows[1:], columns=headers) if len(rows) > 1 else pd.DataFrame(columns=headers)
data.columns = [col.lower() for col in data.columns]

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

st.info(
    f""" 
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
        for _, row_values in rows_with_index:
            child_name = row_values[headers.index("child")]
            log_sheet.append_row([
                timestamp,
                selected_action,
                staff,
                child_name,
                action_dict[selected_action]
            ])
        st.success(f"✅ {selected_action} logged for all children under {staff}")
        st.rerun()

# --- Per Child Actions ---
st.subheader("Children ", divider="gray")

total_children = len(data)
staff_children = len(rows_with_index)

st.write(f"🏕️ Total in Center: **{total_children}**")
st.write(f"🧑‍🏫 Under {staff}: **{staff_children}**")

for i, (sheet_row_num, row_values) in enumerate(rows_with_index):
    child_name = row_values[headers.index("child")]
    with st.expander(f"**{child_name}**"):
        st.write(f"Assigned to: {staff}")
        st.write(f"Location: {new_location}")

        incident_note = st.text_input(f"Log incident for {child_name}:", key=f"incident_{i}")
        if st.button(f"Save Incident for {child_name}", key=f"save_incident_{i}"):
            incident_sheet.append_row([now_timestamp(), staff, child_name, incident_note])
            st.success("Incident logged!")
            st.rerun()

        if st.button(f"Snack ✅ for {child_name}", key=f"snack_{i}"):
            log_sheet.append_row([now_timestamp(), "SNACK", staff, child_name, "Snack Provided"])
            st.success(f"Snack logged for {child_name}")
            st.rerun()

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
        sheet.append_row([staff, new_location, new_child.strip()])
        log_sheet.append_row([now_timestamp(), "Add", staff, new_child.strip(), "Added"])
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

# --- Sidebar Memos ---
with st.sidebar:
    st.header("📋 Staff Memos:")
    memo_rows = memo_sheet.get_all_values()
    memo_headers = memo_rows[0]
    memo_data = pd.DataFrame(memo_rows[1:], columns=memo_headers) if len(memo_rows) > 1 else pd.DataFrame(columns=["staff", "date", "memo"])
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
        staff_sheet.append_row([new_staff.strip()])
        st.rerun()
