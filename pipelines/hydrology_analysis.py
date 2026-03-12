import whitebox
import os

wbt = whitebox.WhiteboxTools()

# 1. SET YOUR FOLDER
# Point this to the folder containing PIRAYANKUPPAM_DTM.tif or THANDALAM_DTM.tif
data_dir = r"D:\GeoAI\dtm_ai_project\data\dtm"
wbt.set_working_dir(data_dir)

# Define your input file name precisely as it appears in your folder
input_dtm = "PIRAYANKUPPAM_DTM.tif" 

print("Step 1: Filling Depressions (Hydrological Correction)...")
# (Input, Output)
wbt.fill_depressions(input_dtm, "filled_dtm.tif")

print("Step 2: Calculating Flow Accumulation (The Watershed Logic)...")
# (Input, Output)
wbt.d8_flow_accumulation("filled_dtm.tif", "accumulation.tif")

print("Step 3: Creating Drainage Lines (Thresholding)...")
# (Input Accumulation, Output Streams, Threshold Value)
# Lower threshold (e.g., 500) = more small street drains
# Higher threshold (e.g., 5000) = only the big main trunks
wbt.extract_streams("accumulation.tif", "drainage_network.tif", 1000.0)

print("Step 4: Mapping Waterlogging (Low-Lying Areas)...")
# (Filled - Original = Puddles)
wbt.subtract("filled_dtm.tif", input_dtm, "waterlogging_map.tif")

print("✅ DONE! You now have your Watershed lines and Waterlogging zones.")