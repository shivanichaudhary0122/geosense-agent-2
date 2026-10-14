"""
GeoSense Agent 2.0
Bhubaneswar Automatic Data Downloader

Study Area:
    Bhubaneswar Municipal Corporation (BMC)

Downloads:
    1. Official BMC boundary from BhubaneswarOne
    2. Geofabrik Eastern Zone OSM shapefile archive
    3. Extracts OSM shapefiles
    4. Clips available OSM layers to BMC boundary
    5. Saves clipped layers as GeoPackage files

Python environment:
    geosense / Python 3.11
"""

# ==============================================================
# IMPORTS
# ==============================================================

import os
import sys
import time
import zipfile
from pathlib import Path

import requests
import geopandas as gpd


# ==============================================================
# PROJECT PATHS
# ==============================================================

BASE_DIR = Path(r"C:\Users\shiva\GeoSense_Agent")

BMC_DIR = BASE_DIR / "data" / "shapefiles" / "bhubaneswar"
OSM_DIR = BASE_DIR / "data" / "shapefiles" / "osm"
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed" / "bhubaneswar"


# ==============================================================
# URLs
# ==============================================================

BMC_URL = (
    "https://bhubaneswarone.in/arcgis/rest/services/"
    "BhubaneswarOne/AdministrativeBoundary/MapServer/2/query"
    "?where=1%3D1"
    "&outFields=*"
    "&returnGeometry=true"
    "&outSR=4326"
    "&f=geojson"
)

OSM_URL = (
    "https://download.geofabrik.de/"
    "asia/india/eastern-zone-latest-free.shp.zip"
)


# ==============================================================
# OSM FILE NAMES
# ==============================================================

