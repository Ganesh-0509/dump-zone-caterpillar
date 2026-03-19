"""Truck spawning and zone assignment logic."""

from __future__ import annotations

from dataclasses import dataclass
from shapely.geometry import Polygon

from simulation.truck_agent import Truck, TruckState
from planning.fleet_manager import FleetManager


@dataclass
class TruckGeneratorConfig:
    """Configuration for truck generation."""

    spawn_interval: int = 1
    truck_speed: float = 1.0
    entrance_x: float = 0.0
    entrance_y: float = 50.0
    initial_payload: float = 1.0
    max_active_trucks: int = 30
    loading_queue_capacity: int = 100
    release_interval: int = 1


class TruckGenerator:
    """Spawns trucks and assigns them to zones."""

    def __init__(self, zones: list[Polygon], config: TruckGeneratorConfig, fleet_manager: FleetManager):
        if not zones:
            raise ValueError("zones list cannot be empty.")

        self.zones = zones
        self.config = config
        self.fleet_manager = fleet_manager
        self.truck_counter = 0
        self.next_queue_step = config.spawn_interval
        self.next_release_step = 0
        self.queued_loads = 0
        self.zone_dump_counts = [0] * len(zones)

    def update_loading_queue(self, current_step: int) -> None:
        """Add incoming loads to queue at spawn interval cadence."""
        while current_step >= self.next_queue_step:
            if self.queued_loads < self.config.loading_queue_capacity:
                self.queued_loads += 1
            self.next_queue_step += self.config.spawn_interval

    def should_spawn(
        self,
        current_step: int,
        active_truck_count: int = 0,
        entry_congested: bool = False,
    ) -> bool:
        """Check if a truck should spawn at this step."""
        if self.queued_loads <= 0:
            return False

        if active_truck_count >= self.config.max_active_trucks:
            return False

        if entry_congested:
            return False

        if current_step < self.next_release_step:
            return False

        return True

    def spawn_truck(self, current_step: int = 0) -> Truck:
        """Create a new truck with assigned zone."""
        truck_id = self.truck_counter
        self.truck_counter += 1

        if self.queued_loads > 0:
            self.queued_loads -= 1
        self.next_release_step = current_step + self.config.release_interval

        # Pick zone with fewest assignments to enforce strict spread.
        zone_index = self.zone_dump_counts.index(min(self.zone_dump_counts))
        self.zone_dump_counts[zone_index] += 1

        assigned_zone = self.zones[zone_index]
        self.fleet_manager.add_truck_to_zone(zone_index)

        # Use an interior point to avoid unreachable centroid targets in concave zones.
        target_point = assigned_zone.representative_point()
        target_x, target_y = target_point.x, target_point.y

        truck = Truck(
            truck_id=truck_id,
            position_x=self.config.entrance_x,
            position_y=self.config.entrance_y,
            speed=self.config.truck_speed,
            payload=self.config.initial_payload,
            assigned_zone=assigned_zone,
            target_x=target_x,
            target_y=target_y,
            state=TruckState.MOVING_TO_ZONE,
        )

        return truck
