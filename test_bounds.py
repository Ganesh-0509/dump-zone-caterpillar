#!/usr/bin/env python
"""Check polygon and metadata bounds."""

from app import initialize_simulation, simulation_state

initialize_simulation()
engine = simulation_state['engine']

polygon = simulation_state['polygon']
metadata = simulation_state['metadata']

print("Backend Polygon Bounds:")
print(f"  min_x: {polygon.bounds[0]}")
print(f"  min_y: {polygon.bounds[1]}")
print(f"  max_x: {polygon.bounds[2]}")
print(f"  max_y: {polygon.bounds[3]}")
print(f"  width: {polygon.bounds[2] - polygon.bounds[0]}")
print(f"  height: {polygon.bounds[3] - polygon.bounds[1]}")

print("\nGrid Metadata:")
print(f"  grid_width: {metadata.grid_width}")
print(f"  grid_height: {metadata.grid_height}")
print(f"  origin_x: {metadata.origin_x}")
print(f"  origin_y: {metadata.origin_y}")
print(f"  cell_size: {metadata.cell_size}")

print("\nTruck entrance:")
print(f"  ({engine.config.generator_config.entrance_x}, {engine.config.generator_config.entrance_y})")
