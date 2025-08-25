import csv
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, Polygon
from typing import List, Dict, Tuple
import os
import osmnx as ox
from multiprocessing import Pool, cpu_count
from .inarisk_client import INARISKClient
from .visualizer import POIVisualizer
from .village_aggregator import VillageAggregator
import time
from datetime import datetime

class CSVPOICollector:
    """
    POI Collector that works with CSV input files (compatible with respondor-main format)
    Instead of querying OpenStreetMap directly, it processes existing POI data from CSV files
    and enhances it with risk assessment and network data collection
    """
    
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

    def collect_from_csv(self, csv_file_path: str, assess_risks: bool = True, existing_roads: gpd.GeoDataFrame = None) -> Dict[str, gpd.GeoDataFrame]:
        """
        Main method to process CSV file and collect POI data with risk assessment
        
        Args:
            csv_file_path (str): Path to CSV file with format: name,category,lat,lng,[additional_columns]
            assess_risks (bool): Whether to assess hazard risks using INARISK
            existing_roads (gpd.GeoDataFrame, optional): Pre-existing roads data to use instead of collecting from OSM
            
        Returns:
            Dict[str, gpd.GeoDataFrame]: Dictionary of POI data by type
        """
        if self.debug:
            start_time = time.time()
            print(f"\nExecution started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Processing CSV file: {csv_file_path}")

        # Read and validate CSV file
        pois_df = self._read_csv_file(csv_file_path)
        
        # Group POIs by category
        poi_groups = self._group_pois_by_category(pois_df)
        
        # Use existing roads or collect new ones
        if existing_roads is not None and not existing_roads.empty:
            print(f"Using existing roads data: {len(existing_roads)} road segments")
            poi_groups['roads'] = existing_roads
        else:
            # Calculate geographic bounds for road network collection
            bounds = self._calculate_bounds(pois_df)
            
            # Collect road network for the area
            roads_gdf = self._collect_roads_for_area(bounds)
            if not roads_gdf.empty:
                poi_groups['roads'] = roads_gdf

        results = {}
        
        # Process each POI group
        for poi_type, gdf in poi_groups.items():
            if not gdf.empty:
                if assess_risks:
                    gdf = self._assess_hazard_risks(gdf)
                    
                    # Special handling for villages - aggregate if needed
                    if poi_type == 'villages':
                        aggregator = VillageAggregator()
                        gdf = aggregator.aggregate_villages(gdf)
                
                # Save to file
                output_file = os.path.join(self.output_dir, f"{poi_type}.geojson")
                gdf.to_file(output_file, driver="GeoJSON")
                print(f"Saved {len(gdf)} {poi_type} POIs to {output_file}")
                
                results[poi_type] = gdf

        # Create visualizations if risk assessment was performed
        if assess_risks and results:
            center_lat = pois_df['lat'].mean()
            center_lon = pois_df['lng'].mean()
            
            visualizer = POIVisualizer(self.output_dir)
            visualizer.create_risk_maps(results, center_lat, center_lon)

        if self.debug:
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"\nExecution completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Total execution time: {execution_time:.2f} seconds")

        return results

    def _read_csv_file(self, csv_file_path: str) -> pd.DataFrame:
        """Read and validate CSV file"""
        print(f"Reading CSV file: {csv_file_path}")
        
        df_list = []
        with open(csv_file_path, 'r') as f:
            reader = csv.reader(f)
            for row_num, row in enumerate(reader, 1):
                if len(row) < 4:
                    print(f"Warning: Row {row_num} has insufficient columns, skipping")
                    continue
                
                try:
                    name = row[0].strip()
                    category = row[1].strip().lower()
                    lat = float(row[2])
                    lng = float(row[3])
                    
                    # Additional columns (if present)
                    extra_data = {}
                    if len(row) > 4:
                        # Assume columns 4+ contain additional data
                        for i, value in enumerate(row[4:], 4):
                            extra_data[f'col_{i}'] = value
                    
                    row_data = {
                        'name': name,
                        'category': category,
                        'lat': lat,
                        'lng': lng,
                        **extra_data
                    }
                    df_list.append(row_data)
                    
                except (ValueError, IndexError) as e:
                    print(f"Warning: Row {row_num} has invalid data, skipping: {e}")
                    continue
        
        if not df_list:
            raise ValueError("No valid data found in CSV file")
        
        df = pd.DataFrame(df_list)
        print(f"Loaded {len(df)} POI records")
        return df

    def _group_pois_by_category(self, pois_df: pd.DataFrame) -> Dict[str, gpd.GeoDataFrame]:
        """Group POIs by category and convert to GeoDataFrames"""
        poi_groups = {}
        
        # Category mapping (normalize category names)
        category_mapping = {
            'village': 'villages',
            'shelter': 'shelter',
            'depot': 'shelter',  # Depots can be treated as shelters for evacuation
            'warehouse': 'shelter',
            'airport': 'shelter',
            'hospital': 'shelter',
            'clinic': 'shelter'
        }
        
        for category in pois_df['category'].unique():
            # Filter POIs for this category
            category_pois = pois_df[pois_df['category'] == category].copy()
            
            if len(category_pois) == 0:
                continue
            
            # Create Point geometries
            geometries = [Point(row['lng'], row['lat']) for _, row in category_pois.iterrows()]
            
            # Create GeoDataFrame
            gdf = gpd.GeoDataFrame(category_pois, geometry=geometries, crs='EPSG:4326')
            
            # Map category to standard names
            output_category = category_mapping.get(category, 'other')
            
            if output_category in poi_groups:
                # Combine with existing data
                poi_groups[output_category] = pd.concat([poi_groups[output_category], gdf], ignore_index=True)
            else:
                poi_groups[output_category] = gdf
            
            print(f"Grouped {len(category_pois)} POIs as '{output_category}' (from category '{category}')")
        
        return poi_groups

    def _calculate_bounds(self, pois_df: pd.DataFrame) -> Tuple[float, float, float, float]:
        """Calculate geographic bounds of all POIs"""
        min_lat = pois_df['lat'].min()
        max_lat = pois_df['lat'].max()
        min_lng = pois_df['lng'].min()
        max_lng = pois_df['lng'].max()
        
        # Add some padding (roughly 1km in degrees)
        padding = 0.01
        bounds = (min_lat - padding, max_lat + padding, min_lng - padding, max_lng + padding)
        
        if self.debug:
            print(f"POI bounds: lat({min_lat:.4f}, {max_lat:.4f}), lng({min_lng:.4f}, {max_lng:.4f})")
        
        return bounds

    def _collect_roads_for_area(self, bounds: Tuple[float, float, float, float]) -> gpd.GeoDataFrame:
        """Collect road network for the bounded area"""
        min_lat, max_lat, min_lng, max_lng = bounds
        
        try:
            print("Collecting road network from OpenStreetMap...")
            
            # Calculate center and radius for the area
            center_lat = (min_lat + max_lat) / 2
            center_lng = (min_lng + max_lng) / 2
            
            # Rough estimate of radius in meters
            lat_diff = max_lat - min_lat
            lng_diff = max_lng - min_lng
            radius = max(lat_diff, lng_diff) * 111000 / 2  # degrees to meters approximation
            
            # Collect road network
            point = (center_lat, center_lng)
            roads_graph = ox.graph_from_point(point, dist=radius, network_type='all')
            roads_gdf = ox.graph_to_gdfs(roads_graph, nodes=False)
            
            print(f"Collected {len(roads_gdf)} road segments")
            return roads_gdf
            
        except Exception as e:
            print(f"Warning: Could not collect road network: {e}")
            return gpd.GeoDataFrame()

    def _assess_hazard_risks(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Assess hazard risks for the POIs"""
        print(f"Assessing hazard risks for {len(gdf)} POIs...")
        
        # Extract coordinate points for risk assessment
        points = []
        for geom in gdf.geometry:
            if geom.geom_type == 'Point':
                points.append((geom.y, geom.x))  # lat, lon format for INARISK
            elif geom.geom_type in ['LineString', 'Polygon', 'MultiPolygon']:
                centroid = geom.centroid
                points.append((centroid.y, centroid.x))
            else:
                # Fallback to bounds
                bounds = geom.bounds
                points.append((bounds[1], bounds[0]))  # min_lat, min_lng
        
        # Assess risks for each hazard type
        for hazard_type in self.hazard_types:
            if hazard_type in self.inarisk_client.hazard_layers:
                try:
                    risk_values = self.inarisk_client.get_risk_for_points(
                        points, hazard_type, batch_size=self.batch_size
                    )
                    gdf[f'{hazard_type}_risk'] = risk_values
                except Exception as e:
                    print(f"Warning: Could not assess {hazard_type} risk: {e}")
                    gdf[f'{hazard_type}_risk'] = 0.0
        
        return gdf