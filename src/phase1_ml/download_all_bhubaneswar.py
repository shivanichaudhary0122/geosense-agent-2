"""
GeoSense Agent 2.0
Bhubaneswar Municipal Corporation (BMC)
Automatic Phase-1 Data Downloader

Downloads:
1. Official BMC boundary from BhubaneswarOne
2. OSM Eastern Zone shapefile from Geofabrik

Then:
- extracts OSM data
- identifies required OSM layers
- clips OSM layers to BMC
- saves clipped layers as GeoPackage
"""

# ============================================================
# IMPORTS
# ============================================================

import os
import time
import json
import zipfile
from pathlib import Path

import requests
import geopandas as gpd


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(r"C:\Users\shiva\GeoSense_Agent")

BMC_DIR = BASE_DIR / "data" / "shapefiles" / "bhubaneswar"

OSM_DIR = BASE_DIR / "data" / "shapefiles" / "osm"

RAW_DIR = BASE_DIR / "data" / "raw"

PROCESSED_DIR = (
    BASE_DIR
    / "data"
    / "processed"
    / "bhubaneswar"
)


# ============================================================
# CREATE DIRECTORIES
# ============================================================

for folder in [
    BMC_DIR,
    OSM_DIR,
    RAW_DIR,
    PROCESSED_DIR,
]:
    folder.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# URLs
# ============================================================

BMC_URL = (
    "https://bhubaneswarone.in/arcgis/rest/services/"
    "BhubaneswarOne/AdministrativeBoundary/MapServer/2/query"
)

OSM_URL = (
    "https://download.geofabrik.de/"
    "asia/india/eastern-zone-latest-free.shp.zip"
)


# ============================================================
# 1. DOWNLOAD BMC BOUNDARY
# ============================================================

def download_bmc_boundary():

    print("\n" + "=" * 70)
    print("STEP 1: DOWNLOADING OFFICIAL BMC BOUNDARY")
    print("=" * 70)

    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }

    output_file = (
        BMC_DIR /
        "BMC_Boundary.geojson"
    )

    print("Connecting to BhubaneswarOne...")

    try:

        response = requests.get(
            BMC_URL,
            params=params,
            timeout=(30, 120)
        )

        response.raise_for_status()

        data = response.json()

        if "features" not in data:

            raise RuntimeError(
                "BMC service did not return valid GeoJSON."
            )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                data,
                f,
                indent=2
            )

        print("SUCCESS")
        print("BMC boundary saved to:")
        print(output_file)

        return output_file

    except Exception as e:

        print("\nERROR downloading BMC boundary:")
        print(e)

        raise


# ============================================================
# 2. DOWNLOAD OSM EASTERN ZONE
# ============================================================

