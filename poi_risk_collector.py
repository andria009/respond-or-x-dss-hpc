from src.poi_collector import POICollector
import argparse

def main():
    parser = argparse.ArgumentParser(description='Collect POIs from OpenStreetMap')
    parser.add_argument('--lat', type=float, required=True,
                      help='Latitude of the center point')
    parser.add_argument('--lon', type=float, required=True,
                      help='Longitude of the center point')
    parser.add_argument('--radius', type=float, required=True,
                      help='Search radius in kilometers')
    parser.add_argument('--poi-types', type=str, nargs='+', required=True,
                      choices=['buildings', 'villages', 'shelter', 'roads'],
                      help='Types of POIs to collect')
    parser.add_argument('--output-dir', type=str, default='pois_output',
                      help='Output directory for POI files')
    parser.add_argument('--no-risk', action='store_true',
                      help='Skip hazard risk assessment')
    parser.add_argument('--batch-size', type=int, default=20,
                      help='Batch size for INARISK API requests (default: 20)')
    parser.add_argument('--hazards', type=str, nargs='+', default=['earthquake', 'flood', 'volcanic', 'landslide'],
                      choices=['earthquake', 'flood', 'volcanic', 'landslide'],
                      help='Hazard types to assess (default: all hazards)')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug output for API requests')
    parser.add_argument('--parallel', action='store_true',
                      help='Enable parallel processing')
    parser.add_argument('--workers', type=int, default=4,
                      help='Number of worker processes for parallel processing (default: 4)')

    args = parser.parse_args()
    
    collector = POICollector(
        output_dir=args.output_dir,
        batch_size=args.batch_size,
        debug=args.debug,
        hazard_types=args.hazards,
        parallel=args.parallel,
        workers=args.workers
    )
    pois = collector.collect_pois(
        args.lat, 
        args.lon, 
        args.radius, 
        args.poi_types,
        assess_risks=not args.no_risk
    )
    
    print(f"\nCollection complete. Files saved in: {args.output_dir}")

if __name__ == "__main__":
    main()