# # preprocess_population.py
import geopandas as gpd
import pandas as pd

# 1. Load data
input_file = '../data/nz_population.geojson'
gdf = gpd.read_file(input_file)

# 2. Extract only necessary columns
columns_needed = ['GridID', 'PopEst2023', 'geometry']
gdf = gdf[columns_needed]

# 3. Check for missing values
print("Missing values per column:")
print(gdf.isnull().sum())

# 4. Check/convert data types
print("\nData types:")
print(gdf.dtypes)

# 5. Check/convert coordinate system (NZTM2000)
if gdf.crs is None or gdf.crs.to_epsg() != 2193:
    gdf = gdf.to_crs(epsg=2193)

# 6. Calculate basic statistics
print("\n--- Population Statistics ---")
total_pop = gdf['PopEst2023'].sum()
avg_pop = gdf['PopEst2023'].mean()
max_pop = gdf['PopEst2023'].max()
min_pop = gdf['PopEst2023'].min()

print(f"Total population: {total_pop:,}")
print(f"Average population per grid: {avg_pop:,.2f}")
print(f"Max population in a grid: {max_pop:,}")
print(f"Min population in a grid: {min_pop:,}")

# 7. Save to CSV (for later visualization and clustering)
output_csv = '../data/nz_population_preprocessed.csv'
gdf.to_csv(output_csv, index=False)
print(f"\nPreprocessed data saved to: {output_csv}")










