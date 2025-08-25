"""
Network Graph Processor for respondor-main compatibility
Handles PYCGR files and network graph processing similar to respondor-main's osm_graph.py
"""

import json
import csv
import networkx as nx
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
from typing import Dict, List, Tuple, Optional
import os
from networkx.readwrite import json_graph

class NetworkProcessor:
    """
    Processes network graph files in PYCGR format and JSON format
    Compatible with respondor-main network processing
    """
    
    def __init__(self, debug: bool = False):
        self.debug = debug

    def read_pycgr_file(self, pycgr_path: str) -> Tuple[Dict, List]:
        """
        Read PYCGR file and extract nodes and edges
        
        Args:
            pycgr_path (str): Path to PYCGR file
            
        Returns:
            Tuple[Dict, List]: (nodes_dict, edges_list)
        """
        nodes = {}
        edges = []
        total_nodes = None
        total_edges = None
        count_edges = 0
        count_nodes = 0
        
        print(f'Reading PYCGR file: {pycgr_path}')
        
        with open(pycgr_path) as f:
            count = 0
            for line in f:
                if count == 7:
                    total_nodes = int(line.strip())
                elif count == 8:
                    total_edges = int(line.strip())
                elif count > 8:
                    if count_nodes < total_nodes:
                        # Reading nodes: node_id lat lon
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            node_id, lat, lon = parts[0], float(parts[1]), float(parts[2])
                            nodes[node_id] = {
                                'id': node_id,
                                'lat': lat,
                                'lon': lon,
                                'coords': (lat, lon)
                            }
                            count_nodes += 1
                    else:
                        # Reading edges: source_id target_id length street_type max_speed bidirectional
                        parts = line.strip().split()
                        if len(parts) >= 6:
                            edge = {
                                'source_id': parts[0],
                                'target_id': parts[1],
                                'length': float(parts[2]),
                                'street_type': parts[3],
                                'max_speed': float(parts[4]),
                                'bidirectional': bool(int(parts[5]))
                            }
                            edges.append(edge)
                            count_edges += 1
                count += 1
        
        if self.debug:
            print(f"Loaded {count_nodes} nodes and {count_edges} edges from PYCGR file")
            
        return nodes, edges

    def read_network_json(self, json_path: str) -> nx.Graph:
        """
        Read NetworkX JSON file (adjacency format)
        
        Args:
            json_path (str): Path to network JSON file
            
        Returns:
            nx.Graph: NetworkX graph object
        """
        print(f'Reading network JSON file: {json_path}')
        
        with open(json_path) as f:
            data = json.load(f)
        
        graph = json_graph.adjacency_graph(data)
        
        if self.debug:
            print(f"Loaded graph with {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
            
        return graph

    def create_networkx_from_pycgr(self, pycgr_path: str) -> nx.Graph:
        """
        Create NetworkX graph from PYCGR file
        
        Args:
            pycgr_path (str): Path to PYCGR file
            
        Returns:
            nx.Graph: NetworkX graph
        """
        nodes, edges = self.read_pycgr_file(pycgr_path)
        
        # Create NetworkX graph
        G = nx.Graph()
        
        # Add nodes
        for node_id, node_data in nodes.items():
            G.add_node(int(node_id), 
                      lat=node_data['lat'], 
                      lon=node_data['lon'])
        
        # Add edges
        for edge in edges:
            source_id = int(edge['source_id'])
            target_id = int(edge['target_id'])
            
            G.add_edge(source_id, target_id,
                      length=edge['length'],
                      highway=edge['street_type'],
                      max_speed=edge['max_speed'],
                      bidirectional=edge['bidirectional'])
        
        if self.debug:
            print(f"Created NetworkX graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
            
        return G

    def create_roads_geodataframe(self, graph: nx.Graph) -> gpd.GeoDataFrame:
        """
        Convert NetworkX graph to GeoDataFrame of road segments
        
        Args:
            graph (nx.Graph): NetworkX graph with lat/lon node attributes
            
        Returns:
            gpd.GeoDataFrame: Roads as LineString geometries
        """
        road_features = []
        
        for source, target, data in graph.edges(data=True):
            # Get node coordinates
            source_node = graph.nodes[source]
            target_node = graph.nodes[target]
            
            source_coords = (source_node['lon'], source_node['lat'])
            target_coords = (target_node['lon'], target_node['lat'])
            
            # Create LineString geometry
            geometry = LineString([source_coords, target_coords])
            
            # Create feature
            feature = {
                'geometry': geometry,
                'source_id': source,
                'target_id': target,
                'length': data.get('length', 0),
                'highway': data.get('highway', 'unknown'),
                'max_speed': data.get('max_speed', 50),
                'bidirectional': data.get('bidirectional', True)
            }
            road_features.append(feature)
        
        # Create GeoDataFrame
        roads_gdf = gpd.GeoDataFrame(road_features, crs='EPSG:4326')
        
        if self.debug:
            print(f"Created roads GeoDataFrame with {len(roads_gdf)} segments")
            
        return roads_gdf

    def match_pois_to_network(self, pois_csv_path: str, graph: nx.Graph) -> pd.DataFrame:
        """
        Match POIs from CSV file to nearest network nodes
        
        Args:
            pois_csv_path (str): Path to POIs CSV file
            graph (nx.Graph): Network graph
            
        Returns:
            pd.DataFrame: POIs with matched node IDs
        """
        print(f"Matching POIs to network nodes...")
        
        # Read POIs
        pois = []
        with open(pois_csv_path) as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    pois.append({
                        'name': row[0].strip(),
                        'category': row[1].strip(),
                        'lat': float(row[2]),
                        'lng': float(row[3])
                    })
        
        # Create coordinate lists for network nodes
        node_coords = []
        node_ids = []
        for node_id, node_data in graph.nodes(data=True):
            node_coords.append((node_data['lat'], node_data['lon']))
            node_ids.append(node_id)
        
        # Match each POI to nearest network node
        matched_pois = []
        for poi in pois:
            poi_coord = (poi['lat'], poi['lng'])
            
            # Find nearest node (simple distance calculation)
            min_distance = float('inf')
            nearest_node_id = None
            
            for i, node_coord in enumerate(node_coords):
                # Simple Euclidean distance (could be improved with proper geographic distance)
                distance = ((poi_coord[0] - node_coord[0])**2 + (poi_coord[1] - node_coord[1])**2)**0.5
                if distance < min_distance:
                    min_distance = distance
                    nearest_node_id = node_ids[i]
            
            matched_poi = poi.copy()
            matched_poi['node_id'] = nearest_node_id
            matched_poi['distance_to_node'] = min_distance
            matched_pois.append(matched_poi)
        
        matched_df = pd.DataFrame(matched_pois)
        
        if self.debug:
            print(f"Matched {len(matched_df)} POIs to network nodes")
            print(f"Average distance to nearest node: {matched_df['distance_to_node'].mean():.6f} degrees")
        
        return matched_df

    def create_subnetwork(self, pois_df: pd.DataFrame, graph: nx.Graph) -> nx.Graph:
        """
        Create subnetwork containing shortest paths between all POI pairs
        
        Args:
            pois_df (pd.DataFrame): POIs with node_id column
            graph (nx.Graph): Full network graph
            
        Returns:
            nx.Graph: Subnetwork graph
        """
        print("Creating subnetwork from POI shortest paths...")
        
        # Get unique node IDs that correspond to POIs
        poi_node_ids = pois_df['node_id'].unique().tolist()
        
        if self.debug:
            print(f"Creating subnetwork for {len(poi_node_ids)} POI nodes")
        
        # Find all shortest paths between POI nodes
        all_path_nodes = set()
        path_count = 0
        
        for i, source_node in enumerate(poi_node_ids):
            for target_node in poi_node_ids[i+1:]:  # Avoid duplicate pairs
                try:
                    path = nx.shortest_path(graph, source_node, target_node, weight='length')
                    all_path_nodes.update(path)
                    path_count += 1
                    
                    if self.debug and path_count % 100 == 0:
                        print(f"Processed {path_count} paths...")
                        
                except nx.NetworkXNoPath:
                    if self.debug:
                        print(f"No path found between nodes {source_node} and {target_node}")
                    continue
        
        # Create subgraph with all nodes from shortest paths
        subgraph = graph.subgraph(all_path_nodes).copy()
        
        print(f"Created subnetwork with {subgraph.number_of_nodes()} nodes and {subgraph.number_of_edges()} edges")
        print(f"Original network: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        print(f"Reduction: {(1 - subgraph.number_of_nodes()/graph.number_of_nodes())*100:.1f}% nodes, "
              f"{(1 - subgraph.number_of_edges()/graph.number_of_edges())*100:.1f}% edges")
        
        return subgraph

    def save_network_as_geojson(self, graph: nx.Graph, output_path: str):
        """
        Save network graph as GeoJSON file
        
        Args:
            graph (nx.Graph): NetworkX graph
            output_path (str): Output file path
        """
        roads_gdf = self.create_roads_geodataframe(graph)
        roads_gdf.to_file(output_path, driver="GeoJSON")
        print(f"Saved network as GeoJSON: {output_path}")

    def save_pois_as_geojson(self, pois_df: pd.DataFrame, output_path: str):
        """
        Save POIs DataFrame as GeoJSON file
        
        Args:
            pois_df (pd.DataFrame): POIs with lat, lng columns
            output_path (str): Output file path
        """
        # Create Point geometries
        geometries = [Point(row['lng'], row['lat']) for _, row in pois_df.iterrows()]
        
        # Create GeoDataFrame
        pois_gdf = gpd.GeoDataFrame(pois_df, geometry=geometries, crs='EPSG:4326')
        
        # Save to file
        pois_gdf.to_file(output_path, driver="GeoJSON")
        print(f"Saved POIs as GeoJSON: {output_path}")