"""
GeoSense - BMC Flood Feature
Shortcut approach using Bhuvan Odisha historical flood WMS layers

Output:
    candidate_features_final.gpkg
    candidate_features_final.csv

Flood variables:
    flood_event_count
    flood_risk
"""

import os
import io
import requests
import numpy as np
import pandas as pd
import geopandas as gpd

from PIL import Image
from pyproj import Transformer
from scipy.ndimage import distance_transform_edt


# ============================================================
# PATHS
# ============================================================

ROOT = r"C:\Users\shiva\GeoSense_Agent"

CANDIDATES = os.path.join(
    ROOT,
    "data",
    "processed",
    "bhubaneswar",
    "candidate_locations.gpkg"
)

PARTIAL_FEATURES = os.path.join(
    ROOT,
    "data",
    "processed",
    "bhubaneswar",
    "candidate_features_partial.gpkg"
)

HOSPITAL_FEATURES = os.path.join(
    ROOT,
    "data",
    "processed",
    "bhubaneswar",
    "candidate_hospital_distance.gpkg"
)

OUTPUT_GPKG = os.path.join(
    ROOT,
    "data",
    "processed",
    "bhubaneswar",
    "candidate_features_final.gpkg"
)

OUTPUT_CSV = os.path.join(
    ROOT,
    "data",
    "processed",
    "bhubaneswar",
    "candidate_features_final.csv"
)

FLOOD_DIR = os.path.join(
    ROOT,
    "data",
    "raw",
    "flood"
)

os.makedirs(FLOOD_DIR, exist_ok=True)


# ============================================================
# BHUVAN FLOOD WMS
# ============================================================

WMS_URL = "https://bhuvan-ras2.nrsc.gov.in/cgi-bin/flood.exe"

FLOOD_LAYERS = [
    "or_100911_flood",
    "or_120911_flood",
    "or_140911_flood",
    "or_141013_flood",
    "or_1213141013_flood",
    "or_12151013_flood",
    "or_151013_flood",
    "or_12161013_flood",
    "or_251013_flood",
    "or_281013m_flood",
    "or_291013_flood",
    "or_28291013_flood",
]


# ============================================================
# BMC BOUNDING BOX
# EPSG:4326
# ============================================================

MIN_LON = 85.73224587291011
MIN_LAT = 20.211271502493148
MAX_LON = 85.90339892522559
MAX_LAT = 20.36640055656385

WIDTH = 3000
HEIGHT = 3000

# Candidate influence radius
# 250 m = half of 500 m candidate grid spacing
BUFFER_M = 250.0


# ============================================================
# FUNCTION: DOWNLOAD FLOOD WMS
# ============================================================

def download_flood_layer(layer):

    output_png = os.path.join(
        FLOOD_DIR,
        f"{layer}_BMC_3000.png"
    )

    # Reuse existing file
    if os.path.exists(output_png):
        print(f"Using existing: {os.path.basename(output_png)}")

        with open(output_png, "rb") as f:
            content = f.read()

        return content

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": layer,
        "STYLES": "",
        "CRS": "EPSG:4326",

        # EPSG:4326 axis order for this Bhuvan service
        "BBOX": (
            f"{MIN_LAT},{MIN_LON},"
            f"{MAX_LAT},{MAX_LON}"
        ),

        "WIDTH": WIDTH,
        "HEIGHT": HEIGHT,
        "FORMAT": "image/png",
        "TRANSPARENT": "TRUE",
    }

    print(f"Downloading {layer} ...")

    r = requests.get(
        WMS_URL,
        params=params,
        timeout=180
    )

    r.raise_for_status()

    if "image/png" not in r.headers.get(
        "Content-Type", ""
    ).lower():
        raise RuntimeError(
            f"{layer}: server did not return PNG"
        )

    with open(output_png, "wb") as f:
        f.write(r.content)

    print(
        f"  Downloaded: "
        f"{len(r.content) / 1024:.1f} KB"
    )

    return r.content


# ============================================================
# FUNCTION: CREATE FLOOD MASK
# ============================================================

def get_flood_mask(content):

    image = Image.open(io.BytesIO(content)).convert("RGBA")

    image = np.array(image)

    rgb = image[:, :, :3]
    alpha = image[:, :, 3]

    # --------------------------------------------------------
    # Flood pixels in the Bhuvan images are cyan/colored
    # while background is transparent.
    #
    # Primary criterion = alpha > 0
    # --------------------------------------------------------

    mask = alpha > 0

    # Remove almost-black transparent/background artefacts
    brightness = rgb.sum(axis=2)

    mask = mask & (brightness > 20)

    return mask


