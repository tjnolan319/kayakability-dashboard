import requests
import csv
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error
import warnings
warnings.filterwarnings('ignore')

# Configuration for Sites
merrimack_sites = {
    "01073500": {
        "name": "Merrimack River below Concord River at Lowell, MA",
        "lat": 42.6334,
        "lon": -71.3162,
        "ideal_discharge_range": (800, 2000),
        "ideal_gage_range": (2.0, 4.5),
        "difficulty": "Class I-II"
    },
    "01100000": {
        "name": "Merrimack River at Lowell, MA", 
        "lat": 42.65,
        "lon": -71.30,
        "ideal_discharge_range": (1000, 2500),
        "ideal_gage_range": (1.5, 5.0),
        "difficulty": "Class I-II"
    },
    "01096500": {
        "name": "Merrimack River at North Chelmsford, MA",
        "lat": 42.6278,
        "lon": -71.3667,
        "ideal_discharge_range": (800, 2200),
        "ideal_gage_range": (2.0, 4.8),
        "difficulty": "Class I-II"
    },
    "01094000": {
        "name": "Merrimack River near Goffs Falls below Manchester, NH",
        "lat": 43.0167,
        "lon": -71.4833,
        "ideal_discharge_range": (600, 1800),
        "ideal_gage_range": (1.8, 4.2),
        "difficulty": "Class II"
    },
    "01092000": {
        "name": "Merrimack River at Franklin Junction, NH",
        "lat": 43.4361,
        "lon": -71.6472,
        "ideal_discharge_range": (400, 1500),
        "ideal_gage_range": (1.5, 3.8),
        "difficulty": "Class I"
    }
}

