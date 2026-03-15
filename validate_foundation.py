"""Validate the simulation foundation: polygon, zones, grid, and terrain."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from shapely.geometry import Point

from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon, CELL_EMPTY, CELL_INVALID
from mapping.terrain_map import initialize_height_map, add_dump, get_height


def validate_polygon_rendering() -> bool:
    """Verify polygon loading and basic properties."""
    print("\n=== POLYGON RENDERING ===")
    
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    
    # Check polygon validity
    assert dump_polygon.is_valid, "Polygon is invalid"
    assert dump_polygon.area > 0, "Polygon has zero area"
    assert len(dump_polygon.exterior.coords) >= 4, "Polygon has fewer than 3 unique vertices"
    
    min_x, min_y, max_x, max_y = dump_polygon.bounds
    print(f"✓ Polygon loaded successfully")
    print(f"  - Area: {dump_polygon.area:.2f} m²")
    print(f"  - Bounds: ({min_x:.1f}, {min_y:.1f}) to ({max_x:.1f}, {max_y:.1f})")
    print(f"  - Vertices: {len(dump_polygon.exterior.coords) - 1}")
    
    # Test point containment
    test_point = Point((60, 40))
    is_inside = dump_polygon.contains(test_point)
    print(f"  - Point (60, 40) inside polygon: {is_inside}")
    
    return True


def validate_zone_partitioning() -> bool:
    """Verify zone generation and coverage."""
    print("\n=== ZONE PARTITIONING ===")
    
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    config = ZoneGenerationConfig(zone_count=8, random_seed=7)
    zones = generate_voronoi_zones(dump_polygon, config)
    
    assert len(zones) > 0, "No zones generated"
    assert len(zones) <= config.zone_count, "Generated more zones than requested"
    
    print(f"✓ Zone partitioning successful")
    print(f"  - Target zones: {config.zone_count}")
    print(f"  - Generated zones: {len(zones)}")
    
    # Check zone properties
    total_zone_area = 0.0
    for idx, zone in enumerate(zones):
        assert zone.is_valid, f"Zone {idx} is invalid"
        assert zone.area > 0, f"Zone {idx} has zero area"
        total_zone_area += zone.area
        print(f"  - Zone {idx + 1}: area={zone.area:.2f}, valid={zone.is_valid}")
    
    polygon_area = dump_polygon.area
    coverage_percent = (total_zone_area / polygon_area) * 100
    print(f"  - Total zone area: {total_zone_area:.2f} m²")
    print(f"  - Polygon area: {polygon_area:.2f} m²")
    print(f"  - Coverage: {coverage_percent:.1f}%")
    
    assert coverage_percent > 95, f"Zone coverage too low: {coverage_percent:.1f}%"
    
    return True


def validate_grid_alignment() -> bool:
    """Verify grid creation and cell alignment."""
    print("\n=== GRID ALIGNMENT ===")
    
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)
    
    assert grid.shape[0] == metadata.grid_height, "Height mismatch"
    assert grid.shape[1] == metadata.grid_width, "Width mismatch"
    
    print(f"✓ Grid alignment correct")
    print(f"  - Grid shape: {metadata.grid_height} (height) × {metadata.grid_width} (width)")
    print(f"  - Cell size: {metadata.cell_size} m")
    print(f"  - Origin: ({metadata.origin_x:.1f}, {metadata.origin_y:.1f})")
    
    # Check cell states
    empty_count = np.sum(grid == CELL_EMPTY)
    invalid_count = np.sum(grid == CELL_INVALID)
    total_cells = grid.shape[0] * grid.shape[1]
    
    print(f"  - Empty cells (valid): {empty_count}")
    print(f"  - Invalid cells (outside): {invalid_count}")
    print(f"  - Total cells: {total_cells}")
    
    valid_percent = (empty_count / total_cells) * 100
    print(f"  - Valid cell coverage: {valid_percent:.1f}%")
    
    assert empty_count > 0, "No valid cells created"
    assert invalid_count > 0, "No invalid cells created (boundary may be missing)"
    
    # Test coordinate transformations
    from mapping.occupancy_grid import grid_to_world, world_to_grid
    
    test_grid_x, test_grid_y = 10, 15
    world_x, world_y = grid_to_world(test_grid_x, test_grid_y, metadata.origin_x, metadata.origin_y, metadata.cell_size)
    back_grid_x, back_grid_y = world_to_grid(world_x, world_y, metadata.origin_x, metadata.origin_y, metadata.cell_size)
    
    assert back_grid_x == test_grid_x, "X coordinate transform mismatch"
    assert back_grid_y == test_grid_y, "Y coordinate transform mismatch"
    
    print(f"  - Coordinate transform test: ({test_grid_x}, {test_grid_y}) → ({world_x:.2f}, {world_y:.2f}) → ({back_grid_x}, {back_grid_y}) ✓")
    
    return True


def validate_terrain_height_updates() -> bool:
    """Verify terrain height map updates."""
    print("\n=== TERRAIN HEIGHT UPDATES ===")
    
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)
    height_map = initialize_height_map(grid.shape)
    
    # All cells should start at zero
    initial_max = np.max(height_map)
    assert initial_max == 0.0, "Initial height map not zeroed"
    print(f"✓ Height map initialized at zero")
    
    # Find a valid cell to test
    valid_cells = np.argwhere(grid == CELL_EMPTY)
    assert len(valid_cells) > 0, "No valid cells to update"
    
    test_cell = valid_cells[0]
    test_y, test_x = test_cell[0], test_cell[1]
    
    # Add material
    dump_height_1 = 5.0
    add_dump(height_map, test_x, test_y, dump_height_1, metadata)
    height_1 = get_height(height_map, test_x, test_y, metadata)
    
    assert height_1 == dump_height_1, f"Height mismatch: expected {dump_height_1}, got {height_1}"
    print(f"✓ First dump successful")
    print(f"  - Cell ({test_x}, {test_y}) height: {height_1:.2f} m")
    
    # Add more material (accumulate)
    dump_height_2 = 3.5
    add_dump(height_map, test_x, test_y, dump_height_2, metadata)
    height_2 = get_height(height_map, test_x, test_y, metadata)
    
    expected_height = dump_height_1 + dump_height_2
    assert height_2 == expected_height, f"Height accumulation failed: expected {expected_height}, got {height_2}"
    print(f"✓ Accumulation successful")
    print(f"  - Added {dump_height_2:.2f} m")
    print(f"  - Cell ({test_x}, {test_y}) height: {height_2:.2f} m")
    
    # Check that other cells remain at zero
    other_cells = np.argwhere((grid == CELL_EMPTY) & ((np.arange(grid.shape[0])[:, None] != test_y) | (np.arange(grid.shape[1]) != test_x)))
    if len(other_cells) > 0:
        sample_cell = other_cells[0]
        sample_y, sample_x = sample_cell[0], sample_cell[1]
        sample_height = get_height(height_map, sample_x, sample_y, metadata)
        assert sample_height == 0.0, f"Unrelated cell height changed: {sample_height}"
    print(f"✓ Other cells unchanged")
    
    # Test statistics
    occupied_cells = np.sum(height_map > 0)
    max_height = np.max(height_map)
    print(f"  - Occupied cells: {occupied_cells}")
    print(f"  - Maximum height: {max_height:.2f} m")
    
    return True


def main() -> None:
    """Run all validation checks."""
    print("\n" + "="*60)
    print("SIMULATION FOUNDATION VALIDATION")
    print("="*60)
    
    try:
        validate_polygon_rendering()
        validate_zone_partitioning()
        validate_grid_alignment()
        validate_terrain_height_updates()
        
        print("\n" + "="*60)
        print("✓ ALL VALIDATIONS PASSED")
        print("="*60)
        print("\nSimulation foundation is correct and ready for Phase-3.")
        
    except AssertionError as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
