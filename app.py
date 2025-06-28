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
    initial_sidebar_state="collapsed"
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
    .current-conditions {
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        padding: 1.5rem;
        border-radius: 15px;
        border: 2px solid #0ea5e9;
        margin: 1rem 0;
        height: 100%;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid #3b82f6;
        margin-bottom: 0.5rem;
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
    .compact-guide {
        background: #f8fafc;
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #3b82f6;
        font-size: 0.9rem;
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
            "site_id": ["01073500"] * len(dates),
            "site_name": ["Merrimack River below Concord River at Lowell, MA"] * len(dates),
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

def create_multi_site_map(df):
    """Create a map showing all sites"""
    # Get the latest data for each site
    latest_by_site = df.groupby('site_id').last().reset_index()
    
    # Add color information for each site
    colors = []
    for _, row in latest_by_site.iterrows():
        _, _, _, hex_color = get_score_color_info(row['kayakability_score'])
        rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
        colors.append(list(rgb_color) + [200])
    
    latest_by_site['color'] = colors
    
    # Create map centered on Merrimack River
    center_lat = latest_by_site['lat'].mean()
    center_lon = latest_by_site['lon'].mean()
    
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=9,
        pitch=0,
    )
    
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=latest_by_site,
        get_position='[lon, lat]',
        get_color='color',
        get_radius=400,
        pickable=True,
        auto_highlight=True,
    )
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{site_name}</b><br/><b>Score:</b> {kayakability_score}<br/><b>Discharge:</b> {discharge_cfs} CFS<br/><b>Height:</b> {gage_height_ft} ft",
            "style": {"backgroundColor": "steelblue", "color": "white"}
        }
    )

def create_trend_chart(df, days=30):
    """Create trend chart using Altair"""
    recent_data = df.tail(days).reset_index(drop=True)
    
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
        height=250,
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
        height=250,
        title='Discharge Trend (CFS)'
    )
    
    return discharge_chart

# Load data
df = load_data()

# Handle multiple sites
if 'site_id' in df.columns:
    # Multi-site data
    latest_by_site = df.groupby('site_id').last().reset_index()
    best_site = latest_by_site.loc[latest_by_site['kayakability_score'].idxmax()]
    latest = best_site
else:
    # Single site data (backward compatibility)
    latest = df.iloc[-1]

# Header
st.markdown("<h1 class='main-header'>🛶 Kayakability Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.2rem;'>Real-time water conditions for safe kayaking on the Merrimack River</p>", unsafe_allow_html=True)
st.markdown("---")

# Top section: Map (3/4) + Current Conditions (1/4)
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### 🗺️ Merrimack River Monitoring Sites")
    if 'site_id' in df.columns:
        map_chart = create_multi_site_map(df)
    else:
        map_chart = create_simple_map(latest)
    selected_point = st.pydeck_chart(map_chart, on_select="rerun")

