import os
import time
import requests
import pandas as pd
from site_config import merrimack_sites
from time_series_analysis import (
    calculate_kayakability_score,
    forecast_conditions,
    find_optimal_windows,
)

def fetch_hourly_usgs_data(site_id, days_back=7):
    """
    Fetch hourly USGS data for the given site ID and number of days back.
    Returns a DataFrame with columns: datetime, discharge_cfs, gage_height_ft
    """
    # Calculate start time in epoch (seconds)
    end_time = pd.Timestamp.utcnow()
    start_time = end_time - pd.Timedelta(days=days_back)

    url = (
        f"https://waterservices.usgs.gov/nwis/iv/"
        f"?format=json&sites={site_id}"
        f"&parameterCd=00060,00065"
        f"&startDT={start_time.strftime('%Y-%m-%dT%H:%M:%S')}"
        f"&endDT={end_time.strftime('%Y-%m-%dT%H:%M:%S')}"
        f"&siteStatus=all"
    )

    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"Error fetching data for site {site_id}: {e}")
        return pd.DataFrame()

    try:
        # Parse JSON into DataFrame
        time_series = data['value']['timeSeries']
        # Create empty lists to hold parsed data
        records = []

        # Extract discharge (00060) and gage height (00065) series
        discharge_series = None
        gage_series = None
        for series in time_series:
            param_code = series['variable']['variableCode'][0]['value']
            if param_code == '00060':  # discharge
                discharge_series = series
            elif param_code == '00065':  # gage height
                gage_series = series

        if discharge_series is None or gage_series is None:
            print(f"Missing discharge or gage height data for site {site_id}")
            return pd.DataFrame()

        # Create dicts of datetime to value for each parameter
        discharge_data = {
            point['dateTime']: float(point['value'])
            for point in discharge_series['values'][0]['value']
            if point['value'] is not None
        }
        gage_data = {
            point['dateTime']: float(point['value'])
            for point in gage_series['values'][0]['value']
            if point['value'] is not None
        }

        # Combine by datetime (intersection)
        common_times = set(discharge_data.keys()) & set(gage_data.keys())
        for dt in sorted(common_times):
            records.append({
                'datetime': pd.to_datetime(dt),
                'discharge_cfs': discharge_data[dt],
                'gage_height_ft': gage_data[dt]
            })

        df = pd.DataFrame(records)
        return df

    except Exception as e:
        print(f"Error parsing data for site {site_id}: {e}")
        return pd.DataFrame()

def save_forecast_data(historical_df, forecast_df, optimal_windows, output_folder='kayak_forecast_data'):
    os.makedirs(output_folder, exist_ok=True)

    # Save historical data
    historical_file = os.path.join(output_folder, 'historical_hourly_data.csv')
    if not historical_df.empty:
        historical_df.to_csv(historical_file, index=False)
    else:
        pd.DataFrame(columns=[
            'datetime', 'discharge_cfs', 'gage_height_ft',
            'site_id', 'site_name', 'kayakability_score'
        ]).to_csv(historical_file, index=False)

    # Save forecast data
    forecast_file = os.path.join(output_folder, 'forecast_data.csv')
    if not forecast_df.empty:
        forecast_df.to_csv(forecast_file, index=False)
    else:
        pd.DataFrame(columns=[
            'site_id', 'site_name', 'datetime', 'discharge_cfs',
            'gage_height_ft', 'kayakability_score', 'forecast_type'
        ]).to_csv(forecast_file, index=False)

    # Save optimal windows
    windows_file = os.path.join(output_folder, 'optimal_windows.csv')
    if optimal_windows:
        pd.DataFrame(optimal_windows).to_csv(windows_file, index=False)
    else:
        pd.DataFrame(columns=[
            'site_id', 'site_name', 'start_time', 'end_time',
            'duration_hours', 'avg_score', 'max_score',
            'avg_discharge', 'avg_gage'
        ]).to_csv(windows_file, index=False)

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

        # Save historical data to CSV for this site (so time_series_analysis can read it)
        site_folder = "kayak_forecast_data"
        os.makedirs(site_folder, exist_ok=True)
        csv_path = os.path.join(site_folder, f"{site_id}_historical.csv")
        historical_df.to_csv(csv_path, index=False)

        # Generate forecast (pass CSV path now)
        print("  🔮 Generating 10-day forecast...")
        forecast_df = forecast_conditions(site_id, site_info, csv_path)

        if not forecast_df.empty:
            all_forecast_data.append(forecast_df)

            # Find optimal windows
            windows = find_optimal_windows(forecast_df)
            all_optimal_windows.extend(windows)

            print(f"  ✅ Found {len(windows)} optimal windows")
        else:
            print("  ⚠️  Could not generate forecast")

        time.sleep(1)  # Respect API limits

    # Combine all data
    combined_historical = pd.concat(all_historical_data, ignore_index=True) if all_historical_data else pd.DataFrame()
    combined_forecast = pd.concat(all_forecast_data, ignore_index=True) if all_forecast_data else pd.DataFrame()

    # Save combined files
    output_folder = save_forecast_data(combined_historical, combined_forecast, all_optimal_windows)

    # Output recommendations
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
    try:
        results = main()
        print("\n✅ System completed successfully!")
    except Exception as e:
        print(f"\n❌ System error: {e}")
        print("Make sure you have installed: pip install requests pandas numpy scikit-learn")
