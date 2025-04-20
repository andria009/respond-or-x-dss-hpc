import folium
from folium import plugins
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from branca.colormap import LinearColormap

class POIVisualizer:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self.risk_colors = LinearColormap(
            colors=['blue', 'yellow', 'red'],
            vmin=0, vmax=1,
            caption='Risk Level'
        )
        # Special style for roads
        self.road_style = {
            'weight': 3,
            'opacity': 1
        }

    def create_risk_maps(self, pois_dict: dict, center_lat: float, center_lon: float):
        """Create interactive maps for each hazard type"""
        
        # Get all available hazard types from the data
        hazard_types = []
        for poi_data in pois_dict.values():
            hazard_cols = [col for col in poi_data.columns if col.endswith('_risk')]
            hazard_types.extend([h.replace('_risk', '') for h in hazard_cols])
        hazard_types = list(set(hazard_types))

        for hazard_type in hazard_types:
            # Create base map
            m = folium.Map(location=[center_lat, center_lon], zoom_start=13)
            
            # Add POI layers
            for poi_type, gdf in pois_dict.items():
                risk_col = f'{hazard_type}_risk'
                if risk_col not in gdf.columns:
                    continue

                if poi_type == 'roads':
                    # Special styling for roads
                    folium.GeoJson(
                        gdf,
                        name=poi_type,
                        style_function=lambda x: {
                            **self.road_style,
                            'color': self.risk_colors(x['properties'][risk_col])
                        },
                        tooltip=folium.GeoJsonTooltip(
                            fields=['name', risk_col, 'highway'],
                            aliases=['Road Name', f'{hazard_type.title()} Risk', 'Road Type'],
                            localize=True
                        )
                    ).add_to(m)
                else:
                    # Original styling for other POIs
                    folium.GeoJson(
                        gdf,
                        name=poi_type,
                        style_function=lambda x: {
                            'fillColor': self.risk_colors(x['properties'][risk_col]),
                            'color': 'black',
                            'weight': 1,
                            'fillOpacity': 0.7
                        },
                        tooltip=folium.GeoJsonTooltip(
                            fields=['name', risk_col],
                            aliases=['Name', f'{hazard_type.title()} Risk'],
                            localize=True
                        )
                    ).add_to(m)

            # Add layer control and color map
            folium.LayerControl().add_to(m)
            self.risk_colors.add_to(m)

            # Save the map
            output_file = os.path.join(self.output_dir, f'map_{hazard_type}_risk.html')
            m.save(output_file)
            print(f"Created risk map for {hazard_type} at: {output_file}")