with col2:
    # Current conditions summary - show best site
    icon, status, css_class, color = get_score_color_info(latest['kayakability_score'])
    
    st.markdown(f"""
    <div class="current-conditions">
        <h3 style="margin: 0 0 1rem 0; color: #1e40af;">Best Conditions</h3>
        <div style="text-align: center; margin-bottom: 1rem;">
            <span style="font-size: 2.5rem;">{icon}</span>
            <h2 style="margin: 0.5rem 0; color: #1e40af;">{latest['kayakability_score']:.0f}</h2>
            <p class="{css_class}" style="margin: 0; font-size: 1.2rem;">{status}</p>
        </div>
        <div style="font-size: 0.85rem; color: #64748b;">
            <p><strong>Site:</strong> {latest['site_name'].split(' at ')[-1] if ' at ' in str(latest['site_name']) else latest['site_name']}</p>
            <p><strong>Discharge:</strong> {latest['discharge_cfs']:.0f if pd.notna(latest['discharge_cfs']) else 'N/A'} CFS</p>
            <p><strong>Gage Height:</strong> {latest['gage_height_ft']:.1f if pd.notna(latest['gage_height_ft']) else 'N/A'} ft</p>
            <p><strong>Updated:</strong> {latest['timestamp'].strftime('%m/%d %I:%M %p') if pd.notna(latest['timestamp']) else 'N/A'}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Location & Status section
st.markdown("---")
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 📍 Location & Status")
    
    # Site information
    site_display_name = latest['site_name'].replace("Merrimack River ", "").replace(" at ", " - ") if pd.notna(latest['site_name']) else "Unknown Site"
    
    st.markdown(f"""
    <div class="info-box">
        <strong>Site:</strong> {site_display_name}<br>
        <strong>Site ID:</strong> {latest.get('site_id', 'N/A')}<br>
        <strong>Coordinates:</strong> {latest['lat']:.4f}, {latest['lon']:.4f}<br>
        <strong>Last Updated:</strong> {latest['timestamp'].strftime('%Y-%m-%d %I:%M %p') if pd.notna(latest['timestamp']) else 'N/A'}
    </div>
    """, unsafe_allow_html=True)
    
    # Conditions interpretation
    if latest['kayakability_score'] >= 80:
        st.success("✅ **Excellent conditions** - Perfect for kayaking! Water levels are ideal for paddlers of all skill levels.")
    elif latest['kayakability_score'] >= 50:
        st.warning("⚠️ **Use caution** - Conditions are manageable but may be challenging. Recommended for experienced kayakers only.")
    else:
        st.error("🚫 **Unsafe conditions** - Water levels are dangerous for kayaking. Please avoid the water until conditions improve.")

with col2:
    st.markdown("### 🎯 Score Guide")
    st.markdown("""
    <div class="compact-guide">
        <strong style="color: #16a34a;">🟢 80-100:</strong> Excellent<br>
        <strong style="color: #eab308;">🟡 50-79:</strong> Caution<br>
        <strong style="color: #dc2626;">🔴 0-49:</strong> Unsafe
    </div>
    """, unsafe_allow_html=True)

# Charts section
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📈 Score Trend (Last 30 Days)")
    trend_chart = create_trend_chart(df, 30)
    st.altair_chart(trend_chart, use_container_width=True)

with col2:
    st.markdown("### 💧 Discharge Pattern (Last 30 Days)")
    discharge_chart = create_discharge_chart(df, 30)
    st.altair_chart(discharge_chart, use_container_width=True)

# Quick stats
st.markdown("---")
if 'site_id' in df.columns:
    st.markdown("### 📊 All Sites Overview")
    
    # Create columns for each site
    sites = df['site_id'].unique()
    cols = st.columns(min(len(sites), 4))
    
    for i, site_id in enumerate(sites):
        site_data = df[df['site_id'] == site_id].iloc[-1]
        icon, status, css_class, color = get_score_color_info(site_data['kayakability_score'])
        
        with cols[i % 4]:
            site_short_name = site_data['site_name'].split(' at ')[-1] if ' at ' in str(site_data['site_name']) else site_data['site_name']
            st.markdown(f"""
            <div class="metric-card" style="text-align: center;">
                <h4 style="margin: 0; color: #64748b; font-size: 0.8rem;">{site_short_name}</h4>
                <div style="font-size: 1.5rem; margin: 0.5rem 0;">{icon}</div>
                <h3 style="margin: 0; color: #1e40af;">{site_data['kayakability_score']:.0f}</h3>
                <p class="{css_class}" style="margin: 0; font-size: 0.9rem;">{status}</p>
            </div>
            """, unsafe_allow_html=True)
else:
    st.markdown("### 📊 Quick Statistics")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        avg_score = df['kayakability_score'].mean()
        st.metric("Average Score", f"{avg_score:.1f}")

    with col2:
        good_days = len(df[df['kayakability_score'] >= 80])
        st.metric("Great Days", good_days, delta=f"{good_days/len(df)*100:.0f}%")

    with col3:
        max_discharge = df['discharge_cfs'].max()
        st.metric("Max Discharge", f"{max_discharge:.0f} CFS")

    with col4:
        recent_avg = df.tail(7)['kayakability_score'].mean()
        overall_avg = df['kayakability_score'].mean()
        delta = recent_avg - overall_avg
        st.metric("7-Day Average", f"{recent_avg:.1f}", delta=f"{delta:+.1f}")

# Data table (expandable)
with st.expander("📋 View Recent Data"):
    recent_data = df.tail(10)[['timestamp', 'kayakability_score', 'discharge_cfs', 'gage_height_ft']].copy()
    recent_data['timestamp'] = recent_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
    recent_data = recent_data.round(1)
    st.dataframe(recent_data, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #94a3b8; padding: 1rem;">
    <p><strong>🛶 Kayakability Dashboard</strong> | Built by Timothy Nolan</p>
    <p><small>Data updated daily at 9AM EST • Click the map marker for detailed conditions</small></p>
</div>
""", unsafe_allow_html=True)
