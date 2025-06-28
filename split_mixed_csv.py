import csv

# Input file (the corrupted/mixed one)
input_file = "mixed_data.csv"

# Output files
river_output_file = "river_data.csv"
weather_output_file = "weather_data.csv"

# Headers
river_headers = [
    "site_id", "site_name", "discharge_cfs", "gage_height_ft",
    "timestamp", "lat", "lon", "kayakability_score"
]

weather_headers = river_headers + [
    "temp", "dew_point", "feels_like", "humidity", "visibility",
    "wind_dir", "weather", "cloud_cover", "obs_time"
]

# Open and split the file
with open(input_file, "r", newline="") as infile, \
     open(river_output_file, "w", newline="") as river_out, \
     open(weather_output_file, "w", newline="") as weather_out:

    reader = csv.reader(infile)
    river_writer = csv.writer(river_out)
    weather_writer = csv.writer(weather_out)

    # Write headers
    river_writer.writerow(river_headers)
    weather_writer.writerow(weather_headers)

    for row in reader:
        if len(row) == 8:
            river_writer.writerow(row)
        elif len(row) == 17:
            weather_writer.writerow(row)
        else:
            print(f"⚠️ Skipped row with unexpected length {len(row)}: {row}")
