import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, LineString, mapping
import pandas as pd
import numpy as np
import json
import folium
from branca.colormap import LinearColormap
import os
from src.route_visualizer import RouteVisualizer

class RouteFinder:
    def __init__(self, roads_file, villages_file, shelters_file):
        self.roads = gpd.read_file(roads_file)
        self.villages = gpd.read_file(villages_file)
        self.shelters = gpd.read_file(shelters_file)
        self.G = self._create_road_network()
        
    def _create_road_network(self):
        """Create NetworkX graph from road network"""
        G = nx.Graph()
        
        # Highway type weights (higher value = better road)
        highway_weights = {
            'primary': 1.0,
            'secondary': 0.9,
            'tertiary': 0.8,
            'residential': 0.7,
            'service': 0.6,
            'living_street': 0.5,
            'footway': 0.4,
            'path': 0.3
        }
        
        for _, road in self.roads.iterrows():
            # Get coordinates using coords property for LineString
            coords = list(road.geometry.coords)
            
            # Get road properties from the GeoDataFrame
            highway_type = road['highway'] if 'highway' in road else 'residential'
            if isinstance(highway_type, list):
                highway_type = highway_type[0]
            
            highway_weight = highway_weights.get(highway_type, 0.5)
            
            # Calculate risk score (average of all available risks)
            available_risks = []
            for risk_type in ['earthquake_risk', 'flood_risk', 'volcanic_risk', 'landslide_risk']:
                if risk_type in road and road[risk_type] is not None:
                    available_risks.append(road[risk_type])
            
            risk_score = sum(available_risks) / len(available_risks) if available_risks else 0
            
            # Edge weight combines distance, road type and risk
            # Lower weight = better path
            for i in range(len(coords)-1):
                start = tuple(coords[i])
                end = tuple(coords[i+1])
                
                # Calculate distance between points
                distance = ((start[0] - end[0])**2 + (start[1] - end[1])**2)**0.5
                
                # Combined weight: distance * (1/highway_weight) * (1 + risk_score)
                weight = distance * (1/highway_weight) * (1 + risk_score)
                
                G.add_edge(start, end, 
                          weight=weight,
                          distance=distance,
                          highway_type=highway_type,
                          risk_score=risk_score)
        
        return G
    
    def _find_nearest_node(self, point):
        """Find nearest node in graph to given point"""
        nodes = list(self.G.nodes())
        distances = [((node[0] - point[0])**2 + (node[1] - point[1])**2)**0.5 
                    for node in nodes]
        return nodes[np.argmin(distances)]
    
    def find_best_routes(self, max_routes=3):
        """Find best routes from each village to shelters"""
        routes = []
        
        for _, village in self.villages.iterrows():
            village_center = village.geometry.centroid
            village_point = (village_center.x, village_center.y)
            village_node = self._find_nearest_node(village_point)
            
            shelter_routes = []
            for _, shelter in self.shelters.iterrows():
                if shelter.geometry.geom_type != 'Polygon':
                    continue
                    
                shelter_center = shelter.geometry.centroid
                shelter_point = (shelter_center.x, shelter_center.y)
                shelter_node = self._find_nearest_node(shelter_point)
                
                try:
                    # Find shortest path
                    path = nx.shortest_path(self.G, village_node, shelter_node, 
                                         weight='weight')
                    
                    # Calculate route metrics
                    total_distance = 0
                    total_risk = 0
                    worst_road = 1.0
                    
                    for i in range(len(path)-1):
                        edge = self.G[path[i]][path[i+1]]
                        total_distance += edge['distance']
                        total_risk += edge['risk_score']
                        
                        # Track worst road type in route
                        highway_type = edge['highway_type']
                        if isinstance(highway_type, list):
                            highway_type = highway_type[0]
                        road_quality = {
                            'primary': 1.0,
                            'secondary': 0.9,
                            'tertiary': 0.8,
                            'residential': 0.7,
                            'service': 0.6,
                            'living_street': 0.5,
                            'footway': 0.4,
                            'path': 0.3
                        }.get(highway_type, 0.5)
                        worst_road = min(worst_road, road_quality)
                    
                    avg_risk = total_risk / len(path)
                    
                    shelter_routes.append({
                        'village_name': village['name'] if 'name' in village else 'Unknown Village',
                        'shelter_name': shelter['name'] if 'name' in shelter else 'Unknown Shelter',
                        'total_distance': total_distance,
                        'average_risk': avg_risk,
                        'worst_road_type': worst_road,
                        'path': path
                    })
                    
                except nx.NetworkXNoPath:
                    continue
            
            # Sort routes by combined score
            if shelter_routes:
                shelter_routes.sort(key=lambda x: (
                    x['total_distance'] * 
                    (1 + x['average_risk']) * 
                    (1 / x['worst_road_type'])
                ))
                
                # Take top N routes
                routes.extend(shelter_routes[:max_routes])
        
        return pd.DataFrame(routes)

    def save_routes(self, routes_df, output_file):
        """Save routes to GeoJSON"""
        features = []
        
        for _, route in routes_df.iterrows():
            path_coords = route['path']
            
            # Create LineString from path
            line = LineString(path_coords)
            
            # Create GeoJSON feature
            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'LineString',
                    'coordinates': list(line.coords)
                },
                'properties': {
                    'village_name': route['village_name'],
                    'shelter_name': route['shelter_name'],
                    'total_distance': route['total_distance'],
                    'average_risk': route['average_risk'],
                    'worst_road_type': route['worst_road_type']
                }
            }
            features.append(feature)
        
        # Create GeoJSON collection
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(geojson, f)

    def visualize_routes(self, routes_df, output_dir):
        """Create interactive map visualization of evacuation routes"""
        visualizer = RouteVisualizer(self.villages, self.shelters)
        visualizer.create_map(routes_df, output_dir)
    
    def find_single_route(self, village_node, shelter_node, village_name, shelter_name):
        """Find a single route between a village and shelter node"""
        try:
            # Find shortest path
            path = nx.shortest_path(self.G, village_node, shelter_node, weight='weight')
            
            # Calculate route metrics
            total_distance = 0
            total_risk = 0
            worst_road = 1.0
            
            for i in range(len(path)-1):
                edge = self.G[path[i]][path[i+1]]
                total_distance += edge['distance']
                total_risk += edge['risk_score']
                
                # Track worst road type in route
                highway_type = edge['highway_type']
                if isinstance(highway_type, list):
                    highway_type = highway_type[0]
                road_quality = {
                    'primary': 1.0,
                    'secondary': 0.9,
                    'tertiary': 0.8,
                    'residential': 0.7,
                    'service': 0.6,
                    'living_street': 0.5,
                    'footway': 0.4,
                    'path': 0.3
                }.get(highway_type, 0.5)
                worst_road = min(worst_road, road_quality)
            
            avg_risk = total_risk / len(path)
            
            return {
                'village_name': village_name,
                'shelter_name': shelter_name,
                'total_distance': total_distance,
                'average_risk': avg_risk,
                'worst_road_type': worst_road,
                'path': path
            }
            
        except nx.NetworkXNoPath:
            return None