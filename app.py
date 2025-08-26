import os
import base64
from datetime import timedelta

import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd

# Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, firestore

# -----------------------------------------------------------------------------
# Page setup
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Raspberry Pi Server", layout="wide")

# -----------------------------------------------------------------------------
# Firebase initialization (exactly once; safe for Streamlit reruns)
# -----------------------------------------------------------------------------
def init_firebase():
    if not firebase_admin._apps:
        try:
            service_account = dict(st.secrets["firebase"])
        except Exception:
            st.error(
                "Firebase credentials not found. "
                "Add your service account JSON under `[firebase]` in Settings → Secrets."
            )
            st.stop()

        try:
            cred = credentials.Certificate(service_account)
            firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(
                "Failed to initialize Firebase. "
                "Please verify your service account fields in Secrets."
            )
            # Show a short, non-sensitive hint
            st.caption("Tip: Ensure `private_key` retains its BEGIN/END lines and newlines.")
            st.stop()

init_firebase()
db = firestore.client()

# -----------------------------------------------------------------------------
# Data access
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_firestore_data(collection_name: str) -> pd.DataFrame:
    """
    Pulls a small recent window of docs from Firestore based on the latest timestamp,
    then returns a tidy DataFrame with timestamp + voltage columns.
    """
    # Find latest doc to establish the time window
    latest = list(
        db.collection(collection_name)
          .order_by("timestamp", direction=firestore.Query.DESCENDING)
          .limit(1)
          .stream()
    )
    if not latest:
        return pd.DataFrame()

    latest_ts = latest[0].to_dict().get("timestamp")
    if latest_ts is None:
        return pd.DataFrame()

    # Look back a few seconds around the latest to capture a burst of points
    start_ts = latest_ts - timedelta(seconds=5)

    docs = (
        db.collection(collection_name)
          .where("timestamp", ">=", start_ts)
          .order_by("timestamp", direction=firestore.Query.ASCENDING)
          .stream()
    )

    rows = []
    for d in docs:
        doc = d.to_dict()
        ts = doc.get("timestamp")
        v = doc.get("voltage")
        if ts is not None and v is not None:
            rows.append({"timestamp": ts, "voltage": v})

    return pd.DataFrame(rows)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def apply_background_image_if_exists(path: str = "background.jpg") -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{img_b64}");
                background-size: cover;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        st.warning("Background image found but could not be applied.")

# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------
apply_background_image_if_exists()

with st.sidebar:
    st.title("Navigation")
    side_page = st.radio("Go to", ["Home", "Upload", "About"])

COLLECTION = "voltage"  # 🔁 use the same collection name everywhere

if side_page == "Home":
    st.subheader("Live Graph from Database")

    df = fetch_firestore_data(COLLECTION)

    if not df.empty:
        # Ensure pandas datetime for plotting
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        fig, ax = plt.subplots()
        ax.plot(df["timestamp"], df["voltage"], marker=".", label="VOLTAGE (V)")
        ax.set_xlabel("Time")
        ax.set_ylabel("Voltage")
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning(f"No data found in the '{COLLECTION}' collection yet.")

    # Refresh button
    if st.button("🔄 Refresh", type="primary"):
        st.cache_data.clear()
        st.rerun()

    # Device info cards
    st.subheader("Device Information")
    on = st.toggle("Status")
    st.success("✅ Activated!") if on else st.warning("⚠️ Deactivated")

    curr_power_v = 69
    power_generated_wh = 420
    st.markdown(
        f"""
        <div style="display:flex; gap:12px; flex-wrap:wrap;">
          <div style="flex:1; min-width:220px; padding:12px; border-radius:10px; background:#f9f9f9;">
            <h4>⚡ Current Power</h4>
            <p style="font-size:20px;"><b>{curr_power_v} V</b></p>
          </div>
          <div style="flex:1; min-width:220px; padding:12px; border-radius:10px; background:#f9f9f9;">
            <h4>🔋 Power Generated</h4>
            <p style="font-size:20px;"><b>{power_generated_wh} Wh</b></p>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

elif side_page == "Upload":
    st.title("📂 Upload Files")
    uploaded = st.file_uploader("Choose a file")
    if uploaded is not None:
        st.success(f"Uploaded: {uploaded.name}")

else:  # About
    st.title("About")
    st.write(
        "This app streams recent voltage readings from Firestore and renders a live chart. "
        "Credentials are loaded securely from Streamlit Secrets."
    )
