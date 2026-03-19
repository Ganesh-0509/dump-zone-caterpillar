#!/usr/bin/env python
"""Test what the API returns for truck data."""

from app import initialize_simulation, simulation_state
import json

# Initialize
initialize_simulation()
engine = simulation_state['engine']

# Run simulation a few steps
for i in range(15):
    engine.step()

# Get the state that would be returned by the API
from app import get_state
response = get_state()
data = json.loads(response.get_json(force=True))

print("API Response (first 50 lines):")
print(json.dumps(data, indent=2)[:2000])
