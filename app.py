import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# --- Config ---
CSV_URL = "https://raw.githubusercontent.com/tjnolan319/kayakability-dashboard/main/kayak_conditions.csv"

# --- Load Data ---
@st.cache_data(ttl=3600)
def load_data(url):
    df = pd.read_csv(url)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df

df = load_data(CSV_URL)
latest = df.iloc[-1]

# --- App Layout ---
st.set_page_config(page_title="Kayakability Dashboard", layout="centered")

st.title("🛶 Kayakability Dashboard")
st.caption("Auto-updating daily based on USGS water data.")

st.subheader(f"📍 {latest['site_name']}")
st.markdown(f"**Last Measured:** {latest['timestamp'].strftime('%Y-%m-%d %I:%M %p')}")

col1, col2, col3 = st.columns(3)
col1.metric("Kayakability Score", f"{int(latest['kayakability_score'])}/100")
col2.metric("Discharge", f"{latest['discharge_cfs']} cfs")
col3.metric("Gage Height", f"{latest['gage_height_ft']} ft")

st.markdown("---")

st.subheader("📊 Historical Kayakability Score")
st.line_chart(df.set_index('timestamp')['kayakability_score'])

st.markdown("---")

with st.expander("📄 Raw Data Table"):
    st.dataframe(df)

st.caption("Built by Tim Nolan · Powered by Streamlit + GitHub + USGS API")
