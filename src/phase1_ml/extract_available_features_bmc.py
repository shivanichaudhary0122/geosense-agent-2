"""
BMC Candidate Feature Extraction

Calculates the currently available features for all BMC
candidate locations:

1. Distance to nearest road (m)
2. Population density (persons/km²)
3. Elevation (m)

Input files:
    candidate_locations.gpkg
    bmc_roads.gpkg
    BMC_Population_Density_Corrected.gpkg
    BMC_DEM_30m_UTM45N.tif

Output files:
    candidate_features_partial.gpkg
    candidate_features_partial.csv

Target CRS:
    EPSG:32645
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio


# ============================================================
# 1. PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\shiva\GeoSense_Agent"
)


# ============================================================
# 2. INPUT FILES
# ============================================================

CANDIDATES = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "candidate_locations.gpkg"
)

ROADS = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "osm"
    / "bmc_roads.gpkg"
)

POP_DENSITY = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "BMC_Population_Density_Corrected.gpkg"
)

DEM = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "BMC_DEM_30m_UTM45N.tif"
)


# ============================================================
# 3. OUTPUT FILES
# ============================================================

OUTPUT_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "candidate_features_partial.gpkg"
)

OUTPUT_CSV = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "candidate_features_partial.csv"
)

OUTPUT_LAYER = "candidate_features_partial"


# ============================================================
# 4. SETTINGS
# ============================================================

TARGET_CRS = "EPSG:32645"

CANDIDATE_LAYER = "candidate_locations"

# IMPORTANT:
# Actual layer inside bmc_roads.gpkg is "roads"
ROAD_LAYER = "roads"

POP_LAYER = "BMC_Population_Density_Corrected"


# ============================================================
# START
# ============================================================

print("=" * 70)
print("BMC CANDIDATE FEATURE EXTRACTION")
print("=" * 70)


# ============================================================
# 5. CHECK INPUT FILES
# ============================================================

print("\nChecking input files...")

input_files = {
    "Candidates": CANDIDATES,
    "Roads": ROADS,
    "Population density": POP_DENSITY,
    "DEM": DEM,
}

for name, path in input_files.items():

    print(f"\n{name}:")
    print(path)

    if not path.exists():
        raise FileNotFoundError(
            f"{name} file not found:\n{path}"
        )

print("\nAll input files found.")


# ============================================================
# 6. READ CANDIDATE LOCATIONS
# ============================================================

print("\n" + "=" * 70)
print("1. READING CANDIDATE LOCATIONS")
print("=" * 70)

candidates = gpd.read_file(
    CANDIDATES,
    layer=CANDIDATE_LAYER
)

print(
    f"Candidate locations: "
    f"{len(candidates):,}"
)

print(
    f"Original CRS: "
    f"{candidates.crs}"
)

# Reproject to metric CRS
candidates = candidates.to_crs(
    TARGET_CRS
)

print(
    f"Working CRS: "
    f"{candidates.crs}"
)


# ============================================================
# 7. DISTANCE TO ROADS
# ============================================================

print("\n" + "=" * 70)
print("2. CALCULATING DISTANCE TO NEAREST ROAD")
print("=" * 70)

print(
    f"Reading road layer: "
    f"{ROAD_LAYER}"
)

roads = gpd.read_file(
    ROADS,
    layer=ROAD_LAYER
)

print(
    f"Road features: "
    f"{len(roads):,}"
)

print(
    f"Road CRS: "
    f"{roads.crs}"
)

# Reproject roads
roads = roads.to_crs(
    TARGET_CRS
)

# Remove invalid geometries
roads = roads[
    roads.geometry.notna()
    & ~roads.geometry.is_empty
].copy()

print(
    f"Valid road features: "
    f"{len(roads):,}"
)

if roads.empty:
    raise ValueError(
        "No valid road geometries were found."
    )


# ------------------------------------------------------------
# Merge roads
# ------------------------------------------------------------

print("\nMerging road geometries...")

road_union = roads.geometry.union_all()

print("Road geometries merged successfully.")


# ------------------------------------------------------------
# Calculate distance
# ------------------------------------------------------------

print(
    "\nCalculating distance from "
    "each candidate to nearest road..."
)

candidates["dist_road_m"] = (
    candidates.geometry.distance(
        road_union
    )
)

print(
    "\nRoad-distance statistics:"
)

print(
    f"Minimum : "
    f"{candidates['dist_road_m'].min():.2f} m"
)

print(
    f"Maximum : "
    f"{candidates['dist_road_m'].max():.2f} m"
)

print(
    f"Mean    : "
    f"{candidates['dist_road_m'].mean():.2f} m"
)

print(
    f"Median  : "
    f"{candidates['dist_road_m'].median():.2f} m"
)


# ============================================================
# 8. POPULATION DENSITY
# ============================================================

print("\n" + "=" * 70)
print("3. EXTRACTING POPULATION DENSITY")
print("=" * 70)

print(
    f"Reading population layer: "
    f"{POP_LAYER}"
)

pop = gpd.read_file(
    POP_DENSITY,
    layer=POP_LAYER
)

print(
    f"Population polygons: "
    f"{len(pop):,}"
)

print(
    f"Population CRS: "
    f"{pop.crs}"
)

# Reproject
pop = pop.to_crs(
    TARGET_CRS
)

# Check field
if "pop_dens" not in pop.columns:

    print("\nAvailable fields:")

    for field in pop.columns:
        print(f"  {field}")

    raise ValueError(
        "\nField 'pop_dens' was not found "
        "in the population-density layer."
    )


print(
    "\nSpatially joining population density "
    "to candidate locations..."
)

# Keep only required fields
pop_subset = pop[
    [
        "pop_dens",
        "geometry"
    ]
].copy()


# ------------------------------------------------------------
# Spatial join
# ------------------------------------------------------------

candidate_pop = gpd.sjoin(
    candidates[
        [
            "candidate_id",
            "geometry"
        ]
    ],
    pop_subset,
    how="left",
    predicate="within"
)


# ------------------------------------------------------------
# Handle possible duplicate joins
# ------------------------------------------------------------

if "index_right" in candidate_pop.columns:

    candidate_pop = candidate_pop.drop(
        columns=["index_right"]
    )

candidate_pop = (
    candidate_pop
    .drop_duplicates(
        subset="candidate_id",
        keep="first"
    )
)


# ------------------------------------------------------------
# Transfer population density
# ------------------------------------------------------------

population_lookup = (
    candidate_pop
    .set_index("candidate_id")["pop_dens"]
)

candidates["pop_dens"] = (
    candidates["candidate_id"]
    .map(population_lookup)
)


print(
    "\nPopulation-density statistics:"
)

valid_pop = candidates[
    "pop_dens"
].dropna()

if len(valid_pop) > 0:

    print(
        f"Minimum : "
        f"{valid_pop.min():.2f} persons/km²"
    )

    print(
        f"Maximum : "
        f"{valid_pop.max():.2f} persons/km²"
    )

    print(
        f"Mean    : "
        f"{valid_pop.mean():.2f} persons/km²"
    )

    print(
        f"Median  : "
        f"{valid_pop.median():.2f} persons/km²"
    )


missing_pop = (
    candidates["pop_dens"]
    .isna()
    .sum()
)

print(
    f"\nCandidates without population density: "
    f"{missing_pop}"
)


# ============================================================
# 9. ELEVATION
# ============================================================

print("\n" + "=" * 70)
print("4. EXTRACTING ELEVATION")
print("=" * 70)

print(f"DEM:")
print(DEM)

with rasterio.open(DEM) as src:

    print(
        f"\nDEM CRS: "
        f"{src.crs}"
    )

    print(
        f"DEM resolution: "
        f"{src.res}"
    )

    print(
        f"DEM dimensions: "
        f"{src.width} x {src.height}"
    )

    print(
        f"DEM NoData: "
        f"{src.nodata}"
    )

    # Transform candidates to DEM CRS
    candidate_dem = candidates.to_crs(
        src.crs
    )

    coordinates = [
        (geom.x, geom.y)
        for geom in candidate_dem.geometry
    ]

    print(
        "\nSampling DEM at candidate locations..."
    )

    samples = list(
        src.sample(coordinates)
    )

    elevation_values = np.array(
        [
            value[0]
            for value in samples
        ],
        dtype=float
    )

    # Handle nodata
    if src.nodata is not None:

        elevation_values[
            np.isclose(
                elevation_values,
                src.nodata
            )
        ] = np.nan


candidates["elevation_m"] = (
    elevation_values
)


# ------------------------------------------------------------
# Elevation statistics
# ------------------------------------------------------------

valid_elevation = (
    candidates["elevation_m"]
    .dropna()
)

print(
    "\nElevation statistics:"
)

if len(valid_elevation) > 0:

    print(
        f"Minimum : "
        f"{valid_elevation.min():.2f} m"
    )

    print(
        f"Maximum : "
        f"{valid_elevation.max():.2f} m"
    )

    print(
        f"Mean    : "
        f"{valid_elevation.mean():.2f} m"
    )

    print(
        f"Median  : "
        f"{valid_elevation.median():.2f} m"
    )


missing_elevation = (
    candidates["elevation_m"]
    .isna()
    .sum()
)

print(
    f"\nCandidates without elevation: "
    f"{missing_elevation}"
)


# ============================================================
# 10. FEATURE QUALITY CHECK
# ============================================================

print("\n" + "=" * 70)
print("5. FEATURE QUALITY CHECK")
print("=" * 70)

feature_columns = [
    "dist_road_m",
    "pop_dens",
    "elevation_m",
]

print(
    "\nMissing values:"
)

for field in feature_columns:

    missing = (
        candidates[field]
        .isna()
        .sum()
    )

    print(
        f"{field:20s}: "
        f"{missing:4d} / "
        f"{len(candidates)}"
    )


# ============================================================
# 11. SAVE GEOPACKAGE
# ============================================================

print("\n" + "=" * 70)
print("6. SAVING GEOPACKAGE")
print("=" * 70)

if OUTPUT_GPKG.exists():

    print(
        "Existing output found. "
        "Replacing it..."
    )

    OUTPUT_GPKG.unlink()


candidates.to_file(
    OUTPUT_GPKG,
    layer=OUTPUT_LAYER,
    driver="GPKG"
)

print(
    f"\nGeoPackage saved:"
)

print(OUTPUT_GPKG)


# ============================================================
# 12. SAVE CSV
# ============================================================

print("\n" + "=" * 70)
print("7. SAVING CSV")
print("=" * 70)

# Convert to WGS84 for longitude/latitude
candidates_wgs84 = candidates.to_crs(
    "EPSG:4326"
)

csv_data = candidates.copy()

csv_data["longitude"] = (
    candidates_wgs84.geometry.x
)

csv_data["latitude"] = (
    candidates_wgs84.geometry.y
)

# Remove geometry for CSV
csv_data = csv_data.drop(
    columns=["geometry"]
)

csv_data.to_csv(
    OUTPUT_CSV,
    index=False
)

print(
    f"\nCSV saved:"
)

print(OUTPUT_CSV)


# ============================================================
# 13. SAMPLE OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("8. SAMPLE RESULTS")
print("=" * 70)

print(
    candidates[
        [
            "candidate_id",
            "dist_road_m",
            "pop_dens",
            "elevation_m"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# 14. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("FEATURE EXTRACTION COMPLETED")
print("=" * 70)

print(
    f"\nCandidates processed: "
    f"{len(candidates):,}"
)

print("\nFeatures calculated:")

print("  1. dist_road_m")
print("  2. pop_dens")
print("  3. elevation_m")

print("\nFeatures still required:")

print("  4. dist_hospital_m")
print("  5. flood_risk")

print("\nOutput GeoPackage:")
print(OUTPUT_GPKG)

print("\nOutput CSV:")
print(OUTPUT_CSV)

print("\n" + "=" * 70)