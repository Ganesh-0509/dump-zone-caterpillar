#!/usr/bin/env python
"""Test to check which dump locations are being selected."""

from pathlib import Path
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon, CELL_DUMP_PILE, CELL_EMPTY
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig

def test_dump_locations():
    """Track dump locations selected for each truck."""
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=3, random_seed=42)
    generator_config = TruckGeneratorConfig(
        spawn_interval=2,
        truck_speed=0.5,
        entrance_x=dump_polygon.bounds[0],
        entrance_y=dump_polygon.bounds[1],
        initial_payload=1.0,
    )
    
    zones = generate_voronoi_zones(dump_polygon, zone_config)
    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=0.5)
    height_map = initialize_height_map(grid.shape)
    
    sim_config = SimulationConfig(max_steps=30, generator_config=generator_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)
    
    dump_locations = {}
    
    for step in range(30):
        engine.step()
        
        # Check newly returned/completed trucks
        for truck in engine.trucks:
            truck_id = truck.truck_id
            if truck_id not in dump_locations and truck.dump_grid_x >= 0 and truck.dump_grid_y >= 0:
                dump_locations[truck_id] = (truck.dump_grid_x, truck.dump_grid_y)
    
    print("Dump locations assigned:")
    unique_locations = set()
    for truck_id, (x, y) in sorted(dump_locations.items()):
        print(f"  Truck {truck_id}: ({x}, {y})")
        unique_locations.add((x, y))
    
    print(f"\nTotal unique dump locations: {len(unique_locations)}")
    print(f"Total trucks: {len(dump_locations)}")
    
    # Check actual grid content
    dump_cells = (engine.occupancy_grid == CELL_DUMP_PILE).sum()
    print(f"\nGrid analysis:")
    print(f"  Total DUMP_PILE cells: {dump_cells}")
    print(f"  Expected unique locations: {len(unique_locations)}")
    
    # Show locations with DUMP_PILE
    import numpy as np
    locations_with_pile = np.argwhere(engine.occupancy_grid == CELL_DUMP_PILE)
    print(f"\nActual locations with DUMP_PILE in grid:")
    for y, x in locations_with_pile:
        print(f"  ({x}, {y}): height={engine.height_map[y, x]:.1f}")

if __name__ == "__main__":
    test_dump_locations()