OSM_FILE_PATTERNS = {
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


# ==============================================================
# DIRECTORY SETUP
# ==============================================================

def create_directories():

    directories = [
        BMC_DIR,
        OSM_DIR,
        RAW_DIR,
        PROCESSED_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# ==============================================================
# STEP 1
# DOWNLOAD OFFICIAL BMC BOUNDARY
# ==============================================================

def download_bmc_boundary():

    print("\n" + "=" * 70)
    print("STEP 1: DOWNLOADING OFFICIAL BMC BOUNDARY")
    print("=" * 70)

    output_file = BMC_DIR / "BMC_Boundary.geojson"

    print("Connecting to BhubaneswarOne...")

    try:

        response = requests.get(
            BMC_URL,
            timeout=(30, 120)
        )

        response.raise_for_status()

        data = response.json()

        if "features" not in data:
            raise RuntimeError(
                "The BMC service did not return valid GeoJSON features."
            )

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as f:

            import json

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


# ==============================================================
# STEP 2
# DOWNLOAD OSM EASTERN ZONE
# ==============================================================

def download_osm():

    print("\n" + "=" * 70)
    print("STEP 2: DOWNLOADING OSM EASTERN ZONE")
    print("=" * 70)

    # ----------------------------------------------------------
    # OSM directory
    # ----------------------------------------------------------

    osm_dir = OSM_DIR / "eastern_zone"

    osm_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ----------------------------------------------------------
    # ZIP file
    # ----------------------------------------------------------

    zip_path = (
        osm_dir /
        "eastern-zone-latest-free.shp.zip"
    )

    print("Download URL:")
    print(OSM_URL)

    print("\nDownload size is approximately 562 MB.")
    print("Resume-enabled download.")
    print("Automatic retry is enabled.\n")

    # ----------------------------------------------------------
    # Check existing partial file
    # ----------------------------------------------------------

    existing_size = (
        zip_path.stat().st_size
        if zip_path.exists()
        else 0
    )

    if existing_size > 0:

        print(
            f"Existing partial file found:"
            f" {existing_size / (1024 ** 2):.2f} MB"
        )

        print(
            "The download will attempt to resume."
        )

    else:

        print(
            "No previous download found."
        )

        print(
            "Starting new download."
        )

    # ----------------------------------------------------------
    # Get remote file size
    # ----------------------------------------------------------

    total_size = 0

    try:

        head = requests.head(
            OSM_URL,
            allow_redirects=True,
            timeout=(30, 120)
        )

        head.raise_for_status()

        content_length = head.headers.get(
            "Content-Length"
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

    # ----------------------------------------------------------
    # Check whether existing file is complete
    # ----------------------------------------------------------

    if (
        total_size > 0
        and existing_size >= total_size
    ):

        print(
            "\nThe OSM ZIP already appears"
            " to be completely downloaded."
        )

        print(
            f"File: {zip_path}"
        )

        return zip_path

    # ----------------------------------------------------------
    # Download settings
    # ----------------------------------------------------------

    max_retries = 10

    chunk_size = 1024 * 1024

    # ----------------------------------------------------------
    # Retry loop
    # ----------------------------------------------------------

    for attempt in range(
        1,
        max_retries + 1
    ):

        current_size = (
            zip_path.stat().st_size
            if zip_path.exists()
            else 0
        )

        print(
            "\n"
            + "-" * 70
        )

        print(
            f"DOWNLOAD ATTEMPT "
            f"{attempt}/{max_retries}"
        )

        print(
            f"Current file size:"
            f" {current_size / (1024 ** 2):.2f} MB"
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

        # ------------------------------------------------------
        # Request headers
        # ------------------------------------------------------

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
                # Resume supported
                # ------------------------------------------------

                if (
                    current_size > 0
                    and response.status_code == 206
                ):

                    mode = "ab"

                    print(
                        "Server supports resume."
                    )

                    print(
                        "Continuing download..."
                    )

                # ------------------------------------------------
                # Server ignored Range
                # ------------------------------------------------

                elif (
                    current_size > 0
                    and response.status_code == 200
                ):

                    print(
                        "WARNING:"
                        " Server did not honor"
                        " the Range request."
                    )

                    print(
                        "Restarting this attempt"
                        " from the beginning."
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
                ) as file:

                    for chunk in response.iter_content(
                        chunk_size=chunk_size
                    ):

                        if not chunk:
                            continue

                        file.write(chunk)

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

            # ------------------------------------------------------
            # Check final file
            # ------------------------------------------------------

            final_size = zip_path.stat().st_size

            if (
                total_size > 0
                and final_size < total_size
            ):

                print(
                    "\nDownload is incomplete."
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
                "\n"
                "Connection interrupted."
            )

            print(
                f"Reason: {e}"
            )

            if zip_path.exists():

                partial_size = (
                    zip_path.stat().st_size
                )

                print(
                    "Partial file retained:"
                    f" {partial_size / (1024 ** 2):.2f} MB"
                )

            if attempt < max_retries:

                print(
                    "Waiting 10 seconds"
                    " before retry..."
                )

                time.sleep(10)

            else:

                print(
                    "\nMaximum retry count reached."
                )

                raise

    raise RuntimeError(
        "OSM download failed after"
        " maximum retry attempts."
    )


# ==============================================================
# STEP 3
# EXTRACT OSM ZIP
# ==============================================================

def extract_osm(zip_path):

    print("\n" + "=" * 70)
    print("STEP 3: EXTRACTING OSM DATA")
    print("=" * 70)

    extract_dir = (
        OSM_DIR /
        "eastern_zone" /
        "extracted"
    )

    extract_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    print("ZIP file:")
    print(zip_path)

    print("\nExtracting...")

    try:

        with zipfile.ZipFile(
            zip_path,
            "r"
        ) as zip_ref:

            zip_ref.extractall(
                extract_dir
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
            " The downloaded ZIP file is invalid."
        )

        print(
            "The download may be incomplete."
        )

        raise


# ==============================================================
# STEP 4
# FIND OSM SHAPEFILES
# ==============================================================

def find_osm_layers(extract_dir):

    print("\n" + "=" * 70)
    print("STEP 4: FINDING OSM SHAPEFILES")
    print("=" * 70)

    found = {}

    # ----------------------------------------------------------
    # Search recursively
    # ----------------------------------------------------------

    for root, dirs, files in os.walk(
        extract_dir
    ):

        for filename in files:

            lower_name = filename.lower()

            if not lower_name.endswith(
                ".shp"
            ):
                continue

            for layer_type, valid_names in (
                OSM_FILE_PATTERNS.items()
            ):

                valid_lower_names = {
                    x.lower()
                    for x in valid_names
                }

                if lower_name in valid_lower_names:

                    full_path = (
                        Path(root) /
                        filename
                    )

                    found[layer_type] = (
                        full_path
                    )

    # ----------------------------------------------------------
    # Print results
    # ----------------------------------------------------------

    for layer_type in [
        "roads",
        "buildings",
        "landuse",
        "pois",
    ]:

        if layer_type in found:

            print(
                f"{layer_type.upper():12}"
                f" -> {found[layer_type]}"
            )

        else:

            print(
                f"{layer_type.upper():12}"
                " -> NOT FOUND"
            )

    return found


# ==============================================================
# STEP 5
# CLIP OSM LAYERS TO BMC
# ==============================================================

def clip_osm_to_bmc(
    bmc_path,
    osm_layers
):

    print("\n" + "=" * 70)
    print("STEP 5: CLIPPING OSM DATA TO BMC")
    print("=" * 70)

    # ----------------------------------------------------------
    # Read BMC boundary
    # ----------------------------------------------------------

    print(
        "Reading BMC boundary..."
    )

    bmc = gpd.read_file(
        bmc_path
    )

    if bmc.empty:

        raise RuntimeError(
            "BMC boundary is empty."
        )

    print(
        f"BMC CRS: {bmc.crs}"
    )

    # ----------------------------------------------------------
    # Ensure geographic CRS for OSM clipping
    # ----------------------------------------------------------

    if bmc.crs is None:

        raise RuntimeError(
            "BMC boundary has no CRS."
        )

    # ----------------------------------------------------------
    # Fix invalid geometry if possible
    # ----------------------------------------------------------

    try:

        bmc["geometry"] = (
            bmc.geometry.make_valid()
        )

    except Exception:

        pass

    # ----------------------------------------------------------
    # Output directory
    # ----------------------------------------------------------

    output_dir = (
        PROCESSED_DIR /
        "osm"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # ----------------------------------------------------------
    # Process each OSM layer
    # ----------------------------------------------------------

    output_names = {
        "roads": "bmc_roads.gpkg",
        "buildings": "bmc_buildings.gpkg",
        "landuse": "bmc_landuse.gpkg",
        "pois": "bmc_pois.gpkg",
    }

    for layer_type, input_path in (
        osm_layers.items()
    ):

        print(
            "\nProcessing:"
            f" {layer_type}"
        )

        print(
            f"Input: {input_path}"
        )

        try:

            gdf = gpd.read_file(
                input_path
            )

            if gdf.empty:

                print(
                    "Layer is empty."
                    " Skipping."
                )

                continue

            print(
                f"Features loaded:"
                f" {len(gdf):,}"
            )

            # --------------------------------------------------
            # Reproject BMC to OSM CRS
            # --------------------------------------------------

            if gdf.crs is None:

                raise RuntimeError(
                    f"{layer_type} has no CRS."
                )

            bmc_layer = bmc.to_crs(
                gdf.crs
            )

            # --------------------------------------------------
            # Clip
            # --------------------------------------------------

            print(
                "Clipping to BMC boundary..."
            )

            clipped = gpd.clip(
                gdf,
                bmc_layer
            )

            print(
                f"Features after clip:"
                f" {len(clipped):,}"
            )

            if clipped.empty:

                print(
                    "No features found"
                    " inside BMC."
                )

                continue

            # --------------------------------------------------
            # Output
            # --------------------------------------------------

            output_file = (
                output_dir /
                output_names[layer_type]
            )

            print(
                "Saving:"
                f" {output_file}"
            )

            clipped.to_file(
                output_file,
                driver="GPKG",
                layer=layer_type
            )

            print(
                "SUCCESS"
            )

        except Exception as e:

            print(
                f"\nWARNING:"
                f" Could not process"
                f" {layer_type}"
            )

            print(
                f"Reason: {e}"
            )

            print(
                "Continuing with"
                " remaining layers..."
            )

    return output_dir


# ==============================================================
# STEP 6
# PRINT FINAL SUMMARY
# ==============================================================

def print_summary():

    print("\n")
    print("=" * 70)
    print("GEOSENSE BHUBANESWAR DATA DOWNLOAD SUMMARY")
    print("=" * 70)

    print(
        "\nBMC boundary:"
    )

    print(
        BMC_DIR /
        "BMC_Boundary.geojson"
    )

    print(
        "\nOSM data:"
    )

    print(
        OSM_DIR /
        "eastern_zone"
    )

    print(
        "\nProcessed OSM:"
    )

    print(
        PROCESSED_DIR /
        "osm"
    )

    print(
        "\nProject directory:"
    )

    print(
        BASE_DIR
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "CURRENT DOWNLOAD STAGE COMPLETED"
    )

    print(
        "=" * 70
    )


# ==============================================================
# MAIN
# ==============================================================

def main():

    print("\n")
    print("=" * 70)
    print("GEOSENSE AGENT 2.0")
    print("BHUBANESWAR AUTOMATIC DATA DOWNLOADER")
    print("=" * 70)

    print(
        "\nStudy Area:"
    )

    print(
        "Bhubaneswar Municipal Corporation (BMC)"
    )

    print(
        "\nProject:"
    )

    print(
        BASE_DIR
    )

    # ----------------------------------------------------------
    # Create directories
    # ----------------------------------------------------------

    create_directories()

    # ----------------------------------------------------------
    # Step 1
    # ----------------------------------------------------------

    bmc_path = download_bmc_boundary()

    # ----------------------------------------------------------
    # Step 2
    # ----------------------------------------------------------

    osm_zip = download_osm()

    # ----------------------------------------------------------
    # Step 3
    # ----------------------------------------------------------

    extract_dir = extract_osm(
        osm_zip
    )

    # ----------------------------------------------------------
    # Step 4
    # ----------------------------------------------------------

    osm_layers = find_osm_layers(
        extract_dir
    )

    # ----------------------------------------------------------
    # Step 5
    # ----------------------------------------------------------

    if osm_layers:

        clip_osm_to_bmc(
            bmc_path,
            osm_layers
        )

    else:

        print(
            "\nWARNING:"
            " No expected OSM shapefiles"
            " were found."
        )

    # ----------------------------------------------------------
    # Summary
    # ----------------------------------------------------------

    print_summary()


# ==============================================================
# PROGRAM ENTRY POINT
# ==============================================================

if __name__ == "__main__":
    main(Test-Path "C:\Users\shiva\GeoSense_Agent\data\shapefiles\osm\eastern-zone-latest-free.shp.zip")

