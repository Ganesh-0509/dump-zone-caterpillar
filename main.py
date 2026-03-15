"""Phase-1, Phase-2, and Phase-3 entrypoint: geometric environment, mapping, and truck simulation."""

from __future__ import annotations

from pathlib import Path

from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig
from visualization.plot_environment import plot_dump_environment, plot_grid_environment, plot_simulation_state


def main() -> None:
    """Run the Phase-1, Phase-2, and Phase-3 simulation flow."""
    project_root = Path(__file__).resolve().parent
    polygon_path = project_root / "data" / "dump_polygon.json"

    # Phase 1: Geometry
    dump_polygon = load_dump_polygon(polygon_path)
    config = ZoneGenerationConfig(zone_count=8, random_seed=7)
    zones = generate_voronoi_zones(dump_polygon, config)

    print(f"Loaded dump polygon area: {dump_polygon.area:.2f}")
    print(f"Generated zones: {len(zones)}")

    # Phase 2: Mapping
    grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=1.0)
    height_map = initialize_height_map(grid.shape)

    print(f"Created occupancy grid: {metadata.grid_width}x{metadata.grid_height}")
    print(f"Initialized terrain height map shape: {height_map.shape}")

    # Phase 3: Truck Simulation
    generator_config = TruckGeneratorConfig(spawn_interval=10, truck_speed=0.5)
    sim_config = SimulationConfig(max_steps=250, generator_config=generator_config)
    engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)

    print(f"Starting simulation with max_steps={sim_config.max_steps}")

    # Run simulation with an animated visualization every 5 steps
    engine.run(visualize=True, viz_interval=5, dump_polygon=dump_polygon)

    print(f"\nSimulation complete!")
    stats = engine.get_statistics()
    print(f"Total trucks spawned: {stats['total_trucks']}")

    # Keep the final state visible
    import matplotlib.pyplot as plt
    plt.show()


if __name__ == "__main__":
    main()

