import json
from pathlib import Path
import pandas as pd



def create_school_geojson(school_json: list, out_path: str | Path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    out = school_json.copy()


    # Create GeoJSON structure
    def create_geojson_feature_point(lat, lon, properties):
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat]
            },
            "properties": properties
        }
    
    def create_geojson_feature_collection(school_json):
        features = []
        for entry in school_json:
            lat = entry['lat']
            lon = entry['lon']
            properties = {k: v for k, v in entry.items() if k not in ['lat', 'lon']}
            feature = create_geojson_feature_point(lat, lon, properties)
            features.append(feature)
        return {
            "type": "FeatureCollection",
            "features": features
        }

    geojson_data = create_geojson_feature_collection(out)

    out_path.write_text(json.dumps(geojson_data, indent=2), encoding="utf-8")