import time
import requests
import pandas as pd
import streamlit as st

API_BASE = "http://localhost:8000/api"

st.set_page_config(page_title="GreenPulse AI", layout="wide", page_icon="🌿")
st.title("🌿 GreenPulse AI — Real-Time Air Quality Intelligence")
st.caption("Powered by Pathway + RandomForest | Auto-refresh every 3 seconds")

placeholder = st.empty()

while True:
    try:
        payload = requests.get(f"{API_BASE}/predictions", timeout=3).json()
        df = pd.DataFrame(payload.get("data", []))
        with placeholder.container():
            c1, c2 = st.columns(2)
            c1.metric("Total Readings", len(df))
            if not df.empty and "pm25" in df.columns:
                c2.metric("Avg PM2.5", f"{df['pm25'].mean():.1f} µg/m³")
                st.bar_chart(df.groupby("city")["aqi_score"].mean())
                st.dataframe(df.tail(20), use_container_width=True)
            else:
                st.info("Waiting for streaming data...")
    except Exception as e:
        st.warning(f"Connecting to pipeline... ({e})")
    time.sleep(3)
    st.rerun()
