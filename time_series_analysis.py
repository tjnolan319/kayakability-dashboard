import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

def calculate_kayakability_score(discharge, gage_height, ideal_discharge_range, ideal_gage_range):
    """
    Calculate kayakability score based on discharge and gage height.
    Returns a score from 0-100 where 100 is optimal conditions.
    """
    # Handle missing values
    if pd.isna(discharge) or pd.isna(gage_height):
        return 0
    
    # Extract ideal ranges
    min_discharge, max_discharge = ideal_discharge_range
    min_gage, max_gage = ideal_gage_range
    
    # Calculate discharge score (0-50 points)
    if min_discharge <= discharge <= max_discharge:
        discharge_score = 50  # Perfect discharge
    elif discharge < min_discharge:
        # Too low - exponential decay
        ratio = discharge / min_discharge
        discharge_score = 50 * max(0, ratio ** 2)
    else:
        # Too high - exponential decay
        ratio = max_discharge / discharge
        discharge_score = 50 * max(0, ratio ** 2)
    
    # Calculate gage height score (0-50 points)
    if min_gage <= gage_height <= max_gage:
        gage_score = 50  # Perfect gage height
    elif gage_height < min_gage:
        # Too low - exponential decay
        ratio = gage_height / min_gage
        gage_score = 50 * max(0, ratio ** 2)
    else:
        # Too high - exponential decay
        ratio = max_gage / gage_height
        gage_score = 50 * max(0, ratio ** 2)
    
    # Combine scores
    total_score = discharge_score + gage_score
    
    # Apply bonus for being in the sweet spot of both ranges
    if (min_discharge <= discharge <= max_discharge and 
        min_gage <= gage_height <= max_gage):
        # Bonus points for optimal conditions
        discharge_center = (min_discharge + max_discharge) / 2
        gage_center = (min_gage + max_gage) / 2
        
        discharge_proximity = 1 - abs(discharge - discharge_center) / (max_discharge - discharge_center)
        gage_proximity = 1 - abs(gage_height - gage_center) / (max_gage - gage_center)
        
        bonus = min(10, (discharge_proximity + gage_proximity) * 5)
        total_score += bonus
    
    return round(min(100, max(0, total_score)))

def find_optimal_windows(forecast_df, min_score=60, min_duration=2):
    """
    Find optimal kayaking windows in the forecast data.
    
    Parameters:
    - forecast_df: DataFrame with forecast data
    - min_score: Minimum kayakability score to consider (default 60)
    - min_duration: Minimum window duration in hours (default 2)
    
    Returns list of optimal windows with metadata
    """
    if forecast_df.empty:
        return []
    
    # Sort by datetime
    df = forecast_df.sort_values('datetime').copy()
    df['datetime'] = pd.to_datetime(df['datetime'])
    
    optimal_windows = []
    
    # Group by site to find windows for each location
    for site_id in df['site_id'].unique():
        site_df = df[df['site_id'] == site_id].copy()
        site_name = site_df['site_name'].iloc[0]
        
        # Find consecutive hours with good scores
        good_conditions = site_df['kayakability_score'] >= min_score
        
        if not good_conditions.any():
            continue
        
        # Find contiguous blocks of good conditions
        blocks = []
        current_block = []
        
        for idx, is_good in enumerate(good_conditions):
            if is_good:
                current_block.append(idx)
            else:
                if len(current_block) >= min_duration:
                    blocks.append(current_block)
                current_block = []
        
        # Don't forget the last block
        if len(current_block) >= min_duration:
            blocks.append(current_block)
        
        # Convert blocks to windows with metadata
        for block in blocks:
            if len(block) < min_duration:
                continue
                
            start_idx = block[0]
            end_idx = block[-1]
            
            window_data = site_df.iloc[start_idx:end_idx+1]
            
            window = {
                'site_id': site_id,
                'site_name': site_name,
                'start_time': window_data['datetime'].iloc[0],
                'end_time': window_data['datetime'].iloc[-1],
                'duration_hours': len(block),
                'avg_score': round(window_data['kayakability_score'].mean(), 1),
                'max_score': window_data['kayakability_score'].max(),
                'min_score': window_data['kayakability_score'].min(),
                'avg_discharge': round(window_data['discharge_cfs'].mean(), 1),
                'avg_gage': round(window_data['gage_height_ft'].mean(), 2),
                'score_trend': 'stable'  # Could be enhanced to detect trends
            }
            
            optimal_windows.append(window)
    
    # Sort by average score (best first), then by duration
    optimal_windows.sort(key=lambda x: (x['avg_score'], x['duration_hours']), reverse=True)
    
    return optimal_windows

