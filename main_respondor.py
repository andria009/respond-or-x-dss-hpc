#!/usr/bin/env python3
"""
Main script for respond-or-x-dss-hpc that accepts respondor-main input format
Takes a JSON configuration file similar to respondor-main input.json
"""

import json
import sys
import os
import csv
from src.poi_collector_csv import CSVPOICollector
from src.route_finder import RouteFinder
from src.network_processor import NetworkProcessor
from src.respondor_output_formatter import RespondorOutputFormatter
import pandas as pd

def validate_input_json(input_config):
    """Validate the input JSON configuration"""
    required_keys = ['name', 'output_dir', 'poi_file']
    for key in required_keys:
        if key not in input_config:
            raise ValueError(f"Missing required key: {key}")
    
    # Check if poi_file exists
    if not os.path.exists(input_config['poi_file']):
        raise FileNotFoundError(f"POI file not found: {input_config['poi_file']}")

def validate_poi_csv(poi_file):
    """
    Validate POI CSV file format (compatible with respondor-main format)
    Expected format: name, category, lat, lng, [additional columns]
    """
    lat_list = []
    lon_list = []
    name_list = []
    
    with open(poi_file) as f:
        reader = csv.reader(f)
        for row_num, row in enumerate(reader, 1):
            if len(row) < 4:
                raise ValueError(f"Row {row_num}: must have at least 4 columns (name, category, lat, lng)")
            
            name = row[0].strip()
            category = row[1].strip()
            
            try:
                lat = float(row[2])
                lon = float(row[3])
            except ValueError:
                raise ValueError(f"Row {row_num}: invalid coordinates - lat: {row[2]}, lng: {row[3]}")
            
            name_list.append(name)
            lat_list.append(lat)
            lon_list.append(lon)

    # Validate coordinate ranges
    lat_avg = sum(lat_list) / len(lat_list)
    lon_avg = sum(lon_list) / len(lon_list)
    
    if not (-90.0 <= lat_avg <= 90.0):
        raise ValueError(f"Invalid average latitude: {lat_avg}")
    if not (-180.0 <= lon_avg <= 180.0):
        raise ValueError(f"Invalid average longitude: {lon_avg}")

    # Check for unusual coordinates (threshold of 0.3 degrees)
    threshold = 0.3
    unusual_points = []
    for i in range(len(name_list)):
        if abs(lat_list[i] - lat_avg) > threshold or abs(lon_list[i] - lon_avg) > threshold:
            unusual_points.append(f"{i+1}: {name_list[i]} ({lat_list[i]}, {lon_list[i]})")
    
    if unusual_points:
        print("Warning: Unusual coordinates detected:")
        for point in unusual_points:
            print(f"  {point}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python main_respondor.py <input.json>")
        print("\nExpected JSON format:")
        print("""{
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
    "output_respondor_format": true,
    "use_existing_network": false
}""")
        sys.exit(1)

    input_json = sys.argv[1]
    
    # Load and validate input configuration
    with open(input_json) as f:
        config = json.load(f)
    
    validate_input_json(config)
    validate_poi_csv(config['poi_file'])
    
    # Set default values
    defaults = {
        'assess_risks': True,
        'hazard_types': ['earthquake', 'flood', 'volcanic', 'landslide'],
        'batch_size': 20,
        'parallel': True,
        'workers': 4,
        'debug': False,
        'generate_routes': True,
        'max_routes': 3,
        'risk_category': 'INDEKS_BAHAYA_GEMPABUMI',
        'use_existing_network': False,
        'output_respondor_format': True
    }
    
    for key, default_value in defaults.items():
        if key not in config:
            config[key] = default_value

    # Create output directory if it doesn't exist
    if not os.path.exists(config['output_dir']):
        os.makedirs(config['output_dir'])
        print(f"Created output directory: {config['output_dir']}")

    print(f"Processing project: {config['name']}")
    print(f"POI file: {config['poi_file']}")
    print(f"Output directory: {config['output_dir']}")
    print(f"Risk assessment: {'enabled' if config['assess_risks'] else 'disabled'}")
    
    if config['assess_risks']:
        print(f"Hazard types: {', '.join(config['hazard_types'])}")
        print(f"Risk category: {config['risk_category']}")
    
    print(f"Route generation: {'enabled' if config['generate_routes'] else 'disabled'}")
    
    # Process network data if available
    network_processor = NetworkProcessor(debug=config['debug'])
    roads_from_network = None
    
    if config.get('use_existing_network', False):
        if 'network_pycgr_file' in config and os.path.exists(config['network_pycgr_file']):
            print(f"Processing existing network file: {config['network_pycgr_file']}")
            
            # Create NetworkX graph from PYCGR file
            graph = network_processor.create_networkx_from_pycgr(config['network_pycgr_file'])
            
            # Match POIs to network nodes
            matched_pois = network_processor.match_pois_to_network(config['poi_file'], graph)
            
            # Create subnetwork based on POIs
            subnetwork = network_processor.create_subnetwork(matched_pois, graph)
            
            # Save subnetwork as GeoJSON for route processing
            subnetwork_path = os.path.join(config['output_dir'], 'roads.geojson')
            network_processor.save_network_as_geojson(subnetwork, subnetwork_path)
            
            # Save matched POIs
            matched_pois_path = os.path.join(config['output_dir'], 'matched_pois.csv')
            matched_pois.to_csv(matched_pois_path, index=False)
            print(f"Saved matched POIs to: {matched_pois_path}")
            
            # Convert network to GeoDataFrame for risk assessment
            roads_from_network = network_processor.create_roads_geodataframe(subnetwork)

    # Initialize CSV POI Collector
    collector = CSVPOICollector(
        output_dir=config['output_dir'],
        batch_size=config['batch_size'],
        debug=config['debug'],
        hazard_types=config['hazard_types'],
        parallel=config['parallel'],
        workers=config['workers']
    )
    
    # Process POIs from CSV file
    pois = collector.collect_from_csv(
        config['poi_file'],
        assess_risks=config['assess_risks'],
        existing_roads=roads_from_network
    )
    
    print(f"\nPOI collection complete. Processed {sum(len(poi_data) for poi_data in pois.values())} POIs")
    
    # Generate routes if requested
    if config['generate_routes']:
        # Check if we have the required POI types for routing
        required_files = []
        poi_files = {}
        
        for poi_type in ['villages', 'shelter', 'roads']:
            poi_file = os.path.join(config['output_dir'], f"{poi_type}.geojson")
            if os.path.exists(poi_file):
                poi_files[poi_type] = poi_file
            else:
                print(f"Warning: {poi_type}.geojson not found, skipping route generation")
        
        if len(poi_files) >= 3:  # Need villages, shelters, and roads
            print("\nStarting route generation...")
            
            try:
                finder = RouteFinder(
                    roads_file=poi_files['roads'],
                    villages_file=poi_files['villages'],
                    shelters_file=poi_files['shelter']
                )
                
                # Find routes
                if config['parallel']:
                    print(f"Using parallel processing with {config['workers']} workers")
                    # For now, use sequential processing (parallel version would need modification)
                    routes = finder.find_best_routes(max_routes=config['max_routes'])
                else:
                    routes = finder.find_best_routes(max_routes=config['max_routes'])
                
                if len(routes) > 0:
                    # Save routes
                    routes_output_dir = os.path.join(config['output_dir'], 'routes')
                    if not os.path.exists(routes_output_dir):
                        os.makedirs(routes_output_dir)
                    
                    output_file = os.path.join(routes_output_dir, 'evacuation_routes.geojson')
                    finder.save_routes(routes, output_file)
                    
                    # Create visualization
                    finder.visualize_routes(routes, routes_output_dir)
                    
                    print(f"Route generation complete. Found {len(routes)} routes.")
                    print(f"Routes saved to: {output_file}")
                else:
                    print("No routes found.")
                    
            except Exception as e:
                print(f"Route generation failed: {e}")
        else:
            print("Insufficient POI data for route generation (need villages, shelters, and roads)")
    
    # Generate respondor-main compatible output format if requested
    if config.get('output_respondor_format', True):
        print(f"\nGenerating respondor-main compatible output format...")
        
        formatter = RespondorOutputFormatter(
            project_name=config['name'],
            output_dir=config['output_dir'],
            debug=config['debug']
        )
        
        formatter.generate_respondor_outputs(
            pois=pois,
            original_csv_path=config['poi_file'],
            assess_risks=config['assess_risks']
        )
        
        print(f"Respondor-main format outputs generated successfully!")
    
    print(f"\nProcessing complete. Results saved in: {config['output_dir']}")

if __name__ == "__main__":
    main()