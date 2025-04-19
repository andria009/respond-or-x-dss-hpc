import osmnx as ox
import geopandas as gpd
from typing import List, Tuple
import os
from .inarisk_client import INARISKClient

class POICollector:
    def __init__(self, output_dir: str = "pois_output", batch_size: int = 20, 
                 debug: bool = False, hazard_types: List[str] = None):
        ox.settings.use_cache = True
        ox.settings.log_console = True
        self.output_dir = output_dir
        self.batch_size = batch_size
        self.debug = debug
        self.hazard_types = hazard_types or ['earthquake', 'flood', 'volcanic', 'landslide']
        self.inarisk_client = INARISKClient(debug=debug)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

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
        
        # Only assess specified hazard types
        for hazard_type in self.hazard_types:
            if hazard_type in self.inarisk_client.hazard_layers:
                risk_values = self.inarisk_client.get_risk_for_points(points, hazard_type, 
                                                                    batch_size=self.batch_size)
                gdf[f'{hazard_type}_risk'] = risk_values
            
        return gdf

    def collect_pois(self, latitude: float, longitude: float, radius: float, 
                    poi_types: List[str], assess_risks: bool = True) -> dict:
        """
        Collect POIs and assess hazard risks.
        """
        radius_meters = radius * 1000
        results = {}

        for poi_type in poi_types:
            tags = {}
            if poi_type == "buildings":
                tags["building"] = True
            elif poi_type == "villages":
                tags["place"] = "village"
            elif poi_type == "shelter":
                tags["amenity"] = "shelter"
            elif poi_type == "roads":
                pois = self._collect_roads(latitude, longitude, radius_meters)
            else:
                continue

            if poi_type != "roads":
                pois = ox.features_from_point((latitude, longitude), tags, radius_meters)

            if assess_risks and not pois.empty:
                pois = self._assess_hazard_risks(pois)

            # Save to file
            output_file = os.path.join(self.output_dir, f"{poi_type}.geojson")
            pois.to_file(output_file, driver="GeoJSON")
            print(f"Saved {len(pois)} {poi_type} to {output_file}")
            
            results[poi_type] = pois

        return results

    def _collect_roads(self, latitude: float, longitude: float, 
                      radius_meters: float) -> gpd.GeoDataFrame:
        """Collect road network data"""
        point = (latitude, longitude)
        roads = ox.graph_from_point(point, dist=radius_meters, network_type='all')
        roads_gdf = ox.graph_to_gdfs(roads, nodes=False)
        return roads_gdf