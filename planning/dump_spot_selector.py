"""Select optimal dump locations within zones using distance transforms."""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt
from shapely.geometry import Point, Polygon

from mapping.occupancy_grid import GridMetadata, CELL_EMPTY, CELL_INVALID, CELL_DUMP_PILE


def select_dump_spot(
    zone_polygon: Polygon,
    occupancy_grid: np.ndarray,
    metadata: GridMetadata,
) -> tuple[int, int]:
    """Select the optimal dump cell within a zone using distance transform.
    
    Returns grid coordinates (grid_x, grid_y) of the best dump location.
    
    Algorithm:
    1. Find all grid cells inside zone polygon
    2. Filter cells that are valid and empty
    3. Build binary free-space mask
    4. Compute Euclidean distance transform
    5. Return cell with maximum distance (maximum clearance)
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

    # Create free-space mask (valid, empty, inside zone)
    free_space = np.zeros((metadata.grid_height, metadata.grid_width), dtype=np.bool_)

    for grid_y in range(metadata.grid_height):
        for grid_x in range(metadata.grid_width):
            cell_state = occupancy_grid[grid_y, grid_x]
            is_in_zone = zone_mask[grid_y, grid_x]
            is_valid = cell_state != CELL_INVALID
            is_empty = cell_state == CELL_EMPTY

            if is_in_zone and is_valid and is_empty:
                free_space[grid_y, grid_x] = True

    # Check if any free space exists
    if not np.any(free_space):
        # Fallback: find any valid cell in zone
        zone_valid = zone_mask & (occupancy_grid != CELL_INVALID)
        if np.any(zone_valid):
            coords = np.argwhere(zone_valid)
            idx = np.random.choice(len(coords))
            grid_y, grid_x = coords[idx]
            return grid_x, grid_y
        raise ValueError("No valid cells found in zone.")

    # Compute distance transform
    distance_map = distance_transform_edt(free_space)

    # Find cell with maximum distance
    best_idx = np.argmax(distance_map)
    best_grid_y, best_grid_x = np.unravel_index(best_idx, distance_map.shape)

    return best_grid_x, best_grid_y


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
