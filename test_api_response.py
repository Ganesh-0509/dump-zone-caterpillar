#!/usr/bin/env python
"""Simulate what the API returns."""

from app import initialize_simulation, simulation_state, get_state
import json

initialize_simulation()

# Simulate a few steps
for _ in range(3):
    simulation_state['engine'].step()

# Get the state response
from flask import Flask
app = Flask(__name__)

with app.app_context():
    response = get_state()
    data = response.get_json()

print("API Response State (first truck):")
if data['trucks']:
    truck = data['trucks'][0]
    print(json.dumps(truck, indent=2))
    
print("\nMetadata would return:")
polygon = simulation_state['polygon']
meta = simulation_state['metadata']
metadata = {
    'status': 'success',
    'bounds': {
        'min_x': float(polygon.bounds[0]),
        'min_y': float(polygon.bounds[1]),
        'max_x': float(polygon.bounds[2]),
        'max_y': float(polygon.bounds[3]),
    },
    'zones': len(simulation_state['zones']),
}
print(json.dumps(metadata, indent=2))
