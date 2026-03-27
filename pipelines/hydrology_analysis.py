import os
import glob
import rasterio
from whitebox import WhiteboxTools

wbt = WhiteboxTools()
wbt.verbose = True

def repair_metadata(tif_path, default_crs="EPSG:4326"):
    """
    Checks if a TIFF has geokeys. If not, assigns a default CRS.
    This prevents WhiteboxTools from panicking.
    """
    with rasterio.open(tif_path, 'r+') as src:
        if src.crs is None:
            print(f"⚠️  Missing CRS in {os.path.basename(tif_path)}. Assigning {default_crs}...")
            src.crs = rasterio.crs.CRS.from_string(default_crs)

def run_hydrology_analysis(dtm_path, output_folder):
    dtm_path = os.path.abspath(dtm_path)
    output_folder = os.path.abspath(output_folder)
    os.makedirs(output_folder, exist_ok=True)

    # File paths
    filled_dtm = os.path.join(output_folder, "filled_dtm.tif")
    flow_dir = os.path.join(output_folder, "flow_direction.tif")
    flow_acc = os.path.join(output_folder, "flow_accumulation.tif")
    streams_raster = os.path.join(output_folder, "streams.tif")
    streams_vector = os.path.join(output_folder, "streams.gpkg")

    print(f"\n--- Processing: {os.path.basename(dtm_path)} ---")

    # 1. FIX METADATA FIRST
    try:
        repair_metadata(dtm_path)
    except Exception as e:
        print(f"❌ Could not repair metadata: {e}")
        return

    # 2. RUN TOOLS (With check to ensure output exists before next step)
    print("Filling sinks...")
    wbt.fill_depressions(dem=dtm_path, output=filled_dtm)
    
    if not os.path.exists(filled_dtm):
        print("❌ Fill Depressions failed. Skipping this file.")
        return

    print("Calculating flow direction...")
    wbt.d8_pointer(dem=filled_dtm, output=flow_dir)

    print("Calculating flow accumulation...")
    # Fix: Whitebox uses 'dem' or 'i' depending on the tool version. 
    # Usually 'dem' for accumulation as well.
    wbt.d8_flow_accumulation(i=filled_dtm, output=flow_acc, out_type="cells")

    if not os.path.exists(flow_acc):
        print("❌ Flow accumulation failed.")
        return

    print("Extracting streams...")
    wbt.extract_streams(flow_accum=flow_acc, output=streams_raster, threshold=1000)

    print("Converting streams to vector...")
    if os.path.exists(streams_raster) and os.path.exists(flow_dir):
        wbt.raster_streams_to_vector(
            streams=streams_raster,
            d8_pntr=flow_dir,
            output=streams_vector
        )
    
    print(f"✅ Finished: {os.path.basename(dtm_path)}")

def process_all_dtms():
    # Using relative paths from the project root
    dtm_folder = os.path.abspath("data/dtm")
    output_root = os.path.abspath("data/hydrology")
    
    dtm_files = glob.glob(os.path.join(dtm_folder, "*.tif"))
    print(f"Found {len(dtm_files)} DTM files")

    for dtm in dtm_files:
        name = os.path.splitext(os.path.basename(dtm))[0]
        output_folder = os.path.join(output_root, name)
        run_hydrology_analysis(dtm, output_folder)

if __name__ == "__main__":
    process_all_dtms()