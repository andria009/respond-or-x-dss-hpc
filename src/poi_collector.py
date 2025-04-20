import osmnx as ox
import geopandas as gpd
from typing import List, Tuple
import os
from multiprocessing import Pool, cpu_count
from .inarisk_client import INARISKClient
from .visualizer import POIVisualizer
import time
from datetime import datetime
from .village_aggregator import VillageAggregator

class POICollector:
    def __init__(self, output_dir: str = "pois_output", batch_size: int = 20, 
                 debug: bool = False, hazard_types: List[str] = None,
                 parallel: bool = False, workers: int = 4):
        ox.settings.use_cache = True
        ox.settings.log_console = True
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.debug = debug
        self.hazard_types = hazard_types or ['earthquake', 'flood', 'volcanic', 'landslide']
        self.parallel = parallel
        self.workers = min(workers, cpu_count())
        self.inarisk_client = INARISKClient(debug=debug)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

    def _process_poi_type(self, args):
        """Process a single POI type (for parallel processing)"""
        poi_type, latitude, longitude, radius_meters = args
        tags = {}
        if poi_type == "buildings":
            tags["building"] = True
        elif poi_type == "villages":
            # Fetch village boundaries
            tags = {
                "boundary": "administrative",
                "admin_level": "9",  # Level for villages in Indonesia
                "place": ["village", "suburb", "neighbourhood"]
            }
            pois = ox.features_from_point((latitude, longitude), tags, radius_meters)
            # Filter for polygon geometries only
            pois = pois[pois.geometry.type.isin(['Polygon', 'MultiPolygon'])]
            return poi_type, pois
        elif poi_type == "shelter":
            tags["amenity"] = "shelter"
        elif poi_type == "roads":
            return poi_type, self._collect_roads(latitude, longitude, radius_meters)
        
        pois = ox.features_from_point((latitude, longitude), tags, radius_meters)
        return poi_type, pois

    def collect_pois(self, latitude: float, longitude: float, radius: float, 
                    poi_types: List[str], assess_risks: bool = True) -> dict:
        if self.debug:
            start_time = time.time()
            print(f"\nExecution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
        radius_meters = radius * 1000
        results = {}

        if self.parallel:
            # Prepare arguments for parallel processing
            args_list = [(poi_type, latitude, longitude, radius_meters) 
                        for poi_type in poi_types]
            
            # Process POI types in parallel
            with Pool(self.workers) as pool:
                poi_results = pool.map(self._process_poi_type, args_list)
                
            # Convert results to dictionary
            for poi_type, pois in poi_results:
                if not pois.empty:
                    if assess_risks:
                        pois = self._assess_hazard_risks(pois)
                        
                        # Aggregate villages before saving if this is village data
                        if poi_type == "villages":
                            aggregator = VillageAggregator()
                            pois = aggregator.aggregate_villages(pois)
                        
                        output_file = os.path.join(self.output_dir, f"{poi_type}.geojson")
                        pois.to_file(output_file, driver="GeoJSON")
                        print(f"Saved {len(pois)} {poi_type} to {output_file}")
                        
                        results[poi_type] = pois
        else:
            # Original sequential processing
            for poi_type in poi_types:
                poi_type, pois = self._process_poi_type((poi_type, latitude, longitude, radius_meters))
                if not pois.empty:
                    if assess_risks:
                        pois = self._assess_hazard_risks(pois)
                    output_file = os.path.join(self.output_dir, f"{poi_type}.geojson")
                    pois.to_file(output_file, driver="GeoJSON")
                    print(f"Saved {len(pois)} {poi_type} to {output_file}")
                    results[poi_type] = pois

        # Create visualizations after collecting all POIs
        if assess_risks:
            visualizer = POIVisualizer(self.output_dir)
            visualizer.create_risk_maps(results, latitude, longitude)

        if self.debug:
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"\nExecution completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Total execution time: {execution_time:.2f} seconds")

        return results

    def _assess_hazard_risks(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        points = []
        for geom in gdf.geometry:
            if geom.geom_type == 'Point':
                points.append((geom.y, geom.x))
            elif geom.geom_type in ['LineString', 'Polygon', 'MultiPolygon']:
                centroid = geom.centroid
                points.append((centroid.y, centroid.x))
            else:
                points.append((geom.bounds[1], geom.bounds[0]))
        
        if self.parallel:
            # Process hazard types in parallel
            hazard_args = [
                (points, hazard_type, self.batch_size) 
                for hazard_type in self.hazard_types 
                if hazard_type in self.inarisk_client.hazard_layers
            ]
            
            with Pool(self.workers) as pool:
                risk_results = pool.starmap(self.inarisk_client.get_risk_for_points, hazard_args)
                
            # Add results to GeoDataFrame
            for hazard_type, risk_values in zip(
                [h for h in self.hazard_types if h in self.inarisk_client.hazard_layers], 
                risk_results
            ):
                gdf[f'{hazard_type}_risk'] = risk_values
        else:
            # Original sequential processing
            for hazard_type in self.hazard_types:
                if hazard_type in self.inarisk_client.hazard_layers:
                    risk_values = self.inarisk_client.get_risk_for_points(
                        points, hazard_type, batch_size=self.batch_size
                    )
                    gdf[f'{hazard_type}_risk'] = risk_values
            
        return gdf

    def _collect_roads(self, latitude: float, longitude: float, 
                      radius_meters: float) -> gpd.GeoDataFrame:
        """Collect road network data"""
        point = (latitude, longitude)
        roads = ox.graph_from_point(point, dist=radius_meters, network_type='all')
        roads_gdf = ox.graph_to_gdfs(roads, nodes=False)
        return roads_gdf