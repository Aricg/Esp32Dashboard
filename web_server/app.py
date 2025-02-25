from flask import Flask, request, jsonify, render_template
from collections import defaultdict
import plotly
import plotly.graph_objs as go
import json

app = Flask(__name__)

# In-memory storage for sensor data
sensor_data = defaultdict(list)

@app.route('/', methods=['GET'])
def index():
    # Generate graphs for all sensors
    graphs = []
    for sensor_name, values in sensor_data.items():
        graph = go.Scatter(x=list(range(len(values))), y=values, mode='lines+markers', name=sensor_name)
        layout = go.Layout(title=f'Sensor: {sensor_name}', xaxis=dict(title='Time'), yaxis=dict(title='Value'))
        graphs.append(dict(data=[graph], layout=layout))
    
    # Convert graphs to JSON for rendering in the template
    graph_json = json.dumps(graphs, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('index.html', graph_json=graph_json)

@app.route('/data', methods=['POST'])
def receive_data():
    try:
        data = request.json
        service_name = data.get('service_name')
        sensor_name = data.get('sensor_name')
        sensor_value = data.get('sensor_value')

        if not all([service_name, sensor_name, sensor_value]):
            return jsonify({'error': 'Missing fields'}), 400

        # Store the sensor value
        sensor_data[sensor_name].append(float(sensor_value))
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
