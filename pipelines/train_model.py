import os
import laspy
import numpy as np
from xgboost import XGBClassifier
import joblib

# folders
training_folder = "data/training"
model_output = "models/xgb_model.pkl"

# ground classes across datasets
GROUND_CLASSES = [1, 2, 11]

# number of points to sample from each dataset
SAMPLE_SIZE = 500000


print("Loading training datasets...")

X_all = []
y_all = []

for file in os.listdir(training_folder):

    if file.endswith(".las") or file.endswith(".laz"):

        path = os.path.join(training_folder, file)

        print("Reading:", file)

        las = laspy.read(path)

        total_points = len(las.points)

        print("Total points:", total_points)

        # sample points to avoid RAM issues
        if total_points > SAMPLE_SIZE:

            rng = np.random.default_rng(42)
            idx = rng.choice(total_points, SAMPLE_SIZE, replace=False)

        else:

            idx = np.arange(total_points)

        # features
        z = las.z[idx]
        
        z_norm = z - np.mean(z)

        X = np.vstack((
            z,
            z_norm,
            las.intensity[idx],
            las.return_number[idx],
            las.number_of_returns[idx]
        )).T

        # labels
        cls = np.array(las.classification)[idx]

        y = np.isin(cls, GROUND_CLASSES).astype(np.uint8)

        print("Ground points:", np.sum(y == 1))
        print("Non-ground points:", np.sum(y == 0))

        X_all.append(X)
        y_all.append(y)


print("Combining datasets...")

X_train = np.vstack(X_all)
y_train = np.concatenate(y_all)

print("Total training samples:", len(y_train))

print("Training XGBoost model...")

pos = np.sum(y_train == 1)
neg = np.sum(y_train == 0)

scale = neg / pos

print("Scale pos weight:", scale)

model = XGBClassifier(
    n_estimators=300,
    max_depth=10,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=scale,
    n_jobs=-1
)

model.fit(X_train, y_train)

os.makedirs("models", exist_ok=True)

joblib.dump(model, model_output)

print("Model saved to:", model_output)