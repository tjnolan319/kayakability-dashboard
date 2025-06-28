import requests
import csv
import os
from datetime import datetime
import time

# Configuration for Sites (Shortened for brevity)
merrimack_sites = {
    "01073500": {
        "name": "Merrimack River below Concord River at Lowell, MA",
        "lat": 42.6334,
        "lon": -71.3162,
        "ideal_discharge_range": (800, 2000),
        "ideal_gage_range": (2.0, 4.5)
    },
    "01100000": {
        "name": "Merrimack River at Lowell, MA", 
        "lat": 42.65,
        "lon": -71.30,
        "ideal_discharge_range": (1000, 2500),
        "ideal_gage_range": (1.5, 5.0)
    },
    "01096500": {
        "name": "Merrimack River at North Chelmsford, MA",
        "lat": 42.6278,
        "lon": -71.3667,
        "ideal_discharge_range": (800, 2200),
        "ideal_gage_range": (2.0, 4.8)
    },
    "01094000": {
        "name": "Merrimack River near Goffs Falls below Manchester, NH",
        "lat": 43.0167,
        "lon": -71.4833,
        "ideal_discharge_range": (600, 1800),
        "ideal_gage_range": (1.8, 4.2)
    },
    "01092000": {
        "name": "Merrimack River at Franklin Junction, NH",
        "lat": 43.4361,
        "lon": -71.6472,
        "ideal_discharge_range": (400, 1500),
        "ideal_gage_range": (1.5, 3.8)
    }
}

parameter_codes = {
    '00060': 'discharge_cfs',
    '00065': 'gage_height_ft'
}

def append_to_csv(file_path, fieldnames, rows):
    """Append rows to CSV, create file with header if not exists"""
    if not rows:  # Don't create empty files
        return
    
    file_exists = os.path.isfile(file_path)
    mode = 'a' if file_exists else 'w'
    
    with open(file_path, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)

def calculate_kayakability_score(discharge, gage_height, ideal_discharge_range, ideal_gage_range):
    """Calculate kayakability score based on discharge and gage height"""
    score = 0
    
    # Check discharge
    if ideal_discharge_range[0] <= discharge <= ideal_discharge_range[1]:
        score += 50
    elif discharge < ideal_discharge_range[0]:
        # Too low
        ratio = discharge / ideal_discharge_range[0]
        score += max(0, 25 * ratio)
    else:
        # Too high
        ratio = ideal_discharge_range[1] / discharge
        score += max(0, 25 * ratio)
    
    # Check gage height
    if ideal_gage_range[0] <= gage_height <= ideal_gage_range[1]:
        score += 50
    elif gage_height < ideal_gage_range[0]:
        # Too low
        ratio = gage_height / ideal_gage_range[0]
        score += max(0, 25 * ratio)
    else:
        # Too high
        ratio = ideal_gage_range[1] / gage_height
        score += max(0, 25 * ratio)
    
    return min(100, max(0, round(score)))

def write_split_csvs(site_data_list, output_folder='data_exports'):
    """Write data to separate CSV files"""
    if not site_data_list:
        print("❌ No data to write")
        return

    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Define file paths
    river_file = os.path.join(output_folder, 'river_data.csv')
    weather_file = os.path.join(output_folder, 'weather_data.csv')
    combined_file = os.path.join(output_folder, 'combined_data.csv')

    # Define headers
    river_headers = [
        'site_id', 'site_name', 'discharge_cfs', 'gage_height_ft',
        'timestamp', 'lat', 'lon', 'kayakability_score'
    ]

    weather_headers = [
        'site_id', 'site_name', 'lat', 'lon',
        'temperature_f', 'humidity_percent', 'wind_speed_mph',
        'wind_direction', 'weather_description', 'precipitation_chance', 'weather_timestamp'
    ]

    combined_headers = [
        'site_id', 'site_name', 'lat', 'lon', 'timestamp',
        'discharge_cfs', 'gage_height_ft', 'kayakability_score',
        'temperature_f', 'humidity_percent', 'wind_speed_mph',
        'wind_direction', 'weather_description', 'precipitation_chance', 'weather_timestamp'
    ]

    river_rows = []
    weather_rows = []
    combined_rows = []

    for site_data in site_data_list:
        # River data row
        river_row = {key: site_data.get(key) for key in river_headers}
        river_rows.append(river_row)

        # Weather data row (only if weather data exists)
        if site_data.get('weather_timestamp'):
            weather_row = {key: site_data.get(key) for key in weather_headers}
            weather_rows.append(weather_row)

        # Combined data row
        combined_row = {key: site_data.get(key) for key in combined_headers}
        combined_rows.append(combined_row)

    # Write the files
    append_to_csv(river_file, river_headers, river_rows)
    print(f"✅ Written {len(river_rows)} rows to {river_file}")

    if weather_rows:
        append_to_csv(weather_file, weather_headers, weather_rows)
        print(f"✅ Written {len(weather_rows)} rows to {weather_file}")
    else:
        print("⚠️  No weather data to write")

    append_to_csv(combined_file, combined_headers, combined_rows)
    print(f"✅ Written {len(combined_rows)} rows to {combined_file}")

    return {
        'river_file': river_file,
        'weather_file': weather_file,
        'combined_file': combined_file,
        'output_folder': output_folder
    }

