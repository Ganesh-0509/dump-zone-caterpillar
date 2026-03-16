"""Phase-1, Phase-2, and Phase-3 entrypoint: geometric environment, mapping, and truck simulation."""

from __future__ import annotations

import argparse
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
    parser = argparse.ArgumentParser(description="Autonomous Dump Zone Simulator")
    parser.add_argument("--mode", choices=["batch", "animation"], default="batch", help="Run mode: batch or animation")
    parser.add_argument("--no-visualize", action="store_true", help="Disable visualization in batch mode")
    args = parser.parse_args()

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

    print(f"Starting simulation with max_steps={sim_config.max_steps} in {args.mode} mode")

    if args.mode == "animation":
        import matplotlib.pyplot as plt
        from matplotlib.animation import FuncAnimation

        # Do not use block=True inside the update loop
        def update(frame):
            if engine.current_step < engine.config.max_steps:
                engine.step()

            plt.clf()
            plot_simulation_state(
                dump_polygon=dump_polygon,
                zones=zones,
                occupancy_grid=engine.occupancy_grid,
                metadata=metadata,
                trucks=engine.trucks,
                height_map=engine.height_map,
                step=engine.current_step,
                block=False,
                analytics_summary=getattr(engine, "analytics", None).get_summary() if hasattr(engine, "analytics") else None
            )

        fig = plt.figure(figsize=(13, 9))
        
        # Interval is slightly faster (50ms) as requested
        ani = FuncAnimation(
            fig,
            update,
            frames=sim_config.max_steps,
            interval=50,
            repeat=False
        )
        plt.show()

        print(f"\nSimulation complete!")
        print("\nSimulation Results")
        if hasattr(engine, "analytics"):
            summary = engine.analytics.get_summary()
            print(f"Packing Density: {summary['packing_density']:.2f}")
            print(f"Average Cycle Time: {summary['average_cycle_time']:.1f} steps")
            print(f"Fleet Utilization: {summary['fleet_utilization']:.2f}")
            print(f"Total Dumps: {summary.get('total_dumps', 0)}")
            print(f"Dump Throughput: {summary['dump_throughput']:.2f} dumps/step")
            
        stats = engine.get_statistics()
        print(f"Total trucks spawned: {stats['total_trucks']}")
        
    else:
        # Batch Mode
        # Run simulation with an animated visualization every 5 steps
        engine.run(visualize=not args.no_visualize, viz_interval=5, dump_polygon=dump_polygon)

        print(f"\nSimulation complete!")
        stats = engine.get_statistics()
        print(f"Total trucks spawned: {stats['total_trucks']}")

        if not args.no_visualize:
            # Keep the final state visible
            import matplotlib.pyplot as plt
            plt.show()


if __name__ == "__main__":
    main()

