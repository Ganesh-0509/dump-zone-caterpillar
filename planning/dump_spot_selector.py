"""Select optimal dump locations within zones using distance transforms and advanced validation."""

from __future__ import annotations

from collections import deque
import numpy as np
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Point, Polygon

from mapping.occupancy_grid import GridMetadata, CELL_EMPTY, CELL_INVALID, CELL_DUMP_PILE
from planning.slope_validator import SlopeValidator


def select_dump_spot(
    zone_polygon: Polygon,
    occupancy_grid: np.ndarray,
    metadata: GridMetadata,
    height_grid: np.ndarray | None = None,
    truck_position: tuple[float, float] | None = None,
    slope_validator: SlopeValidator | None = None,
) -> tuple[int, int]:
    """
    Select the optimal dump cell within a zone using distance transform and slope validation.
    
    Returns grid coordinates (grid_x, grid_y) of the best dump location.
    
    Enhanced Algorithm:
    1. Find all grid cells inside zone polygon
    2. Filter cells that are valid and empty
    3. If height_grid provided, validate slope and accessibility
    4. Score remaining candidates
    5. Return best candidate
    """
    if not zone_polygon.is_valid:
        raise ValueError("Zone polygon is invalid.")

    # Create binary mask for cells inside zone
    zone_mask = np.zeros((metadata.grid_height, metadata.grid_width), dtype=np.bool_)

    for grid_y in range(metadata.grid_height):
        for grid_x in range(metadata.grid_width):
            world_x = metadata.origin_x + grid_x * metadata.cell_size
            world_y = metadata.origin_y + grid_y * metadata.cell_size
            cell_center_x = world_x + metadata.cell_size / 2.0
            cell_center_y = world_y + metadata.cell_size / 2.0

            if zone_polygon.contains(Point(cell_center_x, cell_center_y)):
                zone_mask[grid_y, grid_x] = True

    # Create candidate mask
    candidates = np.zeros((metadata.grid_height, metadata.grid_width), dtype=np.bool_)

    for grid_y in range(metadata.grid_height):
        for grid_x in range(metadata.grid_width):
            cell_state = occupancy_grid[grid_y, grid_x]
            is_in_zone = zone_mask[grid_y, grid_x]
            is_valid = cell_state != CELL_INVALID
            is_empty = cell_state == CELL_EMPTY

            if is_in_zone and is_valid and is_empty:
                candidates[grid_y, grid_x] = True

    # Apply slope validation if height map provided
    if height_grid is not None and slope_validator is not None:
        candidates = _filter_by_slope(
            candidates,
            zone_mask,
            height_grid,
            slope_validator,
            metadata,
        )

    # Apply access isolation validation
    if height_grid is not None:
        candidates = _filter_by_accessibility(
            candidates,
            zone_mask,
            occupancy_grid,
            height_grid,
            metadata,
        )

    # Check if any candidates remain
    if not np.any(candidates):
        # Fallback: find any valid cell in zone
        zone_valid = zone_mask & (occupancy_grid != CELL_INVALID)
        if np.any(zone_valid):
            coords = np.argwhere(zone_valid)
            idx = np.random.choice(len(coords))
            grid_y, grid_x = coords[idx]
            return grid_x, grid_y
        raise ValueError("No valid cells found in zone.")

    # Score candidates if slope validator available
    if slope_validator is not None and truck_position is not None:
        zone_centroid = (zone_polygon.centroid.x, zone_polygon.centroid.y)
        scores = _score_candidates(
            candidates,
            zone_mask,
            height_grid if height_grid is not None else np.zeros_like(occupancy_grid, dtype=np.float32),
            zone_centroid,
            truck_position,
            slope_validator,
            metadata,
        )
        # Find top 10% of candidates and select randomly to encourage spread
        valid_scores = scores[candidates]
        if len(valid_scores) > 0:
            top_threshold = np.percentile(valid_scores, 90)
            top_candidates = np.argwhere(candidates & (scores >= top_threshold))
            if len(top_candidates) > 0:
                selected_idx = np.random.randint(0, len(top_candidates))
                best_grid_y, best_grid_x = top_candidates[selected_idx]
                return best_grid_x, best_grid_y
        # Fallback to best score
        best_idx = np.argmax(scores)
    else:
        # Fallback to distance transform
        distance_map = distance_transform_edt(candidates)
        best_idx = np.argmax(distance_map)

    best_grid_y, best_grid_x = np.unravel_index(best_idx, candidates.shape)
    return best_grid_x, best_grid_y


def _filter_by_slope(
    candidates: np.ndarray,
    zone_mask: np.ndarray,
    height_grid: np.ndarray,
    slope_validator: SlopeValidator,
    metadata: GridMetadata,
) -> np.ndarray:
    """Filter candidates based on slope stability."""
    filtered = candidates.copy()

    for grid_y in range(candidates.shape[0]):
        for grid_x in range(candidates.shape[1]):
            if not candidates[grid_y, grid_x]:
                continue

            # Check if this spot has stable slope
            if height_grid[grid_y, grid_x] > 0:
                slope = slope_validator.compute_slope(height_grid, grid_x, grid_y, metadata.cell_size)
                if slope > slope_validator.max_slope:
                    filtered[grid_y, grid_x] = False
                    continue

            # Check if spot has base support
            if not slope_validator.has_base_support(height_grid, grid_x, grid_y, zone_mask):
                filtered[grid_y, grid_x] = False

    return filtered


