import requests
import csv
import os
from datetime import datetime
import time
import json

# --- Configuration for Multiple Sites ---
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

def get_nws_office_and_grid(lat, lon):
    """Get NWS office and grid coordinates for a location"""
    try:
        url = f"https://api.weather.gov/points/{lat},{lon}"
        headers = {'User-Agent': 'KayakabilityDashboard/1.0 (contact@example.com)'}
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            'office': data['properties']['gridId'],
            'grid_x': data['properties']['gridX'],
            'grid_y': data['properties']['gridY'],
            'forecast_url': data['properties']['forecast'],
            'forecast_hourly_url': data['properties']['forecastHourly']
        }
    except Exception as e:
        print(f"⚠️ Could not get NWS grid info for {lat}, {lon}: {e}")
        return None

def fetch_weather_data(lat, lon):
    """Fetch current weather and forecast from NWS API"""
    try:
        # Get grid info first
        grid_info = get_nws_office_and_grid(lat, lon)
        if not grid_info:
            return None
        
        headers = {'User-Agent': 'KayakabilityDashboard/1.0 (contact@example.com)'}
        
        # Get current conditions from gridpoint weather
        current_url = f"https://api.weather.gov/gridpoints/{grid_info['office']}/{grid_info['grid_x']},{grid_info['grid_y']}"
        
        current_response = requests.get(current_url, headers=headers, timeout=10)
        current_response.raise_for_status()
        current_data = current_response.json()
        
        # Get forecast
        forecast_response = requests.get(grid_info['forecast_url'], headers=headers, timeout=10)
        forecast_response.raise_for_status()
        forecast_data = forecast_response.json()
        
        # Extract current conditions
        props = current_data['properties']
        weather_info = {
            'temperature_f': None,
            'humidity_percent': None,
            'wind_speed_mph': None,
            'wind_direction': None,
            'weather_description': None,
            'precipitation_chance': None,
            'weather_timestamp': datetime.utcnow().isoformat()
        }
        
        # Temperature (convert from Celsius to Fahrenheit if needed)
        if 'temperature' in props and props['temperature']['values']:
            temp_c = props['temperature']['values'][0]['value']
            if temp_c is not None:
                weather_info['temperature_f'] = round((temp_c * 9/5) + 32, 1)
        
        # Humidity
        if 'relativeHumidity' in props and props['relativeHumidity']['values']:
            humidity = props['relativeHumidity']['values'][0]['value']
            if humidity is not None:
                weather_info['humidity_percent'] = round(humidity, 1)
        
        # Wind speed (convert from m/s to mph)
        if 'windSpeed' in props and props['windSpeed']['values']:
            wind_ms = props['windSpeed']['values'][0]['value']
            if wind_ms is not None:
                weather_info['wind_speed_mph'] = round(wind_ms * 2.237, 1)
        
        # Wind direction
        if 'windDirection' in props and props['windDirection']['values']:
            wind_dir = props['windDirection']['values'][0]['value']
            if wind_dir is not None:
                weather_info['wind_direction'] = get_wind_direction_text(wind_dir)
        
        # Get weather description and precipitation from forecast
        if 'periods' in forecast_data['properties'] and forecast_data['properties']['periods']:
            current_period = forecast_data['properties']['periods'][0]
            weather_info['weather_description'] = current_period.get('shortForecast', 'Unknown')
            
            # Look for precipitation chance in the current or next period
            for period in forecast_data['properties']['periods'][:2]:
                if period.get('probabilityOfPrecipitation', {}).get('value'):
                    weather_info['precipitation_chance'] = period['probabilityOfPrecipitation']['value']
                    break
        
        return weather_info
        
    except Exception as e:
        print(f"⚠️ Could not fetch weather data for {lat}, {lon}: {e}")
        return None

def get_wind_direction_text(degrees):
    """Convert wind direction degrees to text"""
    if degrees is None:
        return None
    
    directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                  "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    
    index = int((degrees + 11.25) / 22.5) % 16
    return directions[index]

