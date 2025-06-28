# Kayakability Dashboard

This repository contains the code and data for a real-time Kayak Conditions Dashboard. The goal is to assess the paddling conditions on the Merrimack River (and potentially other rivers) using real-time data from USGS and other sources.

---

## Project Status

⚠️ **Work in Progress**  
This project is actively being developed. The current version fetches real-time river data (discharge and gage height) from the USGS API, calculates a simple kayakability score, and outputs the results as a CSV file for visualization.

Future improvements will include:  
- Adding weather data (wind, rain, temperature)  
- Expanding to multiple river sites  
- Enhancing the scoring algorithm  
- Connecting the data to Tableau for interactive visualization  
- Automating data updates via GitHub Actions

---

## How to Use

- The Python script `kayak_data_export.py` fetches and processes the data.  
- The output CSV (`kayak_conditions.csv`) contains the latest scores and can be used as a data source for dashboards.

---

## Notes

- This repository and data are public and intended for demonstration and portfolio purposes.  
- Please do not use this data for safety-critical decisions.

---

## Contact

For questions or suggestions, feel free to contact me directly.
