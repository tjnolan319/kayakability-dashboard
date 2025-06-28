import requests
import csv
import os
from datetime import datetime
import time

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

def fetch_site_data(site_id, site_info):
    """Fetch data for a single site"""
    print(f"🔄 Fetching data for {site_info['name']}...")
    
    # Build API URL
    url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&parameterCd={','.join(parameter_codes.keys())}&siteStatus=all"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check if we have data
        if 'value' not in data or 'timeSeries' not in data['value']:
            print(f"⚠️ No data available for site {site_id}")
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
            'kayakability_score': None
        }
        
        # Extract latest values
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
        
        # Apply scoring if we have data
        if output['discharge_cfs'] is not None or output['gage_height_ft'] is not None:
            output['kayakability_score'] = score_kayakability(
                output['discharge_cfs'], 
                output['gage_height_ft'],
                site_info['ideal_discharge_range'],
                site_info['ideal_gage_range']
            )
            return output
        else:
            print(f"⚠️ No valid parameter data found for site {site_id}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching data for site {site_id}: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error for site {site_id}: {e}")
        return None

def score_kayakability(discharge, gage, ideal_discharge_range, ideal_gage_range):
    """Enhanced scoring function with site-specific ideal ranges"""
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
    print("🛶 Merrimack River Multi-Site Data Collector")
    print("=" * 50)
    
    all_site_data = []
    successful_sites = 0
    
    for site_id, site_info in merrimack_sites.items():
        site_data = fetch_site_data(site_id, site_info)
        
        if site_data:
            all_site_data.append(site_data)
            successful_sites += 1
            
            # Print summary for this site
            print(f"✅ {site_data['site_name']}")
            print(f"   📊 Score: {site_data['kayakability_score']}")
            if site_data['discharge_cfs']:
                print(f"   💧 Discharge: {site_data['discharge_cfs']:.1f} CFS")
            if site_data['gage_height_ft']:
                print(f"   📏 Gage Height: {site_data['gage_height_ft']:.2f} ft")
            print()
        
        # Small delay between requests to be respectful to the API
        time.sleep(1)
    
    # Write all data to CSV
    if all_site_data:
        write_to_csv(all_site_data)
        
        print("=" * 50)
        print(f"🎯 Summary: {successful_sites}/{len(merrimack_sites)} sites successfully processed")
        
        # Show best conditions
        best_site = max(all_site_data, key=lambda x: x['kayakability_score'])
        print(f"🏆 Best conditions: {best_site['site_name']} (Score: {best_site['kayakability_score']})")
        
    else:
        print("❌ No data collected from any sites")

if __name__ == "__main__":
    main()