def download_osm():

    print("\n" + "=" * 70)
    print("STEP 2: DOWNLOADING OSM EASTERN ZONE")
    print("=" * 70)

    osm_dir = (
        OSM_DIR /
        "eastern_zone"
    )

    osm_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    zip_path = (
        osm_dir /
        "eastern-zone-latest-free.shp.zip"
    )

    print("Download URL:")
    print(OSM_URL)

    print("\nDownload size is approximately 562 MB.")
    print("Automatic retry is enabled.")
    print("A completely new download will be used if")
    print("no previous ZIP file exists.\n")

    # --------------------------------------------------------
    # Check existing ZIP
    # --------------------------------------------------------

    if zip_path.exists():

        existing_size = (
            zip_path.stat().st_size
        )

        print(
            f"Existing ZIP found:"
            f" {existing_size / (1024 ** 2):.2f} MB"
        )

        print(
            "This file will be used for resume."
        )

    else:

        existing_size = 0

        print(
            "No existing OSM ZIP found."
        )

        print(
            "Starting download from 0%."
        )

    # --------------------------------------------------------
    # Get remote file size
    # --------------------------------------------------------

    total_size = 0

    try:

        head = requests.head(
            OSM_URL,
            allow_redirects=True,
            timeout=(30, 120)
        )

        head.raise_for_status()

        content_length = (
            head.headers.get(
                "Content-Length"
            )
        )

        if content_length:

            total_size = int(
                content_length
            )

            print(
                f"\nRemote file size:"
                f" {total_size / (1024 ** 2):.2f} MB"
            )

    except Exception as e:

        print(
            "\nWARNING:"
            " Could not determine remote file size."
        )

        print(e)

    # --------------------------------------------------------
    # Check if existing file is complete
    # --------------------------------------------------------

    if (
        total_size > 0
        and existing_size >= total_size
    ):

        print(
            "\nOSM ZIP already appears complete."
        )

        print(
            f"File: {zip_path}"
        )

        return zip_path

    # --------------------------------------------------------
    # Download settings
    # --------------------------------------------------------

    max_retries = 10

    chunk_size = 1024 * 1024

    # --------------------------------------------------------
    # Download / resume loop
    # --------------------------------------------------------

    for attempt in range(
        1,
        max_retries + 1
    ):

        current_size = (
            zip_path.stat().st_size
            if zip_path.exists()
            else 0
        )

        print("\n" + "-" * 70)

        print(
            f"DOWNLOAD ATTEMPT "
            f"{attempt}/{max_retries}"
        )

        if total_size > 0:

            percent = (
                current_size /
                total_size *
                100
            )

            print(
                f"Current progress:"
                f" {percent:.2f}%"
            )

        else:

            print(
                f"Downloaded:"
                f" {current_size / (1024 ** 2):.2f} MB"
            )

        # ----------------------------------------------------
        # Resume header
        # ----------------------------------------------------

        headers = {}

        if current_size > 0:

            headers["Range"] = (
                f"bytes={current_size}-"
            )

        try:

            with requests.get(
                OSM_URL,
                headers=headers,
                stream=True,
                timeout=(30, 300)
            ) as response:

                # ------------------------------------------------
                # Server supports resume
                # ------------------------------------------------

                if (
                    current_size > 0
                    and response.status_code == 206
                ):

                    mode = "ab"

                    print(
                        "Resume supported."
                    )

                    print(
                        "Continuing download..."
                    )

                # ------------------------------------------------
                # Server does not support resume
                # ------------------------------------------------

                elif (
                    current_size > 0
                    and response.status_code == 200
                ):

                    print(
                        "Server did not honor"
                        " Range request."
                    )

                    print(
                        "Restarting from 0%."
                    )

                    mode = "wb"

                    current_size = 0

                else:

                    response.raise_for_status()

                    mode = "wb"

                # ------------------------------------------------
                # Download
                # ------------------------------------------------

                downloaded = current_size

                with open(
                    zip_path,
                    mode
                ) as f:

                    for chunk in response.iter_content(
                        chunk_size=chunk_size
                    ):

                        if not chunk:
                            continue

                        f.write(chunk)

                        downloaded += len(
                            chunk
                        )

                        if total_size > 0:

                            percent = (
                                downloaded /
                                total_size *
                                100
                            )

                            print(
                                f"\rDownloaded:"
                                f" {percent:6.2f}%",
                                end="",
                                flush=True
                            )

                print()

            # ----------------------------------------------------
            # Verify
            # ----------------------------------------------------

            final_size = (
                zip_path.stat().st_size
            )

            if (
                total_size > 0
                and final_size < total_size
            ):

                print(
                    "\nDownload incomplete."
                )

                print(
                    f"Current:"
                    f" {final_size / (1024 ** 2):.2f} MB"
                )

                print(
                    f"Expected:"
                    f" {total_size / (1024 ** 2):.2f} MB"
                )

                print(
                    "Retrying..."
                )

                time.sleep(5)

                continue

            print(
                "\nOSM download completed successfully."
            )

            print(
                "Saved to:"
            )

            print(zip_path)

            return zip_path

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError
        ) as e:

            print(
                "\nDownload connection interrupted."
            )

            print(
                f"Reason: {e}"
            )

            if zip_path.exists():

                partial_size = (
                    zip_path.stat().st_size
                )

                print(
                    f"Partial file retained:"
                    f" {partial_size / (1024 ** 2):.2f} MB"
                )

            if attempt < max_retries:

                print(
                    "Waiting 10 seconds before retry..."
                )

                time.sleep(10)

            else:

                raise

    raise RuntimeError(
        "OSM download failed after"
        " maximum retry attempts."
    )


