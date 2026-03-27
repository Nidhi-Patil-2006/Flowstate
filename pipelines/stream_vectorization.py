import os
from whitebox import WhiteboxTools
import geopandas as gpd
import rasterio

wbt = WhiteboxTools()


# --------------------------------------------------
# Create QGIS style file so streams appear blue
# --------------------------------------------------
def create_stream_style(base_folder):

    qml_content = """
<qgis styleCategories="AllStyleCategories">
  <renderer-v2 type="singleSymbol">
    <symbols>
      <symbol type="line" name="0">
        <layer class="SimpleLine">
          <prop k="color" v="0,0,255,255"/>
          <prop k="width" v="1.2"/>
        </layer>
      </symbol>
    </symbols>
  </renderer-v2>
</qgis>
"""

    qml_path = os.path.join(base_folder, "streams.qml")

    with open(qml_path, "w") as f:
        f.write(qml_content)

    print("Created style:", qml_path)


# --------------------------------------------------
# Fix CRS of streams using DEM
# --------------------------------------------------
def fix_stream_crs(base_folder):

    streams_path = os.path.join(base_folder, "streams.shp")
    dtm_path = os.path.join(base_folder, "filled_dtm.tif")

    if not os.path.exists(streams_path):
        return

    streams = gpd.read_file(streams_path)

    # If CRS missing, copy from DEM
    if streams.crs is None:

        with rasterio.open(dtm_path) as src:
            dem_crs = src.crs

        streams = streams.set_crs(dem_crs)

        streams.to_file(streams_path)

        print("CRS assigned from DEM:", dem_crs)


# --------------------------------------------------
# Convert stream raster to vector
# --------------------------------------------------
def convert_streams(base_folder):

    streams_raster = os.path.abspath(os.path.join(base_folder, "streams.tif"))
    flow_dir = os.path.abspath(os.path.join(base_folder, "flow_direction.tif"))
    output = os.path.abspath(os.path.join(base_folder, "streams.shp"))

    if not os.path.exists(streams_raster):
        print("Missing streams.tif:", streams_raster)
        return

    if not os.path.exists(flow_dir):
        print("Missing flow_direction.tif:", flow_dir)
        return

    print("\nVectorizing streams:", base_folder)

    try:

        wbt.raster_streams_to_vector(
            streams=streams_raster,
            d8_pntr=flow_dir,
            output=output
        )

        print("Saved:", output)

        # Fix CRS automatically
        fix_stream_crs(base_folder)

        # Create automatic QGIS style
        create_stream_style(base_folder)

    except Exception as e:

        print("Vectorization failed:", base_folder)
        print(e)


# --------------------------------------------------
# Process all hydrology folders
# --------------------------------------------------
def process_all():

    hydrology_folder = os.path.abspath("data/hydrology")

    if not os.path.exists(hydrology_folder):
        print("Hydrology folder not found:", hydrology_folder)
        return

    folders = os.listdir(hydrology_folder)

    print("Datasets found:", folders)

    for folder in folders:

        base = os.path.join(hydrology_folder, folder)

        if os.path.isdir(base):
            convert_streams(base)


# --------------------------------------------------
# Run
# --------------------------------------------------
if __name__ == "__main__":

    process_all()