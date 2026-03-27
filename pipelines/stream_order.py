import os
import geopandas as gpd


def assign_stream_order(base_folder):

    streams_path = os.path.join(base_folder, "streams.shp")

    if not os.path.exists(streams_path):
        print("Skipping:", base_folder)
        return

    print("Ordering streams:", base_folder)

    streams = gpd.read_file(streams_path)

    # Preserve CRS
    crs = streams.crs

    # Compute length
    streams["length"] = streams.geometry.length

    # Sort streams
    streams = streams.sort_values("length")

    # Assign simple hierarchy
    streams["order"] = 1
    streams.loc[streams["length"] > streams["length"].quantile(0.5), "order"] = 2
    streams.loc[streams["length"] > streams["length"].quantile(0.8), "order"] = 3

    output = os.path.join(base_folder, "streams_ordered.shp")

    streams = streams.set_crs(crs)

    streams.to_file(output)

    print("Saved:", output)

    create_style(base_folder)


# ------------------------------------------------
# Create QGIS style automatically
# ------------------------------------------------
def create_style(base_folder):

    qml = """
<qgis styleCategories="AllStyleCategories">
 <renderer-v2 type="categorizedSymbol" attr="order">
  <categories>

   <category value="1" label="1st Order">
    <symbol type="line">
     <layer class="SimpleLine">
      <prop k="color" v="0,150,255,255"/>
      <prop k="width" v="0.5"/>
     </layer>
    </symbol>
   </category>

   <category value="2" label="2nd Order">
    <symbol type="line">
     <layer class="SimpleLine">
      <prop k="color" v="0,0,255,255"/>
      <prop k="width" v="1.2"/>
     </layer>
    </symbol>
   </category>

   <category value="3" label="Main Channel">
    <symbol type="line">
     <layer class="SimpleLine">
      <prop k="color" v="0,0,150,255"/>
      <prop k="width" v="2"/>
     </layer>
    </symbol>
   </category>

  </categories>
 </renderer-v2>
</qgis>
"""

    path = os.path.join(base_folder, "streams_ordered.qml")

    with open(path, "w") as f:
        f.write(qml)

    print("Created style:", path)


# ------------------------------------------------
# Process all datasets
# ------------------------------------------------
def process_all():

    hydrology_folder = "data/hydrology"

    for folder in os.listdir(hydrology_folder):

        base = os.path.join(hydrology_folder, folder)

        if os.path.isdir(base):
            assign_stream_order(base)


if __name__ == "__main__":

    process_all()