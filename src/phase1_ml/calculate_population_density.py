import geopandas as gpd
import os

# ---------------------------------------------------------
# INPUT / OUTPUT
# ---------------------------------------------------------
input_gpkg = r"C:\Users\shiva\GeoSense_Agent\data\processed\bhubaneswar\BMC_Ward_Population.gpkg"

output_gpkg = r"C:\Users\shiva\GeoSense_Agent\data\processed\bhubaneswar\BMC_Ward_Population_Density.gpkg"

input_layer = "BMC_Ward_Population"
output_layer = "BMC_Ward_Population_Density"

# ---------------------------------------------------------
# READ DATA
# ---------------------------------------------------------
print("=" * 60)
print("BMC POPULATION DENSITY CALCULATION")
print("=" * 60)

print("\nReading:", input_gpkg)

gdf = gpd.read_file(
    input_gpkg,
    layer=input_layer
)

print("Number of wards:", len(gdf))

# ---------------------------------------------------------
# CHECK REQUIRED FIELDS
# ---------------------------------------------------------
required_fields = ["wardno", "totalwardp", "Shape_Area"]

missing = [f for f in required_fields if f not in gdf.columns]

if missing:
    raise ValueError(
        f"Missing required fields: {missing}\n"
        f"Available fields: {gdf.columns.tolist()}"
    )

# ---------------------------------------------------------
# CONVERT TO NUMERIC
# ---------------------------------------------------------
gdf["totalwardp"] = gdf["totalwardp"].astype(float)
gdf["Shape_Area"] = gdf["Shape_Area"].astype(float)

# ---------------------------------------------------------
# AREA
# Shape_Area is in square metres
# Convert m² → km²
# ---------------------------------------------------------
gdf["area_km2"] = gdf["Shape_Area"] / 1_000_000

# ---------------------------------------------------------
# POPULATION DENSITY
# people / km²
# ---------------------------------------------------------
gdf["pop_dens"] = (
    gdf["totalwardp"] / gdf["area_km2"]
)

# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------
print("\nPopulation density statistics")
print("-" * 40)

print("Minimum :", round(gdf["pop_dens"].min(), 2))
print("Maximum :", round(gdf["pop_dens"].max(), 2))
print("Mean    :", round(gdf["pop_dens"].mean(), 2))
print("Median  :", round(gdf["pop_dens"].median(), 2))

print(
    "\nMissing density values:",
    gdf["pop_dens"].isna().sum()
)

print("\nFirst 10 wards:")
print(
    gdf[
        ["wardno", "totalwardp", "area_km2", "pop_dens"]
    ].head(10).to_string(index=False)
)

print("\nLast 10 wards:")
print(
    gdf[
        ["wardno", "totalwardp", "area_km2", "pop_dens"]
    ].tail(10).to_string(index=False)
)

# ---------------------------------------------------------
# SAVE
# ---------------------------------------------------------
if os.path.exists(output_gpkg):
    os.remove(output_gpkg)

gdf.to_file(
    output_gpkg,
    layer=output_layer,
    driver="GPKG"
)

print("\n" + "=" * 60)
print("COMPLETED")
print("=" * 60)

print("Output:")
print(output_gpkg)

print("Output layer:")
print(output_layer)