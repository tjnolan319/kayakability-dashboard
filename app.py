import streamlit as st
import pandas as pd
import datetime
import altair as alt
import pydeck as pdk

# Load the data
df = pd.read_csv("kayak_conditions.csv")

# Parse timestamp
df["timestamp"] = pd.to_datetime(df["timestamp"])

# Get latest row
latest = df.iloc[-1]

# --- Scoring colors ---
def get_score_color(score):
    if score >= 80:
        return "🟢 Great"
    elif score >= 50:
        return "🟡 Caution"
    else:
        return "🔴 Unsafe"

# --- Page settings ---
st.set_page_config(page_title="Kayakability Dashboard", page_icon="🛶", layout="centered")

# --- Header ---
st.markdown("<h1 style='text-align: center; color: #1e3a8a;'>🛶 Kayakability Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #475569;'>Real-time data on kayaking conditions for the Merrimack River</p>", unsafe_allow_html=True)
st.markdown("---")

# --- Score card ---
st.subheader(f"📊 Score: {latest['kayakability_score']} ({get_score_color(latest['kayakability_score'])})")
st.text(f"Site: {latest['site_name']}")
st.text(f"Discharge: {latest['discharge_cfs']} cfs")
st.text(f"Gage Height: {latest['gage_height_ft']} ft")
st.text(f"Updated: {latest['timestamp'].strftime('%Y-%m-%d %I:%M %p')}")

# --- Map ---
st.markdown("### 🗺️ Map")
map_data = pd.DataFrame({
    'lat': [latest['lat']],
    'lon': [latest['lon']],
    'score': [latest['kayakability_score']]
})

st.map(map_data)

# Optional: Add fancy styled PyDeck map instead
# st.pydeck_chart(pdk.Deck(
#     initial_view_state=pdk.ViewState(
#         latitude=latest['lat'],
#         longitude=latest['lon'],
#         zoom=12,
#         pitch=50,
#     ),
#     layers=[
#         pdk.Layer(
#             'ScatterplotLayer',
#             data=map_data,
#             get_position='[lon, lat]',
#             get_color='[0, 100, 255, 160]',
#             get_radius=500,
#         ),
#     ],
# ))

st.markdown("---")
st.markdown("<small style='color:#94a3b8;'>Built by Timothy Nolan | Updated daily at 9AM EST</small>", unsafe_allow_html=True)
