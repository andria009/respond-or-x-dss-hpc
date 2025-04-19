# OpenStreetMap POI Collector

A Python application to collect Points of Interest (POI) data from OpenStreetMap and assess hazard risks using INARISK data.

## Features

- Collect various types of POIs:
  - Buildings
  - Villages
  - Shelters
  - Road networks
- Assess hazard risks from INARISK:
  - Earthquake
  - Flood
  - Volcanic
  - Landslide
- Specify search area by coordinates and radius
- Save results in GeoJSON format
- Organize outputs by POI type

## Installation
Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## Usage
Run the script with the following arguments:
```bash
python main.py --lat LATITUDE --lon LONGITUDE --radius RADIUS_KM --poi-types TYPE1 [TYPE2 ...] --output-dir OUTPUT_DIR
```
### Arguments
- `--lat` : Latitude of the center point
- `--lon` : Longitude of the center point
- `--radius` : Search radius in kilometers
- `--poi-types` : Types of POIs to collect (choices: buildings, villages, shelter, roads)
- `--no-risk` : Skip hazard risk assessment
- `--hazards` : Specific hazard types to assess (choices: earthquake, flood, volcanic, landslide)
- `--batch-size` : Number of points per INARISK API request (default: 20)
- `--debug` : Enable detailed output for API requests
- `--output-dir` : Output directory for POI files (default: pois_output)

### Example
```bash
python main.py --lat 37.7749 --lon -122.4194 --radius 10 --poi-types buildings villages --hazards earthquake flood --batch-size 10 --debug --output-dir my_pois
```
### Output
The program creates a directory containing separate GeoJSON files for each POI type. Each feature in the GeoJSON includes risk assessment values (if enabled):
- buildings.geojson
- roads.geojson
- shelter.geojson
- villages.geojson

Risk values range from 0 (lowest) to 1 (highest) for each hazard type:
- earthquake_risk
- flood_risk
- volcanic_risk
- landslide_risk