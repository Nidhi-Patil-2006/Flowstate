import os
import json
import pdal

files = [
    "data/raw/PIRAYANKUPPAM.las",
    "data/raw/THANDALAM.las"
]

for f in files:

    name = os.path.basename(f).replace(".las","")

    pipeline = {
        "pipeline":[
            f,
            {
                "type":"filters.range",
                "limits":"Classification[2:2]"
            },
            {
                "type":"filters.reprojection",
                "in_srs":"EPSG:4326",
                "out_srs":"EPSG:32644"
            },
            {
                "type":"writers.gdal",
                "filename":f"data/dtm/{name}_DTM.tif",
                "resolution":1.0,
                "radius":2.0,
                "output_type":"min",
                "nodata":-9999
            }
        ]
    }

    p = pdal.Pipeline(json.dumps(pipeline))
    p.execute()

    print("Generated:", name)   