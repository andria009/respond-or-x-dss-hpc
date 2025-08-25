# RESPOND-OR-X-DSS-HPC Integration with respondor-main Input Format

This document describes the successful integration that allows respond-or-x-dss-hpc to accept the same input format as respondor-main.

## Overview

The respond-or-x-dss-hpc system has been modified to accept CSV-based POI input files and JSON configuration files, making it compatible with respondor-main's input format while maintaining its core functionality for disaster risk assessment and evacuation route planning.

## New Components

### 1. Main Script: `main_respondor.py`
- Accepts JSON configuration files (similar to respondor-main's input.json)
- Processes CSV POI files with format: `name,category,lat,lng,[additional_columns]`
- Supports both standalone operation and integration with existing network data

### 2. CSV POI Collector: `src/poi_collector_csv.py`
- Processes CSV files instead of querying OpenStreetMap directly
- Groups POIs by category (village, shelter, depot, etc.)
- Maintains risk assessment capabilities using INARISK API
- Can use existing road network data or collect new data from OSM

### 3. Network Processor: `src/network_processor.py`
- Reads PYCGR network files (respondor-main format)
- Converts between NetworkX graphs and GeoDataFrames
- Creates subnetworks based on POI locations
- Matches POIs to network nodes

## Input Format

### JSON Configuration File
```json
{
    "name": "project_name",
    "output_dir": "output/directory",
    "poi_file": "path/to/locations.csv",
    "risk_category": "INDEKS_BAHAYA_GEMPABUMI",
    "assess_risks": true,
    "hazard_types": ["earthquake", "flood", "volcanic", "landslide"],
    "batch_size": 20,
    "parallel": true,
    "workers": 4,
    "debug": false,
    "generate_routes": true,
    "max_routes": 3,
    "use_existing_network": false,
    "network_pycgr_file": "path/to/network.pycgrc",
    "output_respondor_format": true
}
```

### CSV POI File Format
```csv
name,category,lat,lng,[additional_columns]
ANCOL,village,-6.125215,106.8362474
SHELTER_1,shelter,-6.1200000,106.8300000
```

Supported categories:
- `village` → mapped to `villages`
- `shelter` → mapped to `shelter`
- `depot` → mapped to `shelter` (treated as evacuation destination)
- `warehouse` → mapped to `shelter`
- `airport` → mapped to `shelter`
- `hospital` → mapped to `shelter`
- `clinic` → mapped to `shelter`

## Usage

### 1. Setup Environment
```bash
# Create virtual environment in parent directory (shared between projects)
python3 -m venv ../respondor_env

# Activate environment
source ../respondor_env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Basic Usage (CSV + OSM)
```bash
python main_respondor.py config.json
```

### 3. Advanced Usage (with existing network)
```bash
# Set use_existing_network: true in config.json
python main_respondor.py config_with_network.json
```

## Output Files

The system can generate output in two formats:

### 1. Original respond-or-x-dss-hpc Format (GeoJSON)
- `villages.geojson` - Village/community locations with risk data
- `shelter.geojson` - Emergency shelters and safe locations
- `roads.geojson` - Road network with risk assessments
- `routes/evacuation_routes.geojson` - Calculated evacuation routes
- `routes/evacuation_routes_map.html` - Interactive route visualization
- `map_*_risk.html` - Risk visualization maps for each hazard type

### 2. respondor-main Compatible Format
When `output_respondor_format: true` (default), the system also generates:

**CSV Files:**
- `nodes.csv` - Network nodes with coordinates and risk data
  ```csv
  Node Id,Latitude,Longitude,Risk
  0,-6.1231755,106.8451135,0.555556
  ```
- `links.csv` - Network edges with properties and risk data
  ```csv
  Source,Target,Risk,Length,Max_Speed,Bidirectional
  0,1,0.728395,56.14,50,1
  ```
- `{project_name}_locations.csv` - Processed POI locations with node IDs
  ```csv
  ANCOL,village,-6.125215,106.8362474,10000
  ```

**PYCGRC Format Files:**
- `{project_name}_subnetwork.pycgrc` - Binary network format
- `{project_name}_subnetwork.pycgrc_node_risk` - Space-separated node risks
- `{project_name}_subnetwork.pycgrc_risk` - Space-separated edge risks

**JSON Format:**
- `{project_name}_subnetwork.json` - NetworkX adjacency format

## Key Features

### Input Compatibility
- ✅ Accepts respondor-main CSV POI format
- ✅ Accepts respondor-main JSON configuration format  
- ✅ Can process existing PYCGR network files
- ✅ Maintains backward compatibility with original command-line interface

### Core Functionality Preserved
- ✅ INARISK risk assessment integration
- ✅ Multiple hazard type support (earthquake, flood, volcanic, landslide)
- ✅ Parallel processing capabilities
- ✅ Route optimization and visualization
- ✅ Interactive map generation

### Network Processing
- ✅ Reads PYCGR network files
- ✅ Matches POIs to network nodes
- ✅ Creates optimized subnetworks
- ✅ Converts between different data formats

## Testing

### Simple Test
```bash
# Create test POI file
echo "VILLAGE_1,village,-6.125215,106.8362474" > test.csv
echo "SHELTER_1,shelter,-6.120000,106.830000" >> test.csv

# Create test config
cat > test_config.json << EOF
{
    "name": "test",
    "output_dir": "output/test",
    "poi_file": "test.csv",
    "assess_risks": false,
    "generate_routes": true,
    "debug": true
}
EOF

# Run test
python main_respondor.py test_config.json
```

## Integration Benefits

1. **Unified Interface**: Both systems now accept the same input format
2. **Data Reusability**: POI data can be shared between systems
3. **Enhanced Network Processing**: Combines respondor-main's network optimization with respond-or-x-dss-hpc's risk assessment
4. **Flexible Deployment**: Can operate standalone or as part of larger workflow
5. **Preserved Functionality**: All original features remain available

## Performance Notes

- Large datasets (10,000+ POIs) may take several minutes to process
- Network processing with existing PYCGR files is faster than OSM collection
- Parallel processing significantly improves performance for risk assessment
- Route generation time depends on network complexity and number of POIs

The integration successfully bridges the gap between respondor-main's network optimization capabilities and respond-or-x-dss-hpc's comprehensive risk assessment and visualization features.