def create_time_features(df):
    """Create time-based features for forecasting"""
    df = df.copy()
    df['hour'] = df['datetime'].dt.hour
    df['day_of_week'] = df['datetime'].dt.dayofweek
    df['day_of_year'] = df['datetime'].dt.dayofyear
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    df['discharge_lag1'] = df['discharge_cfs'].shift(1)
    df['discharge_lag6'] = df['discharge_cfs'].shift(6)
    df['gage_lag1'] = df['gage_height_ft'].shift(1)
    df['gage_lag6'] = df['gage_height_ft'].shift(6)
    df['discharge_ma6'] = df['discharge_cfs'].rolling(window=6, center=True).mean()
    df['gage_ma6'] = df['gage_height_ft'].rolling(window=6, center=True).mean()
    return df

def train_forecast_model(df, target_col='discharge_cfs'):
    """Train a forecasting model for the given target column"""
    if len(df) < 24:
        return None, None
    
    df_features = create_time_features(df)
    feature_cols = [
        'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
        'discharge_lag1', 'discharge_lag6',
        'gage_lag1', 'gage_lag6',
        'discharge_ma6', 'gage_ma6'
    ]
    
    df_clean = df_features.dropna(subset=feature_cols + [target_col])
    if len(df_clean) < 12:
        return None, None
    
    X = df_clean[feature_cols]
    y = df_clean[target_col]
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    model = LinearRegression()
    model.fit(X_scaled, y)
    
    return model, scaler

def forecast_conditions(site_id, site_info, csv_path, forecast_hours=240):
    """
    Generate forecast conditions for a site using historical data
    """
    try:
        df = pd.read_csv(csv_path, parse_dates=['datetime'])
    except Exception as e:
        print(f"Error reading CSV {csv_path}: {e}")
        return pd.DataFrame()
    
    if df.empty:
        return pd.DataFrame()
    
    # Train models for both discharge and gage height
    discharge_model, discharge_scaler = train_forecast_model(df, 'discharge_cfs')
    gage_model, gage_scaler = train_forecast_model(df, 'gage_height_ft')
    
    if discharge_model is None or gage_model is None:
        print(f"Could not train models for site {site_id}")
        return pd.DataFrame()
    
    # Generate future timestamps
    last_time = df['datetime'].max()
    future_times = [last_time + timedelta(hours=i) for i in range(1, forecast_hours + 1)]
    
    forecast_data = []
    latest_discharge = df['discharge_cfs'].iloc[-1]
    latest_gage = df['gage_height_ft'].iloc[-1]
    
    for future_time in future_times:
        # Create time features
        hour = future_time.hour
        day_of_week = future_time.dayofweek
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)
        
        # Use latest values for lag features (simplified)
        features = np.array([[hour_sin, hour_cos, day_sin, day_cos,
                              latest_discharge, latest_discharge,
                              latest_gage, latest_gage,
                              latest_discharge, latest_gage]])
        
        # Make predictions
        try:
            discharge_pred = discharge_model.predict(discharge_scaler.transform(features))[0]
            gage_pred = gage_model.predict(gage_scaler.transform(features))[0]
        except Exception as e:
            print(f"Prediction error for {future_time}: {e}")
            continue
        
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
        
        # Update latest values for next iteration
        latest_discharge = discharge_pred
        latest_gage = gage_pred
    
    return pd.DataFrame(forecast_data)

# Export all functions
__all__ = [
    "calculate_kayakability_score",
    "find_optimal_windows", 
    "create_time_features",
    "train_forecast_model",
    "forecast_conditions"
]
