import requests
import csv
import os
from datetime import datetime
import time

# Configuration for Sites (Shortened for brevity)
merrimack_sites = {
    "01073500": {"name": "Merrimack River below Concord River at Lowell, MA", "lat": 42.6334, "lon": -71.3162, "ideal_discharge_range": (800, 2000), "ideal_gage_range": (2.0, 4.5)},
    "01100000": {"name": "Merrimack River at Lowell, MA", "lat": 42.65, "lon": -71.30, "ideal_discharge_range": (1000, 2500), "ideal_gage_range": (1.5, 5.0)},
    # ... add other sites as needed
}

parameter_codes = {'00060': 'discharge_cfs', '00065': 'gage_height_ft'}

def write_split_csvs(site_data_list, output_folder='data_exports'):
    if not site_data_list:
        print("❌ No data to write")
        return

    os.makedirs(output_folder, exist_ok=True)

    river_file = os.path.join(output_folder, 'river_data.csv')
    weather_file = os.path.join(output_folder, 'weather_data.csv')
    combined_file = os.path.join(output_folder, 'combined_data.csv')

    river_headers = [
        'site_id', 'site_name', 'discharge_cfs', 'gage_height_ft',
        'timestamp', 'lat', 'lon', 'kayakability_score'
    ]

    weather_headers = [
        'site_id', 'site_name', 'temperature_f', 'humidity_percent', 'wind_speed_mph',
        'wind_direction', 'weather_description', 'precipitation_chance', 'weather_timestamp'
    ]

    combined_headers = river_headers + weather_headers[2:]  # avoid repeating site_id, site_name

    # Prepare rows for each file
    river_rows = []
    weather_rows = []
    combined_rows = []

    for site_data in site_data_list:
        # River data row
        river_row = {key: site_data.get(key) for key in river_headers}
        river_rows.append(river_row)

        # Weather data row — only if weather_timestamp exists
        if site_data.get('weather_timestamp'):
            weather_row = {key: site_data.get(key) for key in weather_headers}
            weather_rows.append(weather_row)

        # Combined data row
        combined_row = {key: site_data.get(key) for key in combined_headers}
        combined_rows.append(combined_row)

    # Write or append function
    def write_csv(file_path, fieldnames, rows):
        file_exists = os.path.isfile(file_path)
        mode = 'a' if file_exists else 'w'

        with open(file_path, mode, newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
                print(f"📄 Created new file: {file_path}")
            writer.writerows(rows)
        print(f"✅ {'Appended' if file_exists else 'Wrote'} {len(rows)} rows to {file_path}")

    # Write all three files
    write_csv(river_file, river_headers, river_rows)
    write_csv(weather_file, weather_headers, weather_rows)
    write_csv(combined_file, combined_headers, combined_rows)

def main():
    all_site_data = []
    for site_id, site_info in merrimack_sites.items():
        # Simulate fetching (replace this with real fetch_site_data call)
        dummy = {
            'site_id': site_id,
            'site_name': site_info['name'],
            'discharge_cfs': 1000.0,
            'gage_height_ft': 3.2,
            'timestamp': datetime.now().isoformat(),
            'lat': site_info['lat'],
            'lon': site_info['lon'],
            'kayakability_score': 75,
            'temperature_f': 68,
            'humidity_percent': 50,
            'wind_speed_mph': 10,
            'wind_direction': 'SSE',
            'weather_description': 'Sunny',
            'precipitation_chance': 10,
            'weather_timestamp': datetime.now().isoformat()
        }
        all_site_data.append(dummy)
        time.sleep(1)

    write_split_csvs(all_site_data)

if __name__ == "__main__":
    main()
