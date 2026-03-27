import os
import numpy as np
import rasterio


# -----------------------------------------------------
# Normalize raster
# -----------------------------------------------------
def normalize(arr):

    arr = arr.astype(float)
    arr[arr <= 0] = np.nan

    mn = np.nanmin(arr)
    mx = np.nanmax(arr)

    if mx - mn == 0:
        return np.zeros_like(arr)

    return (arr - mn) / (mx - mn)


# -----------------------------------------------------
# Create QGIS style for flood risk
# -----------------------------------------------------
def create_flood_style(base_folder):

    qml = """
<qgis styleCategories="AllStyleCategories">
  <renderer-v2 type="singlebandpseudocolor">
    <rastershader>
      <colorrampshader colorRampType="INTERPOLATED">

        <item alpha="255" value="0" label="Low Risk" color="#00ff00"/>
        <item alpha="255" value="0.5" label="Medium Risk" color="#ffff00"/>
        <item alpha="255" value="1" label="High Risk" color="#ff0000"/>

      </colorrampshader>
    </rastershader>
  </renderer-v2>
</qgis>
"""

    path = os.path.join(base_folder, "flood_risk.qml")

    with open(path, "w") as f:
        f.write(qml)

    print("Created style:", path)


# -----------------------------------------------------
# Compute flood risk
# -----------------------------------------------------
def compute_flood_risk(base_folder):

    flow_acc_path = os.path.join(base_folder, "flow_accumulation.tif")
    twi_path = os.path.join(base_folder, "twi.tif")
    dtm_path = os.path.join(base_folder, "filled_dtm.tif")

    if not (os.path.exists(flow_acc_path)
            and os.path.exists(twi_path)
            and os.path.exists(dtm_path)):

        print("Skipping:", base_folder)
        return

    print("Computing flood risk:", base_folder)

    with rasterio.open(flow_acc_path) as src:
        flow_acc = src.read(1)
        meta = src.meta

    with rasterio.open(twi_path) as src:
        twi = src.read(1)

    with rasterio.open(dtm_path) as src:
        dtm = src.read(1)

    # slope
    gy, gx = np.gradient(dtm)
    slope = np.sqrt(gx**2 + gy**2)

    # normalize layers
    n_flow = normalize(flow_acc)
    n_twi = normalize(twi)
    n_slope = normalize(slope)

    # flood risk formula
    flood_risk = (n_flow * 0.4) + (n_twi * 0.4) + ((1 - n_slope) * 0.2)

    flood_risk[np.isnan(flood_risk)] = 0

    output = os.path.join(base_folder, "flood_risk.tif")

    with rasterio.open(output, "w", **meta) as dst:
        dst.write(flood_risk.astype("float32"), 1)

    print("Saved:", output)

    create_flood_style(base_folder)


# -----------------------------------------------------
# Process all datasets
# -----------------------------------------------------
def process_all():

    hydrology_folder = "data/hydrology"

    for folder in os.listdir(hydrology_folder):

        base = os.path.join(hydrology_folder, folder)

        if os.path.isdir(base):

            compute_flood_risk(base)


# -----------------------------------------------------
# Run
# -----------------------------------------------------
if __name__ == "__main__":

    process_all()