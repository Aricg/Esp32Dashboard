import csv
import json
import os
from collections import defaultdict
from datetime import datetime

import plotly
import plotly.graph_objs as go
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# Directory to store sensor data files
DATA_DIR = "sensor_data"

# Maximum number of points to store per sensor (in-memory)
MAX_POINTS = 10000

# In-memory storage for sensor data
sensor_data = defaultdict(list)

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)


@app.route("/", methods=["GET"])
def index():
    # Generate graphs for all sensors
    graphs = []
    for sensor_name, values in sensor_data.items():
        if values:
            timestamps = [datetime.fromisoformat(v[0]) for v in values]
            values_data = [v[1] for v in values]
            graph = go.Scatter(
                x=timestamps, y=values_data, mode="lines+markers", name=sensor_name
            )
            layout = go.Layout(
                title=f"Sensor: {sensor_name} - Last {len(values)} Points",
                xaxis=dict(title="Time", color="white"),
                yaxis=dict(title="Value", color="white"),
                paper_bgcolor="#1e1e1e",  # Background color of the graph
                plot_bgcolor="#1e1e1e",  # Background color of the plotting area
                font=dict(color="white"),  # Text color
                margin=dict(l=50, r=50, t=80, b=50),
            )
            graphs.append(dict(data=[graph], layout=layout))

    # Convert graphs to JSON for rendering in the template
    graph_json = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template("index.html", graph_json=graph_json)


@app.route("/data", methods=["POST"])
def receive_data():
    try:
        data = request.json
        sensor_name = data.get("sensor_name")
        sensor_value = data.get("sensor_value")

        if not all([sensor_name, sensor_value]):
            return jsonify({"error": "Missing fields"}), 400

        # Add timestamp to the data
        timestamp = datetime.now().isoformat()
        sensor_data[sensor_name].append((timestamp, float(sensor_value)))

        # Trim the list to keep only the last MAX_POINTS values
        if len(sensor_data[sensor_name]) > MAX_POINTS:
            sensor_data[sensor_name] = sensor_data[sensor_name][-MAX_POINTS:]

        # Save data to a daily log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = os.path.join(DATA_DIR, f"{sensor_name}_{today}.csv")
        with open(log_file, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([timestamp, sensor_value])

        return jsonify({"status": "success"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
