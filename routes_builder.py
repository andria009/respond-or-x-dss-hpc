import argparse
import os
import time
from datetime import datetime
from src.route_finder import RouteFinder
import multiprocessing as mp
import pandas as pd
from itertools import product

def process_village_routes(args):
    """Process routes for a single village"""
    village, shelters, finder, max_routes = args
    village_routes = []
    
    village_center = village.geometry.centroid
    village_point = (village_center.x, village_center.y)
    village_node = finder._find_nearest_node(village_point)
    
    for _, shelter in shelters.iterrows():
        if shelter.geometry.geom_type != 'Polygon':
            continue
            
        shelter_center = shelter.geometry.centroid
        shelter_point = (shelter_center.x, shelter_center.y)
        shelter_node = finder._find_nearest_node(shelter_point)
        
        try:
            path = finder.find_single_route(
                village_node, 
                shelter_node, 
                village['name'] if 'name' in village else 'Unknown Village',
                shelter['name'] if 'name' in shelter else 'Unknown Shelter'
            )
            if path:
                village_routes.append(path)
        except:
            continue
    
    # Sort routes by combined score and take top N
    if village_routes:
        village_routes.sort(key=lambda x: (
            x['total_distance'] * 
            (1 + x['average_risk']) * 
            (1 / x['worst_road_type'])
        ))
        return village_routes[:max_routes] if max_routes > 0 else village_routes
    
    return []

def main():
    parser = argparse.ArgumentParser(description='Find best evacuation routes from villages to shelters')
    parser.add_argument('--input-dir', type=str, required=True,
                      help='Directory containing input GeoJSON files')
    parser.add_argument('--max-routes', type=int, default=3,
                      help='Maximum number of routes per village. Use -1 for all routes')
    parser.add_argument('--output-dir', type=str, default='routes_output',
                      help='Output directory for evacuation routes')
    parser.add_argument('--parallel', action='store_true',
                      help='Enable parallel processing')
    parser.add_argument('--workers', type=int, default=None,
                      help='Number of worker processes (default: CPU count - 1)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug mode with detailed progress output')
    
    args = parser.parse_args()
    
    if args.debug:
        start_time = time.time()
        print(f"\nExecution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Validate inputs and create output directory
    if not os.path.exists(args.input_dir):
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    
    required_files = ['roads.geojson', 'villages.geojson', 'shelter.geojson']
    for file in required_files:
        file_path = os.path.join(args.input_dir, file)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required file not found: {file_path}")
    
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
        if args.debug:
            print(f"Created output directory: {args.output_dir}")
    
    if args.debug:
        print("\nInitializing RouteFinder...")
    
    # Initialize route finder
    finder = RouteFinder(
        roads_file=os.path.join(args.input_dir, 'roads.geojson'),
        villages_file=os.path.join(args.input_dir, 'villages.geojson'),
        shelters_file=os.path.join(args.input_dir, 'shelter.geojson')
    )
    
    if args.debug:
        print("Finding best routes...")
        network_time = time.time()
    
    # Process routes
    if args.parallel:
        # Set up parallel processing
        n_workers = args.workers if args.workers else max(1, mp.cpu_count() - 1)
        if args.debug:
            print(f"Using {n_workers} worker processes")
        
        # Prepare arguments for parallel processing
        process_args = [
            (village, finder.shelters, finder, args.max_routes)
            for _, village in finder.villages.iterrows()
        ]
        
        # Execute parallel processing
        with mp.Pool(n_workers) as pool:
            all_routes = pool.map(process_village_routes, process_args)
        
        # Flatten results
        routes = pd.DataFrame([
            route for village_routes in all_routes
            for route in village_routes
        ])
    else:
        # Sequential processing
        routes = finder.find_best_routes(max_routes=args.max_routes)
    
    if args.debug:
        route_time = time.time()
        print(f"Found {len(routes)} routes in {route_time - network_time:.2f} seconds")
        print("\nCreating route visualization...")
    
    # Create visualization
    finder.visualize_routes(routes, args.output_dir)
    
    if args.debug:
        print("\nSaving routes...")
    
    # Save routes
    output_file = os.path.join(args.output_dir, 'evacuation_routes.geojson')
    finder.save_routes(routes, output_file)
    
    if args.debug:
        end_time = time.time()
        total_time = end_time - start_time
        print(f"\nRoutes saved to: {output_file}")
        print(f"Total execution time: {total_time:.2f} seconds")
        print(f"Execution completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Print summary
    print("\nRoute Finding Summary:")
    print(f"Total routes found: {len(routes)}")
    print(f"Routes per village: {args.max_routes if args.max_routes > 0 else 'All'}")
    print(f"Processing mode: {'Parallel' if args.parallel else 'Sequential'}")
    if args.parallel:
        print(f"Worker processes: {n_workers}")
    print(f"Output file: {output_file}")

if __name__ == '__main__':
    main()