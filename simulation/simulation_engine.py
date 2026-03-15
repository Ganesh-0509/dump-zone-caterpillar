"""Main simulation engine controlling truck movement and updates."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import Polygon

from simulation.truck_agent import Truck, TruckState
from simulation.truck_generator import TruckGenerator, TruckGeneratorConfig
from planning.dump_spot_selector import select_dump_spot
from mapping.occupancy_grid import GridMetadata, CELL_DUMP_PILE, grid_to_world
from mapping.terrain_map import add_dump
from planning.traffic_manager import TrafficManager


@dataclass
class SimulationConfig:
    """Configuration for the simulation engine."""

    max_steps: int = 500
    generator_config: TruckGeneratorConfig = field(default_factory=TruckGeneratorConfig)


class SimulationEngine:
    """Manages the truck simulation loop."""

    def __init__(
        self,
        zones: list[Polygon],
        config: SimulationConfig,
        occupancy_grid: np.ndarray,
        height_map: np.ndarray,
        metadata: GridMetadata,
    ):
        if not zones:
            raise ValueError("zones list cannot be empty.")

        self.zones = zones
        self.config = config
        self.occupancy_grid = occupancy_grid
        self.height_map = height_map
        self.metadata = metadata
        self.generator = TruckGenerator(zones, config.generator_config)
        self.trucks: list[Truck] = []
        self.traffic_manager = TrafficManager()
        self.current_step = 0
        self.history: list[dict] = []

    def step(self) -> None:
        """Execute one simulation step."""
        # Spawn new trucks if needed
        if self.generator.should_spawn(self.current_step):
            new_truck = self.generator.spawn_truck()

            # Select dump spot for this truck
            try:
                dump_grid_x, dump_grid_y = select_dump_spot(
                    new_truck.assigned_zone,
                    self.occupancy_grid,
                    self.metadata,
                )
                new_truck.set_dump_location(dump_grid_x, dump_grid_y)

                # Convert grid to world coordinates
                dump_world_x, dump_world_y = grid_to_world(
                    dump_grid_x,
                    dump_grid_y,
                    self.metadata.origin_x,
                    self.metadata.origin_y,
                    self.metadata.cell_size,
                )
                new_truck.set_target(dump_world_x, dump_world_y)
                new_truck.compute_path(
                    self.occupancy_grid,
                    self.metadata,
                    dump_world_x,
                    dump_world_y,
                    self.traffic_manager,
                    self.current_step
                )
            except ValueError:
                # No valid dump spot; use zone centroid fallback
                fallback_x = new_truck.assigned_zone.centroid.x
                fallback_y = new_truck.assigned_zone.centroid.y
                new_truck.set_target(fallback_x, fallback_y)
                new_truck.compute_path(
                    self.occupancy_grid,
                    self.metadata,
                    fallback_x,
                    fallback_y,
                    self.traffic_manager,
                    self.current_step
                )

            self.trucks.append(new_truck)

        # Update all trucks
        for truck in self.trucks:
            if truck.state == TruckState.MOVING_TO_ZONE:
                # Update path if blocked
                if truck.path and truck.current_path_index < len(truck.path):
                    next_node = truck.path[truck.current_path_index]
                    if self.occupancy_grid[next_node[1], next_node[0]] != 0: # CELL_EMPTY
                        truck.compute_path(
                            self.occupancy_grid,
                            self.metadata,
                            truck.target_x,
                            truck.target_y,
                            self.traffic_manager,
                            self.current_step
                        )
                        
                target_reached = truck.move_along_path(self.metadata)
                if target_reached:
                    truck.state = TruckState.DUMPING
                    self.traffic_manager.release_reservations(truck.truck_id)

            elif truck.state == TruckState.DUMPING:
                # Update occupancy grid and height map
                if truck.dump_grid_x >= 0 and truck.dump_grid_y >= 0:
                    try:
                        self.occupancy_grid[truck.dump_grid_y, truck.dump_grid_x] = CELL_DUMP_PILE
                        add_dump(
                            self.height_map,
                            truck.dump_grid_x,
                            truck.dump_grid_y,
                            truck.payload,
                            self.metadata,
                        )
                    except IndexError:
                        pass

                truck.payload = 0.0
                truck.state = TruckState.RETURNING
                
                # Compute path back to entrance
                truck.set_target(
                    self.config.generator_config.entrance_x,
                    self.config.generator_config.entrance_y,
                )
                truck.compute_path(
                    self.occupancy_grid,
                    self.metadata,
                    self.config.generator_config.entrance_x,
                    self.config.generator_config.entrance_y,
                    self.traffic_manager,
                    self.current_step
                )

            elif truck.state == TruckState.RETURNING:
                # Update path if blocked
                if truck.path and truck.current_path_index < len(truck.path):
                    next_node = truck.path[truck.current_path_index]
                    if self.occupancy_grid[next_node[1], next_node[0]] != 0: # CELL_EMPTY
                        truck.compute_path(
                            self.occupancy_grid,
                            self.metadata,
                            truck.target_x,
                            truck.target_y,
                            self.traffic_manager,
                            self.current_step
                        )
                        
                # Return to entrance
                target_reached = truck.move_along_path(self.metadata)
                if target_reached:
                    truck.state = TruckState.IDLE
                    self.traffic_manager.release_reservations(truck.truck_id)

        # Record state snapshot for visualization
        snapshot = {
            "step": self.current_step,
            "truck_count": len(self.trucks),
            "truck_positions": [(t.position_x, t.position_y) for t in self.trucks],
            "truck_states": [t.state.value for t in self.trucks],
        }
        self.history.append(snapshot)

        self.current_step += 1

    def run(
        self,
        visualize: bool = False,
        viz_interval: int = 10,
        dump_polygon: Polygon | None = None,
    ) -> None:
        """Run simulation for configured max_steps."""
        if visualize:
            import matplotlib.pyplot as plt
            from visualization.plot_environment import plot_simulation_state

            if dump_polygon is None:
                raise ValueError("dump_polygon must be provided for visualization.")

        while self.current_step < self.config.max_steps:
            self.step()

            if visualize and self.current_step % viz_interval == 0:
                plt.clf()
                plot_simulation_state(
                    dump_polygon,
                    self.zones,
                    self.occupancy_grid,
                    self.metadata,
                    self.trucks,
                    step=self.current_step,
                    block=False,
                )
                plt.pause(0.1)

    def get_current_trucks(self) -> list[Truck]:
        """Get all active trucks at current step."""
        return self.trucks.copy()

    def get_moving_trucks(self) -> list[Truck]:
        """Get trucks currently moving to zone."""
        return [t for t in self.trucks if t.state == TruckState.MOVING_TO_ZONE]

    def get_dumping_trucks(self) -> list[Truck]:
        """Get trucks currently dumping."""
        return [t for t in self.trucks if t.state == TruckState.DUMPING]

    def get_returning_trucks(self) -> list[Truck]:
        """Get trucks currently returning."""
        return [t for t in self.trucks if t.state == TruckState.RETURNING]

    def get_idle_trucks(self) -> list[Truck]:
        """Get idle trucks."""
        return [t for t in self.trucks if t.state == TruckState.IDLE]

    def get_statistics(self) -> dict:
        """Get simulation statistics."""
        return {
            "step": self.current_step,
            "total_trucks": len(self.trucks),
            "moving": len(self.get_moving_trucks()),
            "dumping": len(self.get_dumping_trucks()),
            "returning": len(self.get_returning_trucks()),
            "idle": len(self.get_idle_trucks()),
        }
