import streamlit as st
import pandas as pd
import datetime
import altair as alt
import pydeck as pdk
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
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

def get_score_color(score):
    """Return color and status based on score"""
    if score >= 80:
        return "🟢", "Great", "status-great"
    elif score >= 50:
        return "🟡", "Caution", "status-caution"
    else:
        return "🔴", "Unsafe", "status-unsafe"

def create_trend_chart(df, days=30):
    """Create an interactive trend chart"""
    recent_data = df.tail(days)
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('Kayakability Score', 'Discharge (CFS)', 'Gage Height (ft)'),
        vertical_spacing=0.08,
        shared_xaxes=True
    )
    
    # Score trend
    fig.add_trace(
        go.Scatter(
            x=recent_data['timestamp'],
            y=recent_data['kayakability_score'],
            mode='lines+markers',
            name='Score',
            line=dict(color='#3b82f6', width=3),
            fill='tonexty'
        ),
        row=1, col=1
    )
    
    # Discharge trend
    fig.add_trace(
        go.Scatter(
            x=recent_data['timestamp'],
            y=recent_data['discharge_cfs'],
            mode='lines+markers',
            name='Discharge',
            line=dict(color='#06b6d4', width=2)
        ),
        row=2, col=1
    )
    
    # Gage height trend
    fig.add_trace(
        go.Scatter(
            x=recent_data['timestamp'],
            y=recent_data['gage_height_ft'],
            mode='lines+markers',
            name='Gage Height',
            line=dict(color='#8b5cf6', width=2)
        ),
        row=3, col=1
    )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title_text="Recent Trends",
        title_x=0.5
    )
    
    return fig

def create_score_distribution(df):
    """Create score distribution chart"""
    fig = px.histogram(
        df, 
        x='kayakability_score',
        nbins=20,
        title='Score Distribution (Historical)',
        color_discrete_sequence=['#3b82f6']
    )
    fig.update_layout(
        xaxis_title="Kayakability Score",
        yaxis_title="Frequency",
        showlegend=False
    )
    return fig

def create_enhanced_map(latest_data):
    """Create an enhanced 3D map"""
    # Color based on score
    _, _, color_class = get_score_color(latest_data['kayakability_score'])
    color = [0, 255, 0] if color_class == "status-great" else [255, 255, 0] if color_class == "status-caution" else [255, 0, 0]
    
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
        get_fill_color=color + [200],
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
    
    # Date range selector
    date_range = st.date_input(
        "Select Date Range",
        value=(df['timestamp'].min().date(), df['timestamp'].max().date()),
        min_value=df['timestamp'].min().date(),
        max_value=df['timestamp'].max().date()
    )
    
    # Trend days selector
    trend_days = st.slider("Trend Analysis Days", 7, 90, 30)
    
    # Score threshold
    score_threshold = st.slider("Alert Threshold", 0, 100, 50)
    
    st.markdown("### 📊 Quick Stats")
    st.metric("Total Records", len(df))
    st.metric("Average Score", f"{df['kayakability_score'].mean():.1f}")
    st.metric("Days Above Threshold", len(df[df['kayakability_score'] >= score_threshold]))

# Main content
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Current conditions card
    icon, status, css_class = get_score_color(latest['kayakability_score'])
    
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
    st.markdown("""
    <div class="metric-card">
        <h4 style="margin: 0; color: #64748b;">Discharge</h4>
        <h2 style="margin: 0; color: #1e40af;">{:.0f} CFS</h2>
    </div>
    """.format(latest['discharge_cfs']), unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div class="metric-card">
        <h4 style="margin: 0; color: #64748b;">Gage Height</h4>
        <h2 style="margin: 0; color: #1e40af;">{:.1f} ft</h2>
    </div>
    """.format(latest['gage_height_ft']), unsafe_allow_html=True)

# Site information
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📍 Location Details")
    st.write(f"**Site:** {latest['site_name']}")
    st.write(f"**Coordinates:** {latest['lat']:.4f}, {latest['lon']:.4f}")
    st.write(f"**Last Updated:** {latest['timestamp'].strftime('%Y-%m-%d %I:%M %p')}")

with col2:
    st.markdown("### 🎯 Score Interpretation")
    st.markdown("""
    - **🟢 80-100:** Excellent conditions, safe for all skill levels
    - **🟡 50-79:** Use caution, suitable for experienced kayakers
    - **🔴 0-49:** Unsafe conditions, avoid kayaking
    """)

# Enhanced map
st.markdown("### 🗺️ Interactive 3D Map")
st.pydeck_chart(create_enhanced_map(latest))

# Charts section
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📈 Trend Analysis")
    trend_chart = create_trend_chart(df, trend_days)
    st.plotly_chart(trend_chart, use_container_width=True)

with col2:
    st.markdown("### 📊 Score Distribution")
    dist_chart = create_score_distribution(df)
    st.plotly_chart(dist_chart, use_container_width=True)

# Data table (expandable)
with st.expander("📋 View Recent Data"):
    st.dataframe(
        df.tail(10)[['timestamp', 'kayakability_score', 'discharge_cfs', 'gage_height_ft']].round(2),
        use_container_width=True
    )

# Alerts section
st.markdown("---")
if latest['kayakability_score'] < score_threshold:
    st.warning(f"⚠️ **Alert**: Current score ({latest['kayakability_score']:.0f}) is below your threshold ({score_threshold})")
else:
    st.success(f"✅ **All Good**: Current conditions are above your threshold ({score_threshold})")

# Footer
st.markdown("---")
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown("""
    <div style="text-align: center; color: #94a3b8;">
        <p>🛶 <strong>Kayakability Dashboard</strong> 🛶</p>
        <p>Built by Timothy Nolan | Data updated daily at 9AM EST</p>
        <p><small>This dashboard provides real-time water condition assessments for safe kayaking decisions.</small></p>
    </div>
    """, unsafe_allow_html=True)
