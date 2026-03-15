"""Initialize and manage terrain height maps for dump operations."""

from __future__ import annotations

import numpy as np

from mapping.occupancy_grid import GridMetadata


def initialize_height_map(grid_shape: tuple[int, int]) -> np.ndarray:
    """Initialize height map with all cells at zero elevation."""
    height, width = grid_shape
    if height <= 0 or width <= 0:
        raise ValueError("Grid shape dimensions must be positive.")

    return np.zeros((height, width), dtype=np.float32)


def add_dump(
    height_map: np.ndarray,
    grid_x: int,
    grid_y: int,
    dump_height: float,
    metadata: GridMetadata,
) -> None:
    """Add material (increase height) at a grid cell.
    
    Modifies height_map in-place.
    """
    if dump_height < 0:
        raise ValueError("dump_height must be non-negative.")

    if not (0 <= grid_x < metadata.grid_width and 0 <= grid_y < metadata.grid_height):
        raise IndexError(f"Grid indices ({grid_x}, {grid_y}) out of bounds.")

    height_map[grid_y, grid_x] += dump_height


def get_height(
    height_map: np.ndarray,
    grid_x: int,
    grid_y: int,
    metadata: GridMetadata,
) -> float:
    """Query height at a grid cell."""
    if not (0 <= grid_x < metadata.grid_width and 0 <= grid_y < metadata.grid_height):
        raise IndexError(f"Grid indices ({grid_x}, {grid_y}) out of bounds.")

    return float(height_map[grid_y, grid_x])
