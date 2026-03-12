import os
import laspy
import numpy as np
import joblib

input_folder = "data/raw"
output_folder = "data/classified"

os.makedirs(output_folder, exist_ok=True)

print("Loading model...")
model = joblib.load("models/xgb_model.pkl")

CHUNK_SIZE = 5000000

for file in os.listdir(input_folder):

    if file.endswith(".las") or file.endswith(".laz"):

        input_path = os.path.join(input_folder, file)
        output_path = os.path.join(output_folder, file)

        print("Processing:", file)

        with laspy.open(input_path) as reader:

            header = reader.header

            with laspy.open(output_path, mode="w", header=header) as writer:

                for points in reader.chunk_iterator(CHUNK_SIZE):

                    z = points.z
                    z_norm = z - np.mean(z)

                    X = np.vstack((
                        z,
                        z_norm,
                        points.intensity,
                        points.return_number,
                        points.number_of_returns
                    )).T

                    preds = model.predict(X)

                    cls = np.where(preds == 1, 2, 1).astype(np.uint8)

                    points.classification = cls

                    writer.write_points(points)

        print("Saved:", output_path)

print("All files processed.")