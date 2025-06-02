import gspread
from google.oauth2.service_account import Credentials
import firebase_admin
from firebase_admin import credentials as fb_credentials, db
import streamlit as st  # Only if you're running this from inside Streamlit

# --- Google Sheets setup ---
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

# Load your sheets
spreadsheet, assignment_sheet, meta_sheet, log_sheet, staff_sheet, incident_sheet, memo_sheet = get_gsheet()

# --- Firebase setup ---
fb_cred = fb_credentials.Certificate("Group Manager Firebase Service Account.json")
firebase_admin.initialize_app(fb_cred, {
    'databaseURL': 'https://group-manager-a55a2-default-rtdb.firebaseio.com'
})

# --- Migrate Staff ---
staff_rows = staff_sheet.get_all_values()[1:]  # Skip header
staff_ref = db.reference("staff")
for row in staff_rows:
    staff_name = row[0].strip()
    staff_ref.push({"name": staff_name})
print("Staff migrated")

# --- Migrate Assignments ---
assignment_rows = assignment_sheet.get_all_values()[1:]
assignment_ref = db.reference("assignments")
for row in assignment_rows:
    staff, location, child = row
    assignment_ref.push({
        "staff": staff,
        "location": location,
        "name": child
    })
print("Assignments migrated")

# --- Migrate Logs ---
log_rows = log_sheet.get_all_values()[1:]
log_ref = db.reference("logs")
for row in log_rows:
    timestamp, action, staff, child, notes = row
    log_ref.push({
        "timestamp": timestamp,
        "action": action,
        "staff": staff,
        "child": child,
        "notes": notes
    })
print("Logs migrated")

# --- Migrate Incidents ---
incident_rows = incident_sheet.get_all_values()[1:]
incident_ref = db.reference("incidents")
for row in incident_rows:
    timestamp, staff, child, note = row
    incident_ref.push({
        "timestamp": timestamp,
        "staff": staff,
        "child": child,
        "note": note
    })
print("Incidents migrated")

# --- Migrate Memos ---
memo_rows = memo_sheet.get_all_values()[1:]
memo_ref = db.reference("memos")
for row in memo_rows:
    staff, date, memo = row
    memo_ref.push({
        "staff": staff,
        "date": date,
        "memo": memo
    })
print("Memos migrated")
