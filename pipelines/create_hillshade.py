import os
import rasterio
import numpy as np


def hillshade(base_folder):

    dtm_path = os.path.join(base_folder, "filled_dtm.tif")

    if not os.path.exists(dtm_path):
        print("Skipping:", base_folder)
        return

    print("Generating hillshade:", base_folder)

    with rasterio.open(dtm_path) as src:
        elevation = src.read(1)
        transform = src.transform
        meta = src.meta

    x, y = np.gradient(elevation)

    slope = np.pi/2 - np.arctan(np.sqrt(x*x + y*y))
    aspect = np.arctan2(-x, y)

    azimuth = 315 * np.pi / 180
    altitude = 45 * np.pi / 180

    shaded = np.sin(altitude) * np.sin(slope) + \
             np.cos(altitude) * np.cos(slope) * np.cos(azimuth - aspect)

    shaded = (shaded - shaded.min()) / (shaded.max() - shaded.min())

    output = os.path.join(base_folder, "hillshade.tif")

    with rasterio.open(output, "w", **meta) as dst:
        dst.write(shaded.astype("float32"), 1)

    print("Saved:", output)


def process_all():

    hydrology_folder = "data/hydrology"

    for folder in os.listdir(hydrology_folder):
        base = os.path.join(hydrology_folder, folder)
        if os.path.isdir(base):
            hillshade(base)


if __name__ == "__main__":
    process_all()