"""Truck agent model with state and movement logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
from shapely.geometry import Polygon

from mapping.occupancy_grid import world_to_grid, grid_to_world, GridMetadata
from planning.path_planner import plan_path
from planning.path_smoother import PathSmoother

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
    dump_grid_x: int = 0
    dump_grid_y: int = 0
    state: TruckState = TruckState.IDLE
    distance_traveled: float = field(default=0.0, init=False)
    
    # Vehicle dimensions for realistic collision and footprint modeling
    truck_length: float = 5.0  # meters
    truck_width: float = 2.5   # meters
    turning_radius: float = 3.0  # meters
    
    # Path following attributes
    path: list[tuple[int, int]] = field(default_factory=list, init=False)
    current_path_index: int = field(default=0, init=False)
    smoothed_path: list[tuple[float, float]] = field(default_factory=list, init=False)
    current_smoothed_index: int = field(default=0, init=False)

    def get_footprint_polygon(self, heading: float = 0.0) -> Polygon:
        """Get the truck's footprint as a polygon."""
        import math
        
        cos_h = math.cos(heading)
        sin_h = math.sin(heading)
        
        corners = [
            (-self.truck_width / 2, -self.truck_length / 2),
            (self.truck_width / 2, -self.truck_length / 2),
            (self.truck_width / 2, self.truck_length / 2),
            (-self.truck_width / 2, self.truck_length / 2),
        ]
        
        rotated = []
        for x, y in corners:
            rx = x * cos_h - y * sin_h
            ry = x * sin_h + y * cos_h
            rotated.append((self.position_x + rx, self.position_y + ry))
        
        return Polygon(rotated)

    def compute_path(
        self,
        occupancy_grid: np.ndarray,
        metadata: GridMetadata,
        goal_x: float,
        goal_y: float,
        traffic_manager=None,
        current_step: int = 0,
    ) -> bool:
        """Compute path to world coordinates using A* search."""
        start_grid_x, start_grid_y = world_to_grid(
            self.position_x,
            self.position_y,
            metadata.origin_x,
            metadata.origin_y,
            metadata.cell_size,
        )
        
        goal_grid_x, goal_grid_y = world_to_grid(
            goal_x,
            goal_y,
            metadata.origin_x,
            metadata.origin_y,
            metadata.cell_size,
        )
        
        # Ensure start and goal are inside grid bounds
        height, width = occupancy_grid.shape
        start_grid_x = max(0, min(width - 1, start_grid_x))
        start_grid_y = max(0, min(height - 1, start_grid_y))
        goal_grid_x = max(0, min(width - 1, goal_grid_x))
        goal_grid_y = max(0, min(height - 1, goal_grid_y))
        
        if traffic_manager:
            traffic_manager.release_reservations(self.truck_id)
        
        planned_path = plan_path(
            (start_grid_x, start_grid_y),
            (goal_grid_x, goal_grid_y),
            occupancy_grid,
            start_time=current_step,
            traffic_manager=traffic_manager,
        )
        
        if planned_path:
            self.path = planned_path
            self.current_path_index = 0
            if traffic_manager:
                traffic_manager.reserve_path(self.truck_id, self.path, current_step)
                
            smoother = PathSmoother()
            reduced = smoother.reduce_waypoints(self.path)
            self.smoothed_path = smoother.smooth_path(reduced, resolution=5, metadata=metadata)
            self.current_smoothed_index = 0
            
            return True
            
        return False

    def move_along_path(self, metadata: GridMetadata) -> bool:
        """Move truck one step along its computed path.
        
        Returns True if final target reached, False otherwise.
        """
        if not self.path or self.current_path_index >= len(self.path):
            # No path or reached end
            return True
            
        # Get target cell
        target_grid_node = self.path[self.current_path_index]
        target_world_x, target_world_y = grid_to_world(
            target_grid_node[0],
            target_grid_node[1],
            metadata.origin_x,
            metadata.origin_y,
            metadata.cell_size,
        )
        
        # We target the center of the cell for smoother movement
        target_world_x += metadata.cell_size / 2.0
        target_world_y += metadata.cell_size / 2.0
        
        dx = target_world_x - self.position_x
        dy = target_world_y - self.position_y
        distance = np.sqrt(dx**2 + dy**2)
        
        if distance < self.speed:
            # Reached this waypoint
            self.position_x = target_world_x
            self.position_y = target_world_y
            self.distance_traveled += distance
            self.current_path_index += 1
            
            # Check if we're done
            if self.current_path_index >= len(self.path):
                return True
                
        else:
            # Move toward waypoint
            self.position_x += self.speed * (dx / distance)
            self.position_y += self.speed * (dy / distance)
            self.distance_traveled += self.speed
            
        return False

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

    def set_dump_location(self, dump_grid_x: int, dump_grid_y: int) -> None:
        """Set truck's dump grid location."""
        self.dump_grid_x = dump_grid_x
        self.dump_grid_y = dump_grid_y

    def __repr__(self) -> str:
        """String representation of truck."""
        return (
            f"Truck(id={self.truck_id}, pos=({self.position_x:.1f}, {self.position_y:.1f}), "
            f"state={self.state.value}, target=({self.target_x:.1f}, {self.target_y:.1f}))"
        )
