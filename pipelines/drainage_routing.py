import os
import numpy as np
import geopandas as gpd
import rasterio
from shapely.geometry import LineString
from skimage.graph import route_through_array


# --------------------------------------------
# Build cost surface
# --------------------------------------------
def build_cost_surface(flow_acc, slope):

    cost = slope + (1 / (flow_acc + 1))

    cost[np.isnan(cost)] = 9999

    return cost


# --------------------------------------------
# Convert world coords to pixel
# --------------------------------------------
def world_to_pixel(transform, x, y):

    row, col = rasterio.transform.rowcol(transform, x, y)

    return row, col


# --------------------------------------------
# Main routing function
# --------------------------------------------
def route_drainage(base_folder):

    print("\nProcessing:", base_folder)

    dtm = os.path.join(base_folder, "burned_dtm.tif")
    flow_acc = os.path.join(base_folder, "flow_accumulation.tif")
    streams = os.path.join(base_folder, "streams.shp")
    hotspots = os.path.join(base_folder, "waterlogging_hotspots.gpkg")

    with rasterio.open(dtm) as src:

        elevation = src.read(1)
        transform = src.transform
        crs = src.crs

    with rasterio.open(flow_acc) as src:

        flow_accum = src.read(1)

    # compute slope
    gy, gx = np.gradient(elevation)

    slope = np.sqrt(gx**2 + gy**2)

    # build cost surface
    cost_surface = build_cost_surface(flow_accum, slope)

    streams_gdf = gpd.read_file(streams)
    hotspots_gdf = gpd.read_file(hotspots)

    stream_union = streams_gdf.geometry.union_all()

    routes = []

    for pt in hotspots_gdf.geometry:

        start = world_to_pixel(transform, pt.x, pt.y)

        # nearest stream point
        nearest_stream = streams_gdf.distance(pt).idxmin()

        stream_pt = streams_gdf.geometry.iloc[nearest_stream].interpolate(0.5, normalized=True)

        end = world_to_pixel(transform, stream_pt.x, stream_pt.y)

        try:

            path, cost = route_through_array(
                cost_surface,
                start,
                end,
                fully_connected=True
            )

            coords = []

            for r, c in path:

                x, y = rasterio.transform.xy(transform, r, c)

                coords.append((x, y))

            routes.append(LineString(coords))

        except:

            continue

    routes_gdf = gpd.GeoDataFrame(geometry=routes, crs=crs)

    output = os.path.join(base_folder, "drainage_routes.gpkg")

    routes_gdf.to_file(output, driver="GPKG")

    print("Saved:", output)


# --------------------------------------------
# Run for all datasets
# --------------------------------------------
def process_all():

    base = "data/hydrology"

    for folder in os.listdir(base):

        dataset = os.path.join(base, folder)

        hotspots = os.path.join(dataset, "waterlogging_hotspots.gpkg")

        if os.path.exists(hotspots):

            route_drainage(dataset)

        else:

            print("Skipping:", folder)


if __name__ == "__main__":

    process_all()