def fetch_hourly_usgs_data(site_id, days_back=7):
    """Fetch hourly USGS data for the past N days"""
    base_url = "https://waterservices.usgs.gov/nwis/iv/"
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    
    params = {
        'format': 'json',
        'sites': site_id,
        'parameterCd': '00060,00065',  # discharge and gage height
        'startDT': start_date.strftime('%Y-%m-%dT%H:%M:%S'),
        'endDT': end_date.strftime('%Y-%m-%dT%H:%M:%S'),
        'siteStatus': 'active'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        if 'value' not in data or 'timeSeries' not in data['value']:
            return pd.DataFrame()
            
        # Parse the time series data
        discharge_data = []
        gage_data = []
        
        for series in data['value']['timeSeries']:
            param_code = series['variable']['variableCode'][0]['value']
            
            if series['values'] and series['values'][0]['value']:
                for value_point in series['values'][0]['value']:
                    timestamp = pd.to_datetime(value_point['dateTime'])
                    value = float(value_point['value'])
                    
                    if param_code == '00060':  # discharge
                        discharge_data.append({
                            'datetime': timestamp,
                            'discharge_cfs': value
                        })
                    elif param_code == '00065':  # gage height
                        gage_data.append({
                            'datetime': timestamp,
                            'gage_height_ft': value
                        })
        
        # Convert to DataFrames and merge
        df_discharge = pd.DataFrame(discharge_data)
        df_gage = pd.DataFrame(gage_data)
        
        if df_discharge.empty or df_gage.empty:
            return pd.DataFrame()
        
        # Merge on datetime
        df = pd.merge(df_discharge, df_gage, on='datetime', how='outer')
        df = df.sort_values('datetime').reset_index(drop=True)
        
        # Fill missing values with forward fill
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        return df
        
    except Exception as e:
        print(f"⚠️  Error fetching USGS data for {site_id}: {e}")
        return pd.DataFrame()

def calculate_kayakability_score(discharge, gage_height, ideal_discharge_range, ideal_gage_range):
    """Calculate kayakability score based on discharge and gage height"""
    if pd.isna(discharge) or pd.isna(gage_height):
        return 0
    
    score = 0
    
    # Check discharge (50% of score)
    if ideal_discharge_range[0] <= discharge <= ideal_discharge_range[1]:
        score += 50
    elif discharge < ideal_discharge_range[0]:
        ratio = discharge / ideal_discharge_range[0]
        score += max(0, 25 * ratio)
    else:
        ratio = ideal_discharge_range[1] / discharge
        score += max(0, 25 * ratio)
    
    # Check gage height (50% of score)
    if ideal_gage_range[0] <= gage_height <= ideal_gage_range[1]:
        score += 50
    elif gage_height < ideal_gage_range[0]:
        ratio = gage_height / ideal_gage_range[0]
        score += max(0, 25 * ratio)
    else:
        ratio = ideal_gage_range[1] / gage_height
        score += max(0, 25 * ratio)
    
    return min(100, max(0, round(score)))

def create_time_features(df):
    """Create time-based features for modeling"""
    df = df.copy()
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek
    df['day_of_year'] = df['datetime'].dt.dayofyear
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    
    # Lag features
    df['discharge_lag1'] = df['discharge_cfs'].shift(1)
    df['discharge_lag6'] = df['discharge_cfs'].shift(6)
    df['gage_lag1'] = df['gage_height_ft'].shift(1)
    df['gage_lag6'] = df['gage_height_ft'].shift(6)
    
    # Rolling averages
    df['discharge_ma6'] = df['discharge_cfs'].rolling(window=6, center=True).mean()
    df['gage_ma6'] = df['gage_height_ft'].rolling(window=6, center=True).mean()
    
    return df

def train_forecast_model(df, target_col='discharge_cfs'):
    """Train a time series forecasting model"""
    if len(df) < 24:  # Need at least 24 hours of data
        return None, None
    
    # Create features
    df_features = create_time_features(df)
    
    # Feature columns for modeling
    feature_cols = [
        'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
        'discharge_lag1', 'discharge_lag6', 'gage_lag1', 'gage_lag6',
        'discharge_ma6', 'gage_ma6'
    ]
    
    # Remove rows with NaN values
    df_clean = df_features.dropna(subset=feature_cols + [target_col])
    
    if len(df_clean) < 12:
        return None, None
    
    X = df_clean[feature_cols]
    y = df_clean[target_col]
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train model
    model = LinearRegression()
    model.fit(X_scaled, y)
    
    return model, scaler

def forecast_conditions(site_id, site_info, historical_df, forecast_hours=240):  # 10 days
    """Generate forecast for river conditions"""
    if historical_df.empty:
        return pd.DataFrame()
    
    # Train models for discharge and gage height
    discharge_model, discharge_scaler = train_forecast_model(historical_df, 'discharge_cfs')
    gage_model, gage_scaler = train_forecast_model(historical_df, 'gage_height_ft')
    
    if discharge_model is None or gage_model is None:
        return pd.DataFrame()
    
    # Create future time points
    last_time = historical_df['datetime'].max()
    future_times = [last_time + timedelta(hours=i) for i in range(1, forecast_hours + 1)]
    
    forecast_data = []
    
    # Get latest values for lag features
    latest_discharge = historical_df['discharge_cfs'].iloc[-1]
    latest_gage = historical_df['gage_height_ft'].iloc[-1]
    
    for future_time in future_times:
        # Create time features
        hour = future_time.hour
        day_of_week = future_time.dayofweek
        
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)
        
        # Use latest values as lag features (simplified approach)
        features = np.array([[
            hour_sin, hour_cos, day_sin, day_cos,
            latest_discharge, latest_discharge,  # lag features
            latest_gage, latest_gage,  # gage lag features
            latest_discharge, latest_gage  # moving averages
        ]])
        
        # Make predictions
        discharge_pred = discharge_model.predict(discharge_scaler.transform(features))[0]
        gage_pred = gage_model.predict(gage_scaler.transform(features))[0]
        
        # Calculate kayakability score
        kayak_score = calculate_kayakability_score(
            discharge_pred, gage_pred,
            site_info['ideal_discharge_range'],
            site_info['ideal_gage_range']
        )
        
        forecast_data.append({
            'site_id': site_id,
            'site_name': site_info['name'],
            'datetime': future_time,
            'discharge_cfs': round(discharge_pred, 1),
            'gage_height_ft': round(gage_pred, 2),
            'kayakability_score': kayak_score,
            'forecast_type': 'predicted'
        })
        
        # Update latest values for next iteration (simple approach)
        latest_discharge = discharge_pred
        latest_gage = gage_pred
    
    return pd.DataFrame(forecast_data)

