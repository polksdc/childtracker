import streamlit as st
import pandas as pd
import datetime
from pytz import timezone
from firebase_setup import staff_ref, assignments_ref, logs_ref, incidents_ref, memos_ref

MT = timezone("US/Mountain")

st.title("📊 Admin Dashboard")

# Assignments
assignments_data = assignments_ref.get() or {}
rows = [[v["staff"], v["name"], v["location"]] for v in assignments_data.values()]
df = pd.DataFrame(rows, columns=["staff", "child", "location"])

if not df.empty:
    st.subheader("Active Assignments")
    st.dataframe(df.groupby("staff").size().reset_index(name="Children"))
else:
    st.write("✅ No active assignments")

# Logs
logs_data = logs_ref.get() or {}
log_rows = [[v["timestamp"], v["action"], v["staff"], v["child"], v["notes"]] for v in logs_data.values()]
log_df = pd.DataFrame(log_rows, columns=["timestamp","action","staff","child","notes"])
if not log_df.empty:
    log_df["ts"] = pd.to_datetime(log_df["timestamp"], format="%B %d, %Y %I:%M %p", errors="coerce")
    log_df = log_df.sort_values("ts", ascending=False).drop(columns="ts")
    st.subheader("Logs")
    st.dataframe(log_df)
    st.dataframe(log_df["staff"].value_counts().reset_index().rename(columns={"index":"staff","staff":"log_count"}))

# Incidents
incidents_data = incidents_ref.get() or {}
inc_rows = [[v["timestamp"], v["staff"], v["child"], v["note"]] for v in incidents_data.values()]
inc_df = pd.DataFrame(inc_rows, columns=["timestamp","staff","child","note"])
if not inc_df.empty:
    inc_df["ts"] = pd.to_datetime(inc_df["timestamp"], format="%B %d, %Y %I:%M %p", errors="coerce")
    inc_df = inc_df.sort_values("ts", ascending=False).drop(columns="ts")
    st.subheader("Incidents")
    st.dataframe(inc_df)

# Memo Management
st.header("📝 Memo Management")
staff_list = [v["name"] for v in (staff_ref.get() or {}).values()]
selected_staff = st.selectbox("Staff for Memo:", staff_list)
selected_date = st.date_input("Date", datetime.datetime.now(MT).date())

memos_data = memos_ref.get() or {}
memo_id, current_memo = None, ""
for k, v in memos_data.items():
    if v.get("staff") == selected_staff and v.get("date") == selected_date.isoformat():
        memo_id, current_memo = k, v.get("memo", "")
        break

memo_text = st.text_area("Memo Content (Markdown):", value=current_memo, height=300)
if st.button("Save Memo"):
    safe_memo = memo_text.replace("\r\n", "\n")
    data = {"staff": selected_staff, "date": selected_date.isoformat(), "memo": safe_memo}
    (memos_ref.child(memo_id).update if memo_id else memos_ref.push)(data)
    st.success("✅ Memo saved!")
    st.rerun()

if memo_id and st.button("Delete Memo"):
    memos_ref.child(memo_id).delete()
    st.success("✅ Memo deleted!")
    st.rerun()

st.markdown("---")
st.markdown(memo_text.replace("\\n","\n"))
