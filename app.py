from flask import Flask, render_template, request, jsonify, send_from_directory
import subprocess
import os

app = Flask(__name__)

UPLOAD_FOLDER = "data/raw"
OUTPUT_FOLDERS = ["data/dtm", "data/hydrology"]

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def run_script(script_name):
    try:
        result = subprocess.run(
            ["python", f"pipelines/{script_name}"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return f"Error in {script_name}:\n{result.stderr}"

        return result.stdout + result.stderr

    except Exception as e:
        return str(e)


@app.route("/")
def index():
    return render_template("index.html")


# ✅ Upload File
@app.route("/upload", methods=["POST"])
def upload_file():
    file = request.files.get("file")

    if not file or file.filename == "":
        return jsonify({"message": "No file selected"})

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    return jsonify({"message": f"Uploaded: {file.filename}"})


# ✅ Run Individual Step (for debugging/manual control)
@app.route("/run", methods=["POST"])
def run_pipeline():
    step = request.json.get("step")

    mapping = {
        # Phase 1
        "train": "train_model.py",
        "predict": "predict_model.py",
        "ground": "extract_ground.py",
        "dtm": "generate_dtm.py",
        "hydrology": "hydrology_analysis.py",
        "stream_vector": "stream_vectorization.py",
        "burn_streams": "burn_streams.py",

        # Trigger
        "hotspots": "waterlogging_hotspots.py",

        # Phase 2
        "drainage": "drainage_routing.py",
        "flood_risk": "flood_risk_map.py",
        "stream_order": "stream_order.py",
        "hillshade": "create_hillshade.py"
    }

    if step not in mapping:
        return jsonify({"output": "Invalid step"})

    output = run_script(mapping[step])
    return jsonify({"output": output})


# ✅ FULL PIPELINE (Phase 1)
@app.route("/run-full", methods=["POST"])
def run_full_pipeline():

    steps = [
        "train_model.py",
        "predict_model.py",
        "extract_ground.py",
        "generate_dtm.py",
        "hydrology_analysis.py",
        "stream_vectorization.py",
        "burn_streams.py"
    ]

    logs = []

    for step in steps:
        logs.append(f"\n===== Running {step} =====\n")
        logs.append(run_script(step))

    return jsonify({"output": "\n".join(logs)})


# ✅ WATERLOGGING PIPELINE (Phase 2)
@app.route("/run-waterlogging", methods=["POST"])
def run_waterlogging():

    steps = [
        "waterlogging_hotspots.py",
        "drainage_routing.py",
        "flood_risk_map.py",
        "stream_order.py",
        "create_hillshade.py"
    ]

    logs = []

    for step in steps:
        logs.append(f"\n===== Running {step} =====\n")
        logs.append(run_script(step))

    return jsonify({"output": "\n".join(logs)})


# ✅ List Output Files
@app.route("/files")
def list_files():
    files = []

    for folder in OUTPUT_FOLDERS:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                files.append(f"{folder}/{f}")

    return jsonify(files)


# ✅ Download File
@app.route("/download")
def download_file():
    filepath = request.args.get("path")

    if not filepath or not os.path.exists(filepath):
        return "File not found"

    folder, filename = os.path.split(filepath)
    return send_from_directory(folder, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)