def find_optimal_windows(forecast_df, window_hours=3, min_score=70):
    """Find optimal 3-hour kayaking windows in the forecast"""
    if forecast_df.empty:
        return []
    
    optimal_windows = []
    
    # Group by site
    for site_id in forecast_df['site_id'].unique():
        site_data = forecast_df[forecast_df['site_id'] == site_id].copy()
        site_data = site_data.sort_values('datetime')
        
        # Calculate rolling average score for windows
        site_data['window_score'] = site_data['kayakability_score'].rolling(
            window=window_hours, center=True
        ).mean()
        
        # Find windows above minimum score
        good_windows = site_data[site_data['window_score'] >= min_score]
        
        if not good_windows.empty:
            # Group consecutive good periods
            good_windows['time_diff'] = good_windows['datetime'].diff().dt.total_seconds() / 3600
            good_windows['group'] = (good_windows['time_diff'] > 1.5).cumsum()
            
            for group_id in good_windows['group'].unique():
                group_data = good_windows[good_windows['group'] == group_id]
                
                if len(group_data) >= window_hours:
                    optimal_windows.append({
                        'site_id': site_id,
                        'site_name': group_data['site_name'].iloc[0],
                        'start_time': group_data['datetime'].min(),
                        'end_time': group_data['datetime'].max(),
                        'duration_hours': len(group_data),
                        'avg_score': round(group_data['kayakability_score'].mean(), 1),
                        'max_score': group_data['kayakability_score'].max(),
                        'avg_discharge': round(group_data['discharge_cfs'].mean(), 1),
                        'avg_gage': round(group_data['gage_height_ft'].mean(), 2)
                    })
    
    # Sort by score and start time
    optimal_windows.sort(key=lambda x: (-x['avg_score'], x['start_time']))
    
    return optimal_windows

def save_forecast_data(historical_df, forecast_df, optimal_windows, output_folder='kayak_forecast_data'):
    """Save all forecast data to CSV files"""
    os.makedirs(output_folder, exist_ok=True)
    
    # Save historical data
    if not historical_df.empty:
        historical_file = os.path.join(output_folder, 'historical_hourly_data.csv')
        historical_df.to_csv(historical_file, index=False)
        print(f"✅ Historical data saved to {historical_file}")
    
    # Save forecast data
    if not forecast_df.empty:
        forecast_file = os.path.join(output_folder, 'forecast_data.csv')
        forecast_df.to_csv(forecast_file, index=False)
        print(f"✅ Forecast data saved to {forecast_file}")
    
    # Save optimal windows
    if optimal_windows:
        windows_file = os.path.join(output_folder, 'optimal_windows.csv')
        pd.DataFrame(optimal_windows).to_csv(windows_file, index=False)
        print(f"✅ Optimal windows saved to {windows_file}")
    
    return output_folder

