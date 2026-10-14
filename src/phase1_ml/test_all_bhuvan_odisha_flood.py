import requests
import geopandas as gpd
from pathlib import Path
from PIL import Image
from io import BytesIO
import time

PROJECT = Path(r"C:\Users\shiva\GeoSense_Agent")

BMC = PROJECT / "data" / "shapefiles" / "bhubaneswar" / "BMC_Boundary.geojson"

WMS_URL = "https://bhuvan-ras2.nrsc.gov.in/cgi-bin/flood.exe"

OUTPUT = PROJECT / "data" / "raw" / "flood" / "odisha_bmc_layer_test.csv"

# ---------------------------------------------------------
# Odisha flood-event layers
# ---------------------------------------------------------

LAYERS = [
    "or_011011_flood",
    "or_050911_flood",
    "or_080911_flood",
    "or_100911_flood",
    "or_120911_flood",
    "or_140911_flood",
    "or_170911_flood",
    "or_190911_flood",
    "or_260911_flood",
    "or_280911_flood",
    "or_290911_flood",

    "or_121013_flood",
    "or_131013_flood",
    "or_131013_flood2",
    "or_141013_flood",
    "or_1213141013_flood",
    "or_12151013_flood",
    "or_151013_flood",
    "or_12161013_flood",
    "or_171013_flood",
    "or_181013_flood",
    "or_251013_flood",
    "or_281013_flood",
    "or_281013m_flood",
    "or_291013_flood",
    "or_28291013_flood",
]

# ---------------------------------------------------------
# BMC boundary
# ---------------------------------------------------------

bmc = gpd.read_file(BMC).to_crs(4326)

minx, miny, maxx, maxy = bmc.total_bounds

print("=" * 75)
print("BHUVAN ODISHA FLOOD — BMC EVENT SCREENING")
print("=" * 75)

print(f"BMC extent:")
print(f"{minx}, {miny}, {maxx}, {maxy}")

results = []

# ---------------------------------------------------------
# Test every layer
# ---------------------------------------------------------

for i, layer in enumerate(LAYERS, 1):

    print(f"\n[{i:02d}/{len(LAYERS)}] {layer}")

    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": layer,
        "STYLES": "",
        "CRS": "EPSG:4326",

        # WMS 1.3.0 EPSG:4326 axis order = lat,lon
        "BBOX": f"{miny},{minx},{maxy},{maxx}",

        "WIDTH": 600,
        "HEIGHT": 600,
        "FORMAT": "image/png",
        "TRANSPARENT": "TRUE",
    }

    try:

        r = requests.get(
            WMS_URL,
            params=params,
            timeout=120
        )

        if r.status_code != 200:
            print("   HTTP ERROR:", r.status_code)

            results.append({
                "layer": layer,
                "status": r.status_code,
                "content_type": r.headers.get("Content-Type"),
                "bytes": len(r.content),
                "unique_colors": None,
                "has_pixels": False
            })

            continue

        content_type = r.headers.get("Content-Type", "")

        if "image" not in content_type.lower():

            print("   Not an image")

            results.append({
                "layer": layer,
                "status": r.status_code,
                "content_type": content_type,
                "bytes": len(r.content),
                "unique_colors": None,
                "has_pixels": False
            })

            continue

        im = Image.open(BytesIO(r.content)).convert("RGBA")

        pixels = list(im.getdata())

        # Count non-transparent pixels
        visible = [
            p for p in pixels
            if p[3] > 0
        ]

        unique_visible = len(set(visible))

        has_pixels = len(visible) > 0

        print("   HTTP:", r.status_code)
        print("   Bytes:", len(r.content))
        print("   Visible pixels:", len(visible))
        print("   Unique visible colors:", unique_visible)

        if has_pixels:
            print("   >>> FLOOD PIXELS PRESENT")
        else:
            print("   >>> EMPTY")

        results.append({
            "layer": layer,
            "status": r.status_code,
            "content_type": content_type,
            "bytes": len(r.content),
            "unique_colors": unique_visible,
            "visible_pixels": len(visible),
            "has_pixels": has_pixels
        })

    except Exception as e:

        print("   ERROR:", e)

        results.append({
            "layer": layer,
            "status": None,
            "content_type": None,
            "bytes": None,
            "unique_colors": None,
            "visible_pixels": None,
            "has_pixels": False
        })

    time.sleep(0.5)


# ---------------------------------------------------------
# Save results
# ---------------------------------------------------------

import pandas as pd

df = pd.DataFrame(results)

df.to_csv(
    OUTPUT,
    index=False
)

print("\n" + "=" * 75)
print("SUMMARY")
print("=" * 75)

print("\nLayers containing visible pixels inside BMC:")

valid = df[df["has_pixels"] == True]

if len(valid) == 0:
    print("NONE")
else:
    print(valid[[
        "layer",
        "bytes",
        "visible_pixels",
        "unique_colors"
    ]].to_string(index=False))

print("\nTotal layers tested:", len(df))
print("Layers with flood pixels:", len(valid))

print("\nSaved:")
print(OUTPUT)

print("=" * 75)