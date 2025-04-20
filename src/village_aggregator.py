import geopandas as gpd
import pandas as pd

class VillageAggregator:
    def aggregate_villages(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Aggregate village data based on available village identifiers"""
        try:
            # Try different possible village identifier columns
            if 'name' in gdf.columns:
                village_groups = gdf.groupby('name')
            elif 'is_in:village' in gdf.columns:
                village_groups = gdf.groupby('is_in:village')
            elif 'addr:village' in gdf.columns:
                village_groups = gdf.groupby('addr:village')
            else:
                # If no village identifier found, return as-is
                return gdf

            # Aggregate data
            aggregated = []
            for name, group in village_groups:
                # Calculate average risks
                avg_earthquake = group['earthquake_risk'].mean()
                avg_flood = group['flood_risk'].mean()
                
                # Merge geometries if multiple polygons
                if len(group) > 1:
                    merged_geom = group.geometry.unary_union
                else:
                    merged_geom = group.geometry.iloc[0]
                
                # Create aggregated village entry
                aggregated.append({
                    'name': name,
                    'geometry': merged_geom,
                    'earthquake_risk': avg_earthquake,
                    'flood_risk': avg_flood,
                    'area': merged_geom.area,
                    'population': group.get('population', 0).sum()
                })
            
            return gpd.GeoDataFrame(aggregated, crs=gdf.crs)
            
        except Exception as e:
            print(f"Warning: Village aggregation failed - {str(e)}")
            return gdf