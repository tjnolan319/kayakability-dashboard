import streamlit as st
import pandas as pd
import datetime
import altair as alt
import pydeck as pdk
import numpy as np
import os

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
    .weather-card {
        background: linear-gradient(135deg, #fff7ed, #fed7aa);
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #f97316;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and preprocess the data from new folder structure"""
    data_folder = "data_exports"
    
    # Try to load from new structure first
    combined_file = os.path.join(data_folder, "combined_data.csv")
    river_file = os.path.join(data_folder, "river_data.csv")
    weather_file = os.path.join(data_folder, "weather_data.csv")
    
    # Check what files exist
    files_available = {
        'combined': os.path.exists(combined_file),
        'river': os.path.exists(river_file),
        'weather': os.path.exists(weather_file),
        'legacy': os.path.exists("kayak_conditions.csv")
    }
    
    try:
        if files_available['combined']:
            # Load combined data (preferred)
            df = pd.read_csv(combined_file)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
            # Also try to load weather data separately for more detailed weather info
            weather_df = None
            if files_available['weather']:
                try:
                    weather_df = pd.read_csv(weather_file)
                    weather_df["weather_timestamp"] = pd.to_datetime(weather_df["weather_timestamp"])
                except Exception as e:
                    st.warning(f"Could not load weather data: {e}")
            
            df = df.sort_values("timestamp")
            return df, weather_df, files_available
            
        elif files_available['river']:
            # Load river data only
            df = pd.read_csv(river_file)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            return df, None, files_available
            
        elif files_available['legacy']:
            # Fall back to legacy file
            df = pd.read_csv("kayak_conditions.csv")
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            return df, None, files_available
            
        else:
            # No data files found, create sample data
            raise FileNotFoundError("No data files found")
            
    except Exception as e:
        st.warning(f"Error loading data: {e}. Using sample data.")
        # Create sample data for demonstration
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        np.random.seed(42)
        
        # Create data for multiple sites
        sites = [
            {"id": "01073500", "name": "Merrimack River below Concord River at Lowell, MA", "lat": 42.6334, "lon": -71.3162},
            {"id": "01100000", "name": "Merrimack River at Lowell, MA", "lat": 42.65, "lon": -71.30},
            {"id": "01096500", "name": "Merrimack River at North Chelmsford, MA", "lat": 42.6278, "lon": -71.3667}
        ]
        
        all_data = []
        for site in sites:
            for date in dates[::7]:  # Weekly data for sample
                discharge = np.random.normal(1500, 400)
                gage_height = np.random.normal(3.5, 1)
                score = max(0, min(100, 100 - abs(discharge - 1500) / 20))
                
                all_data.append({
                    "timestamp": date,
                    "site_id": site["id"],
                    "site_name": site["name"],
                    "discharge_cfs": max(300, discharge),
                    "gage_height_ft": max(1, gage_height),
                    "lat": site["lat"],
                    "lon": site["lon"],
                    "kayakability_score": score,
                    "temperature_f": np.random.normal(65, 15),
                    "humidity_percent": np.random.normal(60, 20),
                    "wind_speed_mph": np.random.normal(8, 4),
                    "weather_description": np.random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Light Rain"]),
                    "weather_timestamp": date
                })
        
        df = pd.DataFrame(all_data)
        files_available = {'sample': True}
        return df, None, files_available

def get_score_color_info(score):
    """Return color and status based on score"""
    if pd.isna(score):
        return "❓", "Unknown", "status-caution", "#64748b"
    elif score >= 80:
        return "🟢", "Great", "status-great", "#16a34a"
    elif score >= 50:
        return "🟡", "Caution", "status-caution", "#eab308"
    else:
        return "🔴", "Unsafe", "status-unsafe", "#dc2626"

def create_multi_site_map(df):
    """Create a map showing all sites"""
    # Get the latest data for each site
    if 'site_id' in df.columns:
        latest_by_site = df.groupby('site_id').last().reset_index()
    else:
        latest_by_site = df.tail(1).copy()
    
    # Add color information for each site
    colors = []
    for _, row in latest_by_site.iterrows():
        _, _, _, hex_color = get_score_color_info(row.get('kayakability_score', 50))
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
    
    if 'site_id' in df.columns and len(df['site_id'].unique()) > 1:
        # Multi-site chart
        score_chart = alt.Chart(recent_data).mark_line(
            point=True, 
            strokeWidth=2
        ).encode(
            x=alt.X('timestamp:T', title='Date'),
            y=alt.Y('kayakability_score:Q', title='Kayakability Score', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('site_id:N', title='Site ID'),
            tooltip=['timestamp:T', 'kayakability_score:Q', 'site_id:N', 'site_name:N']
        ).properties(
            width='container',
            height=250,
            title='Kayakability Score Trend by Site'
        )
    else:
        # Single site chart
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
    
    if 'site_id' in df.columns and len(df['site_id'].unique()) > 1:
        # Multi-site chart
        discharge_chart = alt.Chart(recent_data).mark_line(
            strokeWidth=2
        ).encode(
            x=alt.X('timestamp:T', title='Date'),
            y=alt.Y('discharge_cfs:Q', title='Discharge (CFS)'),
            color=alt.Color('site_id:N', title='Site ID'),
            tooltip=['timestamp:T', 'discharge_cfs:Q', 'site_id:N']
        ).properties(
            width='container',
            height=250,
            title='Discharge Trend by Site (CFS)'
        )
    else:
        # Single site chart
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

def format_weather_info(row):
    """Format weather information for display"""
    if pd.isna(row.get('weather_description')):
        return "Weather data not available"
    
    temp = f"{row.get('temperature_f', 'N/A'):.0f}°F" if pd.notna(row.get('temperature_f')) else 'N/A'
    humidity = f"{row.get('humidity_percent', 'N/A'):.0f}%" if pd.notna(row.get('humidity_percent')) else 'N/A'
    wind = f"{row.get('wind_speed_mph', 'N/A'):.0f} mph" if pd.notna(row.get('wind_speed_mph')) else 'N/A'
    
    return f"{row.get('weather_description', 'N/A')}, {temp}, {humidity} humidity, {wind} wind"

# Load data
df, weather_df, files_info = load_data()

# Header with data source info
st.markdown("<h1 class='main-header'>🛶 Kayakability Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #64748b; font-size: 1.2rem;'>Real-time water conditions for safe kayaking on the Merrimack River</p>", unsafe_allow_html=True)

# Show data source status
if files_info.get('sample'):
    st.info("📋 Currently showing sample data. Upload your data files to see real conditions.")
elif files_info.get('combined'):
    st.success("✅ Loading from combined data export")
elif files_info.get('river'):
    st.warning("⚠️ Loading river data only (weather data not available)")
else:
    st.info("📁 Loading from legacy data file")

st.markdown("---")

# Handle multiple sites
if 'site_id' in df.columns and len(df['site_id'].unique()) > 1:
    # Multi-site data
    latest_by_site = df.groupby('site_id').last().reset_index()
    best_site = latest_by_site.loc[latest_by_site['kayakability_score'].idxmax()]
    latest = best_site
    is_multi_site = True
else:
    # Single site data (backward compatibility)
    latest = df.iloc[-1]
    is_multi_site = False

# Top section: Map (3/4) + Current Conditions (1/4)
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown("### 🗺️ Merrimack River Monitoring Sites")
    map_chart = create_multi_site_map(df)
    st.pydeck_chart(map_chart)

with col2:
    # Current conditions summary - show best site
    icon, status, css_class, color = get_score_color_info(latest.get('kayakability_score'))
    
    # Format values safely
    discharge_text = f"{latest.get('discharge_cfs', 0):.0f}" if pd.notna(latest.get('discharge_cfs')) else 'N/A'
    gage_height_text = f"{latest.get('gage_height_ft', 0):.1f}" if pd.notna(latest.get('gage_height_ft')) else 'N/A'
    
    if pd.notna(latest.get('timestamp')):
        if isinstance(latest['timestamp'], str):
            timestamp_text = pd.to_datetime(latest['timestamp']).strftime('%m/%d %I:%M %p')
        else:
            timestamp_text = latest['timestamp'].strftime('%m/%d %I:%M %p')
    else:
        timestamp_text = 'N/A'
    
    site_name = latest.get('site_name', 'Unknown Site')
    display_name = site_name.split(' at ')[-1] if ' at ' in str(site_name) else site_name
    
    st.markdown(f"""
    <div class="current-conditions">
        <h3 style="margin: 0 0 1rem 0; color: #1e40af;">{'Best Conditions' if is_multi_site else 'Current Conditions'}</h3>
        <div style="text-align: center; margin-bottom: 1rem;">
            <span style="font-size: 2.5rem;">{icon}</span>
            <h2 style="margin: 0.5rem 0; color: #1e40af;">{latest.get('kayakability_score', 0):.0f}</h2>
            <p class="{css_class}" style="margin: 0; font-size: 1.2rem;">{status}</p>
        </div>
        <div style="font-size: 0.85rem; color: #64748b;">
            <p><strong>Site:</strong> {display_name}</p>
            <p><strong>Discharge:</strong> {discharge_text} CFS</p>
            <p><strong
