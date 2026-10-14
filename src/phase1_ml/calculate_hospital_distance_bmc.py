"""
Calculate distance from BMC candidate locations to the
nearest hospital.

Hospital definition:
    OSM POI fclass == "hospital"

Input:
    candidate_locations.gpkg
    bmc_pois.gpkg

Outputs:
    hospital_locations.gpkg
    candidate_hospital_distance.gpkg
    candidate_hospital_distance.csv

CRS:
    EPSG:32645
"""

from pathlib import Path

import geopandas as gpd
import numpy as np


# ============================================================
# 1. PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(
    r"C:\Users\shiva\GeoSense_Agent"
)


# ============================================================
# 2. INPUTS
# ============================================================

CANDIDATES = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "candidate_locations.gpkg"
)

POIS = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "osm"
    / "bmc_pois.gpkg"
)


# ============================================================
# 3. OUTPUTS
# ============================================================

HOSPITAL_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "hospital_locations.gpkg"
)

CANDIDATE_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "candidate_hospital_distance.gpkg"
)

CSV_OUTPUT = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "bhubaneswar"
    / "candidate_hospital_distance.csv"
)


# ============================================================
# 4. SETTINGS
# ============================================================

TARGET_CRS = "EPSG:32645"

CANDIDATE_LAYER = "candidate_locations"
POI_LAYER = "pois"


# ============================================================
# START
# ============================================================

print("=" * 70)
print("BMC HOSPITAL DISTANCE CALCULATION")
print("=" * 70)


# ============================================================
# 5. CHECK INPUTS
# ============================================================

print("\nChecking input files...")

if not CANDIDATES.exists():
    raise FileNotFoundError(
        f"Candidate file not found:\n{CANDIDATES}"
    )

if not POIS.exists():
    raise FileNotFoundError(
        f"POI file not found:\n{POIS}"
    )

print("Candidate file found.")
print("POI file found.")


# ============================================================
# 6. READ CANDIDATES
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

candidates = candidates.to_crs(
    TARGET_CRS
)

print(
    f"Working CRS: "
    f"{candidates.crs}"
)


# ============================================================
# 7. READ OSM POIs
# ============================================================

print("\n" + "=" * 70)
print("2. READING OSM POIs")
print("=" * 70)

pois = gpd.read_file(
    POIS,
    layer=POI_LAYER
)

print(
    f"Total POIs: "
    f"{len(pois):,}"
)

print(
    f"POI CRS: "
    f"{pois.crs}"
)


# ============================================================
# 8. CHECK FCLASS
# ============================================================

if "fclass" not in pois.columns:

    print("\nAvailable fields:")

    for field in pois.columns:
        print(f"  {field}")

    raise ValueError(
        "Field 'fclass' was not found in the POI layer."
    )


# ============================================================
# 9. EXTRACT HOSPITALS
# ============================================================

print("\n" + "=" * 70)
print("3. EXTRACTING HOSPITALS")
print("=" * 70)

hospitals = pois[
    pois["fclass"]
    .astype(str)
    .str.lower()
    .eq("hospital")
].copy()

print(
    f"Hospital locations found: "
    f"{len(hospitals):,}"
)

if hospitals.empty:
    raise ValueError(
        "No hospital features were found "
        "with fclass = 'hospital'."
    )


# ============================================================
# 10. REPROJECT HOSPITALS
# ============================================================

hospitals = hospitals.to_crs(
    TARGET_CRS
)

# Remove invalid geometries
hospitals = hospitals[
    hospitals.geometry.notna()
    & ~hospitals.geometry.is_empty
].copy()

print(
    f"Valid hospital locations: "
    f"{len(hospitals):,}"
)


# ============================================================
# 11. SAVE HOSPITAL LOCATIONS
# ============================================================

print("\nSaving hospital locations...")

if HOSPITAL_OUTPUT.exists():
    HOSPITAL_OUTPUT.unlink()

hospitals.to_file(
    HOSPITAL_OUTPUT,
    layer="hospitals",
    driver="GPKG"
)

print(
    f"Hospital layer saved:"
)

print(HOSPITAL_OUTPUT)


# ============================================================
# 12. CALCULATE NEAREST HOSPITAL DISTANCE
# ============================================================

print("\n" + "=" * 70)
print("4. CALCULATING DISTANCE TO NEAREST HOSPITAL")
print("=" * 70)

print(
    "Merging hospital geometries..."
)

hospital_union = hospitals.geometry.union_all()

print(
    "Hospital geometries merged."
)

print(
    "\nCalculating candidate-to-hospital distances..."
)

candidates["dist_hospital_m"] = (
    candidates.geometry.distance(
        hospital_union
    )
)


# ============================================================
# 13. DISTANCE STATISTICS
# ============================================================

print("\n" + "=" * 70)
print("5. HOSPITAL DISTANCE STATISTICS")
print("=" * 70)

distance = candidates[
    "dist_hospital_m"
]

print(
    f"Minimum : "
    f"{distance.min():.2f} m"
)

print(
    f"Maximum : "
    f"{distance.max():.2f} m"
)

print(
    f"Mean    : "
    f"{distance.mean():.2f} m"
)

print(
    f"Median  : "
    f"{distance.median():.2f} m"
)


# ============================================================
# 14. CHECK MISSING VALUES
# ============================================================

missing = (
    candidates["dist_hospital_m"]
    .isna()
    .sum()
)

print(
    f"\nMissing hospital distances: "
    f"{missing}"
)


# ============================================================
# 15. SAVE GPKG
# ============================================================

print("\n" + "=" * 70)
print("6. SAVING CANDIDATE HOSPITAL DISTANCE")
print("=" * 70)

if CANDIDATE_OUTPUT.exists():
    CANDIDATE_OUTPUT.unlink()

candidates.to_file(
    CANDIDATE_OUTPUT,
    layer="candidate_hospital_distance",
    driver="GPKG"
)

print(
    f"\nGeoPackage saved:"
)

print(CANDIDATE_OUTPUT)


# ============================================================
# 16. SAVE CSV
# ============================================================

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

csv_data = csv_data.drop(
    columns=["geometry"]
)

csv_data.to_csv(
    CSV_OUTPUT,
    index=False
)

print(
    f"\nCSV saved:"
)

print(CSV_OUTPUT)


# ============================================================
# 17. SAMPLE
# ============================================================

print("\n" + "=" * 70)
print("7. SAMPLE RESULTS")
print("=" * 70)

print(
    candidates[
        [
            "candidate_id",
            "dist_hospital_m"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("HOSPITAL DISTANCE CALCULATION COMPLETED")
print("=" * 70)

print(
    f"\nCandidates processed: "
    f"{len(candidates):,}"
)

print(
    f"Hospitals used: "
    f"{len(hospitals):,}"
)

print(
    "\nFeature created:"
)

print(
    "  dist_hospital_m"
)

print(
    "\nOutputs:"
)

print(HOSPITAL_OUTPUT)
print(CANDIDATE_OUTPUT)
print(CSV_OUTPUT)

print("\n" + "=" * 70)