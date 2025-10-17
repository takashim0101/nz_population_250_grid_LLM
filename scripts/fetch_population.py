import requests
import json
import os

# ==========================================
# Settings
# ==========================================
API_URL = "https://services2.arcgis.com/vKb0s8tBIA3bdocZ/arcgis/rest/services/NZGrid_250m_ERP/FeatureServer/1/query"
OUTPUT_PATH = "../data/nz_population.geojson"

# ==========================================
# Query Parameters
# ==========================================
params = {
    "where": "1=1",         # Get all records
    "outFields": "*",        # All fields
    "f": "geojson",          # GeoJSON format
    "outSR": "4326",         # WGS84 coordinates
    "resultOffset": 0,       # Paging support (offset)
    "resultRecordCount": 2000  # Number of records to fetch at once
}

# ==========================================
# Paging
# ==========================================
features = []
print("📡 Fetching data from Stats NZ ArcGIS API...")

while True:
    res = requests.get(API_URL, params=params)
    res.raise_for_status()
    data = res.json()

    # Add the fetched features
    batch = data.get("features", [])
    features.extend(batch)

    print(f"   → Retrieved {len(batch)} records (Total: {len(features)})")

    # Check if there is a next page
    if len(batch) < params["resultRecordCount"]:
        break
    else:
        params["resultOffset"] += params["resultRecordCount"]

print(f"✅ All data fetched: {len(features)} features")

# ==========================================
# Save
# ==========================================
geojson_data = {
    "type": "FeatureCollection",
    "features": features
}

os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(geojson_data, f)

print(f"💾 Saved to {OUTPUT_PATH}")

