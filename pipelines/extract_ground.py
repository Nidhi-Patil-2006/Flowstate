import os
import laspy
import numpy as np

input_folder = "data/classified"
output_folder = "data/ground"

os.makedirs(output_folder, exist_ok=True)

GROUND_CLASSES = [1, 2, 11]

CHUNK_SIZE = 5000000

print("Extracting ground points...")

for file in os.listdir(input_folder):

    if file.endswith(".las") or file.endswith(".laz"):

        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, file)

        print("Processing:", file)

        with laspy.open(input_path) as reader:

            header = reader.header.copy()

            with laspy.open(output_path, mode="w", header=header) as writer:

                total_ground = 0

                for points in reader.chunk_iterator(CHUNK_SIZE):

                    cls = np.array(points.classification).astype(np.uint8)

                    mask = np.isin(cls, GROUND_CLASSES)

                    if np.any(mask):

                        ground_points = points[mask]

                        total_ground += len(ground_points)

                        writer.write_points(ground_points)

        print("Ground points found:", total_ground)
        print("Saved ground file:", output_path)

print("Ground extraction complete.")