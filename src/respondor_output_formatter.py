"""
Output formatter to generate respondor-main compatible output files
"""

import os
import csv
import json
import pandas as pd
import geopandas as gpd
import networkx as nx
from typing import Dict, List, Tuple, Optional
from networkx.readwrite import json_graph

class RespondorOutputFormatter:
    """
    Formats respond-or-x-dss-hpc output to be compatible with respondor-main format
    """
    
    def __init__(self, project_name: str, output_dir: str, debug: bool = False):
        self.project_name = project_name
        self.output_dir = output_dir
        self.debug = debug
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
    
    def generate_respondor_outputs(self, 
                                 pois: Dict[str, gpd.GeoDataFrame], 
                                 original_csv_path: str,
                                 assess_risks: bool = True):
        """
        Generate all respondor-main compatible output files
        
        Args:
            pois (Dict[str, gpd.GeoDataFrame]): POI data by type
            original_csv_path (str): Path to original CSV file
            assess_risks (bool): Whether risk assessment was performed
        """
        
        print(f"Generating respondor-main compatible outputs...")
        
        # 1. Generate processed locations CSV with node IDs
        self._generate_locations_with_nodes(pois, original_csv_path)
        
        # 2. Generate network files if roads data is available
        if 'roads' in pois:
            roads_gdf = pois['roads']
            
            # Create NetworkX graph from roads
            graph = self._create_graph_from_roads(roads_gdf)
            
            # Add risk data to graph if available
            if assess_risks:
                self.add_risk_data_to_graph(graph, pois)
            
            # Generate subnetwork JSON
            subnetwork_path = self._generate_subnetwork_json(graph)
            
            # Generate PYCGRC files
            self._generate_pycgrc_files(graph, assess_risks)
            
            # Generate CSV files (nodes.csv, links.csv)
            self._generate_csv_files(graph, assess_risks)
            
            print(f"Generated respondor-main outputs in: {self.output_dir}")
        else:
            print("Warning: No roads data available, skipping network file generation")
    
    def _generate_locations_with_nodes(self, pois: Dict[str, gpd.GeoDataFrame], original_csv_path: str):
        """Generate processed locations CSV with node IDs (similar to respondor-main format)"""
        
        # Read original CSV
        locations = []
        with open(original_csv_path, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 4:
                    locations.append({
                        'name': row[0].strip(),
                        'category': row[1].strip(),
                        'lat': float(row[2]),
                        'lng': float(row[3]),
                        'extra_cols': row[4:] if len(row) > 4 else []
                    })
        
        # Assign synthetic node IDs (in real respondor-main, these come from network matching)
        output_path = os.path.join(self.output_dir, f"{self.project_name}_locations.csv")
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            for i, location in enumerate(locations):
                # Generate a synthetic node ID (starting from 10000 to avoid conflicts)
                node_id = 10000 + i
                
                row = [
                    location['name'],
                    location['category'], 
                    location['lat'],
                    location['lng'],
                    node_id
                ] + location['extra_cols']
                
                writer.writerow(row)
        
        print(f"Generated locations file: {output_path}")
    
    def _create_graph_from_roads(self, roads_gdf: gpd.GeoDataFrame) -> nx.Graph:
        """Create NetworkX graph from roads GeoDataFrame"""
        
        G = nx.Graph()
        
        node_id = 0
        node_coords = {}
        
        for idx, road in roads_gdf.iterrows():
            geom = road.geometry
            
            if geom.geom_type == 'LineString':
                coords = list(geom.coords)
                
                # Add nodes for start and end points
                start_coord = coords[0]  # (lon, lat)
                end_coord = coords[-1]   # (lon, lat)
                
                # Create unique node IDs based on coordinates
                start_key = f"{start_coord[1]:.6f},{start_coord[0]:.6f}"  # lat,lon for key
                end_key = f"{end_coord[1]:.6f},{end_coord[0]:.6f}"
                
                if start_key not in node_coords:
                    node_coords[start_key] = node_id
                    G.add_node(node_id, lat=start_coord[1], lon=start_coord[0])
                    node_id += 1
                
                if end_key not in node_coords:
                    node_coords[end_key] = node_id
                    G.add_node(node_id, lat=end_coord[1], lon=end_coord[0])
                    node_id += 1
                
                start_node_id = node_coords[start_key]
                end_node_id = node_coords[end_key]
                
                # Calculate edge properties
                length = geom.length * 111000  # Rough conversion to meters
                highway = road.get('highway', 'residential')
                max_speed = road.get('max_speed', 50)
                
                # Add edge
                G.add_edge(start_node_id, end_node_id,
                          length=length,
                          highway=highway,
                          max_speed=max_speed)
        
        if self.debug:
            print(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        
        return G
    
    def _generate_subnetwork_json(self, graph: nx.Graph) -> str:
        """Generate subnetwork JSON file"""
        
        output_path = os.path.join(self.output_dir, f"{self.project_name}_subnetwork.json")
        
        # Convert to adjacency data format
        data = json_graph.adjacency_data(graph)
        
        with open(output_path, 'w') as f:
            json.dump(data, f)
        
        print(f"Generated subnetwork JSON: {output_path}")
        return output_path
    
    def _generate_pycgrc_files(self, graph: nx.Graph, assess_risks: bool):
        """Generate PYCGRC format files"""
        
        base_path = os.path.join(self.output_dir, f"{self.project_name}_subnetwork.pycgrc")
        
        # Main PYCGRC file
        self._write_pycgrc_file(graph, base_path)
        
        if assess_risks:
            # Node risk file (space-separated: node_id risk_value)
            node_risk_path = base_path + "_node_risk"
            self._write_node_risk_file(graph, node_risk_path)
            
            # Edge risk file (space-separated: source target risk length max_speed bidirectional)
            edge_risk_path = base_path + "_risk"
            self._write_edge_risk_file(graph, edge_risk_path)
    
    def _write_pycgrc_file(self, graph: nx.Graph, output_path: str):
        """Write main PYCGRC file"""
        
        with open(output_path, 'w') as f:
            # Write header
            f.write('# Road Graph File v.0.4\n')
            f.write('# number of nodes\n')
            f.write('# number of edges\n') 
            f.write('# node_properties\n')
            f.write('# ...\n')
            f.write('# edge_properties\n')
            f.write('# ...\n')
            
            # Write counts
            f.write(f'{graph.number_of_nodes()}\n')
            f.write(f'{graph.number_of_edges()}\n')
            
            # Write nodes (space-separated: node_id lat lon)
            for node_id, data in graph.nodes(data=True):
                f.write(f"{node_id} {data['lat']} {data['lon']}\n")
            
            # Write edges (space-separated: source target length highway max_speed bidirectional)
            for source, target, data in graph.edges(data=True):
                bidirectional = 1  # Assume bidirectional for now
                f.write(f"{source} {target} {data.get('length', 100)} {data.get('highway', 'residential')} {data.get('max_speed', 50)} {bidirectional}\n")
        
        print(f"Generated PYCGRC file: {output_path}")
    
    def _write_node_risk_file(self, graph: nx.Graph, output_path: str):
        """Write node risk file (space-separated format)"""
        
        with open(output_path, 'w') as f:
            for node_id, data in graph.nodes(data=True):
                # Use synthetic risk value (in real scenario, this comes from INARISK)
                risk_value = data.get('risk', 0.5)  # Default risk
                f.write(f"{node_id} {risk_value}\n")
        
        print(f"Generated node risk file: {output_path}")
    
    def _write_edge_risk_file(self, graph: nx.Graph, output_path: str):
        """Write edge risk file (space-separated format)"""
        
        with open(output_path, 'w') as f:
            for source, target, data in graph.edges(data=True):
                # Calculate edge risk (max of source and target node risks)
                source_risk = graph.nodes[source].get('risk', 0.5)
                target_risk = graph.nodes[target].get('risk', 0.5)
                edge_risk = max(source_risk, target_risk)
                
                length = data.get('length', 100)
                max_speed = data.get('max_speed', 50)
                bidirectional = 1
                
                f.write(f"{source} {target} {edge_risk} {length} {max_speed} {bidirectional}\n")
        
        print(f"Generated edge risk file: {output_path}")
    
    def _generate_csv_files(self, graph: nx.Graph, assess_risks: bool):
        """Generate CSV files (nodes.csv and links.csv)"""
        
        # Generate nodes.csv
        nodes_path = os.path.join(self.output_dir, "nodes.csv")
        with open(nodes_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            if assess_risks:
                writer.writerow(['Node Id', 'Latitude', 'Longitude', 'Risk'])
                for node_id, data in graph.nodes(data=True):
                    risk = data.get('risk', 0.5)
                    writer.writerow([node_id, data['lat'], data['lon'], risk])
            else:
                writer.writerow(['Node Id', 'Latitude', 'Longitude'])
                for node_id, data in graph.nodes(data=True):
                    writer.writerow([node_id, data['lat'], data['lon']])
        
        print(f"Generated nodes CSV: {nodes_path}")
        
        # Generate links.csv
        links_path = os.path.join(self.output_dir, "links.csv")
        with open(links_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            if assess_risks:
                writer.writerow(['Source', 'Target', 'Risk', 'Length', 'Max_Speed', 'Bidirectional'])
                for source, target, data in graph.edges(data=True):
                    source_risk = graph.nodes[source].get('risk', 0.5)
                    target_risk = graph.nodes[target].get('risk', 0.5)
                    edge_risk = max(source_risk, target_risk)
                    
                    length = data.get('length', 100)
                    max_speed = data.get('max_speed', 50)
                    bidirectional = 1
                    
                    writer.writerow([source, target, edge_risk, length, max_speed, bidirectional])
            else:
                writer.writerow(['Source', 'Target', 'Length', 'Max_Speed', 'Bidirectional'])
                for source, target, data in graph.edges(data=True):
                    length = data.get('length', 100)
                    max_speed = data.get('max_speed', 50)
                    bidirectional = 1
                    
                    writer.writerow([source, target, length, max_speed, bidirectional])
        
        print(f"Generated links CSV: {links_path}")
    
    def add_risk_data_to_graph(self, graph: nx.Graph, pois: Dict[str, gpd.GeoDataFrame]):
        """Add risk data from POIs to graph nodes"""
        
        # Extract risk data from all POI types
        all_risk_data = []
        
        for poi_type, gdf in pois.items():
            if poi_type == 'roads':
                continue  # Skip roads for node risk calculation
            
            for _, poi in gdf.iterrows():
                risk_data = {
                    'lat': poi.geometry.centroid.y,
                    'lon': poi.geometry.centroid.x,
                    'risks': {}
                }
                
                # Extract risk columns
                for col in gdf.columns:
                    if col.endswith('_risk'):
                        risk_data['risks'][col] = poi[col]
                
                if risk_data['risks']:  # Only add if has risk data
                    all_risk_data.append(risk_data)
        
        # Assign risk values to graph nodes based on proximity
        for node_id, node_data in graph.nodes(data=True):
            node_lat = node_data['lat']
            node_lon = node_data['lon']
            
            # Find closest POI with risk data
            min_distance = float('inf')
            closest_risks = {}
            
            for risk_point in all_risk_data:
                distance = ((node_lat - risk_point['lat'])**2 + (node_lon - risk_point['lon'])**2)**0.5
                if distance < min_distance:
                    min_distance = distance
                    closest_risks = risk_point['risks']
            
            # Assign average risk value
            if closest_risks:
                risk_values = list(closest_risks.values())
                avg_risk = sum(risk_values) / len(risk_values)
                graph.nodes[node_id]['risk'] = avg_risk
            else:
                graph.nodes[node_id]['risk'] = 0.5  # Default risk
        
        if self.debug:
            print(f"Added risk data to {graph.number_of_nodes()} nodes")