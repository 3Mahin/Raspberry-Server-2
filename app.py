import streamlit as st
import matplotlib.pyplot as plt
import pandas as pd
from datetime import timedelta

st.set_page_config(page_title="Raspberry Pi Server", layout="wide")

# --- Firebase (already initialized as shown earlier) ---
from firebase_admin import firestore
db = firestore.client()

# --- Data fetch (cache for 60s) ---
@st.cache_data(ttl=60)
def fetch_firestore_data(collection_name: str) -> pd.DataFrame:
    # get the latest doc to determine a short time window
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

    start_ts = latest_ts - timedelta(seconds=5)

    docs = db.collection(collection_name)\
             .where("timestamp", ">=", start_ts)\
             .order_by("timestamp", direction=firestore.Query.ASCENDING)\
             .stream()

    rows = []
    for d in docs:
        doc = d.to_dict()
        ts = doc.get("timestamp")
        v  = doc.get("voltage")
        if ts is not None and v is not None:
            rows.append({"timestamp": ts, "voltage": v})

    return pd.DataFrame(rows)

# --- UI ---
with st.sidebar:
    st.title("Navigation")
    side_page = st.radio("Go to", ["Home", "Upload", "About"])

if side_page == "Home":
    st.subheader("Live Graph from Database")

    COLLECTION = "voltage"  # make this the same everywhere
    df = fetch_firestore_data(COLLECTION)

    if not df.empty:
        # Ensure pandas datetime for plotting
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        fig, ax = plt.subplots()
        ax.plot(df["timestamp"], df["voltage"], label="VOLTAGE (V)", marker=".")
        ax.set_xlabel("Time")
        ax.set_ylabel("Voltage")
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)
    else:
        st.warning(f"No data found in the '{COLLECTION}' collection yet.")

    if st.button("🔄 Refresh", type="primary"):
        st.cache_data.clear()
        st.rerun()

    st.subheader("Device Information")
    on = st.toggle("Status")
    st.success("✅ Activated!") if on else st.warning("⚠️ Deactivated")

    curr_power = 69
    power_gen = 420
    st.markdown(
        f"""
        <div style="padding:10px; border-radius:10px; background:#f9f9f9; margin:10px 0;">
            <h4>⚡ Current Power</h4>
            <p style="font-size:20px;"><b>{curr_power} V</b></p>
        </div>
        <div style="padding:10px; border-radius:10px; background:#f9f9f9; margin:10px 0;">
            <h4>🔋 Power Generated</h4>
            <p style="font-size:20px;"><b>{power_gen} Wh</b></p>
        </div>
        """,
        unsafe_allow_html=True
    )

elif side_page == "Upload":
    st.title("📂 Upload Files")
    # TODO: your upload logic

# Optional background image (safe fail)
import base64, os
def get_base64_of_bin_file(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

bg_path = "background.jpg"
if os.path.exists(bg_path):
    try:
        image_base64 = get_base64_of_bin_file(bg_path)
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
    except Exception:
        st.warning("Background image could not be applied.")
else:
    st.info("No background.jpg found (optional).")
