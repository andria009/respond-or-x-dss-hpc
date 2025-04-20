import argparse
import os
import time
from datetime import datetime
from src.route_finder import RouteFinder

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Find best evacuation routes from villages to shelters')
    parser.add_argument('--input-dir', type=str, required=True,
                      help='Directory containing input GeoJSON files (roads.geojson, villages.geojson, shelter.geojson)')
    parser.add_argument('--max-routes', type=int, default=3,
                      help='Maximum number of routes to save per village. Use -1 for all routes. Default: 3')
    parser.add_argument('--output-dir', type=str, default='routes_output',
                      help='Output directory for evacuation routes. Default: routes_output')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug mode with detailed progress output')
    
    args = parser.parse_args()
    
    # Start timing if debug mode is enabled
    if args.debug:
        start_time = time.time()
        print(f"\nExecution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Validate input directory and files
    if not os.path.exists(args.input_dir):
        raise FileNotFoundError(f"Input directory not found: {args.input_dir}")
    
    required_files = ['roads.geojson', 'villages.geojson', 'shelter.geojson']
    for file in required_files:
        file_path = os.path.join(args.input_dir, file)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Required file not found: {file_path}")
    
    # Create output directory if it doesn't exist
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
    
    # Find routes
    routes = finder.find_best_routes(max_routes=args.max_routes if args.max_routes > 0 else None)
    
    # After finding and saving routes
    if args.debug:
        print("\nCreating route visualization...")
    
    finder.visualize_routes(routes, args.output_dir)
    if args.debug:
        route_time = time.time()
        print(f"Found {len(routes)} routes in {route_time - network_time:.2f} seconds")
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
    print(f"Output file: {output_file}")

if __name__ == '__main__':
    main()