"""Truck spawning and zone assignment logic."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from shapely.geometry import Polygon

from simulation.truck_agent import Truck, TruckState
from planning.dump_spot_selector import select_dump_spot
from mapping.occupancy_grid import GridMetadata
from planning.fleet_manager import FleetManager


@dataclass
class TruckGeneratorConfig:
    """Configuration for truck generation."""

    spawn_interval: int = 10
    truck_speed: float = 0.5
    entrance_x: float = 0.0
    entrance_y: float = 50.0
    initial_payload: float = 1.0


class TruckGenerator:
    """Spawns trucks and assigns them to zones."""

    def __init__(self, zones: list[Polygon], config: TruckGeneratorConfig, fleet_manager: FleetManager):
        if not zones:
            raise ValueError("zones list cannot be empty.")

        self.zones = zones
        self.config = config
        self.fleet_manager = fleet_manager
        self.truck_counter = 0
        self.next_spawn_step = config.spawn_interval

    def should_spawn(self, current_step: int) -> bool:
        """Check if a truck should spawn at this step."""
        if current_step >= self.next_spawn_step:
            self.next_spawn_step += self.config.spawn_interval
            return True
        return False

    def spawn_truck(self) -> Truck:
        """Create a new truck with assigned zone."""
        truck_id = self.truck_counter
        self.truck_counter += 1

        # Assign best zone using fleet manager
        zone_index = self.fleet_manager.assign_best_zone((self.config.entrance_x, self.config.entrance_y))
        
        # Fallback if needed
        if zone_index == -1:
            zone_index = truck_id % len(self.zones)
            
        assigned_zone = self.zones[zone_index]
        self.fleet_manager.add_truck_to_zone(zone_index)

        # Zone centroid as target
        target_x, target_y = assigned_zone.centroid.x, assigned_zone.centroid.y

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