def calculate_weather_impact_score(weather_data):
    """Calculate how weather conditions impact kayaking (0-100 scale)"""
    if not weather_data:
        return 50  # Neutral if no weather data
    
    score = 100
    
    # Temperature impact
    temp = weather_data.get('temperature_f')
    if temp is not None:
        if temp < 40:  # Very cold
            score -= 30
        elif temp < 50:  # Cold
            score -= 15
        elif temp > 90:  # Very hot
            score -= 15
        # 50-90°F is considered good
    
    # Wind impact
    wind_speed = weather_data.get('wind_speed_mph')
    if wind_speed is not None:
        if wind_speed > 20:  # High wind
            score -= 25
        elif wind_speed > 15:  # Moderate wind
            score -= 15
        elif wind_speed > 10:  # Light wind
            score -= 5
        # 0-10 mph is considered good
    
    # Precipitation impact
    precip_chance = weather_data.get('precipitation_chance')
    if precip_chance is not None:
        if precip_chance > 70:  # High chance of rain
            score -= 20
        elif precip_chance > 40:  # Moderate chance
            score -= 10
        elif precip_chance > 20:  # Light chance
            score -= 5
    
    # Weather description impact
    description = weather_data.get('weather_description', '').lower()
    if any(word in description for word in ['thunderstorm', 'severe']):
        score -= 40
    elif any(word in description for word in ['rain', 'showers']):
        score -= 15
    elif any(word in description for word in ['snow', 'ice']):
        score -= 35
    
    return max(score, 0)

def fetch_site_data(site_id, site_info):
    """Fetch data for a single site including weather"""
    print(f"🔄 Fetching data for {site_info['name']}...")
    
    # Build API URL for water data
    url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&parameterCd={','.join(parameter_codes.keys())}&siteStatus=all"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check if we have water data
        if 'value' not in data or 'timeSeries' not in data['value']:
            print(f"⚠️ No water data available for site {site_id}")
            return None
            
        series = data['value']['timeSeries']
        if not series:
            print(f"⚠️ No time series data for site {site_id}")
            return None
        
        # Initialize output
        output = {
            'site_id': site_id,
            'site_name': series[0]['sourceInfo']['siteName'],
            'discharge_cfs': None,
            'gage_height_ft': None,
            'timestamp': None,
            'lat': site_info['lat'],
            'lon': site_info['lon'],
            'water_score': None,
            'weather_score': None,
            'kayakability_score': None,
            # Weather fields
            'temperature_f': None,
            'humidity_percent': None,
            'wind_speed_mph': None,
            'wind_direction': None,
            'weather_description': None,
            'precipitation_chance': None,
            'weather_timestamp': None
        }
        
        # Extract latest water values
        for s in series:
            param_code = s['variable']['variableCode'][0]['value']
            
            if param_code in parameter_codes and s['values']:
                values = s['values'][0]['value']
                if values:  # Check if we have actual values
                    latest_value = values[0]
                    value_str = latest_value['value']
                    timestamp = latest_value['dateTime']
                    
                    if value_str and value_str != "":
                        try:
                            value = float(value_str)
                            output[parameter_codes[param_code]] = value
                            output['timestamp'] = timestamp
                        except ValueError:
                            print(f"⚠️ Could not parse value '{value_str}' for parameter {param_code}")
        
        # Fetch weather data
        print(f"🌤️ Fetching weather for {site_info['name']}...")
        weather_data = fetch_weather_data(site_info['lat'], site_info['lon'])
        
        if weather_data:
            # Add weather data to output
            for key, value in weather_data.items():
                output[key] = value
            
            # Calculate weather impact score
            output['weather_score'] = calculate_weather_impact_score(weather_data)
        
        # Calculate water conditions score
        if output['discharge_cfs'] is not None or output['gage_height_ft'] is not None:
            output['water_score'] = score_water_conditions(
                output['discharge_cfs'], 
                output['gage_height_ft'],
                site_info['ideal_discharge_range'],
                site_info['ideal_gage_range']
            )
            
            # Combined kayakability score (weighted average)
            water_weight = 0.7  # Water conditions are more important
            weather_weight = 0.3
            
            if output['water_score'] is not None and output['weather_score'] is not None:
                output['kayakability_score'] = round(
                    (output['water_score'] * water_weight) + (output['weather_score'] * weather_weight)
                )
            elif output['water_score'] is not None:
                output['kayakability_score'] = output['water_score']
            else:
                output['kayakability_score'] = 0
            
            return output
        else:
            print(f"⚠️ No valid water parameter data found for site {site_id}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data for site {site_id}: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error for site {site_id}: {e}")
        return None

