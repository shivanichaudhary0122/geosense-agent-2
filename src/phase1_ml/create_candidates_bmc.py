"""
Create 500 m candidate locations for Bhubaneswar Municipal Corporation (BMC)

Input:
    BMC boundary:
    data/shapefiles/bhubaneswar/BMC_Boundary.geojson

Output:
    data/processed/bhubaneswar/candidate_locations.gpkg
    Layer: candidate_locations

CRS:
    EPSG:32645 (WGS 84 / UTM zone 45N)

Grid spacing:
    500 m

Only points falling inside the BMC boundary are retained.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Point


# ============================================================
# 1. PATHS
# ============================================================

PROJECT_ROOT = Path(r"C:\Users\shiva\GeoSense_Agent")

BMC_BOUNDARY = (
    PROJECT_ROOT
    / "data"
    / "shapefiles"
    / "bhubaneswar"
    / "BMC_Boundary.geojson"
)

OUTPUT_GPKG = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "candidate_locations.gpkg"
)

OUTPUT_LAYER = "candidate_locations"


# ============================================================
# 2. PARAMETERS
# ============================================================

TARGET_CRS = "EPSG:32645"
GRID_SPACING = 500  # metres


# ============================================================
# 3. CHECK INPUT
# ============================================================

print("=" * 70)
print("BMC 500 m CANDIDATE LOCATION GRID")
print("=" * 70)

print("\nInput boundary:")
print(BMC_BOUNDARY)

if not BMC_BOUNDARY.exists():
    raise FileNotFoundError(
        f"\nBMC boundary not found:\n{BMC_BOUNDARY}"
    )


# ============================================================
# 4. READ BMC BOUNDARY
# ============================================================

print("\nReading BMC boundary...")

bmc = gpd.read_file(BMC_BOUNDARY)

if bmc.empty:
    raise ValueError("BMC boundary is empty.")

print(f"Number of boundary features: {len(bmc)}")
print(f"Original CRS: {bmc.crs}")


# ============================================================
# 5. MERGE BOUNDARY INTO ONE GEOMETRY
# ============================================================

print("\nMerging BMC boundary geometry...")

bmc_geometry = bmc.geometry.union_all()

if bmc_geometry.is_empty:
    raise ValueError("BMC boundary geometry is empty.")

print("Boundary geometry created successfully.")


# ============================================================
# 6. REPROJECT TO UTM 45N
# ============================================================

print(f"\nReprojecting boundary to {TARGET_CRS}...")

bmc_utm = gpd.GeoSeries(
    [bmc_geometry],
    crs=bmc.crs
).to_crs(TARGET_CRS)

bmc_geometry_utm = bmc_utm.iloc[0]

print(f"Target CRS: {TARGET_CRS}")

# Boundary area
boundary_area_km2 = bmc_geometry_utm.area / 1_000_000

print(f"BMC boundary area: {boundary_area_km2:.3f} km²")


# ============================================================
# 7. CREATE 500 m GRID
# ============================================================

print(f"\nCreating {GRID_SPACING} m candidate grid...")

minx, miny, maxx, maxy = bmc_geometry_utm.bounds

print("\nBMC projected extent:")
print(f"Min X: {minx:.2f}")
print(f"Min Y: {miny:.2f}")
print(f"Max X: {maxx:.2f}")
print(f"Max Y: {maxy:.2f}")

print("\nGenerating grid points...")

# Generate X and Y coordinates
x_coords = np.arange(
    minx,
    maxx + GRID_SPACING,
    GRID_SPACING
)

y_coords = np.arange(
    miny,
    maxy + GRID_SPACING,
    GRID_SPACING
)

print(f"Number of X positions: {len(x_coords)}")
print(f"Number of Y positions: {len(y_coords)}")

# Generate points
points = [
    Point(x, y)
    for x in x_coords
    for y in y_coords
]

print(f"Total grid points before clipping: {len(points):,}")


# ============================================================
# 8. RETAIN POINTS INSIDE BMC
# ============================================================

print("\nSelecting points inside BMC boundary...")

candidate_points = [
    point
    for point in points
    if bmc_geometry_utm.contains(point)
]

print(
    f"Candidate points inside BMC: "
    f"{len(candidate_points):,}"
)


# ============================================================
# 9. CREATE GEODATAFRAME
# ============================================================

print("\nCreating candidate GeoDataFrame...")

candidates = gpd.GeoDataFrame(
    {
        "candidate_id": [
            f"BMC_{i:05d}"
            for i in range(1, len(candidate_points) + 1)
        ],
        "x_utm": [point.x for point in candidate_points],
        "y_utm": [point.y for point in candidate_points],
    },
    geometry=candidate_points,
    crs=TARGET_CRS
)


# ============================================================
# 10. ADD BASIC ATTRIBUTES
# ============================================================

candidates["grid_m"] = GRID_SPACING

# Longitude / latitude for reference
candidates_wgs84 = candidates.to_crs("EPSG:4326")

candidates["longitude"] = candidates_wgs84.geometry.x
candidates["latitude"] = candidates_wgs84.geometry.y


# ============================================================
# 11. CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_GPKG.parent.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# 12. REMOVE OLD OUTPUT IF IT EXISTS
# ============================================================

if OUTPUT_GPKG.exists():
    print("\nExisting candidate file found.")
    print("Replacing existing output...")

    OUTPUT_GPKG.unlink()


# ============================================================
# 13. SAVE TO GEOPACKAGE
# ============================================================

print("\nSaving candidate locations...")

candidates.to_file(
    OUTPUT_GPKG,
    layer=OUTPUT_LAYER,
    driver="GPKG"
)


# ============================================================
# 14. VALIDATION
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION")
print("=" * 70)

print(f"Output file:")
print(OUTPUT_GPKG)

print(f"\nOutput layer:")
print(OUTPUT_LAYER)

print(f"CRS:")
print(candidates.crs)

print(f"Candidate locations:")
print(f"{len(candidates):,}")

print(f"Grid spacing:")
print(f"{GRID_SPACING} m")

print(
    f"\nCandidate longitude range: "
    f"{candidates['longitude'].min():.6f} - "
    f"{candidates['longitude'].max():.6f}"
)

print(
    f"Candidate latitude range: "
    f"{candidates['latitude'].min():.6f} - "
    f"{candidates['latitude'].max():.6f}"
)

print("\nFirst 5 candidate locations:")
print(
    candidates[
        [
            "candidate_id",
            "longitude",
            "latitude",
            "x_utm",
            "y_utm",
        ]
    ].head()
)


# ============================================================
# 15. FINISHED
# ============================================================

print("\n" + "=" * 70)
print("CANDIDATE GRID CREATED SUCCESSFULLY")
print("=" * 70)

print(f"\nSaved to:")
print(OUTPUT_GPKG)

print(f"\nLayer:")
print(OUTPUT_LAYER)