# ============================================================
# 3. EXTRACT OSM
# ============================================================

def extract_osm(zip_file):

    print("\n" + "=" * 70)
    print("STEP 3: EXTRACTING OSM DATA")
    print("=" * 70)

    extract_dir = (
        OSM_DIR /
        "eastern_zone"
    )

    extract_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    marker = (
        extract_dir /
        "_EXTRACTED"
    )

    # --------------------------------------------------------
    # If already extracted
    # --------------------------------------------------------

    if marker.exists():

        print(
            "OSM data already extracted."
        )

        print(
            f"Location: {extract_dir}"
        )

        return extract_dir

    print(
        "Extracting OSM ZIP..."
    )

    print(
        "This may take several minutes."
    )

    try:

        with zipfile.ZipFile(
            zip_file,
            "r"
        ) as zip_ref:

            zip_ref.extractall(
                extract_dir
            )

        marker.write_text(
            "Extraction completed.",
            encoding="utf-8"
        )

        print(
            "OSM extraction completed."
        )

        print(
            "Extracted to:"
        )

        print(
            extract_dir
        )

        return extract_dir

    except zipfile.BadZipFile:

        print(
            "\nERROR:"
            " The OSM ZIP is invalid."
        )

        print(
            "Delete the ZIP and download it again."
        )

        raise


# ============================================================
# 4. FIND OSM SHAPEFILES
# ============================================================

def find_osm_layers(extract_dir):

    print("\n" + "=" * 70)
    print("STEP 4: LOCATING REQUIRED OSM LAYERS")
    print("=" * 70)

    found = {}

    # --------------------------------------------------------
    # Accepted filenames
    # --------------------------------------------------------

    valid_names = {

        "roads": {
            "gis_osm_roads_free_1.shp",
        },

        "buildings": {
            "gis_osm_buildings_free_1.shp",
            "gis_osm_buildings_a_free_1.shp",
        },

        "landuse": {
            "gis_osm_landuse_a_free_1.shp",
        },

        "pois": {
            "gis_osm_pois_free_1.shp",
        },
    }

    # Convert names to lowercase
    valid_names_lower = {

        key: {
            name.lower()
            for name in names
        }

        for key, names in valid_names.items()
    }

    # --------------------------------------------------------
    # Search recursively
    # --------------------------------------------------------

    for root, dirs, files in os.walk(
        extract_dir
    ):

        for filename in files:

            filename_lower = (
                filename.lower()
            )

            if not filename_lower.endswith(
                ".shp"
            ):
                continue

            for layer_name in valid_names_lower:

                if (
                    filename_lower
                    in valid_names_lower[layer_name]
                ):

                    full_path = (
                        Path(root) /
                        filename
                    )

                    found[layer_name] = (
                        full_path
                    )

    # --------------------------------------------------------
    # Print
    # --------------------------------------------------------

    for layer_name in [
        "roads",
        "buildings",
        "landuse",
        "pois",
    ]:

        if layer_name in found:

            print(
                f"{layer_name.upper():12}:"
                f" {found[layer_name]}"
            )

        else:

            print(
                f"{layer_name.upper():12}:"
                " NOT FOUND"
            )

    return found


# ============================================================
# 5. CLIP OSM TO BMC
# ============================================================

