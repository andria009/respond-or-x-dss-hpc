# RESPOND-OR-x-DSS-HPC
## (POIs + Hazard Risk Collector and Evacuation Route Planning)

Python scripts to collect Points of Interest (POI) data from OpenStreetMap, assess hazard risks using INARISK data, and find optimal evacuation routes from Villages to Shelters.

## Features

### POI and Hazard Risk Collector
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

### Evacuation Route Planning
- Finds optimal routes from villages to emergency shelters
- Considers multiple factors:
  - Road type quality (primary to footpath)
  - Distance optimization
  - Combined hazard risks
  - Road network accessibility
- Generates multiple route options per village
- Supports parallel processing for route calculation
- Individual route processing for better performance
- Configurable number of worker processes for route calculation
- Exports routes in GeoJSON format
- Interactive visualization of evacuation routes

## Requirements

- Python 3.12+
- Required packages:
  - osmnx
  - geopandas
  - pandas
  - requests
  - matplotlib
  - shapely
  - folium
  - networkx
  - branca

## Installation
Create a virtual environment:
```bash
$ python -m venv venv
$ sh venv/Scripts/activate
$ pip install -r requirements.txt
```

## Usage

### POI and Hazard Risk Collector
Run the script with the following arguments:
```bash
python main.py --lat LATITUDE --lon LONGITUDE --radius RADIUS_KM --poi-types TYPE1 [TYPE2 ...] \
  --hazards TYPE1 [TYPE2...] [--batch-size BATCH_SIZE] [--parallel --workers WORKERS] \
  [--debug] --output-dir OUTPUT_DIR
```
#### Arguments
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

#### Example
1. Basic sequential processing
```bash
python poi_risk_collector.py --lat 37.7749 --lon -122.4194 --radius 10 \
  --poi-types buildings villages --hazards earthquake flood \
  --output-dir my_pois
```
2. Parallel processing with 4 workers
```bash
python poi_risk_collector.py --lat 37.7749 --lon -122.4194 --radius 10 \
  --poi-types buildings villages --hazards earthquake flood --batch-size 10 \
  --parallel --workers 4 --output-dir my_pois
```
3. Debug mode
```bash
python poi_risk_collector.py --lat 37.7749 --lon -122.4194 --radius 10 \
  --poi-types buildings villages --hazards earthquake flood --batch-size 10 \
  --debug --output-dir my_pois
```
#### Output
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

#### Visualization
The program generates interactive HTML maps for each hazard type:
- Color gradients from blue (low risk) to red (high risk)
- Road networks colored by risk level
- Village boundaries with aggregated risk values
- Clickable features with risk information
- Layer toggles for different POI types
- Risk level legend

#### Performance Notes
- Parallel processing can significantly improve performance when:
  - Collecting multiple POI types
  - Processing large areas
  - Assessing multiple hazard types
- The optimal number of workers depends on your CPU cores and system resources
- Debug mode provides detailed progress but may slow down execution

### Evacuation Route Planning

After collecting POIs and risk data, run the route planning script:
```bash
python routes_builder.py --input-dir INPUT_DIR [--debug] \
  [--max-routes MAX_ROUTES] \
  [--parallel --workers WORKERS] [--debug] \
  --output-dir OUTPUT_DIR 
```
#### Arguments
Route Planning Arguments:
- `--input-dir` : Directory containing POI files (roads, villages, shelters)
- `--max-routes` : Maximum number of alternative routes per village (default: 3)
- `--parallel` : Enable parallel processing for faster execution
- `--workers` : Number of worker processes for parallel processing (default: 4)
- `--debug` : Enable detailed output process
- `--output-dir` : Output directory for routes and visualizationfiles 

#### Example
1. Basic sequential processing
```bash
python routes_builder.py --input-dir my_pois \
  --output-dir my_pois_routes
```
2. Parallel processing with 4 workers
```bash
python routes_builder.py --input-dir my_pois \
  --parallel --workers 4 \
  --output-dir my_pois_routes
```
3. Debug mode
```bash
python routes_builder.py --input-dir my_pois \
  --max-routes 5 --parallel --workers 4 --debug \
  --output-dir my_pois_routes
```

#### Output
The script generates:
- routes.geojson : Contains all calculated evacuation routes
- evacuation_routes_map.html : Interactive visualization showing:
  - Villages (blue markers)
  - Shelters (red markers)
  - Evacuation routes colored by risk level (green to red)
  - Route details (distance, risk score, road quality)
  - Individual toggles for:
    - Each village
    - Each shelter
    - Specific village-to-shelter routes
  - Risk level color legend
  - Layer control panel

#### Visualization Features
The evacuation route visualization includes:

- Color-coded routes based on risk level (0-1):
  - Green: Low risk
  - Yellow: Medium risk
  - Red: High risk
- Interactive layer toggles for:
  - All villages/shelters
  - Individual villages and shelters
  - Specific evacuation routes
- Route information on hover:
  - Village and shelter names
  - Total distance
  - Average risk score
  - Worst road type quality
- Expandable layer control panel
- Risk level legend

#### Performance Notes
- Parallel processing improves performance when:
  - Processing large number of villages
  - Finding routes to multiple shelters
  - Calculating multiple alternative routes
- Route finding can be CPU-intensive, especially for:
  - Complex road networks
  - Large search areas
  - Multiple alternative paths
- Memory usage increases with:
  - Number of parallel workers
  - Size of road network
  - Number of villages and shelters

## License
MIT License