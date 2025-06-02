# firebase_setup.py
import streamlit as st
import firebase_admin
from firebase_admin import credentials, db

APP_NAME = "campops-main"

if APP_NAME not in firebase_admin._apps:
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
    }, name=APP_NAME)

app = firebase_admin.get_app(APP_NAME)

# Shared DB references
staff_ref = db.reference("staff", app=app)
assignments_ref = db.reference("assignments", app=app)
logs_ref = db.reference("logs", app=app)
incidents_ref = db.reference("incidents", app=app)
memos_ref = db.reference("memos", app=app)
meta_ref = db.reference("meta", app=app)