def clip_osm_to_bmc(
    bmc_file,
    osm_layers
):

    print("\n" + "=" * 70)
    print("STEP 5: CLIPPING OSM DATA TO BMC")
    print("=" * 70)

    print(
        "Reading BMC boundary..."
    )

    bmc = gpd.read_file(
        bmc_file
    )

    if bmc.empty:

        raise RuntimeError(
            "BMC boundary is empty."
        )

    # --------------------------------------------------------
    # Ensure CRS
    # --------------------------------------------------------

    if bmc.crs is None:

        bmc = bmc.set_crs(
            epsg=4326
        )

    else:

        bmc = bmc.to_crs(
            epsg=4326
        )

    print(
        f"BMC CRS: {bmc.crs}"
    )

    # --------------------------------------------------------
    # Dissolve BMC boundary
    # --------------------------------------------------------

    bmc = bmc.dissolve()

    # --------------------------------------------------------
    # Output directory
    # --------------------------------------------------------

    output_dir = (
        PROCESSED_DIR /
        "osm"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # Process each layer
    # --------------------------------------------------------

    for layer_name, input_file in (
        osm_layers.items()
    ):

        print()
        print(
            "=" * 60
        )

        print(
            f"PROCESSING: {layer_name.upper()}"
        )

        print(
            "=" * 60
        )

        input_file = Path(
            input_file
        )

        if not input_file.exists():

            print(
                "WARNING:"
                " Input file does not exist."
            )

            continue

        try:

            print(
                "Reading OSM layer..."
            )

            gdf = gpd.read_file(
                input_file
            )

            print(
                f"Features loaded:"
                f" {len(gdf):,}"
            )

            if gdf.empty:

                print(
                    "Layer is empty."
                    " Skipping."
                )

                continue

            # ------------------------------------------------
            # CRS
            # ------------------------------------------------

            if gdf.crs is None:

                raise RuntimeError(
                    f"{layer_name} has no CRS."
                )

            # ------------------------------------------------
            # Reproject BMC to OSM CRS
            # ------------------------------------------------

            bmc_layer = (
                bmc.to_crs(
                    gdf.crs
                )
            )

            # ------------------------------------------------
            # Clip
            # ------------------------------------------------

            print(
                "Clipping to BMC boundary..."
            )

            clipped = gpd.clip(
                gdf,
                bmc_layer
            )

            print(
                f"Features inside BMC:"
                f" {len(clipped):,}"
            )

            if clipped.empty:

                print(
                    "No features found."
                )

                continue

            # ------------------------------------------------
            # Output
            # ------------------------------------------------

            output_file = (
                output_dir /
                f"bmc_{layer_name}.gpkg"
            )

            clipped.to_file(
                output_file,
                driver="GPKG",
                layer=layer_name
            )

            print(
                "SUCCESS"
            )

            print(
                "Saved:"
            )

            print(
                output_file
            )

        except Exception as e:

            print(
                f"\nERROR processing"
                f" {layer_name}:"
            )

            print(e)

            print(
                "Continuing..."
            )


# ============================================================
# 6. MAIN
# ============================================================

def main():

    print("\n")

    print("=" * 70)
    print("GEOSENSE AGENT 2.0")
    print("BHUBANESWAR AUTOMATIC DATA DOWNLOADER")
    print("=" * 70)

    print()
    print(
        "Study Area:"
    )

    print(
        "Bhubaneswar Municipal Corporation (BMC)"
    )

    print()
    print(
        "Project:"
    )

    print(
        BASE_DIR
    )

    # --------------------------------------------------------
    # STEP 1
    # --------------------------------------------------------

    bmc_file = (
        download_bmc_boundary()
    )

    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    osm_zip = (
        download_osm()
    )

    # --------------------------------------------------------
    # STEP 3
    # --------------------------------------------------------

    osm_extract_dir = (
        extract_osm(
            osm_zip
        )
    )

    # --------------------------------------------------------
    # STEP 4
    # --------------------------------------------------------

    osm_layers = (
        find_osm_layers(
            osm_extract_dir
        )
    )

    print()

    print(
        "Required layers found:"
        f" {len(osm_layers)}"
    )

    # --------------------------------------------------------
    # STEP 5
    # --------------------------------------------------------

    if osm_layers:

        clip_osm_to_bmc(
            bmc_file,
            osm_layers
        )

    else:

        print(
            "\nWARNING:"
            " No required OSM layers found."
        )

    # --------------------------------------------------------
    # FINISHED
    # --------------------------------------------------------

    print("\n")

    print("=" * 70)
    print("DATA DOWNLOAD STAGE COMPLETED")
    print("=" * 70)

    print()

    print(
        "BMC boundary:"
    )

    print(
        bmc_file
    )

    print()

    print(
        "OSM directory:"
    )

    print(
        OSM_DIR
    )

    print()

    print(
        "Processed OSM:"
    )

    print(
        PROCESSED_DIR /
        "osm"
    )

    print()

    print(
        "Next stage:"
    )

    print(
        "SRTM DEM + Census + Flood + Land Use + Climate"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()