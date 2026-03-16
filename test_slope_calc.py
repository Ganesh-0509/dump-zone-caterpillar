#!/usr/bin/env python
"""Test slope calculation."""

import numpy as np
from planning.slope_validator import SlopeValidator
from mapping.occupancy_grid import GridMetadata

# Create test height map with some variation
height_map = np.zeros((10, 10), dtype=np.float32)
height_map[5, 5] = 2.0
height_map[5, 6] = 1.5
height_map[4, 5] = 1.0

# Create validator
validator = SlopeValidator(max_slope=0.6)
metadata = GridMetadata(
    polygon_bounds=(0, 0, 10, 10),
    cell_size=1.0,
    grid_width=10,
    grid_height=10,
    origin_x=0,
    origin_y=0,
)

print("Height map around cell (5,5):")
print(height_map[3:8, 3:8])

# Test slope at center
slope = validator.compute_slope(height_map, 5, 5, metadata.cell_size)
print(f"\nSlope at (5, 5): {slope}")

slope2 = validator.compute_slope(height_map, 5, 6, metadata.cell_size)
print(f"Slope at (5, 6): {slope2}")

slope3 = validator.compute_slope(height_map, 4, 5, metadata.cell_size)
print(f"Slope at (4, 5): {slope3}")

# Test scoring
score = validator.score_dump_spot(5, 5, height_map, np.ones_like(height_map, dtype=bool), (5, 5), 5.0, 5.0, 1.0)
print(f"\nScore at (5, 5): {score}")

score2 = validator.score_dump_spot(5, 6, height_map, np.ones_like(height_map, dtype=bool), (5, 5), 5.0, 5.0, 1.0)
print(f"Score at (5, 6): {score2}")

print("\n--- Testing empty cell ---")
slope_empty = validator.compute_slope(height_map, 0, 0, metadata.cell_size)
print(f"Slope at empty cell (0, 0): {slope_empty}")
