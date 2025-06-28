import requests
import csv
from datetime import datetime

# --- Configuration ---
site_id = "01100000"  # Merrimack River at Lowell, MA
lat, lon = 42.65, -71.30  # Approximate coordinates
parameter_codes = {
    '00060': 'discharge_cfs',
    '00065': 'gage_height_ft'
}

# --- Build API URL ---
url = f"https://waterservices.usgs.gov/nwis/iv/?format=json&sites={site_id}&parameterCd={','.join(parameter_codes.keys())}&siteStatus=all"

# --- Fetch data ---
response = requests.get(url)
data = response.json()

# --- Extract values ---
series = data['value']['timeSeries']
output = {
    'site_id': site_id,
    'site_name': series[0]['sourceInfo']['siteName'],
    'discharge_cfs': None,
    'gage_height_ft': None,
    'timestamp': None,
    'lat': lat,
    'lon': lon,
    'kayakability_score': None
}

for s in series:
    param_code = s['variable']['variableCode'][0]['value']
    value_str = s['values'][0]['value'][0]['value']
    timestamp = s['values'][0]['value'][0]['dateTime']

    if param_code in parameter_codes:
        value = float(value_str) if value_str != "" else None
        output[parameter_codes[param_code]] = value
        output['timestamp'] = timestamp

# --- Scoring function ---
def score_kayakability(discharge, gage):
    score = 100

    # Example logic – adjust as needed
    if discharge is not None:
        if discharge < 500:
            score -= 30
        elif discharge > 2500:
            score -= 30

    if gage is not None:
        if gage < 1.5:
            score -= 20
        elif gage > 5:
            score -= 20

    return max(score, 0)

# --- Apply scoring ---
output['kayakability_score'] = score_kayakability(
    output['discharge_cfs'], output['gage_height_ft']
)

# --- Write to CSV ---
output_file = 'kayak_conditions.csv'
with open(output_file, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=output.keys())
    writer.writeheader()
    writer.writerow(output)

print(f"✅ Data written to {output_file}")
print(f"🛶 Site: {output['site_name']}")
print(f"📊 Score: {output['kayakability_score']}")
