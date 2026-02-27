"""
GreenPulse AI — Streamlit Dashboard
=====================================
Live air quality monitoring dashboard for Indian cities.

Features:
  - Auto-refreshes every N seconds (no manual reload)
  - City-by-city AQI gauge cards
  - Risk distribution pie chart
  - Time-series AQI trend per city
  - Active alerts feed
  - Raw data explorer

Data source: GreenPulse FastAPI server (localhost:8000)
"""

import time
import requests
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────

API_BASE       = "http://localhost:8000"
REFRESH_SECS   = 5
MAX_HISTORY    = 200  # records to pull per city for trend chart

AQI_COLOR_MAP = {
    "Good":        "#00e400",
    "Satisfactory":"#92d050",
    "Moderate":    "#ffff00",
    "Poor":        "#ff7e00",
    "Very Poor":   "#ff0000",
    "Severe":      "#7e0023",
}

RISK_COLOR_MAP = {
    "LOW":    "#2ecc71",
    "MEDIUM": "#f39c12",
    "HIGH":   "#e74c3c",
}

# ── Page Setup ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="GreenPulse AI — Urban Air Quality",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-title { font-size: 2.4rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0; }
    .subtitle   { font-size: 1rem; color: #6c757d; margin-bottom: 1.5rem; }
    .alert-high   { background: #fff5f5; border-left: 4px solid #e74c3c; padding: 0.6rem 1rem; margin: 0.3rem 0; border-radius: 4px; }
    .alert-medium { background: #fffbf0; border-left: 4px solid #f39c12; padding: 0.6rem 1rem; margin: 0.3rem 0; border-radius: 4px; }
    .metric-card  { background: #f8f9fa; border-radius: 8px; padding: 1rem; text-align: center; }
    div[data-testid="metric-container"] { background: #f8f9fa; border-radius: 8px; padding: 0.5rem; }
</style>
""", unsafe_allow_html=True)


# ── API Client ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=REFRESH_SECS)
def fetch_latest() -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/api/v1/latest", timeout=5)
        r.raise_for_status()
        return r.json().get("data", [])
    except Exception:
        return []


@st.cache_data(ttl=REFRESH_SECS)
def fetch_alerts() -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/api/v1/alerts", timeout=5)
        r.raise_for_status()
        return r.json().get("alerts", [])
    except Exception:
        return []


@st.cache_data(ttl=REFRESH_SECS)
def fetch_stats() -> dict:
    try:
        r = requests.get(f"{API_BASE}/api/v1/stats", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


@st.cache_data(ttl=REFRESH_SECS)
def fetch_city_history(city: str) -> list[dict]:
    try:
        r = requests.get(f"{API_BASE}/api/v1/city/{city}?limit={MAX_HISTORY}", timeout=5)
        r.raise_for_status()
        return r.json().get("records", [])
    except Exception:
        return []


@st.cache_data(ttl=30)
def fetch_cities() -> list[str]:
    try:
        r = requests.get(f"{API_BASE}/api/v1/cities", timeout=5)
        r.raise_for_status()
        return r.json().get("cities", [])
    except Exception:
        return []


# ── Chart Builders ─────────────────────────────────────────────────────────────

def make_aqi_gauge(aqi: float, city: str, category: str) -> go.Figure:
    """Speedometer-style AQI gauge for a city."""
    color = AQI_COLOR_MAP.get(category, "#999")
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=aqi,
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": f"<b>{city}</b><br><span style='font-size:0.8em;color:{color}'>{category}</span>"},
        gauge={
            "axis":      {"range": [0, 500], "tickwidth": 1},
            "bar":       {"color": color},
            "bgcolor":   "white",
            "steps": [
                {"range": [0, 50],   "color": "#e8f8e8"},
                {"range": [50, 100], "color": "#f0f8e0"},
                {"range": [100, 200],"color": "#fffff0"},
                {"range": [200, 300],"color": "#fff0e0"},
                {"range": [300, 400],"color": "#ffe0e0"},
                {"range": [400, 500],"color": "#f0d0d8"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 3},
                "thickness": 0.75,
                "value": aqi,
            },
        },
    ))
    fig.update_layout(height=220, margin=dict(t=60, b=10, l=20, r=20))
    return fig


def make_risk_pie(stats: dict) -> go.Figure:
    """Risk distribution donut chart."""
    dist = stats.get("risk_distribution", {})
    if not dist:
        return go.Figure()
    labels = list(dist.keys())
    values = list(dist.values())
    colors = [RISK_COLOR_MAP.get(l, "#aaa") for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.5,
        marker=dict(colors=colors),
        textinfo="label+percent",
    ))
    fig.update_layout(
        title="Risk Distribution (all records)",
        height=300, margin=dict(t=50, b=10, l=10, r=10),
        showlegend=False,
    )
    return fig


def make_aqi_trend(records: list[dict], city: str) -> go.Figure:
    """AQI time-series line chart for a city."""
    if not records:
        return go.Figure()

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "aqi"]).sort_values("timestamp")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp"], y=df["aqi"],
        mode="lines+markers",
        name="AQI",
        line=dict(color="#3498db", width=2),
        marker=dict(
            color=[RISK_COLOR_MAP.get(r, "#aaa") for r in df.get("risk_level", ["LOW"] * len(df))],
            size=6,
        ),
    ))
    fig.add_hline(y=100, line_dash="dash", line_color="#f39c12", annotation_text="Moderate threshold")
    fig.add_hline(y=200, line_dash="dash", line_color="#e74c3c", annotation_text="Poor threshold")
    fig.update_layout(
        title=f"AQI Trend — {city}",
        xaxis_title="Time",
        yaxis_title="AQI",
        height=350,
        margin=dict(t=50, b=40, l=40, r=20),
        plot_bgcolor="white",
        xaxis=dict(showgrid=True, gridcolor="#eee"),
        yaxis=dict(showgrid=True, gridcolor="#eee"),
    )
    return fig


def make_pollutant_bar(latest_data: list[dict]) -> go.Figure:
    """Bar chart comparing PM2.5 across cities."""
    if not latest_data:
        return go.Figure()
    df = pd.DataFrame(latest_data).sort_values("pm25", ascending=True)
    colors = [RISK_COLOR_MAP.get(r, "#aaa") for r in df.get("risk_level", ["LOW"] * len(df))]

    fig = go.Figure(go.Bar(
        x=df["pm25"], y=df["city"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}" for v in df["pm25"]],
        textposition="outside",
    ))
    fig.update_layout(
        title="PM2.5 Levels by City (µg/m³)",
        xaxis_title="PM2.5 (µg/m³)",
        height=320,
        margin=dict(t=50, b=40, l=80, r=40),
        plot_bgcolor="white",
    )
    return fig


# ── Sidebar ────────────────────────────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/leaf.png", width=64)
        st.markdown("## 🌿 GreenPulse AI")
        st.markdown("*Real-Time Urban Air Quality*")
        st.divider()

        auto_refresh = st.toggle("Auto Refresh", value=True)
        refresh_interval = st.slider("Refresh (sec)", 3, 30, REFRESH_SECS)

        st.divider()
        st.markdown("**AQI Colour Scale**")
        for cat, col in AQI_COLOR_MAP.items():
            st.markdown(
                f"<span style='background:{col};padding:2px 8px;border-radius:3px;font-size:0.8em'>{cat}</span>",
                unsafe_allow_html=True,
            )
        st.divider()
        st.markdown(
            "<small>Data: Pathway streaming pipeline<br>Model: RandomForest (sklearn)<br>API: FastAPI</small>",
            unsafe_allow_html=True,
        )

    return auto_refresh, refresh_interval


# ── Main Dashboard ─────────────────────────────────────────────────────────────

def render_header(stats: dict):
    st.markdown('<p class="main-title">🌿 GreenPulse AI</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="subtitle">Real-Time Urban Air Quality Intelligence & Alert System — Powered by Pathway</p>',
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Cities Monitored", stats.get("cities_monitored", "—"))
    with c2:
        st.metric("Total Readings", f"{stats.get('total_records', 0):,}")
    with c3:
        aqi_s = stats.get("aqi_stats", {})
        st.metric("Avg AQI", aqi_s.get("mean", "—"))
    with c4:
        hr = stats.get("high_risk_cities", [])
        st.metric("🚨 High Risk Cities", len(hr), delta=f"{', '.join(hr[:3])}" if hr else "None")


def render_alerts(alerts: list[dict]):
    st.markdown("### 🚨 Active Alerts")
    if not alerts:
        st.success("✅ No active alerts — air quality is acceptable across all monitored cities.")
        return

    for alert in alerts:
        css_class = "alert-high" if alert["risk_level"] == "HIGH" else "alert-medium"
        st.markdown(
            f'<div class="{css_class}">'
            f'<strong>{alert["city"]}</strong> | AQI: <strong>{alert["aqi"]:.0f}</strong> ({alert["category"]}) | '
            f'{alert["risk_level"]} | {alert.get("alert", "")}'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_city_gauges(latest_data: list[dict]):
    st.markdown("### 📊 Live AQI by City")
    if not latest_data:
        st.warning("No data received yet. Ensure the pipeline and simulator are running.")
        return

    cols = st.columns(min(len(latest_data), 4))
    for i, rec in enumerate(sorted(latest_data, key=lambda x: x.get("aqi", 0), reverse=True)):
        with cols[i % 4]:
            fig = make_aqi_gauge(
                aqi=rec.get("aqi", 0),
                city=rec.get("city", "?"),
                category=rec.get("category", "Unknown"),
            )
            st.plotly_chart(fig, use_container_width=True, key=f"gauge_{rec.get('city')}")

            risk = rec.get("risk_level", "?")
            color = RISK_COLOR_MAP.get(risk, "#aaa")
            st.markdown(
                f"<center><span style='background:{color};color:white;padding:2px 10px;"
                f"border-radius:12px;font-weight:600;font-size:0.8em'>{risk}</span></center>",
                unsafe_allow_html=True,
            )


def render_trend_section(cities: list[str]):
    st.markdown("### 📈 AQI Trend Analysis")
    if not cities:
        return

    selected_city = st.selectbox("Select city for trend", cities, key="trend_city")
    history = fetch_city_history(selected_city)

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(make_aqi_trend(history, selected_city), use_container_width=True)
    with col2:
        if history:
            last = history[-1]
            st.markdown(f"**Latest Reading — {selected_city}**")
            for field, label in [
                ("pm25", "PM2.5 (µg/m³)"),
                ("pm10", "PM10 (µg/m³)"),
                ("no2",  "NO2 (µg/m³)"),
                ("co",   "CO (mg/m³)"),
                ("temperature", "Temp (°C)"),
                ("humidity",    "Humidity (%)"),
                ("aqi",         "AQI"),
                ("risk_level",  "Risk Level"),
                ("confidence",  "Confidence (%)"),
            ]:
                val = last.get(field, "—")
                st.markdown(f"**{label}:** {val}")


def render_analytics(latest_data: list[dict], stats: dict):
    st.markdown("### 🔬 Analytics")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_pollutant_bar(latest_data), use_container_width=True)
    with col2:
        st.plotly_chart(make_risk_pie(stats), use_container_width=True)


def render_raw_data(latest_data: list[dict]):
    with st.expander("🗃 Raw Data Explorer"):
        if latest_data:
            df = pd.DataFrame(latest_data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No data available.")


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    auto_refresh, refresh_interval = render_sidebar()

    # ── Fetch data ──────────────────────────────────────────────────────────
    latest_data = fetch_latest()
    alerts      = fetch_alerts()
    stats       = fetch_stats()
    cities      = fetch_cities()

    # ── Render sections ─────────────────────────────────────────────────────
    render_header(stats)
    st.divider()
    render_alerts(alerts)
    st.divider()
    render_city_gauges(latest_data)
    st.divider()
    render_trend_section(cities)
    st.divider()
    render_analytics(latest_data, stats)
    render_raw_data(latest_data)

    # ── Footer ───────────────────────────────────────────────────────────────
    st.markdown(
        "<br><center><small>GreenPulse AI • Powered by Pathway + FastAPI + scikit-learn • "
        f"Last updated: {datetime.now().strftime('%H:%M:%S')}</small></center>",
        unsafe_allow_html=True,
    )

    # ── Auto refresh ─────────────────────────────────────────────────────────
    if auto_refresh:
        time.sleep(refresh_interval)
        st.cache_data.clear()
        st.rerun()


if __name__ == "__main__":
    main()
