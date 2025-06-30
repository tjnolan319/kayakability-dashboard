import os
import time
import pandas as pd
from site_config import merrimack_sites
from time_series_analysis import (
    fetch_hourly_usgs_data,
    calculate_kayakability_score,
    forecast_conditions,
    find_optimal_windows,
)

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

        # Generate forecast
        print("  🔮 Generating 10-day forecast...")
        forecast_df = forecast_conditions(site_id, site_info, historical_df)

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

    # Save files
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
