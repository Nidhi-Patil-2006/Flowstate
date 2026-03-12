import os
import laspy
import numpy as np

# folder containing LAS/LAZ files
folder = "data/raw"   # change this path if needed

for file in os.listdir(folder):
    if file.endswith(".las") or file.endswith(".laz"):
        path = os.path.join(folder, file)
        print("\nProcessing:", file)

        las = laspy.read(path)
        classes = las.classification

        unique, counts = np.unique(classes, return_counts=True)

        for u, c in zip(unique, counts):
            print(f"Class {u}: {c} points")