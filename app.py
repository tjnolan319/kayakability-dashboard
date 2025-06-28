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

# Enhanced CSS for cleaner design
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Global styles */
    .stApp {
        font-family: 'Inter', sans-serif;
    }
    
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Main header */
    .main-header {
        text-align: center;
        background: linear-gradient(135deg, #0f172a, #1e293b, #334155);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1rem;
        font-weight: 400;
        margin-bottom: 2rem;
        opacity: 0.8;
    }
    
    /* Card components */
    .condition-card {
        background: linear-gradient(135deg, #ffffff, #f8fafc);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        height: 100%;
        transition: all 0.3s ease;
    }
    
    .condition-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    .metric-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #f1f5f9;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    
    .metric-card:hover {
        border-color: #cbd5e1;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .weather-card {
        background: linear-gradient(135deg, #fef3c7, #fbbf24);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #f59e0b;
        margin: 1rem 0;
        color: #92400e;
        font-weight: 500;
    }
    
    /* Score styling */
    .score-display {
        text-align: center;
        margin: 1.5rem 0;
    }
    
    .score-number {
        font-size: 3.5rem;
        font-weight: 700;
        margin: 0.5rem 0;
        line-height: 1;
    }
    
    .score-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    
    .score-status {
        font-size: 1.3rem;
        font-weight: 600;
        margin: 0.5rem 0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Status colors */
    .status-excellent { color: #059669; }
    .status-good { color: #16a34a; }
    .status-fair { color: #ca8a04; }
    .status-poor { color: #dc2626; }
    .status-dangerous { color: #991b1b; }
    
    /* Info sections */
    .info-section {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #3b82f6;
        margin: 1rem 0;
    }
    
    .metric-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 0;
        border-bottom: 1px solid #f1f5f9;
    }
    
    .metric-row:last-child {
        border-bottom: none;
    }
    
    .metric-label {
        font-weight: 500;
        color: #475569;
    }
    
    .metric-value {
        font-weight: 600;
        color: #1e293b;
    }
    
    /* Chart containers */
    .chart-container {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin: 1rem 0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    /* Status indicator */
    .status-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
    }
    
    .status-indicator.excellent { background-color: #059669; }
    .status-indicator.good { background-color: #16a34a; }
    .status-indicator.fair { background-color: #ca8a04; }
    .status-indicator.poor { background-color: #dc2626; }
    .status-indicator.dangerous { background-color: #991b1b; }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .main-header {
            font-size: 2rem;
        }
        .score-number {
            font-size: 2.5rem;
        }
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    """Load and preprocess the data from new folder structure"""
    data_folder = "data_exports"
    
    combined_file = os.path.join(data_folder, "combined_data.csv")
    river_file = os.path.join(data_folder, "river_data.csv")
    weather_file = os.path.join(data_folder, "weather_data.csv")
    
    files_available = {
        'combined': os.path.exists(combined_file),
        'river': os.path.exists(river_file),
        'weather': os.path.exists(weather_file),
        'legacy': os.path.exists("kayak_conditions.csv")
    }
    
    try:
        if files_available['combined']:
            df = pd.read_csv(combined_file)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            
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
            df = pd.read_csv(river_file)
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            return df, None, files_available
            
        elif files_available['legacy']:
            df = pd.read_csv("kayak_conditions.csv")
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")
            return df, None, files_available
            
        else:
            raise FileNotFoundError("No data files found")
            
    except Exception as e:
        st.warning(f"Error loading data: {e}. Using sample data.")
        dates = pd.date_range(start="2024-01-01", end="2024-12-31", freq="D")
        np.random.seed(42)
        
        sites = [
            {"id": "01073500", "name": "Merrimack River below Concord River at Lowell, MA", "lat": 42.6334, "lon": -71.3162},
            {"id": "01100000", "name": "Merrimack River at Lowell, MA", "lat": 42.65, "lon": -71.30},
            {"id": "01096500", "name": "Merrimack River at North Chelmsford, MA", "lat": 42.6278, "lon": -71.3667}
        ]
        
        all_data = []
        for site in sites:
            for date in dates[::7]:
                discharge = np.random.normal(1500, 400)
                gage_height = np.random.normal(3.5, 1)
                
                all_data.append({
                    "timestamp": date,
                    "site_id": site["id"],
                    "site_name": site["name"],
                    "discharge_cfs": max(300, discharge),
                    "gage_height_ft": max(1, gage_height),
                    "lat": site["lat"],
                    "lon": site["lon"],
                    "temperature_f": np.random.normal(65, 15),
                    "humidity_percent": np.random.normal(60, 20),
                    "wind_speed_mph": np.random.normal(8, 4),
                    "weather_description": np.random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Light Rain"]),
                    "weather_timestamp": date
                })
        
        df = pd.DataFrame(all_data)
        # Apply enhanced scoring after creating the dataframe
        df['kayakability_score'] = df.apply(calculate_enhanced_kayakability_score, axis=1)
        files_available = {'sample': True}
        return df, None, files_available

def calculate_enhanced_kayakability_score(row):
    """
    Enhanced kayakability scoring algorithm
    Considers multiple factors with weighted importance
    """
    discharge = row.get('discharge_cfs', 1000)
    gage_height = row.get('gage_height_ft', 3.0)
    wind_speed = row.get('wind_speed_mph', 5)
    temp = row.get('temperature_f', 65)
    
    # Optimal ranges for kayaking
    optimal_discharge_min = 800
    optimal_discharge_max = 2500
    optimal_gage_min = 2.5
    optimal_gage_max = 5.0
    max_safe_wind = 15
    comfortable_temp_min = 50
    comfortable_temp_max = 85
    
    # Calculate individual factor scores (0-100)
    
    # Discharge score (40% weight)
    if optimal_discharge_min <= discharge <= optimal_discharge_max:
        discharge_score = 100
    elif discharge < optimal_discharge_min:
        # Too low - exponential penalty
        discharge_score = max(0, 100 * (discharge / optimal_discharge_min) ** 1.5)
    else:
        # Too high - steeper penalty for safety
        excess_ratio = (discharge - optimal_discharge_max) / optimal_discharge_max
        discharge_score = max(0, 100 * np.exp(-2 * excess_ratio))
    
    # Gage height score (30% weight)
    if optimal_gage_min <= gage_height <= optimal_gage_max:
        gage_score = 100
    elif gage_height < optimal_gage_min:
        gage_score = max(0, 100 * (gage_height / optimal_gage_min) ** 2)
    else:
        excess_ratio = (gage_height - optimal_gage_max) / optimal_gage_max
        gage_score = max(0, 100 * np.exp(-1.5 * excess_ratio))
    
    # Wind score (20% weight)
    if wind_speed <= max_safe_wind:
        wind_score = max(0, 100 - (wind_speed / max_safe_wind * 30))
    else:
        # Dangerous wind conditions
        wind_score = max(0, 20 - (wind_speed - max_safe_wind) * 5)
    
    # Temperature score (10% weight)
    if comfortable_temp_min <= temp <= comfortable_temp_max:
        temp_score = 100
    elif temp < comfortable_temp_min:
        temp_score = max(0, 100 - (comfortable_temp_min - temp) * 2)
    else:
        temp_score = max(0, 100 - (temp - comfortable_temp_max) * 1.5)
    
    # Calculate weighted final score
    final_score = (
        discharge_score * 0.40 +
        gage_score * 0.30 +
        wind_score * 0.20 +
        temp_score * 0.10
    )
    
    return min(100, max(0, final_score))

def get_enhanced_score_info(score):
    """Enhanced scoring system with 5 levels"""
    if pd.isna(score):
        return "❓", "Unknown", "status-fair", "#64748b", "unknown"
    elif score >= 85:
        return "🟢", "Excellent", "status-excellent", "#059669", "excellent"
    elif score >= 70:
        return "🔵", "Good", "status-good", "#16a34a", "good"
    elif score >= 50:
        return "🟡", "Fair", "status-fair", "#ca8a04", "fair"
    elif score >= 25:
        return "🟠", "Poor", "status-poor", "#dc2626", "poor"
    else:
        return "🔴", "Dangerous", "status-dangerous", "#991b1b", "dangerous"

def get_score_description(score):
    """Get detailed description for each score range"""
    if pd.isna(score):
        return "Conditions unknown - exercise caution"
    elif score >= 85:
        return "Perfect conditions for kayaking. Enjoy your paddle!"
    elif score >= 70:
        return "Good conditions with minor considerations. Safe for most paddlers."
    elif score >= 50:
        return "Fair conditions. Suitable for experienced paddlers only."
    elif score >= 25:
        return "Poor conditions. High risk - advanced paddlers only."
    else:
        return "Dangerous conditions. Do not kayak - safety risk is too high."

def create_enhanced_map(df):
    """Create an enhanced map visualization"""
    if 'site_id' in df.columns:
        latest_by_site = df.groupby('site_id').last().reset_index()
    else:
        latest_by_site = df.tail(1).copy()
    
    colors = []
    for _, row in latest_by_site.iterrows():
        _, _, _, hex_color, _ = get_enhanced_score_info(row.get('kayakability_score', 50))
        rgb_color = tuple(int(hex_color[i:i+2], 16) for i in (1, 3, 5))
        colors.append(list(rgb_color) + [220])
    
    latest_by_site['color'] = colors
    
    center_lat = latest_by_site['lat'].mean()
    center_lon = latest_by_site['lon'].mean()
    
    view_state = pdk.ViewState(
        latitude=center_lat,
        longitude=center_lon,
        zoom=10,
        pitch=0,
    )
    
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=latest_by_site,
        get_position='[lon, lat]',
        get_color='color',
        get_radius=500,
        pickable=True,
        auto_highlight=True,
    )
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip={
            "html": "<b>{site_name}</b><br/><b>Score:</b> {kayakability_score:.0f}<br/><b>Discharge:</b> {discharge_cfs:.0f} CFS<br/><b>Height:</b> {gage_height_ft:.1f} ft",
            "style": {"backgroundColor": "#1e293b", "color": "white", "fontSize": "14px", "borderRadius": "8px"}
        }
    )

def create_modern_trend_chart(df, days=30):
    """Create modern trend chart with better styling"""
    recent_data = df.tail(days).reset_index(drop=True)
    
    base_chart = alt.Chart(recent_data).add_selection(
        alt.selection_interval(bind='scales')
    )
    
    if 'site_id' in df.columns and len(df['site_id'].unique()) > 1:
        line_chart = base_chart.mark_line(
            strokeWidth=3,
            point=alt.OverlayMarkDef(size=80, filled=True)
        ).encode(
            x=alt.X('timestamp:T', title='Date', axis=alt.Axis(grid=True)),
            y=alt.Y('kayakability_score:Q', title='Kayakability Score', scale=alt.Scale(domain=[0, 100])),
            color=alt.Color('site_id:N', 
                          title='Site ID',
                          scale=alt.Scale(scheme='category10')),
            tooltip=['timestamp:T', 'kayakability_score:Q', 'site_name:N', 'discharge_cfs:Q']
        )
    else:
        line_chart = base_chart.mark_line(
            strokeWidth=4,
            stroke='#3b82f6',
            point=alt.OverlayMarkDef(size=100, filled=True, stroke='white', strokeWidth=2)
        ).encode(
            x=alt.X('timestamp:T', title='Date', axis=alt.Axis(grid=True)),
            y=alt.Y('kayakability_score:Q', title='Kayakability Score', scale=alt.Scale(domain=[0, 100])),
            tooltip=['timestamp:T', 'kayakability_score:Q', 'discharge_cfs:Q', 'gage_height_ft:Q']
        )
    
    # Add reference lines for score thresholds
    rules = alt.Chart(pd.DataFrame({
        'score': [85, 70, 50, 25],
        'label': ['Excellent', 'Good', 'Fair', 'Poor']
    })).mark_rule(
        strokeDash=[5, 5],
        opacity=0.5
    ).encode(
        y='score:Q',
        color=alt.value('#64748b')
    )
    
    return (line_chart + rules).properties(
        width='container',
        height=300,
        title=alt.TitleParams(
            text='Kayakability Score Trend',
            fontSize=16,
            fontWeight='bold'
        )
    ).resolve_scale(
        color='independent'
    )

def create_discharge_area_chart(df, days=30):
    """Create modern area chart for discharge"""
    recent_data = df.tail(days).reset_index(drop=True)
    
    if 'site_id' in df.columns and len(df['site_id'].unique()) > 1:
        chart = alt.Chart(recent_data).mark_line(
            strokeWidth=2
        ).encode(
            x=alt.X('timestamp:T', title='Date'),
            y=alt.Y('discharge_cfs:Q', title='Discharge (CFS)'),
            color=alt.Color('site_id:N', title='Site ID'),
            tooltip=['timestamp:T', 'discharge_cfs:Q', 'site_name:N']
        )
    else:
        chart = alt.Chart(recent_data).mark_area(
            line={'stroke': '#06b6d4', 'strokeWidth': 3},
            color=alt.Gradient(
                gradient='linear',
                stops=[
                    alt.GradientStop(color='#06b6d4', offset=0.3),
                    alt.GradientStop(color='#67e8f9', offset=0.7),
                    alt.GradientStop(color='#cffafe', offset=1)
                ],
                x1=1, x2=1, y1=1, y2=0
            ),
            opacity=0.8
        ).encode(
            x=alt.X('timestamp:T', title='Date'),
            y=alt.Y('discharge_cfs:Q', title='Discharge (CFS)'),
            tooltip=['timestamp:T', 'discharge_cfs:Q', 'gage_height_ft:Q']
        )
    
    return chart.properties(
        width='container',
        height=250,
        title=alt.TitleParams(
            text='Water Discharge Trend',
            fontSize=16,
            fontWeight='bold'
        )
    )

def format_weather_display(row):
    """Format weather information for display"""
    if pd.isna(row.get('weather_description')):
        return "Weather data not available"
    
    temp = f"{row.get('temperature_f', 0):.0f}°F" if pd.notna(row.get('temperature_f')) else 'N/A'
    humidity = f"{row.get('humidity_percent', 0):.0f}%" if pd.notna(row.get('humidity_percent')) else 'N/A'
    wind = f"{row.get('wind_speed_mph', 0):.0f} mph" if pd.notna(row.get('wind_speed_mph')) else 'N/A'
    
    return {
        'description': row.get('weather_description', 'N/A'),
        'temperature': temp,
        'humidity': humidity,
        'wind': wind
    }

# Load data
df, weather_df, files_info = load_data()

# Apply enhanced scoring if not already present
if 'kayakability_score' not in df.columns or df['kayakability_score'].isna().all():
    df['kayakability_score'] = df.apply(calculate_enhanced_kayakability_score, axis=1)

# Header
st.markdown("<h1 class='main-header'>🛶 Kayakability Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Real-time water conditions and safety assessment for the Merrimack River</p>", unsafe_allow_html=True)

# Data source indicator (more subtle)
if files_info.get('sample'):
    st.info("📊 Currently displaying sample data for demonstration")
elif files_info.get('combined'):
    st.success("✅ Connected to live data feed")

# Determine best conditions
if 'site_id' in df.columns and len(df['site_id'].unique()) > 1:
    latest_by_site = df.groupby('site_id').last().reset_index()
    best_site = latest_by_site.loc[latest_by_site['kayakability_score'].idxmax()]
    latest = best_site
    is_multi_site = True
else:
    latest = df.iloc[-1]
    is_multi_site = False

# Main layout
col1, col2 = st.columns([2, 1], gap="large")

with col1:
    st.markdown("### 🗺️ Monitoring Locations")
    map_chart = create_enhanced_map(df)
    st.pydeck_chart(map_chart, use_container_width=True)

with col2:
    # Enhanced current conditions card
    icon, status, css_class, color, status_class = get_enhanced_score_info(latest.get('kayakability_score'))
    score_description = get_score_description(latest.get('kayakability_score'))
    
    site_name = latest.get('site_name', 'Unknown Site')
    display_name = site_name.split(' at ')[-1] if ' at ' in str(site_name) else site_name
    
    if pd.notna(latest.get('timestamp')):
        timestamp_text = latest['timestamp'].strftime('%m/%d %I:%M %p')
    else:
        timestamp_text = 'N/A'
    
    # Create the HTML content
    conditions_html = f"""
    <div class="condition-card">
        <h3 style="margin: 0 0 1rem 0; color: #1e293b; font-weight: 600;">
            {'🏆 Best Conditions' if is_multi_site else '📍 Current Conditions'}
        </h3>
        
        <div class="score-display">
            <div class="score-icon">{icon}</div>
            <div class="score-number" style="color: {color};">{latest.get('kayakability_score', 0):.0f}</div>
            <div class="score-status {css_class}">{status}</div>
        </div>
        
        <div style="background: #f8fafc; padding: 1rem; border-radius: 8px; margin: 1rem 0;">
            <p style="margin: 0; font-size: 0.9rem; color: #475569; line-height: 1.4;">
                {score_description}
            </p>
        </div>
        
        <div style="font-size: 0.9rem; color: #64748b;">
            <div class="metric-row">
                <span class="metric-label">Location</span>
                <span class="metric-value">{display_name}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Discharge</span>
                <span class="metric-value">{latest.get('discharge_cfs', 0):.0f} CFS</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Gage Height</span>  
                <span class="metric-value">{latest.get('gage_height_ft', 0):.1f} ft</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Last Updated</span>
                <span class="metric-value">{timestamp_text}</span>
            </div>
        </div>
    </div>
    """
    
    # Display the HTML
    st.markdown(conditions_html, unsafe_allow_html=True)

# Weather section
if 'weather_description' in df.columns and pd.notna(latest.get('weather_description')):
    st.markdown("### 🌤️ Weather Conditions")
    weather = format_weather_display(latest)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Conditions", weather['description'])
    with col2:
        st.metric("Temperature", weather['temperature'])
    with col3:
        st.metric("Wind Speed", weather['wind'])
    with col4:
        st.metric("Humidity", weather['humidity'])

# Charts section
st.markdown("---")
st.markdown("### 📈 Historical Trends")

col1, col2 = st.columns(2, gap="large")

with col1:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    trend_chart = create_modern_trend_chart(df)
    st.altair_chart(trend_chart, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    discharge_chart = create_discharge_area_chart(df)
    st.altair_chart(discharge_chart, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Footer info
st.markdown("---")
st.markdown("""
<div class="info-section">
    <h4 style="margin: 0 0 1rem 0; color: #1e293b;">📋 Scoring Methodology</h4>
    <p style="margin: 0; color: #475569; line-height: 1.5;">
        Our enhanced kayakability score considers discharge flow (40%), water level (30%), wind conditions (20%), 
        and temperature (10%) to provide a comprehensive safety assessment from 0-100.
    </p>
</div>
""", unsafe_allow_html=True)
