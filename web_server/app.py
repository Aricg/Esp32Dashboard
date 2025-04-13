import csv
import json
import os
import re
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
    # Redirect to historical data page
    return historical_data()


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


@app.route("/historical-data", methods=["GET"])
@app.route("/dashboard", methods=["GET"])  # Add an alternative route
def historical_data():
    # Get list of all sensors from the data directory
    sensors = set()
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.csv'):
            match = re.match(r'(.+)_(\d{4}-\d{2}-\d{2})\.csv', filename)
            if match:
                sensors.add(match.group(1))
    sensors = sorted(list(sensors))

    # Get the selected sensor and date range from query parameters
    selected_sensor = request.args.get('sensor')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Default to the first sensor if none is selected
    if not selected_sensor and sensors:
        selected_sensor = sensors[0]

    # Default dates if not provided (e.g., today)
    today_str = datetime.now().strftime("%Y-%m-%d")
    if not start_date_str:
        start_date_str = today_str
    if not end_date_str:
        end_date_str = today_str
        
    # Validate date strings
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        # Handle invalid date format, maybe render an error or default
        start_date = datetime.now().date()
        end_date = datetime.now().date()
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        # Optionally add a flash message or error indicator here

    # Ensure start_date is not after end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
        start_date_str, end_date_str = end_date_str, start_date_str

    # Generate graph if a sensor is selected
    graph_json = None
    if selected_sensor:
        all_timestamps = []
        all_values = []
        
        # Iterate through files and collect data within the date range
        for filename in os.listdir(DATA_DIR):
            match = re.match(rf'{re.escape(selected_sensor)}_(\d{{4}}-\d{{2}}-\d{{2}})\.csv', filename)
            if match:
                file_date_str = match.group(1)
                try:
                    file_date = datetime.strptime(file_date_str, "%Y-%m-%d").date()
                    if start_date <= file_date <= end_date:
                        file_path = os.path.join(DATA_DIR, filename)
                        with open(file_path, 'r') as file:
                            reader = csv.reader(file)
                            for row in reader:
                                if len(row) >= 2:
                                    try:
                                        timestamp = datetime.fromisoformat(row[0])
                                        value = float(row[1])
                                        all_timestamps.append(timestamp)
                                        all_values.append(value)
                                    except (ValueError, IndexError):
                                        continue # Skip malformed rows
                except ValueError:
                    continue # Skip files with invalid date format in name

        # Sort data by timestamp if data was found
        if all_timestamps:
            sorted_data = sorted(zip(all_timestamps, all_values))
            all_timestamps, all_values = zip(*sorted_data)

            graph = go.Scatter(
                x=list(all_timestamps), 
                y=list(all_values), 
                mode="lines+markers", 
                name=selected_sensor
            )
            layout = go.Layout(
                title=f"{selected_sensor} ({start_date_str} to {end_date_str})",
                xaxis=dict(title="Time", color="white"),
                yaxis=dict(title="Value", color="white"),
                paper_bgcolor="#1e1e1e",
                plot_bgcolor="#1e1e1e",
                font=dict(color="white"),
                margin=dict(l=50, r=50, t=80, b=50),
            )
            graph_data = dict(data=[graph], layout=layout)
            graph_json = json.dumps(graph_data, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        "historical.html", 
        sensors=sensors, 
        graph_json=graph_json,
        selected_sensor=selected_sensor if selected_sensor else "",
        start_date=start_date_str,
        end_date=end_date_str
    )

# Removed the get_dates function and its route

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
