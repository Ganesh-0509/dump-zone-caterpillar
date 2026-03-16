"""Fleet manager for dynamic truck zone assignment."""

from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon

from mapping.occupancy_grid import CELL_DUMP_PILE, world_to_grid


class FleetManager:
    """Manages fleet assignment to optimize yard operations."""

    def __init__(
        self,
        distance_weight: float = 1.0,
        congestion_weight: float = 50.0,
        fill_weight: float = 500.0,
    ) -> None:
        self.distance_weight = distance_weight
        self.congestion_weight = congestion_weight
        self.fill_weight = fill_weight
        
        self.zone_polygons: dict[int, Polygon] = {}
        self.zone_truck_counts: dict[int, int] = {}
        self.zone_dump_counts: dict[int, int] = {}
        self.zone_utilizations: dict[int, float] = {}
        self.zone_total_cells: dict[int, int] = {}

    def register_zone(self, zone_id: int, zone_polygon: Polygon) -> None:
        """Register a zone with the fleet manager."""
        self.zone_polygons[zone_id] = zone_polygon
        self.zone_truck_counts[zone_id] = 0
        self.zone_dump_counts[zone_id] = 0
        self.zone_utilizations[zone_id] = 0.0
        # Estimate total cells trivially by area, will refine in update
        self.zone_total_cells[zone_id] = int(zone_polygon.area) if zone_polygon.area > 0 else 1

    def update_zone_utilization(self, zone_id: int, occupancy_grid: np.ndarray, metadata) -> None:
        """Counts dump pile cells in the zone."""
        polygon = self.zone_polygons.get(zone_id)
        if not polygon:
            return

        minx, miny, maxx, maxy = polygon.bounds
        grid_min_x, grid_min_y = world_to_grid(minx, miny, metadata.origin_x, metadata.origin_y, metadata.cell_size)
        grid_max_x, grid_max_y = world_to_grid(maxx, maxy, metadata.origin_x, metadata.origin_y, metadata.cell_size)

        # Ensure bounds
        height, width = occupancy_grid.shape
        grid_min_x = max(0, min(width - 1, grid_min_x))
        grid_min_y = max(0, min(height - 1, grid_min_y))
        grid_max_x = max(0, min(width - 1, grid_max_x))
        grid_max_y = max(0, min(height - 1, grid_max_y))
        
        if grid_min_x > grid_max_x:
            grid_min_x, grid_max_x = grid_max_x, grid_min_x
        if grid_min_y > grid_max_y:
            grid_min_y, grid_max_y = grid_max_y, grid_min_y

        dump_count = 0
        total_cells = 0
        from shapely.geometry import Point
        
        # NOTE: A more efficient method could be used, but this works for basic simulation
        for y in range(grid_min_y, grid_max_y + 1):
            for x in range(grid_min_x, grid_max_x + 1):
                # world coords approx
                wx = metadata.origin_x + x * metadata.cell_size
                wy = metadata.origin_y + y * metadata.cell_size
                if polygon.contains(Point(wx, wy)):
                    total_cells += 1
                    if occupancy_grid[y, x] == CELL_DUMP_PILE:
                        dump_count += 1
                        
        self.zone_dump_counts[zone_id] = dump_count
        if total_cells > 0:
            self.zone_total_cells[zone_id] = total_cells
            self.zone_utilizations[zone_id] = dump_count / total_cells
        else:
            self.zone_utilizations[zone_id] = 0.0

    def get_zone_truck_count(self, zone_id: int) -> int:
        """Returns number of trucks currently heading to that zone."""
        return self.zone_truck_counts.get(zone_id, 0)
        
    def add_truck_to_zone(self, zone_id: int) -> None:
        """Increment truck count for a zone."""
        if zone_id in self.zone_truck_counts:
            self.zone_truck_counts[zone_id] += 1
            
    def remove_truck_from_zone(self, zone_id: int) -> None:
        """Decrement truck count for a zone."""
        if zone_id in self.zone_truck_counts and self.zone_truck_counts[zone_id] > 0:
            self.zone_truck_counts[zone_id] -= 1

    def assign_best_zone(self, truck_position: tuple[float, float]) -> int:
        """Returns the optimal zone ID for a new truck based on current conditions."""
        best_zone_id = -1
        best_score = float('inf')
        
        truck_x, truck_y = truck_position

        for zone_id, polygon in self.zone_polygons.items():
            centroid = polygon.centroid
            dist = math.hypot(centroid.x - truck_x, centroid.y - truck_y)
            
            trucks_in_zone = self.get_zone_truck_count(zone_id)
            utilization = self.zone_utilizations.get(zone_id, 0.0)
            
            score = (
                self.distance_weight * dist +
                self.congestion_weight * trucks_in_zone +
                self.fill_weight * utilization
            )
            
            if score < best_score:
                best_score = score
                best_zone_id = zone_id

        return best_zone_id