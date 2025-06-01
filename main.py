import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

@st.cache_resource
def get_gsheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", 
              "https://www.googleapis.com/auth/drive"]

    credentials = Credentials.from_service_account_info(
        st.secrets["google"],
        scopes=scopes
    )

    client = gspread.authorize(credentials)

    spreadsheet = client.open_by_key("1y9OvIk1X5x2qoMxLJUAxxlUa4ZjlYDIXWzbatRABEzs")

    assignments = spreadsheet.worksheet("assignments")
    meta = spreadsheet.worksheet("meta")
    log = spreadsheet.worksheet("log")
    staff_sheet = spreadsheet.worksheet("staff")

    return spreadsheet, assignments, meta, log, staff_sheet


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

# --- Load Staff List Dynamically ---
staff_rows = staff_sheet.get_all_values()
STAFF = [row[0].strip() for row in staff_rows if row and row[0].strip()]
STAFF.insert(0, "")

# --- Allow Adding Staff ---
st.sidebar.subheader("Manage Staff List")
new_staff = st.sidebar.text_input("Add new staff member:")
if st.sidebar.button("Add Staff"):
    if new_staff.strip() and new_staff.strip() not in STAFF:
        staff_sheet.append_row([new_staff.strip()])
        st.experimental_rerun()

# --- Load Current Assignments ---
rows = sheet.get_all_values()
if rows:
    headers = [h.lower() for h in rows[0]]
    if len(rows) > 1:
        data = pd.DataFrame(rows[1:], columns=headers)
    else:
        data = pd.DataFrame(columns=headers)
else:
    data = pd.DataFrame(columns=['staff', 'location', 'child'])
    st.write("Sheet is empty or missing headers.")
data.columns = [col.lower() for col in data.columns]

# --- Main UI ---
st.title("Staff Assignment Manager")

staff = st.selectbox("Select Staff", STAFF)

if staff:
    staff_data = data[data["staff"] == staff]

    locations = staff_data["location"].unique()
    location = locations[0] if len(locations) > 0 else ""
    new_location = st.text_input("Location:", value=location)

    if location != new_location:
        for idx, row in enumerate(rows[1:], start=2):
            row_staff = row[headers.index("staff")]
            if row_staff == staff:
                sheet.update_cell(idx, headers.index("location")+1, new_location)
        location = new_location

    rows_with_index = [
        (idx, row) for idx, row in enumerate(rows[1:], start=2)
        if row[headers.index("staff")] == staff
    ]

    st.subheader("Children")
    st.write(f"Total: {len(rows_with_index)}")

    for i, (sheet_row_num, row_values) in enumerate(rows_with_index):
        child_name = row_values[headers.index("child")]

        with st.expander(f"{child_name}"):
            st.write(f"Assigned to: {staff}")
            st.write(f"Location: {new_location}")

            valid_staff = [s for s in STAFF if s]
            move_to = st.selectbox(
                f"Move {child_name} to:",
                [staff] + [s for s in valid_staff if s != staff],
                key=f"move_select_{i}"
            )

            if move_to != staff:
                confirm_key = f"confirm_move_{i}"
                if confirm_key not in st.session_state:
                    st.session_state[confirm_key] = False

                if not st.session_state[confirm_key]:
                    if st.button(f"Confirm move to {move_to}", key=f"confirm_button_{i}"):
                        st.session_state[confirm_key] = True
                else:
                    sheet.delete_rows(sheet_row_num)
                    sheet.append_row([move_to, new_location, child_name])
                    log_sheet.append_row([
                        datetime.datetime.now().isoformat(),
                        "Move",
                        move_to,
                        child_name,
                        f"Moved from {staff} to {move_to}"
                    ])
                    del st.session_state[confirm_key]
                    st.rerun()

            if st.button(f"Remove {child_name}", key=f"remove_{i}"):
                sheet.delete_rows(sheet_row_num)
                log_sheet.append_row([
                    datetime.datetime.now().isoformat(),
                    "Remove",
                    staff,
                    child_name,
                    "Removed"
                ])
                st.rerun()

    st.subheader("Add Child")
    new_child = st.text_input("Child name", key="new_child")
    if st.button("Add Child"):
        if new_child.strip():
            sheet.append_row([staff, new_location, new_child.strip()])
            log_sheet.append_row([
                datetime.datetime.now().isoformat(),
                "Add",
                staff,
                new_child.strip(),
                "Added"
            ])
            st.rerun()

st.header("Shift Change - Staff Swap")
col1, col2 = st.columns(2)
with col1:
    from_staff = st.selectbox("From Staff", [s for s in STAFF if s], key="from_swap")
with col2:
    to_staff = st.selectbox("To Staff", [s for s in STAFF if s], key="to_swap")

if st.button("Swap Roles (move all children)"):
    count = 0
    for idx, row in enumerate(rows[1:], start=2):
        row_staff = row[headers.index("staff")]
        if row_staff == from_staff:
            sheet.update_cell(idx, headers.index("staff")+1, to_staff)
            log_sheet.append_row([
                datetime.datetime.now().isoformat(),
                "Role Swap",
                to_staff,
                row[headers.index("child")],
                f"Moved from {from_staff} to {to_staff}"
            ])
            count += 1
    st.success(f"Moved {count} children from {from_staff} to {to_staff}")
    st.rerun()
