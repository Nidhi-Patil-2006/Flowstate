import os
import rasterio
import geopandas as gpd
import numpy as np
from rasterio.features import rasterize


# --------------------------------------------------
# Burn streams into DEM
# --------------------------------------------------
def burn_streams_into_dem(dem_path, streams_path, output_path, burn_depth=2):

    print("\nBurning streams into DEM:", dem_path)

    if not os.path.exists(dem_path):
        print("DEM missing:", dem_path)
        return

    if not os.path.exists(streams_path):
        print("Streams missing:", streams_path)
        return

    with rasterio.open(dem_path) as src:

        dem = src.read(1)
        transform = src.transform
        meta = src.meta

    streams = gpd.read_file(streams_path)

    if streams.empty:
        print("Streams layer empty:", streams_path)
        return

    # Rasterize stream lines
    stream_mask = rasterize(
        [(geom, 1) for geom in streams.geometry],
        out_shape=dem.shape,
        transform=transform
    )

    # Lower elevation where streams exist
    burned_dem = dem - (stream_mask * burn_depth)

    with rasterio.open(output_path, "w", **meta) as dst:
        dst.write(burned_dem, 1)

    print("Burned DEM saved:", output_path)


# --------------------------------------------------
# Process all hydrology folders
# --------------------------------------------------
def process_all():

    hydrology_folder = "data/hydrology"

    if not os.path.exists(hydrology_folder):
        print("Hydrology folder not found:", hydrology_folder)
        return

    folders = os.listdir(hydrology_folder)

    print("\nDatasets found:", folders)

    for folder in folders:

        base = os.path.join(hydrology_folder, folder)

        if not os.path.isdir(base):
            continue

        dem_path = os.path.join(base, "filled_dtm.tif")
        streams_path = os.path.join(base, "streams.shp")
        output_path = os.path.join(base, "burned_dtm.tif")

        if os.path.exists(dem_path) and os.path.exists(streams_path):

            burn_streams_into_dem(
                dem_path,
                streams_path,
                output_path,
                burn_depth=2
            )

        else:

            print("Skipping:", folder)


# --------------------------------------------------
# Run script
# --------------------------------------------------
if __name__ == "__main__":

    process_all()