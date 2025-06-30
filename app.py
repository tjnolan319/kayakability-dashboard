import streamlit as st
import pandas as pd
import datetime
import altair as alt
import pydeck as pdk
import numpy as np
import os
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Kayakability Forecast Dashboard", 
    page_icon="🛶", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS for modern forecasting design
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
    .forecast-card {
        background: linear-gradient(135deg, #ffffff, #f8fafc);
        padding: 2rem;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        height: 100%;
        transition: all 0.3s ease;
        margin-bottom: 1rem;
    }
    
    .forecast-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    
    .window-card {
        background: linear-gradient(135deg, #ecfdf5, #d1fae5);
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #10b981;
        margin: 0.5rem 0;
        transition: all 0.2s ease;
    }
    
    .window-card:hover {
        background: linear-gradient(135deg, #d1fae5, #a7f3d0);
        transform: translateY(-1px);
    }
    
    .window-card.excellent {
        background: linear-gradient(135deg, #ecfdf5, #d1fae5);
        border-color: #059669;
    }
    
    .window-card.good {
        background: linear-gradient(135deg, #f0f9ff, #dbeafe);
        border-color: #3b82f6;
    }
    
    .window-card.fair {
        background: linear-gradient(135deg, #fefce8, #fef3c7);
        border-color: #f59e0b;
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
    
    /* Forecast timeline */
    .timeline-container {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin: 1rem 0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
    }
    
    .timeline-item {
        display: flex;
        align-items: center;
        padding: 1rem;
        border-left: 4px solid #e2e8f0;
        margin: 0.5rem 0;
        background: #f8fafc;
        border-radius: 0 8px 8px 0;
    }
    
    .timeline-item.excellent {
        border-left-color: #059669;
        background: linear-gradient(90deg, #ecfdf5, #f8fafc);
    }
    
    .timeline-item.good {
        border-left-color: #3b82f6;
        background: linear-gradient(90deg, #eff6ff, #f8fafc);
    }
    
    .timeline-item.fair {
        border-left-color: #f59e0b;
        background: linear-gradient(90deg, #fefce8, #f8fafc);
    }
    
    /* Metric styling */
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
    
    /* Alert styling */
    .alert {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        font-weight: 500;
    }
    
    .alert.success {
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #10b981;
    }
    
    .alert.warning {
        background: #fefce8;
        color: #92400e;
        border: 1px solid #f59e0b;
    }
    
    .alert.info {
        background: #eff6ff;
        color: #1e40af;
        border: 1px solid #3b82f6;
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
def load_forecast_data():
    """Load historical and forecast data from the new system"""
    data_files = {
        'historical': 'historical_hourly_data.csv',
        'forecast': 'forecast_data.csv',
        'windows': 'optimal_windows.csv'
    }
    
    loaded_data = {}
    files_status = {}
    
    for key, filename in data_files.items():
        if os.path.exists(filename):
            try:
                df = pd.read_csv(filename)
                if key in ['historical', 'forecast']:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    df = df.sort_values('timestamp')
                elif key == 'windows':
                    df['start_time'] = pd.to_datetime(df['start_time'])
                    df['end_time'] = pd.to_datetime(df['end_time'])
                    df = df.sort_values('start_time')
                
                loaded_data[key] = df
                files_status[key] = True
            except Exception as e:
                st.error(f"Error loading {filename}: {e}")
                files_status[key] = False
        else:
            files_status[key] = False
    
    # If no data files exist, create sample data
    if not any(files_status.values()):
        loaded_data = create_sample_forecast_data()
        files_status['sample'] = True
    
    return loaded_data, files_status

def create_sample_forecast_data():
    """Create sample forecast data for demonstration"""
    now = datetime.datetime.now()
    
    # Historical data (past 7 days)
    historical_dates = pd.date_range(
        start=now - datetime.timedelta(days=7),
        end=now,
        freq='H'
    )
    
    # Forecast data (next 10 days)
    forecast_dates = pd.date_range(
        start=now + datetime.timedelta(hours=1),
        end=now + datetime.timedelta(days=10),
        freq='H'
    )
    
    sites = [
        {"site_id": "01073500", "site_name": "Merrimack River below Concord River at Lowell, MA", "lat": 42.6334, "lon": -71.3162},
        {"site_id": "01100000", "site_name": "Merrimack River at Lowell, MA", "lat": 42.65, "lon": -71.30}
    ]
    
    # Generate historical data
    historical_data = []
    np.random.seed(42)
    
    for site in sites:
        for date in historical_dates:
            # Add some hourly variation
            hour_factor = np.sin(date.hour * np.pi / 12) * 0.2 + 1
            day_factor = np.sin(date.day * np.pi / 15) * 0.3 + 1
            
            discharge = np.random.normal(1500, 300) * hour_factor * day_factor
            gage_height = np.random.normal(3.5, 0.8) * hour_factor
            
            historical_data.append({
                'timestamp': date,
                'site_id': site['site_id'],
                'site_name': site['site_name'],
                'discharge_cfs': max(300, discharge),
                'gage_height_ft': max(1, gage_height),
                'lat': site['lat'],
                'lon': site['lon']
            })
    
    # Generate forecast data
    forecast_data = []
    for site in sites:
        for date in forecast_dates:
            hour_factor = np.sin(date.hour * np.pi / 12) * 0.2 + 1
            day_factor = np.sin(date.day * np.pi / 15) * 0.3 + 1
            
            discharge = np.random.normal(1400, 250) * hour_factor * day_factor
            gage_height = np.random.normal(3.3, 0.7) * hour_factor
            
            forecast_data.append({
                'timestamp': date,
                'site_id': site['site_id'],
                'site_name': site['site_name'],
                'discharge_cfs': max(300, discharge),
                'gage_height_ft': max(1, gage_height),
                'lat': site['lat'],
                'lon': site['lon'],
                'is_forecast': True
            })
    
    # Calculate kayakability scores
    historical_df = pd.DataFrame(historical_data)
    forecast_df = pd.DataFrame(forecast_data)
    
    historical_df['kayakability_score'] = historical_df.apply(calculate_kayakability_score, axis=1)
    forecast_df['kayakability_score'] = forecast_df.apply(calculate_kayakability_score, axis=1)
    
    # Generate optimal windows
    windows_data = []
    for i, site in enumerate(sites):
        site_forecast = forecast_df[forecast_df['site_id'] == site['site_id']]
        good_periods = site_forecast[site_forecast['kayakability_score'] >= 70]
        
        if len(good_periods) > 0:
            # Create some sample windows
            for j in range(min(5, len(good_periods) // 3)):
                start_idx = j * 3
                if start_idx < len(good_periods):
                    start_time = good_periods.iloc[start_idx]['timestamp']
                    end_time = start_time + datetime.timedelta(hours=3)
                    avg_score = good_periods.iloc[start_idx:start_idx+3]['kayakability_score'].mean()
                    
                    windows_data.append({
                        'site_id': site['site_id'],
                        'site_name': site['site_name'],
                        'start_time': start_time,
                        'end_time': end_time,
                        'duration_hours': 3,
                        'avg_score': avg_score,
                        'min_score': good_periods.iloc[start_idx:start_idx+3]['kayakability_score'].min(),
                        'max_score': good_periods.iloc[start_idx:start_idx+3]['kayakability_score'].max()
                    })
    
    windows_df = pd.DataFrame(windows_data)
    
    return {
        'historical': historical_df,
        'forecast': forecast_df,
        'windows': windows_df
    }

def calculate_kayakability_score(row):
    """Calculate kayakability score based on conditions"""
    discharge = row.get('discharge_cfs', 1000)
    gage_height = row.get('gage_height_ft', 3.0)
    
    # Optimal ranges
    optimal_discharge_min = 800
    optimal_discharge_max = 2500
    optimal_gage_min = 2.5
    optimal_gage_max = 5.0
    
    # Discharge score (60% weight)
    if optimal_discharge_min <= discharge <= optimal_discharge_max:
        discharge_score = 100
    elif discharge < optimal_discharge_min:
        discharge_score = max(0, 100 * (discharge / optimal_discharge_min) ** 1.5)
    else:
        excess_ratio = (discharge - optimal_discharge_max) / optimal_discharge_max
        discharge_score = max(0, 100 * np.exp(-2 * excess_ratio))
    
    # Gage height score (40% weight)
    if optimal_gage_min <= gage_height <= optimal_gage_max:
        gage_score = 100
    elif gage_height < optimal_gage_min:
        gage_score = max(0, 100 * (gage_height / optimal_gage_min) ** 2)
    else:
        excess_ratio = (gage_height - optimal_gage_max) / optimal_gage_max
        gage_score = max(0, 100 * np.exp(-1.5 * excess_ratio))
    
    final_score = discharge_score * 0.6 + gage_score * 0.4
    return min(100, max(0, final_score))

def get_score_info(score):
    """Get score information and styling"""
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

def create_forecast_timeline_chart(historical_df, forecast_df):
    """Create a timeline chart showing historical and forecast data"""
    # Mark historical vs forecast data
    historical_df = historical_df.copy()
    forecast_df = forecast_df.copy()
    historical_df['data_type'] = 'Historical'
    forecast_df['data_type'] = 'Forecast'
    
    # Combine data
    combined_df = pd.concat([historical_df, forecast_df], ignore_index=True)
    
    # Create the chart
    base_chart = alt.Chart(combined_df).add_selection(
        alt.selection_interval(bind='scales')
    )
    
    # Historical data line
    historical_line = base_chart.transform_filter(
        alt.datum.data_type == 'Historical'
    ).mark_line(
        strokeWidth=3,
        stroke='#3b82f6'
    ).encode(
        x=alt.X('timestamp:T', title='Date & Time'),
        y=alt.Y('kayakability_score:Q', title='Kayakability Score', scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('site_id:N', title='Site'),
        tooltip=['timestamp:T', 'kayakability_score:Q', 'site_name:N', 'discharge_cfs:Q']
    )
    
    # Forecast data line (dashed)
    forecast_line = base_chart.transform_filter(
        alt.datum.data_type == 'Forecast'
    ).mark_line(
        strokeWidth=3,
        strokeDash=[5, 5]
    ).encode(
        x=alt.X('timestamp:T', title='Date & Time'),
        y=alt.Y('kayakability_score:Q', title='Kayakability Score', scale=alt.Scale(domain=[0, 100])),
        color=alt.Color('site_id:N', title='Site'),
        tooltip=['timestamp:T', 'kayakability_score:Q', 'site_name:N', 'discharge_cfs:Q']
    )
    
    # Reference lines
    rules = alt.Chart(pd.DataFrame({
        'score': [85, 70, 50, 25],
        'label': ['Excellent', 'Good', 'Fair', 'Poor']
    })).mark_rule(
        strokeDash=[3, 3],
        opacity=0.5
    ).encode(
        y='score:Q',
        color=alt.value('#64748b')
    )
    
    # Current time line
    now_line = alt.Chart(pd.DataFrame({
        'now': [datetime.datetime.now()]
    })).mark_rule(
        strokeWidth=2,
        stroke='red',
        opacity=0.7
    ).encode(
        x='now:T'
    )
    
    return (historical_line + forecast_line + rules + now_line).properties(
        width='container',
        height=400,
        title=alt.TitleParams(
            text='Kayakability Score: Historical Data & 10-Day Forecast',
            fontSize=16,
            fontWeight='bold'
        )
    ).resolve_scale(
        color='independent'
    )

def create_discharge_forecast_chart(historical_df, forecast_df):
    """Create discharge forecast chart"""
    historical_df = historical_df.copy()
    forecast_df = forecast_df.copy()
    historical_df['data_type'] = 'Historical'
    forecast_df['data_type'] = 'Forecast'
    
    combined_df = pd.concat([historical_df, forecast_df], ignore_index=True)
    
    base_chart = alt.Chart(combined_df).add_selection(
        alt.selection_interval(bind='scales')
    )
    
    historical_area = base_chart.transform_filter(
        alt.datum.data_type == 'Historical'
    ).mark_area(
        opacity=0.7,
        color='#06b6d4'
    ).encode(
        x=alt.X('timestamp:T', title='Date & Time'),
        y=alt.Y('discharge_cfs:Q', title='Discharge (CFS)'),
        tooltip=['timestamp:T', 'discharge_cfs:Q', 'site_name:N']
    )
    
    forecast_area = base_chart.transform_filter(
        alt.datum.data_type == 'Forecast'
    ).mark_area(
        opacity=0.5,
        color='#f59e0b'
    ).encode(
        x=alt.X('timestamp:T', title='Date & Time'),
        y=alt.Y('discharge_cfs:Q', title='Discharge (CFS)'),
        tooltip=['timestamp:T', 'discharge_cfs:Q', 'site_name:N']
    )
    
    now_line = alt.Chart(pd.DataFrame({
        'now': [datetime.datetime.now()]
    })).mark_rule(
        strokeWidth=2,
        stroke='red',
        opacity=0.7
    ).encode(
        x='now:T'
    )
    
    return (historical_area + forecast_area + now_line).properties(
        width='container',
        height=300,
        title=alt.TitleParams(
            text='Water Discharge: Historical & Forecast',
            fontSize=16,
            fontWeight='bold'
        )
    )

def format_window_display(window):
    """Format optimal window for display"""
    start_time = window['start_time']
    end_time = window['end_time']
    
    # Format time display
    if start_time.date() == end_time.date():
        time_str = f"{start_time.strftime('%a %m/%d')} {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
    else:
        time_str = f"{start_time.strftime('%a %m/%d %I:%M %p')} - {end_time.strftime('%a %m/%d %I:%M %p')}"
    
    return time_str

# Add nighttime filter checkbox to sidebar
hide_nighttime = st.sidebar.checkbox("🌜 Hide Nighttime Hours", value=False)

# Load the data AFTER all functions are defined
data, files_status = load_forecast_data()

# Filter forecast data for daytime hours (7 AM to 7 PM)
if hide_nighttime and 'forecast' in data:
    forecast_df = data['forecast']
    data['forecast'] = forecast_df[forecast_df['timestamp'].dt.hour.between(7, 19)]

# Add interactive map of forecast sites
if 'forecast' in data:
    st.markdown("### 🗺️ Site Map")
    map_df = data['forecast'][['lat', 'lon', 'site_name']].drop_duplicates()
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v9",
        initial_view_state=pdk.ViewState(
            latitude=map_df['lat'].mean(),
            longitude=map_df['lon'].mean(),
            zoom=9,
            pitch=45,
        ),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=map_df,
                get_position='[lon, lat]',
                get_color='[0, 123, 255, 160]',
                get_radius=500,
            ),
        ],
        tooltip={"text": "{site_name}"}
    ))

# Header
st.markdown("<h1 class='main-header'>🛶 Kayakability Forecast Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Hourly conditions and 10-day forecasting for optimal kayaking windows</p>", unsafe_allow_html=True)

# Data status
if files_status.get('sample'):
    st.info("📊 Currently displaying sample forecast data for demonstration")
else:
    status_messages = []
    if files_status.get('historical'):
        status_messages.append("✅ Historical data loaded")
    if files_status.get('forecast'):
        status_messages.append("✅ Forecast data loaded")
    if files_status.get('windows'):
        status_messages.append("✅ Optimal windows identified")
    
    if status_messages:
        st.success(" | ".join(status_messages))

# Main content
if 'historical' in data and 'forecast' in data:
    historical_df = data['historical']
    forecast_df = data['forecast']
    
    # Current conditions
    latest = historical_df.iloc[-1]
    icon, status, css_class, color, status_class = get_score_info(latest['kayakability_score'])
    
    st.markdown("### 📍 Current Conditions")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"""
        <div class="forecast-card">
            <div class="score-display">
                <div class="score-icon">{icon}</div>
                <div class="score-number" style="color: {color};">{latest['kayakability_score']:.0f}</div>
                <div class="score-status {css_class}">{status}</div>
            </div>
            <div class="metric-row">
                <span class="metric-label">Location</span>
                <span class="metric-value">{latest['site_name'].split(' at ')[-1]}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Last Updated</span>
                <span class="metric-value">{latest['timestamp'].strftime('%m/%d %I:%M %p')}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.metric("Discharge", f"{latest['discharge_cfs']:.0f} CFS")
        st.metric("Gage Height", f"{latest['gage_height_ft']:.1f} ft")
    
    with col3:
        # Next 24 hours summary
        next_24h = forecast_df[forecast_df['timestamp'] <= datetime.datetime.now() + datetime.timedelta(hours=24)]
        if len(next_24h) > 0:
            avg_score = next_24h['kayakability_score'].mean()
            max_score = next_24h['kayakability_score'].max()
            
            st.metric("24h Avg Score", f"{avg_score:.0f}")
            st.metric("24h Peak Score", f"{max_score:.0f}")

    # Optimal windows section
    if 'windows' in data and len(data['windows']) > 0:
        st.markdown("### 🎯 Optimal Kayaking Windows (Next 10 Days)")
        
        windows_df = data['windows'].head(10)  # Show top 10 windows
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### 📅 Recommended Times")
            
            for _, window in windows_df.iterrows():
                icon, status, css_class, color, status_class = get_score_info(window['avg_score'])
                time_str = format_window_display(window)
                
                st.markdown(f"""
                <div class="window-card {status_class}">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <strong>{icon} {time_str}</strong><br>
                            <small style="color: #6b7280;">{window['site_name'].split(' at ')[-1]} • {window['duration_hours']:.1f} hours</small>
                        </div>
                        <div style="text-align: right;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: {color};">{window['avg_score']:.0f}</div>
                            <div style="font-size: 0.8rem; color: #6b7280;">Score</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("#### 📊 Window Summary")
            
            total_windows = len(windows_df)
            excellent_windows = len(windows_df[windows_df['avg_score'] >= 85])
            good_windows = len(windows_df[windows_df['avg_score'] >= 70])
            
            st.metric("Total Windows", total_windows)
            st.metric("Excellent (85+)", excellent_windows)
            st.metric("Good (70+)", good_windows)
            
            if len(windows_df) > 0:
                best_window = windows_df.iloc[0]
                st.markdown(f"""
                <div class="alert success">
                    <strong>🏆 Best Opportunity:</strong><br>
                    {format_window_display(best_window)}<br>
                    Score: {best_window['avg_score']:.0f}/100
                </div>
                """, unsafe_allow_html=True)
    
       else:
            st.markdown("### ⚠️ No Optimal Windows Found")
            st.markdown("No kayaking windows with scores ≥70 were identified in the next 10 days. Check back later for updated forecasts.")
    
        # Charts section
        st.markdown("---")
        st.markdown("### 📈 Detailed Forecasts")
        
        col1, col2 = st.columns(2, gap="large")
        
        with col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            timeline_chart = create_forecast_timeline_chart(historical_df, forecast_df)
            st.altair_chart(timeline_chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            discharge_chart = create_discharge_forecast_chart(historical_df, forecast_df)
            st.altair_chart(discharge_chart, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Detailed site information
        st.markdown("---")
        st.markdown("### 🎯 Site-Specific Analysis")
        
        # Site selector
        sites = forecast_df['site_name'].unique()
        selected_site = st.selectbox("Select a site for detailed analysis:", sites)
        
        if selected_site:
            site_forecast = forecast_df[forecast_df['site_name'] == selected_site]
            site_historical = historical_df[historical_df['site_name'] == selected_site]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                # 24-hour outlook
                next_24h = site_forecast[site_forecast['timestamp'] <= datetime.datetime.now() + datetime.timedelta(hours=24)]
                if len(next_24h) > 0:
                    st.markdown("#### 🌅 Next 24 Hours")
                    avg_score = next_24h['kayakability_score'].mean()
                    icon, status, css_class, color, status_class = get_score_info(avg_score)
                    
                    st.markdown(f"""
                    <div class="forecast-card">
                        <div class="score-display">
                            <div class="score-icon">{icon}</div>
                            <div class="score-number" style="color: {color};">{avg_score:.0f}</div>
                            <div class="score-status {css_class}">{status}</div>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Avg Discharge</span>
                            <span class="metric-value">{next_24h['discharge_cfs'].mean():.0f} CFS</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Peak Score</span>
                            <span class="metric-value">{next_24h['kayakability_score'].max():.0f}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                # 3-day outlook
                next_3d = site_forecast[site_forecast['timestamp'] <= datetime.datetime.now() + datetime.timedelta(days=3)]
                if len(next_3d) > 0:
                    st.markdown("#### 🗓️ Next 3 Days")
                    avg_score = next_3d['kayakability_score'].mean()
                    icon, status, css_class, color, status_class = get_score_info(avg_score)
                    
                    st.markdown(f"""
                    <div class="forecast-card">
                        <div class="score-display">
                            <div class="score-icon">{icon}</div>
                            <div class="score-number" style="color: {color};">{avg_score:.0f}</div>
                            <div class="score-status {css_class}">{status}</div>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Good Hours</span>
                            <span class="metric-value">{len(next_3d[next_3d['kayakability_score'] >= 70])}</span>
                        </div>
                        <div class="metric-row">
                            <span class="metric-label">Excellent Hours</span>
                            <span class="metric-value">{len(next_3d[next_3d['kayakability_score'] >= 85])}</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col3:
                # 10-day outlook
                st.markdown("#### 📊 Full Forecast")
                avg_score = site_forecast['kayakability_score'].mean()
                icon, status, css_class, color, status_class = get_score_info(avg_score)
                
                st.markdown(f"""
                <div class="forecast-card">
                    <div class="score-display">
                        <div class="score-icon">{icon}</div>
                        <div class="score-number" style="color: {color};">{avg_score:.0f}</div>
                        <div class="score-status {css_class}">{status}</div>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Total Hours</span>
                        <span class="metric-value">{len(site_forecast)}</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Kayakable Hours</span>
                        <span class="metric-value">{len(site_forecast[site_forecast['kayakability_score'] >= 50])}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            # Hourly breakdown table
            st.markdown("#### 📋 Hourly Forecast (Next 48 Hours)")
            next_48h = site_forecast[site_forecast['timestamp'] <= datetime.datetime.now() + datetime.timedelta(hours=48)]
            
            if len(next_48h) > 0:
                # Create display dataframe
                display_df = next_48h.copy()
                display_df['Date'] = display_df['timestamp'].dt.strftime('%m/%d')
                display_df['Time'] = display_df['timestamp'].dt.strftime('%I:%M %p')
                display_df['Score'] = display_df['kayakability_score'].round(0).astype(int)
                display_df['Discharge'] = display_df['discharge_cfs'].round(0).astype(int)
                display_df['Gage Height'] = display_df['gage_height_ft'].round(1)
                display_df['Status'] = display_df['kayakability_score'].apply(lambda x: get_score_info(x)[1])
                
                # Display every 3rd hour to avoid overcrowding
                display_df = display_df.iloc[::3]
                
                st.dataframe(
                    display_df[['Date', 'Time', 'Score', 'Status', 'Discharge', 'Gage Height']],
                    use_container_width=True,
                    hide_index=True
                )
    
        # Footer section
        st.markdown("---")
        st.markdown("### ℹ️ About This Forecast")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            **Kayakability Scoring:**
            - **85-100**: Excellent conditions
            - **70-84**: Good for most kayakers  
            - **50-69**: Fair, suitable for experienced paddlers
            - **25-49**: Poor conditions, not recommended
            - **0-24**: Dangerous conditions
            """)
        
        with col2:
            st.markdown("""
            **Data Sources:**
            - USGS Water Data Services
            - National Weather Service
            - Historical flow patterns
            - Real-time gage measurements
            - 10-day hydrologic forecasts
            """)
        
        # Update timestamp
        st.markdown(f"<div style='text-align: center; color: #64748b; margin-top: 2rem;'>Last updated: {datetime.datetime.now().strftime('%Y-%m-%d %I:%M %p')}</div>", unsafe_allow_html=True)
