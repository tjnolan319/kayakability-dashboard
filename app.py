import streamlit as st
import pandas as pd
import datetime
import altair as alt
import pydeck as pdk
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Kayakability Dashboard", 
    page_icon="🛶", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        background: linear-gradient(90deg, #1e3a8a, #3b82f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .score-card {
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid #0ea5e9;
        margin: 1rem 0;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
    }
    .status-great { color: #16a34a; font-weight: bold; }
    .status-caution { color: #eab308; font-weight: bold; }
    .status-unsafe { color: #dc2626; font-weight: bold; }
    .info-box {
        background: #f8fafc;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and preprocess the data"""
    try:
        df = pd.read_csv("kayak_conditions.csv")
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        return df
    except FileNotFoundError:
        # Create sample data for demonstration
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        np.random.seed(42)
        sample_data = {
            "timestamp": dates,
            "site_name": ["Merrimack River - Lowell"] * len(dates),
            "discharge_cfs": np.random.normal(2000, 500, len(dates)).clip(500, 5000),
            "gage_height_ft": np.random.normal(8, 2, len(dates)).clip(3, 15),
            "lat": [42.6334] * len(dates),
            "lon": [-71.3162] * len(dates),
        }
        df = pd.DataFrame(sample_data)
        df["kayakability_score"] = (100 - (df["discharge_cfs"] - 1500).abs() / 50).clip(0, 100)
        return df

def get_score_color_info(score):
    """Return color and status based on score"""
    if score >= 80:
        return "🟢", "Great", "status-great", "#16a34a"
    elif score >= 50:
        return "🟡", "Caution", "status-caution", "#eab308"
    else:
        return "🔴", "Unsafe", "status-unsafe", "#dc2626"

def create_trend_chart(df, days=30):
    """Create trend chart using Altair"""
    recent_data = df.tail(days).reset_index(drop=True)
    
    # Score trend chart
    score_chart = alt.Chart(recent_data).mark_line(
        point=True, 
        strokeWidth=3,
        stroke='#3b82f6'
    ).encode(
        x=alt.X('timestamp:T', title='Date'),
        y=alt.Y('kayakability_score:Q', title='Kayakability Score', scale=alt.Scale(domain=[0, 100])),
        tooltip=['timestamp:T', 'kayakability_score:Q']
    ).properties(
        width='container',
        height=200,
        title='Kayakability Score Trend'
    )
    
    return score_chart

def create_discharge_chart(df, days=30):
    """Create discharge chart using Altair"""
    recent_data = df.tail(days).reset_index(drop=True)
    
    discharge_chart = alt.Chart(recent_data).mark_area(
        line={'stroke': '#06b6d4', 'strokeWidth': 2},
        color=alt.Gradient(
            gradient='linear',
            stops=[alt.GradientStop(color='#06b6d4', offset=0),
                   alt.GradientStop(color='#e0f7fa', offset=1)],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X('timestamp:T', title='Date'),
        y=alt.Y('discharge_cfs:Q', title='Discharge (CFS)'),
        tooltip=['timestamp:T', 'discharge_cfs:Q', 'gage_height_ft:Q']
    ).properties(
        width='container',
        height=200,
        title='Discharge Trend (CFS)'
    )
    
    return discharge_chart

def create_score_histogram(df):
    """Create score distribution using Altair"""
    hist_chart = alt.Chart(df).mark_bar(
        color='#3b82f6',
        opacity=0.7
    ).encode(
        x=alt.X('kayakability_score:Q', bin=alt.Bin(maxbins=20), title='Kayakability Score'),
        y=alt.Y('count()', title='Frequency'),
        tooltip=['count()']
    ).properties(
        width='container',
        height=300,
        title='Score Distribution (Historical)'
    )
    
    return hist_chart

def create_enhanced_map(latest_data):
    """Create an enhanced 3D map"""
    # Color based on score
    _, _, _, hex_color = get_score_color_info(latest_data['kayakability_score'])
    
    # Convert hex to RGB
    rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
    
    map_data = pd.DataFrame({
        'lat': [latest_data['lat']],
        'lon': [latest_data['lon']],
        'score': [latest_data['kayakability_score']],
        'elevation': [latest_data['kayakability_score'] * 10]  # Scale for 3D effect
    })
    
    view_state = pdk.ViewState(
        latitude=latest_data['lat'],
        longitude=latest_data['lon'],
        zoom=11,
        pitch=45,
        bearing=0
    )
    
    layer = pdk.Layer(
        'ColumnLayer',
        data=map_data,
        get_position='[lon, lat]',
        get_elevation='elevation',
        elevation_scale=4,
        radius=200,
        get_fill_color=list(rgb_color) + [200],
        pickable=True,
        auto_highlight=True,
    )
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "Score: {score}\nSite: Merrimack River"}
    )

# Load data
df = load_data()
latest = df.iloc[-1]

# Header
st.markdown("<h1 class='main-header'>🛶 Kayakability Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.2rem;'>Real-time water conditions for safe kayaking on the Merrimack River</p>", unsafe_allow_html=True)

# Sidebar for controls
with st.sidebar:
    st.markdown("### 🎛️ Dashboard Controls")
    
    # Trend days selector
    trend_days = st.slider("Trend Analysis Days", 7, 90, 30)
    
    # Score threshold
    score_threshold = st.slider("Alert Threshold", 0, 100, 50)
    
    st.markdown("---")
    st.markdown("### 📊 Quick Stats")
    
    avg_score = df['kayakability_score'].mean()
    good_days = len(df[df['kayakability_score'] >= 80])
    caution_days = len(df[(df['kayakability_score'] >= 50) & (df['kayakability_score'] < 80)])
    unsafe_days = len(df[df['kayakability_score'] < 50])
    
    st.metric("Total Records", len(df))
    st.metric("Average Score", f"{avg_score:.1f}")
    st.metric("Great Days", good_days, delta=f"{good_days/len(df)*100:.1f}%")
    st.metric("Caution Days", caution_days)
    st.metric("Unsafe Days", unsafe_days)

# Main content
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Current conditions card
    icon, status, css_class, color = get_score_color_info(latest['kayakability_score'])
    
    st.markdown(f"""
    <div class="score-card">
        <h2 style="margin: 0; color: #1e40af;">Current Conditions</h2>
        <div style="display: flex; align-items: center; margin: 1rem 0;">
            <span style="font-size: 3rem;">{icon}</span>
            <div style="margin-left: 1rem;">
                <h1 style="margin: 0; font-size: 3rem; color: #1e40af;">{latest['kayakability_score']:.0f}</h1>
                <p class="{css_class}" style="margin: 0; font-size: 1.5rem;">{status}</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h4 style="margin: 0; color: #64748b;">💧 Discharge</h4>
        <h2 style="margin: 0.5rem 0 0 0; color: #1e40af;">{latest['discharge_cfs']:.0f}</h2>
        <p style="margin: 0; color: #64748b; font-size: 0.9rem;">cubic feet/sec</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <h4 style="margin: 0; color: #64748b;">📏 Gage Height</h4>
        <h2 style="margin: 0.5rem 0 0 0; color: #1e40af;">{latest['gage_height_ft']:.1f}</h2>
        <p style="margin: 0; color: #64748b; font-size: 0.9rem;">feet</p>
    </div>
    """, unsafe_allow_html=True)

# Site information and alerts
st.markdown("---")
col1, col2 = st.columns([1.5, 1])

with col1:
    st.markdown("### 📍 Location & Status")
    
    # Alert section
    if latest['kayakability_score'] < score_threshold:
        st.error(f"⚠️ **Alert**: Current score ({latest['kayakability_score']:.0f}) is below your threshold ({score_threshold})")
    else:
        st.success(f"✅ **All Good**: Current conditions are above your threshold ({score_threshold})")
    
    # Location info
    st.markdown(f"""
    <div class="info-box">
        <strong>📍 Site:</strong> {latest['site_name']}<br>
        <strong>🗺️ Coordinates:</strong> {latest['lat']:.4f}, {latest['lon']:.4f}<br>
        <strong>🕐 Last Updated:</strong> {latest['timestamp'].strftime('%Y-%m-%d %I:%M %p')}
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("### 🎯 Score Guide")
    st.markdown("""
    <div class="info-box">
        <div style="margin: 0.5rem 0;"><span style="color: #16a34a;">🟢 <strong>80-100:</strong></span> Excellent conditions</div>
        <div style="margin: 0.5rem 0;"><span style="color: #eab308;">🟡 <strong>50-79:</strong></span> Use caution</div>
        <div style="margin: 0.5rem 0;"><span style="color: #dc2626;">🔴 <strong>0-49:</strong></span> Unsafe conditions</div>
    </div>
    """, unsafe_allow_html=True)

# Enhanced map
st.markdown("### 🗺️ Interactive 3D Location Map")
st.pydeck_chart(create_enhanced_map(latest))

# Charts section
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📈 Recent Trends")
    trend_chart = create_trend_chart(df, trend_days)
    st.altair_chart(trend_chart, use_container_width=True)
    
    st.markdown("### 💧 Discharge Pattern")
    discharge_chart = create_discharge_chart(df, trend_days)
    st.altair_chart(discharge_chart, use_container_width=True)

with col2:
    st.markdown("### 📊 Historical Distribution")
    hist_chart = create_score_histogram(df)
    st.altair_chart(hist_chart, use_container_width=True)
    
    # Summary statistics
    st.markdown("### 📋 Summary Stats")
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Min Score", f"{df['kayakability_score'].min():.0f}")
        st.metric("Max Discharge", f"{df['discharge_cfs'].max():.0f} CFS")
    with col_b:
        st.metric("Max Score", f"{df['kayakability_score'].max():.0f}")
        st.metric("Max Height", f"{df['gage_height_ft'].max():.1f} ft")

# Data table (expandable)
with st.expander("📋 View Recent Data"):
    recent_data = df.tail(20)[['timestamp', 'kayakability_score', 'discharge_cfs', 'gage_height_ft']].copy()
    recent_data['timestamp'] = recent_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    recent_data = recent_data.round(2)
    st.dataframe(recent_data, use_container_width=True)

# Footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
    <div style="text-align: center; color: #94a3b8;">
        <p>🛶 <strong>Kayakability Dashboard</strong> 🛶</p>
        <p>Built by Timothy Nolan | Data updated daily at 9AM EST</p>
        <p><small>This dashboard provides real-time water condition assessments for safe kayaking decisions.</small></p>
        <p><small>💡 Tip: Use the sidebar controls to customize your view and set personal alert thresholds</small></p>
    </div>
    """, unsafe_allow_html=True)
