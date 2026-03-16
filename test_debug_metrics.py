#!/usr/bin/env python
"""Debug test to check truck state transitions and packing metrics."""

from pathlib import Path
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon, CELL_DUMP_PILE, CELL_EMPTY
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig

def test_debug():
    """Run a small simulation with debug output."""
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
    
    sim_config = SimulationConfig(max_steps=50, generator_config=generator_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)
    
    print("Starting debug simulation...")
    for step in range(50):
        engine.step()
        
        # Count states
        moving_count = sum(1 for t in engine.trucks if hasattr(t, 'state') and str(t.state) == 'TruckState.MOVING_TO_ZONE')
        dumping_count = sum(1 for t in engine.trucks if hasattr(t, 'state') and str(t.state) == 'TruckState.DUMPING')
        returning_count = sum(1 for t in engine.trucks if hasattr(t, 'state') and str(t.state) == 'TruckState.RETURNING')
        
        # Count grid cells
        dump_cells = (engine.occupancy_grid == CELL_DUMP_PILE).sum()
        empty_cells = (engine.occupancy_grid == CELL_EMPTY).sum()
        
        if step % 5 == 0 or step == 49:
            print(f"\nStep {step}:")
            print(f"  Total trucks: {len(engine.trucks)}")
            print(f"  Moving: {moving_count}, Dumping: {dumping_count}, Returning: {returning_count}")
            print(f"  Grid - Dump cells: {dump_cells}, Empty cells: {empty_cells}")
    
    print("\nFinal Metrics:")
    summary = engine.analytics.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Final counts
    dump_cells = (engine.occupancy_grid == CELL_DUMP_PILE).sum()
    total_valid_cells = (engine.occupancy_grid >= 0).sum()
    print(f"\nFinal Grid Analysis:")
    print(f"  Dump cells: {dump_cells}")
    print(f"  Total valid cells: {total_valid_cells}")
    print(f"  Calculated packing density: {dump_cells / max(total_valid_cells, 1):.3f}")

if __name__ == "__main__":
    test_debug()
