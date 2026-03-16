"""Slope validation for stable layered dumping."""

from __future__ import annotations

import numpy as np


class SlopeValidator:
    """Validates dump spots for slope stability and layered growth."""

    def __init__(
        self,
        max_slope: float = 0.6,
        neighbor_radius: int = 2,
        adjacency_weight: float = 50.0,
        slope_weight: float = 100.0,
        distance_weight: float = 1.0,
        zone_center_weight: float = 10.0,
    ):
        """
        Initialize slope validator.
        
        Args:
            max_slope: Maximum allowed slope (rise/run) for stable dumping
            neighbor_radius: Radius to inspect for neighboring filled cells
            adjacency_weight: Weight for cells adjacent to existing material
            slope_weight: Weight for cells with good slope support
            distance_weight: Weight for distance from truck
            zone_center_weight: Weight for proximity to zone center
        """
        self.max_slope = max_slope
        self.neighbor_radius = neighbor_radius
        self.adjacency_weight = adjacency_weight
        self.slope_weight = slope_weight
        self.distance_weight = distance_weight
        self.zone_center_weight = zone_center_weight

    def compute_slope(self, height_grid: np.ndarray, x: int, y: int, cell_size: float = 1.0) -> float:
        """
        Compute maximum slope around a cell.
        
        Args:
            height_grid: 2D array of heights
            x, y: Grid coordinates
            cell_size: Physical size of a cell
            
        Returns:
            Maximum slope found in neighboring cells
        """
        if height_grid[y, x] == 0:
            return 0.0

        max_slope = 0.0
        current_height = height_grid[y, x]

        for dy in range(-self.neighbor_radius, self.neighbor_radius + 1):
            for dx in range(-self.neighbor_radius, self.neighbor_radius + 1):
                if dx == 0 and dy == 0:
                    continue

                ny, nx = y + dy, x + dx
                if 0 <= ny < height_grid.shape[0] and 0 <= nx < height_grid.shape[1]:
                    neighbor_height = height_grid[ny, nx]
                    
                    # Only compute slope if neighbor has material
                    if neighbor_height > 0:
                        distance = ((dx**2 + dy**2) ** 0.5) * cell_size
                        if distance > 0:
                            slope = abs(current_height - neighbor_height) / distance
                            max_slope = max(max_slope, slope)

        return max_slope

    def is_stable_slope(self, height_grid: np.ndarray, x: int, y: int, cell_size: float = 1.0) -> bool:
        """Check if a cell location maintains stable slope."""
        slope = self.compute_slope(height_grid, x, y, cell_size)
        return slope <= self.max_slope

    def count_adjacent_material(
        self,
        height_grid: np.ndarray,
        x: int,
        y: int,
    ) -> int:
        """Count filled cells adjacent to this location."""
        count = 0
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < height_grid.shape[0] and 0 <= nx < height_grid.shape[1]:
                    if height_grid[ny, nx] > 0:
                        count += 1
        return count

    def has_base_support(
        self,
        height_grid: np.ndarray,
        x: int,
        y: int,
        zone_mask: np.ndarray,
    ) -> bool:
        """
        Check if cell is on base boundary or has adjacent material.
        
        Base boundary = cells at the edge of the zone with no material nearby.
        """
        # Has adjacent material
        if self.count_adjacent_material(height_grid, x, y) > 0:
            return True

        # Check if on zone boundary (edge cells of zone_mask)
        if not zone_mask[y, x]:
            return False

        # Check if on boundary of zone
        is_boundary = False
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                ny, nx = y + dy, x + dx
                if ny < 0 or ny >= zone_mask.shape[0] or nx < 0 or nx >= zone_mask.shape[1]:
                    is_boundary = True
                elif not zone_mask[ny, nx]:
                    is_boundary = True

        return is_boundary

    def score_dump_spot(
        self,
        x: int,
        y: int,
        height_grid: np.ndarray,
        zone_mask: np.ndarray,
        zone_centroid: tuple[float, float],
        truck_x: float,
        truck_y: float,
        cell_size: float = 1.0,
    ) -> float:
        """
        Score a potential dump spot.
        
        Higher score = better location for dumping.
        Returns -1 if spot is invalid.
        """
        # Cell must be in zone
        if not zone_mask[y, x]:
            return -1.0

        # Cell must have base support
        if not self.has_base_support(height_grid, x, y, zone_mask):
            return -1.0

        # Must not have excessive slope
        if not self.is_stable_slope(height_grid, x, y, cell_size):
            return -1.0

        # Score based on multiple factors
        score = 0.0

        # Adjacency: prefer cells near existing material
        adjacent_count = self.count_adjacent_material(height_grid, x, y)
        score += self.adjacency_weight * min(adjacent_count / 4.0, 1.0)

        # Slope support: cells with gentle slope are better
        slope = self.compute_slope(height_grid, x, y, cell_size)
        slope_factor = 1.0 - (slope / self.max_slope) if slope > 0 else 0.5
        score += self.slope_weight * slope_factor

        # Distance: prefer cells closer to truck
        distance = ((truck_x - x * cell_size)**2 + (truck_y - y * cell_size)**2) ** 0.5
        score -= self.distance_weight * distance

        # Zone center proximity: slight preference for central locations to avoid edge isolation
        centroid_x, centroid_y = zone_centroid
        center_distance = ((centroid_x - x * cell_size)**2 + (centroid_y - y * cell_size)**2) ** 0.5
        score -= self.zone_center_weight * (center_distance / 100.0)

        return score

    def validate_dump_feasible(
        self,
        height_grid: np.ndarray,
        zone_mask: np.ndarray,
        x: int,
        y: int,
    ) -> bool:
        """Final validation: can this spot be safely filled?"""
        if not zone_mask[y, x]:
            return False

        # Already filled to very high level?
        if height_grid[y, x] > 50:  # Arbitrary limit
            return False

        return True
