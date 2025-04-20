# POI and Hazard Risks Collector

A Python script to collect Points of Interest (POI) data from OpenStreetMap and assess hazard risks using INARISK data.

## Features

- Collects various POI types from OpenStreetMap:
  - Buildings
  - Villages (administrative boundaries)
  - Shelters (including):
    - Emergency assembly points and shelters
    - Community centers
    - Public buildings
    - Hospitals and healthcare facilities
    - Places of worship
  - Roads
- Assess multiple hazard risks from INARISK:
  - Earthquake
  - Flood
  - Volcanic
  - Landslide
- Supports parallel processing for faster data collection
- Generates GeoJSON outputs with risk assessments
- Creates visualization maps for collected POIs and their risks
- Batch processing for INARISK API requests
- Specify search area by coordinates and radius
- Save results in GeoJSON format
- Organize outputs by POI type
- Logging for debugging and monitoring

## Requirements

- Python 3.8+
- Required packages:
  - osmnx
  - geopandas
  - pandas
  - requests
  - matplotlib
  - shapely
  - folium

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
python main.py --lat LATITUDE --lon LONGITUDE --radius RADIUS_KM --poi-types TYPE1 [TYPE2 ...] \
  --hazards TYPE1 [TYPE2...] --batch-size BATCH_SIZE --parallel --workers WORKERS \
  --debug --output-dir OUTPUT_DIR
```
### Arguments
- `--lat` : Latitude of the center point
- `--lon` : Longitude of the center point
- `--radius` : Search radius in kilometers
- `--poi-types` : Types of POIs to collect (choices: buildings, villages, shelter, roads)
- `--no-risk` : Skip hazard risk assessment
- `--hazards` : Specific hazard types to assess (choices: earthquake, flood, volcanic, landslide)
- `--batch-size` : Number of points per INARISK API request (default: 20)
- `--parallel` : Enable parallel processing for faster execution
- `--workers` : Number of worker processes for parallel processing (default: 4)
- `--debug` : Enable detailed output for API requests
- `--output-dir` : Output directory for POI files (default: pois_output)

### Example
1. Basic sequential processing
```bash
python main.py --lat 37.7749 --lon -122.4194 --radius 10 --poi-types buildings villages --hazards earthquake flood --output-dir my_pois
```
2. Parallel processing with 4 workers
```bash
python main.py --lat 37.7749 --lon -122.4194 --radius 10 --poi-types buildings villages --hazards earthquake flood --batch-size 10 --parallel --workers 4 --output-dir my_pois
```
3. Debug mode
```bash
python main.py --lat 37.7749 --lon -122.4194 --radius 10 --poi-types buildings villages --hazards earthquake flood --batch-size 10 --debug --output-dir my_pois
```
### Output
The script generates:
- GeoJSON files for each POI type with risk assessments
- Risk visualization maps (if enabled):
  - buildings.geojson
  - roads.geojson
  - shelter.geojson
  - villages.geojson (administrative boundaries)

Risk values range from 0 (lowest) to 1 (highest) for each hazard type:
- earthquake_risk
- flood_risk
- volcanic_risk
- landslide_risk

### Visualization
The program generates interactive HTML maps for each hazard type:
- Color gradients from blue (low risk) to red (high risk)
- Road networks colored by risk level
- Village boundaries with aggregated risk values
- Clickable features with risk information
- Layer toggles for different POI types
- Risk level legend

### Performance Notes
- Parallel processing can significantly improve performance when:
  - Collecting multiple POI types
  - Processing large areas
  - Assessing multiple hazard types
- The optimal number of workers depends on your CPU cores and system resources
- Debug mode provides detailed progress but may slow down execution

## License
MIT License