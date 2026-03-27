import json
import math
import os
import shutil
import subprocess
from typing import Any, Dict, Optional, Tuple

INPUT_FOLDER = "data/ground"
OUTPUT_FOLDER = "data/dtm"
TEMP_FOLDER = "data/temp_reprojected"

RESOLUTION = 1.0
NODATA = -9999.0


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False
    )


def run_pdal_pipeline(pipeline_dict: Dict[str, Any], json_path: str) -> subprocess.CompletedProcess:
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(pipeline_dict, f, indent=4)

    return run_command(["pdal", "pipeline", json_path])


def get_pdal_info(input_las: str) -> Optional[Dict[str, Any]]:
    result = run_command(["pdal", "info", "--metadata", input_las])

    if result.returncode != 0:
        print("PDAL info failed:")
        print(result.stderr or result.stdout)
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print("Could not parse PDAL metadata JSON.")
        return None


def find_srs_text(obj: Any) -> Optional[str]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() in {"compoundwkt", "prettywkt", "wkt", "json", "proj4", "horizontal"} and isinstance(value, str):
                if value.strip():
                    return value
            found = find_srs_text(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_srs_text(item)
            if found:
                return found
    return None


def find_epsg_code(obj: Any) -> Optional[str]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key.lower() == "authority" and isinstance(value, str) and "epsg:" in value.lower():
                authority = value.upper()
                idx = authority.find("EPSG:")
                return authority[idx:].split('"')[0].strip()
            found = find_epsg_code(value)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = find_epsg_code(item)
            if found:
                return found
    return None


def get_source_crs(metadata: Dict[str, Any]) -> Optional[str]:
    epsg = find_epsg_code(metadata)
    if epsg:
        return epsg

    metadata_section = metadata.get("metadata", {})
    srs = metadata_section.get("srs", {})
    if isinstance(srs, dict):
        epsg = find_epsg_code(srs)
        if epsg:
            return epsg
        srs_text = find_srs_text(srs)
        if srs_text:
            return srs_text

    srs_text = find_srs_text(metadata)
    return srs_text


def get_bounds_center(metadata: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    try:
        bounds = metadata["metadata"]["minx"], metadata["metadata"]["maxx"], metadata["metadata"]["miny"], metadata["metadata"]["maxy"]
        minx, maxx, miny, maxy = bounds
        center_x = (minx + maxx) / 2.0
        center_y = (miny + maxy) / 2.0
        return center_x, center_y
    except Exception:
        pass

    try:
        bbox = metadata["stats"]["bbox"]["native"]["bbox"]
        center_x = (bbox["minx"] + bbox["maxx"]) / 2.0
        center_y = (bbox["miny"] + bbox["maxy"]) / 2.0
        return center_x, center_y
    except Exception:
        return None


def is_geographic_crs(crs_text: str) -> bool:
    upper = crs_text.upper()
    geographic_tokens = ["EPSG:4326", "GEOGCS", "GEOGRAPHICCRS", "LATITUDE", "LONGITUDE"]
    return any(token in upper for token in geographic_tokens)


def extract_epsg_number(crs_text: str) -> Optional[int]:
    upper = crs_text.upper()
    if "EPSG:" in upper:
        try:
            return int(upper.split("EPSG:")[-1].split()[0].split('"')[0].split(",")[0].strip())
        except Exception:
            return None
    return None


def is_projected_epsg(epsg: int) -> bool:
    return (
        2000 <= epsg <= 39999
        and epsg not in {4326, 4258, 4269}
    )


def get_utm_epsg_from_lonlat(lon: float, lat: float) -> str:
    zone = int(math.floor((lon + 180) / 6) + 1)
    if lat >= 0:
        return f"EPSG:{32600 + zone}"
    return f"EPSG:{32700 + zone}"


def reproject_las(input_las: str, output_las: str, source_crs: Optional[str], target_crs: str) -> subprocess.CompletedProcess:
    reader: Dict[str, Any] = {
        "type": "readers.las",
        "filename": input_las
    }

    if source_crs:
        reader["override_srs"] = source_crs

    pipeline = {
        "pipeline": [
            reader,
            {
                "type": "filters.reprojection",
                "out_srs": target_crs
            },
            {
                "type": "writers.las",
                "filename": output_las,
                "a_srs": target_crs
            }
        ]
    }

    return run_pdal_pipeline(pipeline, "temp_reproject.json")


def generate_dtm(input_las: str, output_tif: str) -> subprocess.CompletedProcess:
    pipeline = {
        "pipeline": [
            input_las,
            {
                "type": "writers.gdal",
                "filename": output_tif,
                "resolution": RESOLUTION,
                "output_type": "idw",
                "data_type": "float32",
                "nodata": NODATA
            }
        ]
    }

    return run_pdal_pipeline(pipeline, "temp_generate_dtm.json")


def process_file(file_name: str) -> None:
    input_path = os.path.join(INPUT_FOLDER, file_name)
    name = os.path.splitext(file_name)[0]
    output_dtm = os.path.join(OUTPUT_FOLDER, f"{name}_DTM.tif")

    print(f"\nProcessing: {file_name}")

    metadata = get_pdal_info(input_path)
    if metadata is None:
        print("Skipping: could not read metadata.")
        return

    source_crs = get_source_crs(metadata)
    if not source_crs:
        print("Skipping: no CRS found in LAS metadata.")
        return

    print(f"Detected CRS: {source_crs}")

    target_input = input_path
    needs_reprojection = False

    epsg_num = extract_epsg_number(source_crs)
    if epsg_num is not None and is_projected_epsg(epsg_num):
        print("Projected CRS detected. Direct DTM generation will be used.")
    elif is_geographic_crs(source_crs):
        center = get_bounds_center(metadata)
        if center is None:
            print("Skipping: could not determine file center for UTM selection.")
            return

        center_lon, center_lat = center
        target_crs = get_utm_epsg_from_lonlat(center_lon, center_lat)
        print(f"Geographic CRS detected. Reprojecting to {target_crs}")

        os.makedirs(TEMP_FOLDER, exist_ok=True)
        reprojected_path = os.path.join(TEMP_FOLDER, f"{name}_reprojected.las")

        reproj_result = reproject_las(
            input_las=input_path,
            output_las=reprojected_path,
            source_crs=source_crs,
            target_crs=target_crs
        )

        if reproj_result.returncode != 0 or not os.path.exists(reprojected_path):
            print("Reprojection failed.")
            print(reproj_result.stderr or reproj_result.stdout)
            return

        target_input = reprojected_path
        needs_reprojection = True
    else:
        print("CRS detected but not clearly projected/geographic.")
        print("Trying direct DTM generation first.")

    dtm_result = generate_dtm(target_input, output_dtm)
    if dtm_result.returncode == 0 and os.path.exists(output_dtm):
        if needs_reprojection:
            print(f"DTM saved successfully after reprojection: {output_dtm}")
        else:
            print(f"DTM saved successfully: {output_dtm}")
    else:
        print("DTM generation failed.")
        print(dtm_result.stderr or dtm_result.stdout)


def cleanup_temp_files() -> None:
    for file_name in ["temp_generate_dtm.json", "temp_reproject.json"]:
        if os.path.exists(file_name):
            os.remove(file_name)

    if os.path.exists(TEMP_FOLDER):
        shutil.rmtree(TEMP_FOLDER, ignore_errors=True)


def main() -> None:
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    print("Generating DTM from ground LAS/LAZ files...")

    if not os.path.exists(INPUT_FOLDER):
        print(f"Input folder not found: {INPUT_FOLDER}")
        return

    files = [
        f for f in os.listdir(INPUT_FOLDER)
        if f.lower().endswith(".las") or f.lower().endswith(".laz")
    ]

    if not files:
        print("No LAS/LAZ files found in input folder.")
        return

    for file_name in files:
        process_file(file_name)

    cleanup_temp_files()
    print("\nDTM generation completed.")


if __name__ == "__main__":
    main()