def score_water_conditions(discharge, gage, ideal_discharge_range, ideal_gage_range):
    """Score water conditions only (renamed from score_kayakability)"""
    score = 100
    
    # Discharge scoring
    if discharge is not None:
        min_discharge, max_discharge = ideal_discharge_range
        if discharge < min_discharge * 0.5:  # Too low
            score -= 40
        elif discharge < min_discharge:  # Below ideal but manageable
            score -= 20
        elif discharge > max_discharge * 2:  # Dangerously high
            score -= 50
        elif discharge > max_discharge:  # Above ideal but manageable
            score -= 25
        # If within ideal range, no penalty
    
    # Gage height scoring
    if gage is not None:
        min_gage, max_gage = ideal_gage_range
        if gage < min_gage * 0.7:  # Too low
            score -= 30
        elif gage < min_gage:  # Below ideal but manageable
            score -= 15
        elif gage > max_gage * 1.5:  # Dangerously high
            score -= 40
        elif gage > max_gage:  # Above ideal but manageable
            score -= 20
        # If within ideal range, no penalty
    
    # If we have no data at all, mark as unknown
    if discharge is None and gage is None:
        score = 0
    
    return max(score, 0)

def write_to_csv(site_data_list, output_file='kayak_conditions.csv'):
    """Write all site data to CSV"""
    if not site_data_list:
        print("❌ No data to write")
        return
    
    file_exists = os.path.isfile(output_file)
    
    with open(output_file, 'a', newline='') as f:
        fieldnames = site_data_list[0].keys()
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
            print(f"📄 Created new file: {output_file}")
        
        for site_data in site_data_list:
            writer.writerow(site_data)
    
    print(f"✅ Data for {len(site_data_list)} sites appended to {output_file}")

def main():
    """Main execution function"""
    print("🛶 Merrimack River Multi-Site Data Collector with Weather")
    print("=" * 60)
    
    all_site_data = []
    successful_sites = 0
    
    for site_id, site_info in merrimack_sites.items():
        site_data = fetch_site_data(site_id, site_info)
        
        if site_data:
            all_site_data.append(site_data)
            successful_sites += 1
            
            # Print summary for this site
            print(f"✅ {site_data['site_name']}")
            print(f"   🎯 Overall Score: {site_data['kayakability_score']}")
            print(f"   💧 Water Score: {site_data['water_score']}")
            if site_data['weather_score']:
                print(f"   🌤️ Weather Score: {site_data['weather_score']}")
            
            # Water conditions
            if site_data['discharge_cfs']:
                print(f"   💧 Discharge: {site_data['discharge_cfs']:.1f} CFS")
            if site_data['gage_height_ft']:
                print(f"   📏 Gage Height: {site_data['gage_height_ft']:.2f} ft")
            
            # Weather conditions
            if site_data['temperature_f']:
                print(f"   🌡️ Temperature: {site_data['temperature_f']}°F")
            if site_data['wind_speed_mph']:
                wind_text = f"{site_data['wind_speed_mph']} mph"
                if site_data['wind_direction']:
                    wind_text += f" {site_data['wind_direction']}"
                print(f"   💨 Wind: {wind_text}")
            if site_data['weather_description']:
                print(f"   ☁️ Conditions: {site_data['weather_description']}")
            if site_data['precipitation_chance']:
                print(f"   🌧️ Precip Chance: {site_data['precipitation_chance']}%")
            
            print()
        
        # Small delay between requests to be respectful to APIs
        time.sleep(2)
    
    # Write all data to CSV
    if all_site_data:
        write_to_csv(all_site_data)
        
        print("=" * 60)
        print(f"🎯 Summary: {successful_sites}/{len(merrimack_sites)} sites successfully processed")
        
        # Show best conditions
        best_site = max(all_site_data, key=lambda x: x['kayakability_score'] or 0)
        print(f"🏆 Best conditions: {best_site['site_name']}")
        print(f"   Overall Score: {best_site['kayakability_score']}")
        print(f"   Water: {best_site['water_score']}, Weather: {best_site['weather_score']}")
        
    else:
        print("❌ No data collected from any sites")

if __name__ == "__main__":
    main()
