import streamlit as st
import matplotlib.pyplot as plt    
import numpy as np
import pandas as pd
import random
import base64
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import timedelta

# Firebase Initialization
try:
    # Use the name of your provided JSON key file.
    cred = credentials.Certificate("cse331-77111-firebase-adminsdk-fbsvc-74100017d0.json")
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

# Get a reference to the Firestore database.
db = firestore.client()

# Modified Data Fetching Function
@st.cache_data(ttl=60)


# Temporary debugging function
@st.cache_data(ttl=60)
def fetch_firestore_data(collection_name):
    latest_doc_query = db.collection(collection_name).order_by(
        "timestamp", direction=firestore.Query.DESCENDING
    ).limit(1)
    
    latest_docs = list(latest_doc_query.stream())

    if not latest_docs:
        return pd.DataFrame()

    latest_timestamp = latest_docs[0].to_dict()['timestamp']
    start_timestamp = latest_timestamp - timedelta(seconds=5)

    docs_query = db.collection(collection_name).where(
        "timestamp", ">=", start_timestamp
    ).order_by("timestamp", direction=firestore.Query.ASCENDING)

    docs = docs_query.stream()
    
    data = []
    for doc in docs:
        doc_data = doc.to_dict()
        if 'timestamp' in doc_data and 'voltage' in doc_data:
            data.append(doc_data)

    if not data:
        return pd.DataFrame()

    return pd.DataFrame(data)

# Streamlit App Layout

# Sidebar
with st.sidebar:
    st.title("Navigation")
    side_page = st.radio("Go to", ["Home", "Upload", "About"])

# Main Content
if side_page == "Home":
    st.subheader("Live Graph from Database")

    # Dynamic Graphing Logic
    df = fetch_firestore_data('voltage')

    if not df.empty:

        df['timestamp'] = pd.to_datetime(df['timestamp'])

        fig, ax = plt.subplots()
        
        ax.plot(df['timestamp'], df['voltage'], label="VOLTAGE (V)", marker='.')
        ax.set_xlabel("Time")
        ax.set_ylabel("Voltage")
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning("No data found in the 'sensor_readings' collection. Waiting for data...")

    # Functional Refresh Button
    
    if st.button("🔄 Refresh", type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.subheader(" Device Information: ")
    on = st.toggle("Status")
    if on:
        st.success("✅ Activated!")
    else:
        st.warning("⚠️ Deactivated")

    curr_power = 69
    power_gen = 420
    with st.container():
        st.markdown(f"""
        <div style="padding:10px; border-radius:10px; background:#f9f9f9; margin:10px 0;">
            <h4>⚡ Current Power</h4>
            <p style="font-size:20px; color:#2196F3;"><b>{curr_power} V</b></p>
        </div>
        <div style="padding:10px; border-radius:10px; background:#f9f9f9; margin:10px 0;">
            <h4>🔋 Power Generated</h4>
            <p style="font-size:20px; color:#FF9800;"><b>{power_gen} Wh</b></p>
        </div>
        """, unsafe_allow_html=True)

elif side_page == "Upload":
    st.title("📂 Upload Files")
    # ...

def get_base64_of_bin_file(file_path):
    with open(file_path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

try:
    image_path = "background.jpg"
    image_base64 = get_base64_of_bin_file(image_path)
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/jpg;base64,{image_base64}");
            background-size: cover;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
except FileNotFoundError:
    st.warning("background.jpg not found. Skipping background image.")
