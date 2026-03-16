"""Main simulation engine controlling truck movement and updates."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import Polygon

from simulation.truck_agent import Truck, TruckState
from simulation.truck_generator import TruckGenerator, TruckGeneratorConfig
from planning.dump_spot_selector import select_dump_spot
from mapping.occupancy_grid import GridMetadata, CELL_DUMP_PILE, grid_to_world, world_to_grid
from mapping.terrain_map import add_dump
from planning.traffic_manager import TrafficManager
from planning.spatial_index import SpatialIndex
from planning.fleet_manager import FleetManager
from planning.analytics_manager import AnalyticsManager
from planning.deadlock_manager import DeadlockManager
from planning.slope_validator import SlopeValidator


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
        
        self.fleet_manager = FleetManager()
        for i, zone in enumerate(zones):
            self.fleet_manager.register_zone(i, zone)
            
        self.generator = TruckGenerator(zones, config.generator_config, self.fleet_manager)
        self.trucks: list[Truck] = []
        self.traffic_manager = TrafficManager()
        self.spatial_index = SpatialIndex()
        self.analytics = AnalyticsManager()
        self.deadlock_manager = DeadlockManager(wait_threshold=20)
        self.slope_validator = SlopeValidator(max_slope=0.6)
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
                    height_grid=self.height_map,
                    truck_position=(new_truck.position_x, new_truck.position_y),
                    slope_validator=self.slope_validator,
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
            self.analytics.record_truck_spawn(new_truck.truck_id, self.current_step)

            # Add to spatial index
            start_cell = world_to_grid(
                new_truck.position_x,
                new_truck.position_y,
                self.metadata.origin_x,
                self.metadata.origin_y,
                self.metadata.cell_size,
            )
            self.spatial_index.add_truck(new_truck.truck_id, start_cell)

        # Update all trucks
        for truck in self.trucks:
            old_cell = world_to_grid(
                truck.position_x,
                truck.position_y,
                self.metadata.origin_x,
                self.metadata.origin_y,
                self.metadata.cell_size,
            )

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
                        
                        # Record slope/layer growth metrics
                        slope = self.slope_validator.compute_slope(
                            self.height_map,
                            truck.dump_grid_x,
                            truck.dump_grid_y,
                            self.metadata.cell_size
                        )
                        max_height = self.height_map[truck.dump_grid_y, truck.dump_grid_x]
                        self.analytics.record_layer_growth(slope, max_height)
                    except IndexError:
                        pass
                        
                zone_id = -1
                for i, zone in enumerate(self.zones):
                    if zone == truck.assigned_zone:
                        zone_id = i
                        break
                if zone_id != -1:
                    self.fleet_manager.update_zone_utilization(zone_id, self.occupancy_grid, self.metadata)
                    self.fleet_manager.remove_truck_from_zone(zone_id)
                    self.analytics.record_dump(truck.truck_id, zone_id, truck.payload, self.current_step)

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
                    self.analytics.record_truck_return(truck.truck_id, self.current_step)

            new_cell = world_to_grid(
                truck.position_x,
                truck.position_y,
                self.metadata.origin_x,
                self.metadata.origin_y,
                self.metadata.cell_size,
            )
            self.spatial_index.update_truck(truck.truck_id, old_cell, new_cell)

        # Record state snapshot for visualization
        snapshot = {
            "step": self.current_step,
            "truck_count": len(self.trucks),
            "truck_positions": [(t.position_x, t.position_y) for t in self.trucks],
            "truck_states": [t.state.value for t in self.trucks],
        }
        self.history.append(snapshot)
        
        self.analytics.update_metrics(
            self.occupancy_grid,
            self.zones,
            self.trucks,
            self.metadata,
            self.current_step
        )

        # Detect and resolve deadlocks
        stuck_trucks = self.deadlock_manager.update(self.trucks, self.traffic_manager)
        for truck_id in stuck_trucks:
            truck = next((t for t in self.trucks if t.truck_id == truck_id), None)
            if truck:
                # Force replan by clearing path
                self.traffic_manager.release_reservations(truck_id)
                truck.path = []
                truck.current_path_index = 0
                if hasattr(truck, 'smoothed_path'):
                    truck.smoothed_path = []
                    truck.current_smoothed_index = 0

        self.current_step += 1

    def run(
        self,
        visualize: bool = False,
        viz_interval: int = 10,
        dump_polygon: Polygon | None = None,
    ) -> None:
        """Run simulation for configured max_steps."""
        while self.current_step < self.config.max_steps:
            self.step()

        print("\nSimulation Results")
        summary = self.analytics.get_summary()
        print(f"Packing Density: {summary['packing_density']:.2f}")
        print(f"Average Cycle Time: {summary['average_cycle_time']:.1f} steps")
        print(f"Fleet Utilization: {summary['fleet_utilization']:.2f}")
        print(f"Dump Throughput: {summary['dump_throughput']:.2f} dumps/step")

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

    def check_collisions(self, collision_distance: float = 2.0) -> list[tuple[int, int]]:
        """Check for collisions querying nearby trucks via the spatial index."""
        collisions = set()
        truck_dict = {t.truck_id: t for t in self.trucks}
        
        for truck in self.trucks:
            cell = world_to_grid(
                truck.position_x,
                truck.position_y,
                self.metadata.origin_x,
                self.metadata.origin_y,
                self.metadata.cell_size,
            )
            nearby_ids = self.spatial_index.get_nearby_trucks(cell)
            for other_id in nearby_ids:
                if other_id > truck.truck_id:
                    other_truck = truck_dict.get(other_id)
                    if other_truck:
                        dist = np.hypot(
                            truck.position_x - other_truck.position_x,
                            truck.position_y - other_truck.position_y
                        )
                        if dist < collision_distance:
                            collisions.add((truck.truck_id, other_id))
                            
        return list(collisions)

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