def _filter_by_accessibility(
    candidates: np.ndarray,
    zone_mask: np.ndarray,
    occupancy_grid: np.ndarray,
    height_grid: np.ndarray,
    metadata: GridMetadata,
    reachability_threshold: float = 0.7,
) -> np.ndarray:
    """Filter candidates that would isolate parts of the zone."""
    filtered = candidates.copy()

    # Find entry point (where trucks enter from outside zone)
    entry_points = []
    for grid_y in range(zone_mask.shape[0]):
        for grid_x in range(zone_mask.shape[1]):
            if not zone_mask[grid_y, grid_x]:
                continue
            # Check if adjacent to non-zone cell
            found_entry = False
            for dy in [-1, 0, 1]:
                for dx in [-1, 0, 1]:
                    ny, nx = grid_y + dy, grid_x + dx
                    if ny < 0 or ny >= zone_mask.shape[0] or nx < 0 or nx >= zone_mask.shape[1]:
                        entry_points.append((grid_x, grid_y))
                        found_entry = True
                        break
                if found_entry:
                    break

    if not entry_points:
        return filtered

    entry = entry_points[0]

    # For each candidate, temporarily mark as filled and check reachability
    free_zone_cells = np.sum(zone_mask & (occupancy_grid == CELL_EMPTY))
    
    # Limit reachability checks to avoid excessive computation
    max_candidates_to_check = 50
    candidate_coords = np.argwhere(candidates)
    if len(candidate_coords) > max_candidates_to_check:
        # Sample candidates to check
        sample_indices = np.random.choice(len(candidate_coords), max_candidates_to_check, replace=False)
        candidate_coords = candidate_coords[sample_indices]

    for grid_y, grid_x in candidate_coords:
        # Simulate dump at this location
        temp_grid = occupancy_grid.copy()
        temp_grid[grid_y, grid_x] = CELL_DUMP_PILE

        # Flood fill from entry point
        reachable = _count_reachable_cells(entry, temp_grid, zone_mask)
        reachable_fraction = reachable / max(free_zone_cells, 1)

        if reachable_fraction < reachability_threshold:
            filtered[grid_y, grid_x] = False

    return filtered


def _count_reachable_cells(
    start: tuple[int, int],
    occupancy_grid: np.ndarray,
    zone_mask: np.ndarray,
    max_cells: int = 100000,
) -> int:
    """Count cells reachable from start via BFS with safety limits."""
    visited = set()
    queue = deque([start])
    count = 0

    while queue and count < max_cells:
        grid_x, grid_y = queue.popleft()

        if (grid_x, grid_y) in visited:
            continue

        if grid_x < 0 or grid_x >= occupancy_grid.shape[1]:
            continue
        if grid_y < 0 or grid_y >= occupancy_grid.shape[0]:
            continue

        if not zone_mask[grid_y, grid_x]:
            continue

        if occupancy_grid[grid_y, grid_x] == CELL_DUMP_PILE:
            continue

        visited.add((grid_x, grid_y))
        count += 1

        # Add neighbors (only add if not already visited to limit queue size)
        for dy in [-1, 0, 1]:
            for dx in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = grid_x + dx, grid_y + dy
                if (nx, ny) not in visited:
                    queue.append((nx, ny))

    return count


def _score_candidates(
    candidates: np.ndarray,
    zone_mask: np.ndarray,
    height_grid: np.ndarray,
    zone_centroid: tuple[float, float],
    truck_position: tuple[float, float],
    slope_validator: SlopeValidator,
    metadata: GridMetadata,
) -> np.ndarray:
    """Score all candidates using slope validator."""
    scores = np.full(candidates.shape, -1.0, dtype=np.float32)

    for grid_y in range(candidates.shape[0]):
        for grid_x in range(candidates.shape[1]):
            if not candidates[grid_y, grid_x]:
                continue

            score = slope_validator.score_dump_spot(
                grid_x,
                grid_y,
                height_grid,
                zone_mask,
                zone_centroid,
                truck_position[0],
                truck_position[1],
                metadata.cell_size,
            )
            scores[grid_y, grid_x] = score

    return scores


def get_zone_cells(
    zone_polygon: Polygon,
    metadata: GridMetadata,
) -> list[tuple[int, int]]:
    """Get all grid cell coordinates inside the zone polygon."""
    zone_cells = []

    for grid_y in range(metadata.grid_height):
        for grid_x in range(metadata.grid_width):
            world_x = metadata.origin_x + grid_x * metadata.cell_size
            world_y = metadata.origin_y + grid_y * metadata.cell_size
            cell_center_x = world_x + metadata.cell_size / 2.0
            cell_center_y = world_y + metadata.cell_size / 2.0

            if zone_polygon.contains(Point(cell_center_x, cell_center_y)):
                zone_cells.append((grid_x, grid_y))

    return zone_cells