# ============================================================
# FUNCTION: CONVERT CANDIDATES TO WGS84
# ============================================================

def candidate_pixel_coordinates(gdf):

    transformer = Transformer.from_crs(
        gdf.crs,
        "EPSG:4326",
        always_xy=True
    )

    lon, lat = transformer.transform(
        gdf.geometry.x.values,
        gdf.geometry.y.values
    )

    # Convert geographic coordinate to image pixel
    #
    # x = longitude
    # y = latitude
    #
    # Image row 0 = northern edge

    col = (
        (lon - MIN_LON)
        / (MAX_LON - MIN_LON)
        * WIDTH
    )

    row = (
        (MAX_LAT - lat)
        / (MAX_LAT - MIN_LAT)
        * HEIGHT
    )

    col = np.clip(
        col.astype(int),
        0,
        WIDTH - 1
    )

    row = np.clip(
        row.astype(int),
        0,
        HEIGHT - 1
    )

    return row, col


# ============================================================
# LOAD CANDIDATES
# ============================================================

print("\n" + "=" * 70)
print("GEOSENSE - BMC FLOOD FEATURE")
print("=" * 70)

print("\nLoading candidate locations...")

candidates = gpd.read_file(
    CANDIDATES,
    layer="candidate_locations"
)

print("Candidates:", len(candidates))
print("CRS:", candidates.crs)


# ============================================================
# LOAD EXISTING FEATURES
# ============================================================

print("\nLoading existing features...")

features = gpd.read_file(
    PARTIAL_FEATURES
)

print("Existing feature rows:", len(features))

# Ensure candidate ID is present
if "candidate_id" not in features.columns:
    raise RuntimeError(
        "candidate_id not found in candidate_features_partial.gpkg"
    )


# ============================================================
# LOAD HOSPITAL DISTANCE
# ============================================================

print("\nLoading hospital distance...")

hospital = gpd.read_file(
    HOSPITAL_FEATURES
)

print(
    "Hospital feature rows:",
    len(hospital)
)

# Keep only required columns
hospital_cols = [
    "candidate_id",
    "dist_hospital_m"
]

hospital = hospital[
    [c for c in hospital_cols if c in hospital.columns]
]

# Merge hospital distance
features = features.drop(
    columns=["dist_hospital_m"],
    errors="ignore"
)

features = features.merge(
    hospital,
    on="candidate_id",
    how="left"
)

print(
    "Hospital missing:",
    features["dist_hospital_m"].isna().sum()
)


# ============================================================
# ALIGN CANDIDATES WITH FEATURES
# ============================================================

candidate_lookup = candidates[
    ["candidate_id", "geometry"]
].copy()

candidate_lookup = candidate_lookup.merge(
    features[["candidate_id"]],
    on="candidate_id",
    how="inner"
)

candidate_lookup = candidate_lookup[
    ["candidate_id", "geometry"]
]

print(
    "Candidates used for flood:",
    len(candidate_lookup)
)


# ============================================================
# GET PIXEL LOCATIONS
# ============================================================

rows, cols = candidate_pixel_coordinates(
    candidate_lookup
)


# ============================================================
# FLOOD EVENT COUNT
# ============================================================

event_count = np.zeros(
    len(candidate_lookup),
    dtype=np.int16
)

layer_results = []


# ============================================================
# PROCESS EACH FLOOD LAYER
# ============================================================

