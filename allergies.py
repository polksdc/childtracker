import streamlit as st
import duckdb
import pandas as pd
import io

st.title("Health Report Generator (HTML Export)")

uploaded_file = st.file_uploader("📂 Upload your Rosters Export CSV", type=["csv"])

if uploaded_file is not None:
    # Read CSV directly into pandas
    df_csv = pd.read_csv(uploaded_file)
    con = duckdb.connect(database=':memory:')
    con.register("roster", df_csv)

    query = """
    SELECT
        "Participant",
        "allergies-sensitivities-details" AS Allergies,
        "illness-medical-conditions-details" AS MedicalConditions,
        "behavior-mental-health-info" AS MentalHealthInfo,
        "additional-health-info-or-special-instructions" AS HealthInfo,
        "list-regular-medications" AS Medications,
        "Unit Primary Phone" AS PrimaryPhone,
        "Emergency Phone" AS EmergencyPhone
    FROM roster
    """
    df = con.execute(query).df()
    df.columns = [col.replace("-", " ").replace("/", " ").title() for col in df.columns]

    # Build very basic HTML
    html_table = df.to_html(index=False, justify="center", border=1, escape=False)
    full_html = f"""
    <html>
    <head>
       
    </head>
    <body>
        <h2>YMCA Health & Emergency Summary</h2>
        {html_table}
    </body>
    </html>
    """

    # Create downloadable HTML file
    html_bytes = full_html.encode('utf-8')
    st.success("✅ Report generated!")
    st.download_button(
        label="📥 Download HTML Report",
        data=html_bytes,
        file_name="health_report.html",
        mime="text/html"
    )

else:
    st.info("👆 Please upload a CSV file to generate your report.")
