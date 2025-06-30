import numpy as np
import pandas as pd
from datetime import timedelta
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


def create_time_features(df):
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
    from data_export import calculate_kayakability_score
    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    if df.empty:
        return pd.DataFrame()
    discharge_model, discharge_scaler = train_forecast_model(df, 'discharge_cfs')
    gage_model, gage_scaler = train_forecast_model(df, 'gage_height_ft')
    if discharge_model is None or gage_model is None:
        return pd.DataFrame()
    last_time = df['datetime'].max()
    future_times = [last_time + timedelta(hours=i) for i in range(1, forecast_hours + 1)]
    forecast_data = []
    latest_discharge = df['discharge_cfs'].iloc[-1]
    latest_gage = df['gage_height_ft'].iloc[-1]
    for future_time in future_times:
        hour = future_time.hour
        day_of_week = future_time.dayofweek
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)
        features = np.array([[hour_sin, hour_cos, day_sin, day_cos,
                              latest_discharge, latest_discharge,
                              latest_gage, latest_gage,
                              latest_discharge, latest_gage]])
        discharge_pred = discharge_model.predict(discharge_scaler.transform(features))[0]
        gage_pred = gage_model.predict(gage_scaler.transform(features))[0]
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
        latest_discharge = discharge_pred
        latest_gage = gage_pred
    return pd.DataFrame(forecast_data)


__all__ = [
    "create_time_features",
    "train_forecast_model",
    "forecast_conditions"
]
