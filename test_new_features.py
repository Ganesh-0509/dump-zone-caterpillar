#!/usr/bin/env python
"""Quick test of the simulation engine with new features."""

from pathlib import Path
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine

def test_simulation():
    """Run a small simulation to test all new modules."""
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"
    
    dump_polygon = load_dump_polygon(polygon_path)
    
    zone_config = ZoneGenerationConfig(zone_count=3, random_seed=42)
    from simulation.truck_generator import TruckGeneratorConfig
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
    
    print("Starting test simulation...")
    for step in range(50):
        engine.step()
        if step % 10 == 0:
            print(f"Step {step}: {len(engine.trucks)} trucks active")
    
    print("\nSimulation complete!")
    summary = engine.analytics.get_summary()
    print(f"Packing Density: {summary['packing_density']:.3f}")
    print(f"Fleet Utilization: {summary['fleet_utilization']:.3f}")
    print(f"Average Pile Slope: {summary['average_pile_slope']:.3f}")
    print(f"Max Pile Height: {summary['max_pile_height']:.3f}")
    print(f"Layer Growth Events: {summary['layer_growth_events']}")
    print("\nAll new modules working successfully!")

if __name__ == "__main__":
    test_simulation()
