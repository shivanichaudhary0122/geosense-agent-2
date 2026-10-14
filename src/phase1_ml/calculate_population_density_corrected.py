import geopandas as gpd
import os

# ============================================================
# BMC POPULATION DENSITY - CORRECTED VERSION
# ============================================================

# ------------------------------------------------------------
# INPUT
# ------------------------------------------------------------

INPUT_GPKG = (
    r"C:\Users\shiva\GeoSense_Agent\data\processed"
    r"\bhubaneswar\BMC_Ward_Population.gpkg"
)

INPUT_LAYER = "BMC_Ward_Population"


# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------

OUTPUT_GPKG = (
    r"C:\Users\shiva\GeoSense_Agent\data\processed"
    r"\bhubaneswar\BMC_Population_Density_Corrected.gpkg"
)

OUTPUT_LAYER = "BMC_Population_Density_Corrected"


# ------------------------------------------------------------
# AREA CALCULATION CRS
# ------------------------------------------------------------
# EPSG:32645 = WGS 84 / UTM Zone 45N
# Coordinate units = metres
# geometry.area = square metres

TARGET_CRS = "EPSG:32645"


print("=" * 70)
print("BMC POPULATION DENSITY - CORRECTED VERSION")
print("=" * 70)


# ============================================================
# STEP 1: READ INPUT
# ============================================================

print("\n[1] Reading BMC ward population layer...")

gdf = gpd.read_file(
    INPUT_GPKG,
    layer=INPUT_LAYER
)

print("Input file:")
print(INPUT_GPKG)

print("\nNumber of records:", len(gdf))
print("Original CRS:", gdf.crs)


# ============================================================
# STEP 2: CHECK WARD COUNT
# ============================================================

print("\n[2] Checking BMC ward count...")

if len(gdf) != 67:
    raise ValueError(
        f"Expected 67 BMC wards, but found {len(gdf)}."
    )

print("67 BMC wards confirmed.")


# ============================================================
# STEP 3: CHECK REQUIRED FIELDS
# ============================================================

print("\n[3] Checking required fields...")

required_fields = [
    "wardno",
    "totalwardp"
]

missing_fields = [
    field
    for field in required_fields
    if field not in gdf.columns
]

if missing_fields:
    raise ValueError(
        f"Missing required fields: {missing_fields}\n"
        f"Available fields:\n{gdf.columns.tolist()}"
    )

print("Required fields found.")
print("Population field: totalwardp")


# ============================================================
# STEP 4: CLEAN WARD IDs
# ============================================================

print("\n[4] Checking ward IDs...")

gdf["wardno"] = (
    gdf["wardno"]
    .astype(str)
    .str.strip()
)

duplicate_count = gdf["wardno"].duplicated().sum()

if duplicate_count > 0:
    raise ValueError(
        f"Duplicate ward IDs detected: {duplicate_count}"
    )

print("Duplicate ward IDs:", duplicate_count)


# ============================================================
# STEP 5: CHECK POPULATION
# ============================================================

print("\n[5] Checking population data...")

gdf["totalwardp"] = (
    gdf["totalwardp"]
    .astype(float)
)

if gdf["totalwardp"].isna().any():
    raise ValueError(
        "Missing population values detected."
    )

if (gdf["totalwardp"] < 0).any():
    raise ValueError(
        "Negative population values detected."
    )

print("Population unit: persons")

print(
    "Total BMC population:",
    int(gdf["totalwardp"].sum())
)


# ============================================================
# STEP 6: CHECK GEOMETRY
# ============================================================

print("\n[6] Checking ward geometry...")

empty_geometry = gdf.geometry.is_empty.sum()
invalid_geometry = (~gdf.geometry.is_valid).sum()

print("Empty geometries:", empty_geometry)
print("Invalid geometries:", invalid_geometry)

if empty_geometry > 0:
    raise ValueError(
        "Empty geometries detected."
    )

if invalid_geometry > 0:

    print("\nRepairing invalid geometries...")

    gdf["geometry"] = gdf.geometry.make_valid()

    invalid_after = (
        ~gdf.geometry.is_valid
    ).sum()

    print(
        "Invalid geometries after repair:",
        invalid_after
    )

    if invalid_after > 0:
        raise ValueError(
            "Some geometries remain invalid."
        )


