import os
import rasterio
import numpy as np
import geopandas as gpd
from shapely.geometry import Point
from scipy.ndimage import maximum_filter

hydrology_folder = "data/hydrology"


def compute_slope(dtm):
    """Compute slope from DEM"""

    dzdx = np.gradient(dtm, axis=1)
    dzdy = np.gradient(dtm, axis=0)

    slope = np.sqrt(dzdx**2 + dzdy**2)

    return slope


def compute_twi(flow_acc, slope):
    """Compute Topographic Wetness Index"""

    slope[slope == 0] = 0.0001
    flow_acc[flow_acc <= 0] = 0.0001

    twi = np.log(flow_acc / np.tan(slope))

    return twi


def detect_hotspots(flow_acc_path, dtm_path, base_folder):

    print("Reading rasters...")

    with rasterio.open(flow_acc_path) as src:
        flow_acc = src.read(1)
        transform = src.transform
        crs = src.crs

    with rasterio.open(dtm_path) as src:
        dtm = src.read(1)

    print("Computing slope...")
    slope = compute_slope(dtm)

    print("Computing TWI...")
    twi = compute_twi(flow_acc, slope)

    twi[np.isinf(twi)] = np.nan

    # -------------------------------------------------
    # SAVE TWI RASTER
    # -------------------------------------------------

    twi_path = os.path.join(base_folder, "twi.tif")

    with rasterio.open(
        twi_path,
        "w",
        driver="GTiff",
        height=twi.shape[0],
        width=twi.shape[1],
        count=1,
        dtype=twi.dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        dst.write(twi, 1)

    print("Saved TWI raster:", twi_path)

    # -------------------------------------------------
    # HOTSPOT DETECTION
    # -------------------------------------------------

    # Extreme wetness zones
    twi_threshold = np.nanpercentile(twi, 99.5)

    print("TWI threshold:", twi_threshold)

    wet_mask = twi > twi_threshold

    # ensure significant upstream flow
    flow_mask = flow_acc > 500

    # detect only major peaks
    local_max = twi == maximum_filter(twi, size=40)

    hotspots = wet_mask & flow_mask & local_max

    rows, cols = np.where(hotspots)

    print("Raw hotspot candidates:", len(rows))

    points = []

    # minimum spacing between drainage nodes
    min_distance = 100  # meters

    for r, c in zip(rows, cols):

        x, y = rasterio.transform.xy(transform, r, c)
        new_point = Point(x, y)

        keep = True

        for p in points:
            if new_point.distance(p) < min_distance:
                keep = False
                break

        if keep:
            points.append(new_point)

    print("Filtered hotspots:", len(points))

    gdf = gpd.GeoDataFrame(geometry=points, crs=crs)

    output = os.path.join(base_folder, "waterlogging_hotspots.gpkg")

    gdf.to_file(output)

    print("Saved hotspots:", output)


def process_all():

    for folder in os.listdir(hydrology_folder):

        base = os.path.join(hydrology_folder, folder)

        if not os.path.isdir(base):
            continue

        flow_acc = os.path.join(base, "flow_accumulation.tif")
        dtm = os.path.join(base, "burned_dtm.tif")

        if os.path.exists(flow_acc) and os.path.exists(dtm):

            print("\n===================================")
            print("Processing:", folder)
            print("===================================")

            detect_hotspots(flow_acc, dtm, base)

        else:
            print("Skipping:", folder, "(missing required rasters)")


if __name__ == "__main__":
    process_all()