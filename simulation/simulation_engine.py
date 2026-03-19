"""Main simulation engine controlling truck movement and updates."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import Point, Polygon

from simulation.truck_agent import Truck, TruckState
from simulation.truck_generator import TruckGenerator, TruckGeneratorConfig
from planning.dump_spot_selector import select_dump_spot
from planning.zone_grid_manager import ZoneGridManager
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
        self.dump_cell_reservations: dict[tuple[int, int], int] = {}
        self.current_step = 0
        self.history: list[dict] = []
        
        # Initialize grid-based dump allocation system
        self.zone_grid_manager = ZoneGridManager(zones)

        min_x = min(zone.bounds[0] for zone in zones)
        min_y = min(zone.bounds[1] for zone in zones)
        max_x = max(zone.bounds[2] for zone in zones)
        max_y = max(zone.bounds[3] for zone in zones)
        span_x = max_x - min_x
        span_y = max_y - min_y

        # Operational lanes and holding points for more realistic truck flow.
        self.approach_lane_point = (
            min_x + 0.15 * span_x,
            min_y + 0.90 * span_y,
        )
        self.return_lane_point = (
            min_x + 0.10 * span_x,
            min_y + 0.15 * span_y,
        )
        # Exit point: back near entry but slightly offset (INSIDE polygon for pathfinding)
        self.exit_point = (
            min_x + 0.50 * span_x,  # Center-ish X  (was outside: min_x - 0.20 * span_x)
            min_y + 0.05 * span_y,  # Near bottom    (was: min_y + 0.50 * span_y)
        )
        self.holding_points = [
            (
                min_x + ((i + 0.5) / max(len(zones), 1)) * span_x,
                min_y + 0.20 * span_y,
            )
            for i in range(len(zones))
        ]

        yard_polygon = zones[0].union(zones[1]) if len(zones) > 1 else zones[0]
        for zone in zones[2:]:
            yard_polygon = yard_polygon.union(zone)
        
        # Store yard polygon for boundary checking
        self.yard_polygon = yard_polygon
        inside_hint = yard_polygon.representative_point()

        # Keep operational waypoints routable; fallback to a known inside point if needed.
        if not yard_polygon.contains(Point(*self.approach_lane_point)):
            self.approach_lane_point = (inside_hint.x, inside_hint.y)
        if not yard_polygon.contains(Point(*self.return_lane_point)):
            self.return_lane_point = (inside_hint.x, inside_hint.y)

        safe_holding_points: list[tuple[float, float]] = []
        for hx, hy in self.holding_points:
            if yard_polygon.contains(Point(hx, hy)):
                safe_holding_points.append((hx, hy))
            else:
                safe_holding_points.append((inside_hint.x, inside_hint.y))
        self.holding_points = safe_holding_points
        
        # Set zone distances for grid-based prioritization
        self.zone_grid_manager.set_zone_distances(
            config.generator_config.entrance_x,
            config.generator_config.entrance_y
        )

    def _is_entry_congested(self, threshold_distance: float = 5.0, max_nearby: int = 5) -> bool:
        """Return True when too many trucks are clustered near entrance."""
        entrance_x = self.config.generator_config.entrance_x
        entrance_y = self.config.generator_config.entrance_y

        nearby_count = 0
        for truck in self.trucks:
            distance = np.hypot(truck.position_x - entrance_x, truck.position_y - entrance_y)
            if distance <= threshold_distance:
                nearby_count += 1
                if nearby_count >= max_nearby:
                    return True
        return False

    def _zone_index_for_truck(self, truck: Truck) -> int:
        """Resolve the truck's assigned zone index."""
        return next((i for i, z in enumerate(self.zones) if z == truck.assigned_zone), -1)

    def _holding_point_for_truck(self, truck: Truck) -> tuple[float, float]:
        """Get zone-specific holding point used while waiting for dump slot."""
        zone_index = self._zone_index_for_truck(truck)
        if zone_index == -1 or zone_index >= len(self.holding_points):
            return self.return_lane_point
        return self.holding_points[zone_index]

    def _clip_to_boundary(self, x: float, y: float) -> tuple[float, float]:
        """Clamp truck position to stay within yard polygon boundary."""
        try:
            if not self.yard_polygon.contains(Point(x, y)):
                # Snap to nearest point on polygon boundary
                point = Point(x, y)
                boundary = self.yard_polygon.boundary
                nearest = boundary.interpolate(boundary.project(point))
                # Move slightly inward from boundary
                inx = self.yard_polygon.centroid.x - nearest.x
                iny = self.yard_polygon.centroid.y - nearest.y
                scale = 0.02 if (inx**2 + iny**2) > 0 else 0
                x = nearest.x + inx * scale
                y = nearest.y + iny * scale
        except Exception:
            pass  # If boundary fails, keep original position
        return x, y

    def _apply_collision_avoidance(self) -> None:
        """Apply local collision avoidance between nearby trucks."""
        # Only separate if trucks are actually overlapping (truck width is 2.5m)
        min_separation = 2.5  # meters (actual truck width, minimal buffer)
        
        for i, truck1 in enumerate(self.trucks):
            for truck2 in self.trucks[i+1:]:
                dx = truck2.position_x - truck1.position_x
                dy = truck2.position_y - truck1.position_y
                distance = np.hypot(dx, dy)
                
                # Only intervene if trucks are actually colliding
                if distance < min_separation and distance > 0.001:
                    # Normalize direction and push trucks apart
                    nx = dx / distance
                    ny = dy / distance
                    
                    # Small separation to prevent overlap
                    separation_amount = (min_separation - distance) / 2.0
                    
                    truck1.position_x -= nx * separation_amount
                    truck1.position_y -= ny * separation_amount
                    truck2.position_x += nx * separation_amount
                    truck2.position_y += ny * separation_amount

    def _try_reserve_dump_cell(self, truck: Truck, grid_x: int, grid_y: int) -> bool:
        """Reserve dump cell with simple truck-id priority in conflicts."""
        cell = (grid_x, grid_y)
        holder = self.dump_cell_reservations.get(cell)
        if holder is None:
            self.dump_cell_reservations[cell] = truck.truck_id
            return True

        if holder == truck.truck_id:
            return True

        # Lower truck id has priority when two trucks contend for a narrow approach slot.
        if truck.truck_id < holder:
            self.dump_cell_reservations[cell] = truck.truck_id
            return True

        return False

    def _release_dump_cell_reservation(self, truck: Truck) -> None:
        """Release reserved dump cell for truck when done dumping/removed."""
        cell = (truck.dump_grid_x, truck.dump_grid_y)
        if self.dump_cell_reservations.get(cell) == truck.truck_id:
            del self.dump_cell_reservations[cell]

    def step(self) -> None:
        """Execute one simulation step."""
        # Spawn new trucks if needed
        self.generator.update_loading_queue(self.current_step)
        entry_congested = self._is_entry_congested()
        if self.generator.should_spawn(
            self.current_step,
            active_truck_count=len(self.trucks),
            entry_congested=entry_congested,
        ):
            new_truck = self.generator.spawn_truck(self.current_step)

            # DEBUG: Log spawned truck
            if self.current_step % 10 == 0 or self.current_step < 3:
                print(f"[SPAWN] Step {self.current_step}: Truck {new_truck.truck_id} at ({new_truck.position_x:.1f}, {new_truck.position_y:.1f})")
                print(f"  Entry point: ({self.config.generator_config.entrance_x:.1f}, {self.config.generator_config.entrance_y:.1f})")
                print(f"  Approach lane: ({self.approach_lane_point[0]:.1f}, {self.approach_lane_point[1]:.1f})")

            # Spawn phase: enter via approach lane first.
            target_x, target_y = self.approach_lane_point
            new_truck.set_target(target_x, target_y)
            new_truck.compute_path(
                self.occupancy_grid,
                self.metadata,
                target_x,
                target_y,
                self.traffic_manager,
                self.current_step
            )
            
            # DEBUG: Log path result
            if self.current_step % 10 == 0 or self.current_step < 3:
                if new_truck.path:
                    print(f"  ✓ Path computed: {len(new_truck.path)} nodes")
                else:
                    print(f"  ✗ Path is empty/None!")

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
        trucks_to_remove: list[int] = []
        for truck in self.trucks:
            old_cell = world_to_grid(
                truck.position_x,
                truck.position_y,
                self.metadata.origin_x,
                self.metadata.origin_y,
                self.metadata.cell_size,
            )

            if truck.state == TruckState.MOVING_TO_ZONE:
                # If path is missing, retry planning to current target.
                if not truck.path or truck.current_path_index >= len(truck.path):
                    truck.compute_path(
                        self.occupancy_grid,
                        self.metadata,
                        truck.target_x,
                        truck.target_y,
                        self.traffic_manager,
                        self.current_step
                    )

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
                # Clip truck to stay within polygon
                truck.position_x, truck.position_y = self._clip_to_boundary(
                    truck.position_x, truck.position_y
                )
                
                if target_reached:
                    if truck.approach_stage == 0:
                        # After approach lane, use grid-based dump spot from zone
                        truck.approach_stage = 1
                        try:
                            # Use grid cell location from zone
                            zone_id = self._zone_index_for_truck(truck)
                            dump_location = self.zone_grid_manager.get_next_dump_location(zone_id)
                            
                            if dump_location:
                                # Use grid cell location
                                dump_world_x, dump_world_y = dump_location
                                dump_grid_x, dump_grid_y = world_to_grid(
                                    dump_world_x,
                                    dump_world_y,
                                    self.metadata.origin_x,
                                    self.metadata.origin_y,
                                    self.metadata.cell_size,
                                )
                                truck.set_dump_location(dump_grid_x, dump_grid_y)
                            else:
                                raise ValueError("No empty grid cells in zone")
                        except ValueError:
                            # Fallback to zone centroid grid cell.
                            cx, cy = truck.assigned_zone.centroid.x, truck.assigned_zone.centroid.y
                            gx, gy = world_to_grid(
                                cx,
                                cy,
                                self.metadata.origin_x,
                                self.metadata.origin_y,
                                self.metadata.cell_size,
                            )
                            truck.set_dump_location(gx, gy)

                        if self._try_reserve_dump_cell(truck, truck.dump_grid_x, truck.dump_grid_y):
                            truck.waiting_for_dump_slot = False
                            dump_world_x, dump_world_y = grid_to_world(
                                truck.dump_grid_x,
                                truck.dump_grid_y,
                                self.metadata.origin_x,
                                self.metadata.origin_y,
                                self.metadata.cell_size,
                            )
                            truck.set_target(dump_world_x, dump_world_y)
                            truck.compute_path(
                                self.occupancy_grid,
                                self.metadata,
                                dump_world_x,
                                dump_world_y,
                                self.traffic_manager,
                                self.current_step
                            )
                        else:
                            # Dump slot currently contended: wait at zone holding point.
                            truck.waiting_for_dump_slot = True
                            hold_x, hold_y = self._holding_point_for_truck(truck)
                            truck.set_target(hold_x, hold_y)
                            truck.compute_path(
                                self.occupancy_grid,
                                self.metadata,
                                hold_x,
                                hold_y,
                                self.traffic_manager,
                                self.current_step
                            )
                    elif truck.waiting_for_dump_slot:
                        # Re-check reservation from holding point.
                        if self._try_reserve_dump_cell(truck, truck.dump_grid_x, truck.dump_grid_y):
                            truck.waiting_for_dump_slot = False
                            dump_world_x, dump_world_y = grid_to_world(
                                truck.dump_grid_x,
                                truck.dump_grid_y,
                                self.metadata.origin_x,
                                self.metadata.origin_y,
                                self.metadata.cell_size,
                            )
                            truck.set_target(dump_world_x, dump_world_y)
                            truck.compute_path(
                                self.occupancy_grid,
                                self.metadata,
                                dump_world_x,
                                dump_world_y,
                                self.traffic_manager,
                                self.current_step
                            )
                        else:
                            hold_x, hold_y = self._holding_point_for_truck(truck)
                            truck.set_target(hold_x, hold_y)
                            truck.compute_path(
                                self.occupancy_grid,
                                self.metadata,
                                hold_x,
                                hold_y,
                                self.traffic_manager,
                                self.current_step
                            )
                    elif truck.has_dump_spot and not truck.waiting_for_dump_slot:
                        # Reached reserved dump location: enter timed dumping state.
                        dump_world_x, dump_world_y = grid_to_world(
                            truck.dump_grid_x,
                            truck.dump_grid_y,
                            self.metadata.origin_x,
                            self.metadata.origin_y,
                            self.metadata.cell_size,
                        )
                        truck.position_x = dump_world_x
                        truck.position_y = dump_world_y
                        truck.dump_timer = 0
                        truck.state = TruckState.DUMPING
                        self.traffic_manager.release_reservations(truck.truck_id)

            elif truck.state == TruckState.DUMPING:
                truck.dump_timer += 1
                if truck.dump_timer >= truck.DUMP_DURATION:
                    # Update occupancy grid and height map after dump delay.
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

                    zone_id = next((i for i, z in enumerate(self.zones) if z == truck.assigned_zone), -1)
                    if zone_id != -1:
                        self.fleet_manager.update_zone_utilization(zone_id, self.occupancy_grid, self.metadata)
                        self.fleet_manager.remove_truck_from_zone(zone_id)
                        self.analytics.record_dump(truck.truck_id, zone_id, truck.payload, self.current_step)
                        
                        # Mark grid cell as filled in zone grid manager
                        dump_world_x, dump_world_y = grid_to_world(
                            truck.dump_grid_x,
                            truck.dump_grid_y,
                            self.metadata.origin_x,
                            self.metadata.origin_y,
                            self.metadata.cell_size,
                        )
                        self.zone_grid_manager.mark_cell_filled(zone_id, dump_world_x, dump_world_y)
                        
                        # DEBUG: Log grid status
                        fill_pct = self.zone_grid_manager.get_zone_fill_percentage(zone_id)
                        print(f"[DUMP] Step {self.current_step}: Truck {truck.truck_id} dumped at Zone {zone_id} ({fill_pct:.0f}% filled)")

                    self._release_dump_cell_reservation(truck)
                    truck.payload = 0.0
                    truck.state = TruckState.RETURNING
                    truck.return_stage = 0

                    # Return via return lane first, then exit point.
                    truck.set_target(
                        self.return_lane_point[0],
                        self.return_lane_point[1],
                    )
                    truck.compute_path(
                        self.occupancy_grid,
                        self.metadata,
                        self.return_lane_point[0],
                        self.return_lane_point[1],
                        self.traffic_manager,
                        self.current_step
                    )

            elif truck.state == TruckState.RETURNING:
                # If path is missing, retry planning to current target.
                if not truck.path or truck.current_path_index >= len(truck.path):
                    truck.compute_path(
                        self.occupancy_grid,
                        self.metadata,
                        truck.target_x,
                        truck.target_y,
                        self.traffic_manager,
                        self.current_step
                    )

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
                        
                # Return to exit point
                target_reached = truck.move_along_path(self.metadata)
                # Clip truck to stay within polygon during return
                truck.position_x, truck.position_y = self._clip_to_boundary(
                    truck.position_x, truck.position_y
                )
                
                if target_reached:
                    if truck.return_stage == 0:
                        truck.return_stage = 1
                        truck.set_target(
                            self.exit_point[0],
                            self.exit_point[1],
                        )
                        truck.compute_path(
                            self.occupancy_grid,
                            self.metadata,
                            self.exit_point[0],
                            self.exit_point[1],
                            self.traffic_manager,
                            self.current_step
                        )
                    else:
                        truck.state = TruckState.IDLE
                        truck.has_dump_spot = False
                        truck.waiting_for_dump_slot = False
                        truck.dump_grid_x = -1
                        truck.dump_grid_y = -1
                        self.traffic_manager.release_reservations(truck.truck_id)
                        self.analytics.record_truck_return(truck.truck_id, self.current_step)
                        # DEBUG: Log truck exit
                        print(f"[EXIT] Step {self.current_step}: Truck {truck.truck_id} removed (completed)")
                        trucks_to_remove.append(truck.truck_id)

            new_cell = world_to_grid(
                truck.position_x,
                truck.position_y,
                self.metadata.origin_x,
                self.metadata.origin_y,
                self.metadata.cell_size,
            )
            self.spatial_index.update_truck(truck.truck_id, old_cell, new_cell)

        # Recycle completed trucks to keep active fleet realistic and stable.
        if trucks_to_remove:
            for truck_id in trucks_to_remove:
                truck_obj = next((t for t in self.trucks if t.truck_id == truck_id), None)
                if truck_obj is None:
                    continue

                self._release_dump_cell_reservation(truck_obj)

                final_cell = world_to_grid(
                    truck_obj.position_x,
                    truck_obj.position_y,
                    self.metadata.origin_x,
                    self.metadata.origin_y,
                    self.metadata.cell_size,
                )
                self.spatial_index.remove_truck(truck_id, final_cell)

            self.trucks = [t for t in self.trucks if t.truck_id not in trucks_to_remove]

        # Apply collision avoidance between trucks
        self._apply_collision_avoidance()

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
