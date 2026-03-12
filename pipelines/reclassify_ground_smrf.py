import pdal
import json
import os

input_folder = "data/raw"
output_folder = "data/smrf_classified"

os.makedirs(output_folder, exist_ok=True)

for file in os.listdir(input_folder):

    if file.lower().endswith(".las") or file.lower().endswith(".laz"):

        input_file = os.path.join(input_folder, file)
        output_file = os.path.join(output_folder, file)

        print("Processing:", file)

        pipeline = {
            "pipeline":[
                input_file,
                {
                    "type":"filters.smrf",
                    "slope":0.2,
                    "window":16.0,
                    "threshold":0.45,
                    "scalar":1.25
                },
                {
                    "type":"filters.range",
                    "limits":"Classification[2:2]"
                },
                output_file
            ]
        }

        pipeline_json = json.dumps(pipeline)

        p = pdal.Pipeline(pipeline_json)
        p.execute()

        print("Saved:", output_file)