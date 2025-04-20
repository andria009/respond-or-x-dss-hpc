import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union
import numpy as np

class VillageAggregator:
    @staticmethod
    def aggregate_villages(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        # Group by village name
        village_groups = gdf.groupby('is_in:village')
        
        aggregated_data = []
        for village_name, group in village_groups:
            if pd.isna(village_name):
                continue
                
            # Merge geometries
            merged_geometry = unary_union(group.geometry)
            
            # Calculate average risk values
            avg_earthquake_risk = group['earthquake_risk'].mean()
            avg_flood_risk = group['flood_risk'].mean()
            
            # Get common attributes
            common_attrs = {
                'name': village_name,
                'is_in:municipality': group['is_in:municipality'].iloc[0],
                'is_in:province': group['is_in:province'].iloc[0],
                'is_in:town': group['is_in:town'].iloc[0],
                'earthquake_risk': avg_earthquake_risk,
                'flood_risk': avg_flood_risk
            }
            
            aggregated_data.append({
                'geometry': merged_geometry,
                'properties': common_attrs
            })
        
        # Create new GeoDataFrame with CRS
        aggregated_gdf = gpd.GeoDataFrame.from_features(aggregated_data)
        aggregated_gdf.set_crs(epsg=4326, inplace=True)  # WGS 84 coordinate system
        
        return aggregated_gdf