for i, layer in enumerate(FLOOD_LAYERS, 1):

    print("\n" + "-" * 70)
    print(
        f"Layer {i}/{len(FLOOD_LAYERS)}: {layer}"
    )

    try:

        content = download_flood_layer(layer)

        mask = get_flood_mask(content)

        flood_pixels = int(mask.sum())

        print(
            "Flood pixels:",
            f"{flood_pixels:,}"
        )

        if flood_pixels == 0:
            print("No flood pixels detected.")
            layer_results.append({
                "layer": layer,
                "flood_pixels": 0,
                "affected_candidates": 0
            })
            continue

        # ----------------------------------------------------
        # Distance from every image pixel to nearest flood
        # pixel.
        #
        # distance_transform_edt calculates distance in
        # pixels.
        # ----------------------------------------------------

        non_flood = ~mask

        distance_pixels = distance_transform_edt(
            non_flood
        )

        # ----------------------------------------------------
        # Approximate metres/pixel
        # ----------------------------------------------------

        mean_lat = (
            (MIN_LAT + MAX_LAT) / 2.0
        )

        meters_per_degree_lat = 111320.0

        meters_per_degree_lon = (
            111320.0 *
            np.cos(np.deg2rad(mean_lat))
        )

        pixel_width_m = (
            (MAX_LON - MIN_LON)
            * meters_per_degree_lon
            / WIDTH
        )

        pixel_height_m = (
            (MAX_LAT - MIN_LAT)
            * meters_per_degree_lat
            / HEIGHT
        )

        pixel_size_m = (
            pixel_width_m +
            pixel_height_m
        ) / 2.0

        threshold_pixels = (
            BUFFER_M / pixel_size_m
        )

        print(
            f"Approx. pixel size: "
            f"{pixel_size_m:.2f} m"
        )

        print(
            f"250 m threshold: "
            f"{threshold_pixels:.1f} pixels"
        )

        # ----------------------------------------------------
        # Candidate distance to nearest flood pixel
        # ----------------------------------------------------

        candidate_distances_pixels = (
            distance_pixels[rows, cols]
        )

        candidate_distances_m = (
            candidate_distances_pixels
            * pixel_size_m
        )

        affected = (
            candidate_distances_m
            <= BUFFER_M
        )

        affected_count = int(
            affected.sum()
        )

        print(
            "Affected candidates:",
            affected_count
        )

        event_count += affected.astype(
            np.int16
        )

        layer_results.append({
            "layer": layer,
            "flood_pixels": flood_pixels,
            "affected_candidates": affected_count
        })

    except Exception as e:

        print(
            f"ERROR processing {layer}: {e}"
        )

        layer_results.append({
            "layer": layer,
            "flood_pixels": -1,
            "affected_candidates": -1
        })


# ============================================================
# CREATE FLOOD DATAFRAME
# ============================================================

flood_df = pd.DataFrame({
    "candidate_id":
        candidate_lookup["candidate_id"].values,

    "flood_event_count":
        event_count
})


# ============================================================
# NORMALIZED FLOOD RISK
# ============================================================

n_layers = len(FLOOD_LAYERS)

flood_df["flood_risk"] = (
    flood_df["flood_event_count"]
    / n_layers
)

# Ensure 0-1
flood_df["flood_risk"] = (
    flood_df["flood_risk"]
    .clip(0, 1)
)


# ============================================================
# MERGE FLOOD FEATURE
# ============================================================

features = features.drop(
    columns=[
        "flood_event_count",
        "flood_risk"
    ],
    errors="ignore"
)

features = features.merge(
    flood_df,
    on="candidate_id",
    how="left"
)


# ============================================================
# SAVE GPKG
# ============================================================

print("\n" + "=" * 70)
print("SAVING FINAL FEATURE DATA")
print("=" * 70)

features.to_file(
    OUTPUT_GPKG,
    layer="candidate_features_final",
    driver="GPKG"
)


# ============================================================
# SAVE CSV
# ============================================================

csv_features = features.copy()

csv_features["longitude"] = (
    csv_features.geometry
    .to_crs("EPSG:4326")
    .x
)

csv_features["latitude"] = (
    csv_features.geometry
    .to_crs("EPSG:4326")
    .y
)

csv_features = csv_features.drop(
    columns="geometry"
)

csv_features.to_csv(
    OUTPUT_CSV,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("FLOOD FEATURE SUMMARY")
print("=" * 70)

print(
    "\nFlood event count:"
)

print(
    flood_df["flood_event_count"]
    .describe()
)

print(
    "\nFlood risk:"
)

print(
    flood_df["flood_risk"]
    .describe()
)

print(
    "\nCandidates with flood influence:",
    (
        flood_df["flood_event_count"] > 0
    ).sum()
)

print(
    "Candidates without flood influence:",
    (
        flood_df["flood_event_count"] == 0
    ).sum()
)

print(
    "\nFlood layer summary:"
)

print(
    pd.DataFrame(layer_results).to_string(
        index=False
    )
)

print("\nOutputs:")
print(OUTPUT_GPKG)
print(OUTPUT_CSV)

print("\nDONE.")