def fetch_usgs_data(site_id):
    """Fetch real USGS data for a site"""
    base_url = "https://waterservices.usgs.gov/nwis/iv/"
    params = {
        'format': 'json',
        'sites': site_id,
        'parameterCd': '00060,00065',  # discharge and gage height
        'siteStatus': 'active'
    }
    
    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'value' not in data or 'timeSeries' not in data['value']:
            return None, None
            
        discharge = None
        gage_height = None
        timestamp = None
        
        for series in data['value']['timeSeries']:
            param_code = series['variable']['variableCode'][0]['value']
            if series['values'] and series['values'][0]['value']:
                latest_value = series['values'][0]['value'][-1]
                if param_code == '00060':  # discharge
                    discharge = float(latest_value['value'])
                    timestamp = latest_value['dateTime']
                elif param_code == '00065':  # gage height
                    gage_height = float(latest_value['value'])
                    timestamp = latest_value['dateTime']
        
        return discharge, gage_height, timestamp
        
    except Exception as e:
        print(f"⚠️  Error fetching USGS data for {site_id}: {e}")
        return None, None, None

def main():
    """Main function to collect and save data"""
    print("🚀 Starting kayak conditions data collection...")
    
    all_site_data = []
    
    for site_id, site_info in merrimack_sites.items():
        print(f"📊 Processing site: {site_info['name']}")
        
        # Try to fetch real data, fall back to dummy data
        discharge, gage_height, timestamp = fetch_usgs_data(site_id)
        
        if discharge is None or gage_height is None:
            print(f"⚠️  Using dummy data for {site_id}")
            discharge = 1000.0
            gage_height = 3.2
            timestamp = datetime.now().isoformat()
        
        # Calculate kayakability score
        kayakability_score = calculate_kayakability_score(
            discharge, gage_height,
            site_info['ideal_discharge_range'],
            site_info['ideal_gage_range']
        )
        
        # Create site data record
        site_data = {
            'site_id': site_id,
            'site_name': site_info['name'],
            'discharge_cfs': discharge,
            'gage_height_ft': gage_height,
            'timestamp': timestamp,
            'lat': site_info['lat'],
            'lon': site_info['lon'],
            'kayakability_score': kayakability_score,
            # Weather data (dummy for now - you can add real weather API calls here)
            'temperature_f': 68,
            'humidity_percent': 50,
            'wind_speed_mph': 10,
            'wind_direction': 'SSE',
            'weather_description': 'Sunny',
            'precipitation_chance': 10,
            'weather_timestamp': datetime.now().isoformat()
        }
        
        all_site_data.append(site_data)
        time.sleep(1)  # Be nice to the API
    
    # Write the data to CSV files
    file_info = write_split_csvs(all_site_data)
    
    print(f"\n🎉 Data collection complete!")
    print(f"📁 Files created in: {file_info['output_folder']}")
    print(f"📊 River data: {os.path.basename(file_info['river_file'])}")
    print(f"🌤️  Weather data: {os.path.basename(file_info['weather_file'])}")
    print(f"🔗 Combined data: {os.path.basename(file_info['combined_file'])}")

if __name__ == "__main__":
    main()
