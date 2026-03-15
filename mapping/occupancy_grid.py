"""Create and manage occupancy grids from dump polygons."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from shapely.geometry import Point, Polygon


# Cell state constants
CELL_EMPTY = 0
CELL_DUMP_PILE = 1
CELL_TRUCK = 2
CELL_INVALID = -1


@dataclass(frozen=True)
class GridConfig:
    """Configuration for occupancy grid."""

    cell_size: float = 1.0


@dataclass(frozen=True)
class GridMetadata:
    """Metadata about a grid."""

    polygon_bounds: tuple[float, float, float, float]
    cell_size: float
    grid_width: int
    grid_height: int
    origin_x: float
    origin_y: float


def create_grid_from_polygon(polygon: Polygon, cell_size: float = 1.0) -> tuple[np.ndarray, GridMetadata]:
    """Create occupancy grid from polygon with cells marked valid/invalid."""
    if cell_size <= 0:
        raise ValueError("cell_size must be positive.")

    min_x, min_y, max_x, max_y = polygon.bounds

    width = int(np.ceil((max_x - min_x) / cell_size))
    height = int(np.ceil((max_y - min_y) / cell_size))

    if width <= 0 or height <= 0:
        raise ValueError("Grid dimensions must be at least 1x1.")

    grid = np.full((height, width), CELL_INVALID, dtype=np.int8)

    for grid_y in range(height):
        for grid_x in range(width):
            world_x, world_y = grid_to_world(grid_x, grid_y, min_x, min_y, cell_size)
            cell_x_center = world_x + cell_size / 2.0
            cell_y_center = world_y + cell_size / 2.0

            if polygon.contains(Point(cell_x_center, cell_y_center)):
                grid[grid_y, grid_x] = CELL_EMPTY

    metadata = GridMetadata(
        polygon_bounds=(min_x, min_y, max_x, max_y),
        cell_size=cell_size,
        grid_width=width,
        grid_height=height,
        origin_x=min_x,
        origin_y=min_y,
    )

    return grid, metadata


def is_valid_cell(grid_x: int, grid_y: int, metadata: GridMetadata) -> bool:
    """Check if a grid coordinate is within bounds and valid."""
    if grid_x < 0 or grid_x >= metadata.grid_width:
        return False
    if grid_y < 0 or grid_y >= metadata.grid_height:
        return False
    return True


def grid_to_world(
    grid_x: int,
    grid_y: int,
    origin_x: float,
    origin_y: float,
    cell_size: float,
) -> tuple[float, float]:
    """Convert grid indices to world coordinates (bottom-left corner of cell)."""
    world_x = origin_x + grid_x * cell_size
    world_y = origin_y + grid_y * cell_size
    return world_x, world_y


def world_to_grid(
    world_x: float,
    world_y: float,
    origin_x: float,
    origin_y: float,
    cell_size: float,
) -> tuple[int, int]:
    """Convert world coordinates to grid indices."""
    grid_x = int(np.floor((world_x - origin_x) / cell_size))
    grid_y = int(np.floor((world_y - origin_y) / cell_size))
    return grid_x, grid_y
