#!/usr/bin/env python
"""Test slope tracking with forced adjacent dumps."""

from pathlib import Path
import numpy as np
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon
from mapping.terrain_map import initialize_height_map, add_dump
from planning.slope_validator import SlopeValidator
from mapping.occupancy_grid import GridMetadata

def test_forced_adjacent_dumps():
    """Create adjacent dumps and measure slope."""
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=0.5)
    height_map = initialize_height_map(grid.shape)
    
    validator = SlopeValidator(max_slope=0.6)
    
    # Add first dump
    add_dump(height_map, 10, 10, 1.0, metadata)
    print(f"After first dump at (10, 10):")
    slope1 = validator.compute_slope(height_map, 10, 10, metadata.cell_size)
    print(f"  Slope at (10, 10): {slope1}")
    
    # Add adjacent dump  
    add_dump(height_map, 11, 10, 1.0, metadata)
    print(f"\nAfter second dump at (11, 10) [adjacent]:")
    slope1_after = validator.compute_slope(height_map, 10, 10, metadata.cell_size)
    slope2 = validator.compute_slope(height_map, 11, 10, metadata.cell_size)
    print(f"  Slope at (10, 10): {slope1_after}")
    print(f"  Slope at (11, 10): {slope2}")
    
    # Add third dump at different height
    add_dump(height_map, 12, 10, 2.0, metadata)  # This one gets 2.0m
    print(f"\nAfter third dump at (12, 10) [adjacent, height 2.0]:")
    slope2_after = validator.compute_slope(height_map, 11, 10, metadata.cell_size)
    slope3 = validator.compute_slope(height_map, 12, 10, metadata.cell_size)
    print(f"  Slope at (11, 10): {slope2_after}")
    print(f"  Slope at (12, 10): {slope3}")
    
    # Show height_map
    print(f"\nHeight map section:")
    print(height_map[8:13, 8:13])

if __name__ == "__main__":
    test_forced_adjacent_dumps()
