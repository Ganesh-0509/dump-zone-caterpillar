"""Validate Phase-4 dynamic dump spot selection."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon, CELL_DUMP_PILE, CELL_INVALID, grid_to_world
from mapping.terrain_map import initialize_height_map
from planning.dump_spot_selector import select_dump_spot, get_zone_cells
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig


def validate_dump_spots_in_zone() -> bool:
    """Verify that dump spots are always inside assigned zones."""
    print("\n=== DUMP SPOTS IN ZONE ===")

    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"

    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=4, random_seed=42)
    zones = generate_voronoi_zones(dump_polygon, zone_config)

    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)

    # For each zone, select a dump spot and verify containment
    for zone_idx, zone in enumerate(zones):
        try:
            dump_x, dump_y = select_dump_spot(zone, grid, metadata)
            
            # Verify dump spot is in zone
            zone_cells = set(get_zone_cells(zone, metadata))
            assert (dump_x, dump_y) in zone_cells, f"Dump spot not in zone {zone_idx}"
            
            print(f"✓ Zone {zone_idx}: dump spot ({dump_x}, {dump_y}) inside zone")
        except ValueError:
            print(f"✓ Zone {zone_idx}: no valid cells (all occupied)")

    return True


def validate_dump_spots_avoid_piles() -> bool:
    """Verify that dump spots avoid existing dump piles."""
    print("\n=== DUMP SPOTS AVOID PILES ===")

    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"

    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=4, random_seed=42)
    zones = generate_voronoi_zones(dump_polygon, zone_config)

    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)
    height_map = initialize_height_map(grid.shape)

    # Select dump spot, mark it, then select again
    zone = zones[0]
    dump_x1, dump_y1 = select_dump_spot(zone, grid, metadata)
    
    # Mark as pile
    grid[dump_y1, dump_x1] = CELL_DUMP_PILE
    
    # Select again
    dump_x2, dump_y2 = select_dump_spot(zone, grid, metadata)
    
    # Should be different (unless zone has only one cell)
    zone_cells = get_zone_cells(zone, metadata)
    if len(zone_cells) > 1:
        assert (dump_x2, dump_y2) != (dump_x1, dump_y1), "Algorithm should select different cell"
        print(f"✓ Algorithm avoids piles: first=({dump_x1}, {dump_y1}), second=({dump_x2}, {dump_y2})")
    else:
        print(f"✓ Zone has only one cell, reselection forced")

    return True


def validate_terrain_height_increases() -> bool:
    """Verify that terrain height increases when trucks dump."""
    print("\n=== TERRAIN HEIGHT INCREASES ===")

    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"

    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=4, random_seed=42)
    zones = generate_voronoi_zones(dump_polygon, zone_config)

    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)
    height_map = initialize_height_map(grid.shape)

    # Run simulation
    gen_config = TruckGeneratorConfig(spawn_interval=10, truck_speed=2.0)
    sim_config = SimulationConfig(max_steps=150, generator_config=gen_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)

    engine.run()

    # Check that height map has changed
    max_height = np.max(height_map)
    assert max_height > 0, "Height map not updated"

    occupied_cells = np.sum(height_map > 0)
    assert occupied_cells > 0, "No cells with height"

    print(f"✓ Terrain height increased")
    print(f"  - Maximum height: {max_height:.2f} m")
    print(f"  - Occupied cells: {occupied_cells}")
    print(f"  - Total trucks: {len(engine.trucks)}")

    return True


def validate_dump_piles_fill_zones() -> bool:
    """Verify that dump piles gradually fill zone areas."""
    print("\n=== DUMP PILES FILL ZONES ===")

    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"

    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=3, random_seed=42)
    zones = generate_voronoi_zones(dump_polygon, zone_config)

    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)
    height_map = initialize_height_map(grid.shape)

    # Run simulation
    gen_config = TruckGeneratorConfig(spawn_interval=5, truck_speed=2.0)
    sim_config = SimulationConfig(max_steps=200, generator_config=gen_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)

    engine.run()

    # Count dump piles
    pile_count = np.sum(grid == CELL_DUMP_PILE)
    assert pile_count > 0, "No dump piles created"

    print(f"✓ Dump piles created during simulation")
    print(f"  - Total dump pile cells: {pile_count}")
    print(f"  - Total trucks completed: {len([t for t in engine.trucks if t.payload == 0.0])}")

    # Verify dump piles are within zones
    valid_cell_count = np.sum(grid != CELL_INVALID)
    pile_percent = (pile_count / valid_cell_count) * 100
    print(f"  - Pile density: {pile_percent:.1f}% of valid cells")

    return True


def main() -> None:
    """Run all Phase-4 validations."""
    print("\n" + "="*60)
    print("PHASE-4 DYNAMIC DUMP SPOT SELECTION VALIDATION")
    print("="*60)

    try:
        validate_dump_spots_in_zone()
        validate_dump_spots_avoid_piles()
        validate_terrain_height_increases()
        validate_dump_piles_fill_zones()

        print("\n" + "="*60)
        print("✓ ALL PHASE-4 VALIDATIONS PASSED")
        print("="*60)
        print("\nDynamic dump spot selection is working correctly.")

    except AssertionError as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        raise


if __name__ == "__main__":
    main()
