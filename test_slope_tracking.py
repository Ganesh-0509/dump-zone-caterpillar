#!/usr/bin/env python
"""Debug test to trace slope recording."""

from pathlib import Path
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon, CELL_DUMP_PILE, CELL_EMPTY
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig

def test_slope_tracking():
    """Track slope values recorded in simulation."""
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    zone_config = ZoneGenerationConfig(zone_count=3, random_seed=42)
    generator_config = TruckGeneratorConfig(
        spawn_interval=1,  # Every step
        truck_speed=0.5,
        entrance_x=dump_polygon.bounds[0],
        entrance_y=dump_polygon.bounds[1],
        initial_payload=1.0,
    )
    
    zones = generate_voronoi_zones(dump_polygon, zone_config)
    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=0.5)
    height_map = initialize_height_map(grid.shape)
    
    sim_config = SimulationConfig(max_steps=15, generator_config=generator_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)
    
    print("Tracing slope and layer growth event recording:")
    
    for step in range(15):
        engine.step()
        
        # Check for dumping trucks and what slopes they recorded
        summary = engine.analytics.get_summary()
        if step % 2 == 0:
            print(f"\nStep {step}:")
            print(f"  Layer Growth Events: {summary['layer_growth_events']}")
            print(f"  Average Pile Slope: {summary['average_pile_slope']}")
            print(f"  Max Pile Height: {summary['max_pile_height']}")
            
            # Show height_map state
            height_cells = (height_map > 0).sum()
            max_h = height_map.max()
            print(f"  Height map - Cells with data: {height_cells}, Max height: {max_h:.1f}")

if __name__ == "__main__":
    test_slope_tracking()
