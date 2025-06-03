# === CONTINUING FROM EXISTING CODEBASE ===

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
