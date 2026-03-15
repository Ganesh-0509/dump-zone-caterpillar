"""Truck agent model with state and movement logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
from shapely.geometry import Polygon


class TruckState(Enum):
    """Enumeration of truck states."""

    IDLE = "idle"
    MOVING_TO_ZONE = "moving_to_zone"
    DUMPING = "dumping"
    RETURNING = "returning"


@dataclass
class Truck:
    """Autonomous truck agent."""

    truck_id: int
    position_x: float
    position_y: float
    speed: float
    payload: float = 1.0
    assigned_zone: Optional[Polygon] = None
    target_x: float = 0.0
    target_y: float = 0.0
    state: TruckState = TruckState.IDLE
    distance_traveled: float = field(default=0.0, init=False)

    def move_toward_target(self) -> bool:
        """Move truck one step toward target point.
        
        Returns True if target reached, False otherwise.
        """
        dx = self.target_x - self.position_x
        dy = self.target_y - self.position_y
        distance = np.sqrt(dx**2 + dy**2)

        if distance < self.speed:
            # Snap to target
            self.position_x = self.target_x
            self.position_y = self.target_y
            self.distance_traveled += distance
            return True

        # Normalize and move
        if distance > 0:
            self.position_x += self.speed * (dx / distance)
            self.position_y += self.speed * (dy / distance)
            self.distance_traveled += self.speed

        return False

    def set_target(self, target_x: float, target_y: float) -> None:
        """Set truck's target position."""
        self.target_x = target_x
        self.target_y = target_y

    def __repr__(self) -> str:
        """String representation of truck."""
        return (
            f"Truck(id={self.truck_id}, pos=({self.position_x:.1f}, {self.position_y:.1f}), "
            f"state={self.state.value}, target=({self.target_x:.1f}, {self.target_y:.1f}))"
        )
