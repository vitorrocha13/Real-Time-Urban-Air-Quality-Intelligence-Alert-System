import streamlit as st
import requests
import pandas as pd
import time

st.title("🌿 GreenPulse AI Live Dashboard")

API = "http://localhost:8000/api/predictions"

placeholder = st.empty()

while True:
    try:
        data = requests.get(API).json()["data"]
        df = pd.DataFrame(data)

        with placeholder.container():
            st.metric("Total Readings", len(df))
            if not df.empty:
                st.bar_chart(df.groupby("city")["aqi_score"].mean())

                st.dataframe(df.tail(20))

    except:
        st.warning("Waiting for pipeline...")

    time.sleep(3)
    st.rerun()