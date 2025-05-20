import os
import folium
from branca.colormap import LinearColormap
from shapely.geometry import LineString

class RouteVisualizer:
    def __init__(self, villages, shelters):
        self.villages = villages
        self.shelters = shelters

    def create_map(self, routes_df, output_dir):
        """Create interactive map visualization of evacuation routes"""
        if len(routes_df) == 0:
            print("No routes to visualize")
            return
        
        # Calculate center point from first route
        first_path = routes_df.iloc[0]['path']
        center_lat = sum(p[1] for p in first_path) / len(first_path)
        center_lon = sum(p[0] for p in first_path) / len(first_path)
        
        # Create base map
        m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
        
        # Create feature groups for villages, shelters, and routes
        villages_group = folium.FeatureGroup(name="Villages", show=True)
        shelters_group = folium.FeatureGroup(name="Shelters", show=True)
        
        # Create groups for each village and shelter's routes
        route_groups = {}
        
        # Create color map for risk levels with fixed range
        risk_colors = LinearColormap(
            colors=['green', 'yellow', 'red'],
            vmin=0.0,
            vmax=1.0,
            caption='Route Risk Level (0-1)'
        )
        
        self._add_villages_to_map(m, villages_group, route_groups)
        self._add_shelters_to_map(m, shelters_group)
        self._add_routes_to_map(m, routes_df, risk_colors)
        
        # Add layer control and color map
        folium.LayerControl(collapsed=False).add_to(m)
        risk_colors.add_to(m)
        
        # Save the map
        output_file = os.path.join(output_dir, 'evacuation_routes_map.html')
        m.save(output_file)
        print(f"\nCreated evacuation routes visualization at: {output_file}")

    def _add_villages_to_map(self, m, villages_group, route_groups):
        for _, village in self.villages.iterrows():
            village_name = village['name'] if 'name' in village else 'Unknown Village'
            village_group = folium.FeatureGroup(name=f"Village: {village_name}", show=True)
            
            # Add village marker
            folium.CircleMarker(
                location=[village.geometry.centroid.y, village.geometry.centroid.x],
                radius=8,
                color='blue',
                fill=True,
                popup=village_name,
                tooltip='Village'
            ).add_to(village_group)
            
            # Add to main villages group and map
            village_group.add_to(m)
            villages_group.add_to(m)
            
            # Create group for this village's routes
            route_groups[village_name] = {}

    def _add_shelters_to_map(self, m, shelters_group):
        for _, shelter in self.shelters.iterrows():
            shelter_name = shelter['name'] if 'name' in shelter else 'Unknown Shelter'
            shelter_group = folium.FeatureGroup(name=f"Shelter: {shelter_name}", show=True)
            
            # Add shelter marker
            folium.CircleMarker(
                location=[shelter.geometry.centroid.y, shelter.geometry.centroid.x],
                radius=8,
                color='red',
                fill=True,
                popup=shelter_name,
                tooltip='Shelter'
            ).add_to(shelter_group)
            
            # Add to main shelters group and map
            shelter_group.add_to(m)
            shelters_group.add_to(m)

    def _add_routes_to_map(self, m, routes_df, risk_colors):
        for _, route in routes_df.iterrows():
            village_name = route['village_name']
            shelter_name = route['shelter_name']
            
            # Create group for this specific village-shelter route combination
            route_group = folium.FeatureGroup(
                name=f"Route: {village_name} → {shelter_name}",
                show=True
            )
            
            # Create LineString for the route
            line = LineString(route['path'])
            route_color = risk_colors(route['average_risk'])
            
            # Add route to its group
            folium.GeoJson(
                {
                    'type': 'Feature',
                    'geometry': {
                        'type': 'LineString',
                        'coordinates': list(line.coords)
                    },
                    'properties': {
                        'village': village_name,
                        'shelter': shelter_name,
                        'distance': f"{route['total_distance']:.2f}",
                        'risk': f"{route['average_risk']:.2f}",
                        'road_quality': f"{route['worst_road_type']:.2f}"
                    }
                },
                style_function=lambda x: {
                    'color': route_color,
                    'weight': 2,
                    'opacity': 1
                },
                tooltip=folium.GeoJsonTooltip(
                    fields=['village', 'shelter', 'distance', 'risk', 'road_quality'],
                    aliases=['Village', 'Shelter', 'Distance', 'Risk Score', 'Road Quality'],
                    localize=True
                )
            ).add_to(route_group)
            
            route_group.add_to(m)