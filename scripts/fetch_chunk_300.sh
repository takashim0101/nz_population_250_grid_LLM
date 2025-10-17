#!/bin/bash
set -e
API_URL="https://services2.arcgis.com/vKb0s8tBIA3bdocZ/arcgis/rest/services/NZGrid_250m_ERP/FeatureServer/1/query"
OFFSET=2990000 # Start of chunk 300 (0-indexed, so 299*10000)
RECORDS_PER_FETCH=2000
FETCHES=5 # 10000 records / 2000 per fetch
FINAL_GEOJSON="chunk_300.geojson"

# Start the GeoJSON structure
echo '{"type":"FeatureCollection","features":[' > $FINAL_GEOJSON

echo "Fetching 10,000 records for chunk 300..."

for i in $(seq 1 $FETCHES); do
  echo "Fetching batch $i of $FETCHES..."
  CURRENT_OFFSET=$((OFFSET + (i-1) * RECORDS_PER_FETCH))
  URL="$API_URL?where=1%3D1&outFields=*&f=geojson&outSR=4326&resultOffset=$CURRENT_OFFSET&resultRecordCount=$RECORDS_PER_FETCH"
  
  # Fetch the batch and extract the content of the "features" array
  # The result is a comma-separated list of JSON objects
  FEATURES_JSON=$(curl -s "$URL" | python3 -c "import sys, json; d = json.load(sys.stdin); print(json.dumps(d.get('features', []))[1:-1])")
  
  # If features were returned, append them
  if [ -n "$FEATURES_JSON" ]; then
    # Add a comma before appending if this is not the first batch
    if [ "$i" -gt 1 ]; then
      # Check if the file is not empty and does not just contain the opening bracket
      if [ $(wc -c < "$FINAL_GEOJSON") -gt 33 ]; then
          echo "," >> $FINAL_GEOJSON
      fi
    fi
    echo "$FEATURES_JSON" >> $FINAL_GEOJSON
  fi
done

# Close the GeoJSON structure
echo ']}' >> $FINAL_GEOJSON

echo "Fetching complete. Data for chunk 300 saved to $FINAL_GEOJSON"
