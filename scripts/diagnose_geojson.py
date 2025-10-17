import geopandas as gpd
import os

# --- Configuration ---
# Relative path to the GeoJSON file from this script
GEOJSON_FILE_PATH = '../data/nz_population.geojson'
# ---

def diagnose_geojson(file_path):
    """
    Reads a GeoJSON file and checks for invalid or empty geometries.
    """
    print(f"--- Starting Diagnosis: {file_path} ---")

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found at '{file_path}'")
        print("Please check if GEOJSON_FILE_PATH is correct.")
        return

    # Read the file
    try:
        gdf = gpd.read_file(file_path)
        print(f"File read successfully. Found {len(gdf)} features.")
    except Exception as e:
        print(f"Error reading file: {e}")
        print("The file might be corrupted or not a valid GeoJSON format.")
        return

    # --- Checking Geometries ---
    print("\n--- Checking Geometries ---")

    # 1. Check for empty geometries
    empty_geometries = gdf[gdf.geometry.is_empty]
    if not empty_geometries.empty:
        print(f"Warning: Found {len(empty_geometries)} empty geometries.")
    else:
        print("No empty geometries were found.")

    # 2. Check for invalid geometries
    invalid_geometries = gdf[~gdf.geometry.is_valid]
    if not invalid_geometries.empty:
        print(f"★ PROBLEM FOUND ★: Found {len(invalid_geometries)} invalid geometries.")
        print("This is almost certainly the reason for map rendering failures.")
    else:
        print("All geometries are valid.")

    print("\n--- Diagnosis Complete ---")
    if not invalid_geometries.empty:
        print("Conclusion: Invalid geometries were found. This is very likely the cause of the choropleth map not displaying.")
        print("Suggestion: Open the file in a GIS tool like QGIS and run the 'Fix geometries' algorithm.")
    elif not empty_geometries.empty:
        print("Conclusion: Empty geometries were found. This could also be a potential cause of issues.")
    else:
        print("Conclusion: No obvious geometry errors were found in this basic check. The issue might be more complex (e.g., overly complex shapes).")


if __name__ == '__main__':
    diagnose_geojson(GEOJSON_FILE_PATH)