# ============================================================
# STEP 7: REPROJECT TO EPSG:32645
# ============================================================

print("\n[7] Reprojecting wards...")

print("Target CRS:", TARGET_CRS)

gdf_projected = gdf.to_crs(TARGET_CRS)

print("Projected CRS:", gdf_projected.crs)


# ============================================================
# STEP 8: CALCULATE AREA
# ============================================================

print("\n[8] Calculating ward areas...")

# EPSG:32645 uses metres.
# Therefore geometry.area returns square metres.

gdf_projected["area_m2"] = (
    gdf_projected.geometry.area
)

# Convert square metres to square kilometres.

gdf_projected["area_km2"] = (
    gdf_projected["area_m2"] / 1_000_000
)

if gdf_projected["area_m2"].isna().any():
    raise ValueError(
        "Missing area values detected."
    )

if (gdf_projected["area_m2"] <= 0).any():
    raise ValueError(
        "Zero or negative ward area detected."
    )

print("Area calculation completed.")

print("area_m2  = m²")
print("area_km2 = km²")


# ============================================================
# STEP 9: CALCULATE POPULATION DENSITY
# ============================================================

print("\n[9] Calculating population density...")

# Population density =
# Population / Ward area in km²
#
# Unit = persons/km²

gdf_projected["pop_dens"] = (
    gdf_projected["totalwardp"]
    / gdf_projected["area_km2"]
)

if gdf_projected["pop_dens"].isna().any():
    raise ValueError(
        "Missing population density values detected."
    )

if (gdf_projected["pop_dens"] < 0).any():
    raise ValueError(
        "Negative population density detected."
    )

print("Density unit: persons/km²")


# ============================================================
# STEP 10: STATISTICS
# ============================================================

print("\n" + "=" * 70)
print("POPULATION DENSITY STATISTICS")
print("=" * 70)

print(
    "\nMinimum density:",
    round(
        gdf_projected["pop_dens"].min(),
        2
    ),
    "persons/km²"
)

print(
    "Maximum density:",
    round(
        gdf_projected["pop_dens"].max(),
        2
    ),
    "persons/km²"
)

print(
    "Mean density:",
    round(
        gdf_projected["pop_dens"].mean(),
        2
    ),
    "persons/km²"
)

print(
    "Median density:",
    round(
        gdf_projected["pop_dens"].median(),
        2
    ),
    "persons/km²"
)

print(
    "Total population:",
    int(gdf_projected["totalwardp"].sum())
)


# ============================================================
# STEP 11: SHOW FIRST 10 WARDS
# ============================================================

print("\n" + "=" * 70)
print("FIRST 10 WARDS")
print("=" * 70)

print(
    gdf_projected[
        [
            "wardno",
            "totalwardp",
            "area_m2",
            "area_km2",
            "pop_dens"
        ]
    ]
    .head(10)
    .to_string(index=False)
)


# ============================================================
# STEP 12: SAVE OUTPUT
# ============================================================

print("\n" + "=" * 70)
print("SAVING OUTPUT")
print("=" * 70)

if os.path.exists(OUTPUT_GPKG):

    print("Existing corrected output found.")
    print("Replacing it...")

    os.remove(OUTPUT_GPKG)


gdf_projected.to_file(
    OUTPUT_GPKG,
    layer=OUTPUT_LAYER,
    driver="GPKG"
)


# ============================================================
# STEP 13: FINAL VALIDATION
# ============================================================

print("\nChecking saved output...")

check = gpd.read_file(
    OUTPUT_GPKG,
    layer=OUTPUT_LAYER
)

print("Saved records:", len(check))
print("Saved CRS:", check.crs)


# ============================================================
# FINAL
# ============================================================

print("\n" + "=" * 70)
print("COMPLETED SUCCESSFULLY")
print("=" * 70)

print("\nOutput file:")
print(OUTPUT_GPKG)

print("\nOutput layer:")
print(OUTPUT_LAYER)

print("\nCRS:")
print(TARGET_CRS)

print("\nNumber of wards:")
print(len(check))

print("\nPopulation unit:")
print("persons")

print("\nArea units:")
print("area_m2  = m²")
print("area_km2 = km²")

print("\nDensity unit:")
print("persons/km²")

print("\nFields created:")
print("area_m2")
print("area_km2")
print("pop_dens")

print("\n" + "=" * 70)