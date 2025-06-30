import os
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from site_config import merrimack_sites
from time_series_analysis import forecast_conditions

import warnings
warnings.filterwarnings("ignore")

def fetch_hourly_usgs_data(site_id, days_back=7):
    base_url = "https://waterservices.usgs.gov/nwis/iv/"
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days_back)

    params = {
        'format': 'json',
        'sites': site_id,
        'parameterCd': '00060,00065',
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

        dfs = {}
        for series in data['value']['timeSeries']:
            param = series['variable']['variableCode'][0]['value']
            records = series['values'][0]['value']

            df = pd.DataFrame([{
                'datetime': pd.to_datetime(v['dateTime'], utc=True),
                param: float(v['value'])
            } for v in records if v.get('value') not in ['Ice', 'Eqp']])

            dfs[param] = df

        if '00060' not in dfs or '00065' not in dfs:
            return pd.DataFrame()

        df = pd.merge_asof(
            dfs['00060'].sort_values('datetime'),
            dfs['00065'].sort_values('datetime'),
            on='datetime',
            tolerance=pd.Timedelta('1H'),
            direction='nearest'
        )

        df.rename(columns={'00060': 'discharge_cfs', '00065': 'gage_height_ft'}, inplace=True)
        return df

    except Exception as e:
        print(f"⚠️  Error fetching data for {site_id}: {e}")
        return pd.DataFrame()

def calculate_kayakability_score(discharge, gage_height, ideal_discharge_range, ideal_gage_range):
    if pd.isna(discharge) or pd.isna(gage_height):
        return 0
    score = 0
    if ideal_discharge_range[0] <= discharge <= ideal_discharge_range[1]:
        score += 50
    elif discharge < ideal_discharge_range[0]:
        score += max(0, 25 * (discharge / ideal_discharge_range[0]))
    else:
        score += max(0, 25 * (ideal_discharge_range[1] / discharge))
    if ideal_gage_range[0] <= gage_height <= ideal_gage_range[1]:
        score += 50
    elif gage_height < ideal_gage_range[0]:
        score += max(0, 25 * (gage_height / ideal_gage_range[0]))
    else:
        score += max(0, 25 * (ideal_gage_range[1] / gage_height))
    return min(100, max(0, round(score)))

def find_optimal_windows(forecast_df, window_hours=3, min_score=70):
    if forecast_df.empty:
        return []
    optimal_windows = []
    for site_id in forecast_df['site_id'].unique():
        site_data = forecast_df[forecast_df['site_id'] == site_id].copy()
        site_data = site_data.sort_values('datetime')
        site_data['window_score'] = site_data['kayakability_score'].rolling(
            window=window_hours, center=True).mean()
        good_windows = site_data[site_data['window_score'] >= min_score]
        if not good_windows.empty:
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
    optimal_windows.sort(key=lambda x: (-x['avg_score'], x['start_time']))
    return optimal_windows

def save_forecast_data(historical_df, forecast_df, optimal_windows, output_folder='kayak_forecast_data'):
    os.makedirs(output_folder, exist_ok=True)
    if not historical_df.empty:
        historical_df.to_csv(os.path.join(output_folder, 'historical_hourly_data.csv'), index=False)
    if not forecast_df.empty:
        forecast_df.to_csv(os.path.join(output_folder, 'forecast_data.csv'), index=False)
    if optimal_windows:
        pd.DataFrame(optimal_windows).to_csv(os.path.join(output_folder, 'optimal_windows.csv'), index=False)
    r
