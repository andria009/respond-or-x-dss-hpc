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

            # Define possible risk columns
            risk_columns = [
                'earthquake_risk',
                'flood_risk',
                'landslide_risk',
                'volcanic_risk'
            ]

            # Aggregate data
            aggregated = []
            for name, group in village_groups:
                # Calculate average risks for available risk types
                risk_values = {}
                for risk_col in risk_columns:
                    if risk_col in group.columns:
                        risk_values[risk_col] = group[risk_col].mean()
                
                # Merge geometries if multiple polygons
                if len(group) > 1:
                    merged_geom = group.geometry.unary_union
                else:
                    merged_geom = group.geometry.iloc[0]
                
                # Create base village entry
                village_entry = {
                    'name': name,
                    'geometry': merged_geom,
                    'area': merged_geom.area,
                    'population': group['population'].sum() if 'population' in group.columns else 0
                }
                
                # Add available risk values
                village_entry.update(risk_values)
                
                aggregated.append(village_entry)
            
            return gpd.GeoDataFrame(aggregated, crs=gdf.crs)
            
        except Exception as e:
            print(f"Warning: Village aggregation failed - {str(e)}")
            return gdf