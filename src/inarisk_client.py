import math
import json
import time
import requests
from datetime import datetime
from tqdm import tqdm

class INARISKClient:
    """Client for INARISK API to get hazard risk data."""
    
    def __init__(self, debug: bool = False):
        self.api_url = "https://gis.bnpb.go.id/server/rest/services/inarisk"
        self.hazard_layers = {
            "earthquake": "INDEKS_BAHAYA_GEMPABUMI",
            "flood": "INDEKS_BAHAYA_BANJIR",
            "volcanic": "INDEKS_BAHAYA_GUNUNGAPI",
            "landslide": "INDEKS_BAHAYA_TANAHLONGSOR"
        }
        self.debug = debug

    def lat_lon_to_meters(self, lat, lon):
        """Convert latitude/longitude to Spherical Mercator (EPSG:3857)."""
        origin_shift = 2 * math.pi * 6378137 / 2.0
        x = lon / 180.0 * origin_shift
        y = math.log(math.tan(((lat * math.pi / 180) + math.pi / 2.0) / 2)) * 180 / math.pi
        y = y / 180.0 * origin_shift
        return x, y
    
    def get_risk_for_points(self, points, hazard_type, batch_size=20):
        if self.debug:
            start_time = time.time()
            print(f"\nRisk scraping started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        """Get risk values for multiple points."""
        if hazard_type not in self.hazard_layers:
            raise ValueError(f"Invalid hazard type. Must be one of {list(self.hazard_layers.keys())}")
            
        hazard_layer = self.hazard_layers[hazard_type]
        print(f"Getting {hazard_type} risk for {len(points)} points...")
        
        meter_points = [self.lat_lon_to_meters(lat, lon) for lat, lon in points]
        point_batches = [meter_points[i:i+batch_size] for i in range(0, len(meter_points), batch_size)]
        
        all_results = []
        
        for point_batch in tqdm(point_batches, desc="Processing batches", disable=not self.debug):
            
            geometry = {
                "points": point_batch,
                "spatialReference": {"wkid": 3857}
            }
            
            url = f"{self.api_url}/{hazard_layer}/ImageServer/getSamples"
            params = {
                "geometryType": "esriGeometryMultipoint",
                "geometry": json.dumps(geometry),
                "sampleDistance": "1.25",
                "returnFirstValueOnly": "true",
                "interpolation": "RSP_BilinearInterpolation",
                "f": "pjson"
            }
            
            try:
                # if self.debug:
                #     print("Sending request to INARISK API...")
                
                response = requests.get(url, params=params)
                response.raise_for_status()
                result = response.json()
                
                if 'samples' in result:
                    batch_results = []
                    for i, sample in enumerate(result['samples']):
                        try:
                            risk_value = sample.get('value', '')
                            risk_value = float(risk_value) if risk_value != '' else 0.0
                        except (ValueError, TypeError):
                            risk_value = 0.0
                            
                        batch_results.append(risk_value)
                        
                        # if self.debug:
                        #     orig_point = points[batch_idx * batch_size + i]
                        #     print(f"Point {i+1}: ({orig_point[0]:.6f}, {orig_point[1]:.6f}) -> Risk: {risk_value}")
                    
                    all_results.extend(batch_results)
                else:
                    if self.debug:
                        print("No samples in response")
                    all_results.extend([0.0] * len(point_batch))
                    
            except Exception as e:
                if self.debug:
                    print(f"Error in batch {batch_idx+1}: {e}")
                all_results.extend([0.0] * len(point_batch))
            
            time.sleep(1)  # Rate limiting
        
        if self.debug:
            end_time = time.time()
            execution_time = end_time - start_time
            print(f"\nRisk scraping completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"Total risk scraping time: {execution_time:.2f} seconds")

        return all_results