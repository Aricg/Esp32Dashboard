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
    dates = set()
    
    # Get the selected sensor and date from query parameters
    selected_sensor = request.args.get('sensor')
    selected_date = request.args.get('date')
    
    # Get all available sensors from file names
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.csv'):
            # Extract sensor name from filename (format: sensor_name_YYYY-MM-DD.csv)
            match = re.match(r'(.+)_(\d{4}-\d{2}-\d{2})\.csv', filename)
            if match:
                sensor_name, date = match.groups()
                sensors.add(sensor_name)
                if selected_sensor and sensor_name == selected_sensor:
                    dates.add(date)
    
    # Convert sets to sorted lists
    sensors = sorted(list(sensors))
    dates = sorted(list(dates), reverse=True)
    
    # If no sensor is selected but we have sensors, select the first one
    if not selected_sensor and sensors:
        selected_sensor = sensors[0]
        
    # Get dates for the selected sensor
    if selected_sensor:
        dates = set()
        for filename in os.listdir(DATA_DIR):
            match = re.match(r'(.+)_(\d{4}-\d{2}-\d{2})\.csv', filename)
            if match and match.group(1) == selected_sensor:
                dates.add(match.group(2))
        dates = sorted(list(dates), reverse=True)
    
    # If no date is selected but we have dates, select the first one
    if not selected_date and dates:
        selected_date = dates[0]
    
    # Generate graph if both sensor and date are selected
    graph_json = None
    if selected_sensor and selected_date:
        file_path = os.path.join(DATA_DIR, f"{selected_sensor}_{selected_date}.csv")
        if os.path.exists(file_path):
            timestamps = []
            values = []
            
            with open(file_path, 'r') as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) >= 2:
                        try:
                            # Parse timestamp and value
                            timestamp = datetime.fromisoformat(row[0])
                            value = float(row[1])
                            timestamps.append(timestamp)
                            values.append(value)
                        except (ValueError, IndexError):
                            continue
            
            if timestamps and values:
                graph = go.Scatter(
                    x=timestamps, 
                    y=values, 
                    mode="lines+markers", 
                    name=selected_sensor
                )
                layout = go.Layout(
                    title=f"{selected_sensor} - {selected_date}",
                    xaxis=dict(title="Time", color="white"),
                    yaxis=dict(title="Value", color="white"),
                    paper_bgcolor="#1e1e1e",
                    plot_bgcolor="#1e1e1e",
                    font=dict(color="white"),
                    margin=dict(l=50, r=50, t=80, b=50),
                )
                graph_data = dict(data=[graph], layout=layout)
                graph_json = json.dumps(graph_data, cls=plotly.utils.PlotlyJSONEncoder)
    
    # Ensure selected_sensor and selected_date are always defined
    selected_sensor = selected_sensor if selected_sensor else ""
    selected_date = selected_date if selected_date else ""
    
    return render_template(
        "historical.html", 
        sensors=sensors, 
        dates=dates, 
        graph_json=graph_json,
        selected_sensor=selected_sensor,
        selected_date=selected_date
    )

@app.route("/dates", methods=["GET"])
def get_dates():
    """API endpoint to get available dates for a specific sensor"""
    sensor = request.args.get('sensor')
    dates = []
    
    if sensor:
        for filename in os.listdir(DATA_DIR):
            match = re.match(r'(.+)_(\d{4}-\d{2}-\d{2})\.csv', filename)
            if match and match.group(1) == sensor:
                dates.append(match.group(2))
    
    return jsonify({"dates": sorted(dates, reverse=True)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