def generate_recommendations(optimal_windows):
    """Generate human-readable recommendations"""
    if not optimal_windows:
        return "❌ No optimal kayaking windows found in the 10-day forecast."
    
    recommendations = []
    recommendations.append("🚣 KAYAK FORECAST RECOMMENDATIONS")
    recommendations.append("=" * 50)
    
    # Group by day for better readability
    windows_by_day = {}
    for window in optimal_windows[:10]:  # Top 10 windows
        day = window['start_time'].strftime('%A, %B %d')
        if day not in windows_by_day:
            windows_by_day[day] = []
        windows_by_day[day].append(window)
    
    for day, day_windows in windows_by_day.items():
        recommendations.append(f"\n📅 {day}")
        recommendations.append("-" * 30)
        
        for window in day_windows:
            start_time = window['start_time'].strftime('%I:%M %p')
            end_time = window['end_time'].strftime('%I:%M %p')
            
            recommendations.append(f"⭐ Score: {window['avg_score']}/100")
            recommendations.append(f"🕐 Time: {start_time} - {end_time} ({window['duration_hours']}h)")
            recommendations.append(f"🌊 Site: {window['site_name']}")
            recommendations.append(f"💧 Discharge: {window['avg_discharge']} cfs")
            recommendations.append(f"📏 Gage: {window['avg_gage']} ft")
            recommendations.append("")
    
    return "\n".join(recommendations)

def main():
    """Main function to run the kayak forecasting system"""
    print("🚀 Starting Enhanced Kayak Forecasting System...")
    print("📊 Collecting hourly data and generating 10-day forecast...")
    
    all_historical_data = []
    all_forecast_data = []
    all_optimal_windows = []
    
    for site_id, site_info in merrimack_sites.items():
        print(f"\n🔍 Processing site: {site_info['name']}")
        
        # Fetch historical hourly data (7 days)
        print("  📈 Fetching historical data...")
        historical_df = fetch_hourly_usgs_data(site_id, days_back=7)
        
        if historical_df.empty:
            print(f"  ⚠️  No historical data available for {site_id}")
            continue
        
        # Add site info and kayakability scores
        historical_df['site_id'] = site_id
        historical_df['site_name'] = site_info['name']
        historical_df['kayakability_score'] = historical_df.apply(
            lambda row: calculate_kayakability_score(
                row['discharge_cfs'], row['gage_height_ft'],
                site_info['ideal_discharge_range'], site_info['ideal_gage_range']
            ), axis=1
        )
        
        all_historical_data.append(historical_df)
        
        # Generate forecast
        print("  🔮 Generating 10-day forecast...")
        forecast_df = forecast_conditions(site_id, site_info, historical_df)
        
        if not forecast_df.empty:
            all_forecast_data.append(forecast_df)
            
            # Find optimal windows for this site
            windows = find_optimal_windows(forecast_df)
            all_optimal_windows.extend(windows)
            
            print(f"  ✅ Found {len(windows)} optimal windows")
        else:
            print("  ⚠️  Could not generate forecast")
        
        time.sleep(1)  # Be nice to the API
    
    # Combine all data
    if all_historical_data:
        combined_historical = pd.concat(all_historical_data, ignore_index=True)
    else:
        combined_historical = pd.DataFrame()
    
    if all_forecast_data:
        combined_forecast = pd.concat(all_forecast_data, ignore_index=True)
    else:
        combined_forecast = pd.DataFrame()
    
    # Save data
    output_folder = save_forecast_data(
        combined_historical, combined_forecast, all_optimal_windows
    )
    
    # Generate and display recommendations
    print("\n" + "="*60)
    recommendations = generate_recommendations(all_optimal_windows)
    print(recommendations)
    
    print(f"\n🎉 Forecast complete!")
    print(f"📁 All data saved to: {output_folder}/")
    print(f"📊 Total optimal windows found: {len(all_optimal_windows)}")
    
    return {
        'historical_data': combined_historical,
        'forecast_data': combined_forecast,
        'optimal_windows': all_optimal_windows,
        'output_folder': output_folder
    }

if __name__ == "__main__":
    # Install required packages first:
    # pip install requests pandas numpy scikit-learn
    
    try:
        results = main()
        print("\n✅ System completed successfully!")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        print("Make sure you have installed: pip install requests pandas numpy scikit-learn")
