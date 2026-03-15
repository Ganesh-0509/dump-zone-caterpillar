"""Visualize the dump polygon, zones, occupancy grid, and trucks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Rectangle
from shapely.geometry import Polygon

from mapping.occupancy_grid import GridMetadata, CELL_EMPTY, CELL_INVALID

if TYPE_CHECKING:
    from simulation.truck_agent import Truck


def plot_dump_environment(dump_polygon: Polygon, zones: list[Polygon]) -> None:
    """Plot dump boundary and Voronoi zones using matplotlib."""
    fig, axis = plt.subplots(figsize=(10, 7))

    colormap = plt.get_cmap("tab20")

    for index, zone in enumerate(zones):
        x_coords, y_coords = zone.exterior.xy
        patch = MplPolygon(
            list(zip(x_coords, y_coords)),
            closed=True,
            facecolor=colormap(index % 20),
            alpha=0.45,
            edgecolor="black",
            linewidth=1.0,
            label=f"Zone {index + 1}",
        )
        axis.add_patch(patch)

    boundary_x, boundary_y = dump_polygon.exterior.xy
    axis.plot(boundary_x, boundary_y, color="black", linewidth=2.5, label="Dump Boundary")

    min_x, min_y, max_x, max_y = dump_polygon.bounds
    pad_x = (max_x - min_x) * 0.08
    pad_y = (max_y - min_y) * 0.08

    axis.set_xlim(min_x - pad_x, max_x + pad_x)
    axis.set_ylim(min_y - pad_y, max_y + pad_y)
    axis.set_aspect("equal", adjustable="box")

    axis.set_title("Autonomous Dump Zone Geometry")
    axis.set_xlabel("X Coordinate")
    axis.set_ylabel("Y Coordinate")
    axis.grid(True, alpha=0.25)

    handles, labels = axis.get_legend_handles_labels()
    if handles:
        axis.legend(loc="upper right", fontsize=8, ncol=2)

    plt.tight_layout()
    plt.show()


def plot_grid_environment(
    dump_polygon: Polygon,
    zones: list[Polygon],
    occupancy_grid: np.ndarray,
    metadata: GridMetadata,
) -> None:
    """Plot dump environment with zones and occupancy grid overlay."""
    fig, axis = plt.subplots(figsize=(12, 8))

    colormap = plt.get_cmap("tab20")

    for index, zone in enumerate(zones):
        x_coords, y_coords = zone.exterior.xy
        patch = MplPolygon(
            list(zip(x_coords, y_coords)),
            closed=True,
            facecolor=colormap(index % 20),
            alpha=0.25,
            edgecolor="black",
            linewidth=0.75,
        )
        axis.add_patch(patch)

    for grid_y in range(metadata.grid_height):
        for grid_x in range(metadata.grid_width):
            cell_state = occupancy_grid[grid_y, grid_x]

            if cell_state == CELL_INVALID:
                continue

            world_x = metadata.origin_x + grid_x * metadata.cell_size
            world_y = metadata.origin_y + grid_y * metadata.cell_size

            rect_color = "lightgray" if cell_state == CELL_EMPTY else "red"
            rect = Rectangle(
                (world_x, world_y),
                metadata.cell_size,
                metadata.cell_size,
                facecolor=rect_color,
                edgecolor="gray",
                linewidth=0.3,
                alpha=0.4,
            )
            axis.add_patch(rect)

    boundary_x, boundary_y = dump_polygon.exterior.xy
    axis.plot(boundary_x, boundary_y, color="black", linewidth=2.5, label="Dump Boundary")

    min_x, min_y, max_x, max_y = dump_polygon.bounds
    pad_x = (max_x - min_x) * 0.08
    pad_y = (max_y - min_y) * 0.08

    axis.set_xlim(min_x - pad_x, max_x + pad_x)
    axis.set_ylim(min_y - pad_y, max_y + pad_y)
    axis.set_aspect("equal", adjustable="box")

    axis.set_title("Autonomous Dump Zone with Occupancy Grid")
    axis.set_xlabel("X Coordinate")
    axis.set_ylabel("Y Coordinate")
    axis.grid(True, alpha=0.15)
    axis.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    plt.show()


def plot_simulation_state(
    dump_polygon: Polygon,
    zones: list[Polygon],
    occupancy_grid: np.ndarray,
    metadata: GridMetadata,
    trucks: list[Truck],
    step: int = 0,
) -> None:
    """Plot simulation state including trucks."""
    fig, axis = plt.subplots(figsize=(13, 9))

    colormap = plt.get_cmap("tab20")

    # Plot zones
    for index, zone in enumerate(zones):
        x_coords, y_coords = zone.exterior.xy
        patch = MplPolygon(
            list(zip(x_coords, y_coords)),
            closed=True,
            facecolor=colormap(index % 20),
            alpha=0.15,
            edgecolor="black",
            linewidth=0.75,
        )
        axis.add_patch(patch)

    # Plot grid
    for grid_y in range(metadata.grid_height):
        for grid_x in range(metadata.grid_width):
            cell_state = occupancy_grid[grid_y, grid_x]

            if cell_state == CELL_INVALID:
                continue

            world_x = metadata.origin_x + grid_x * metadata.cell_size
            world_y = metadata.origin_y + grid_y * metadata.cell_size

            rect_color = "lightgray" if cell_state == CELL_EMPTY else "red"
            rect = Rectangle(
                (world_x, world_y),
                metadata.cell_size,
                metadata.cell_size,
                facecolor=rect_color,
                edgecolor="gray",
                linewidth=0.2,
                alpha=0.2,
            )
            axis.add_patch(rect)

    # Plot boundary
    boundary_x, boundary_y = dump_polygon.exterior.xy
    axis.plot(boundary_x, boundary_y, color="black", linewidth=2.5, label="Dump Boundary")

    # Plot trucks
    if trucks:
        truck_x = [t.position_x for t in trucks]
        truck_y = [t.position_y for t in trucks]
        axis.scatter(truck_x, truck_y, color="red", s=100, marker="o", label="Trucks", zorder=5)

        # Label trucks
        for truck in trucks:
            axis.annotate(
                f"T{truck.truck_id}",
                xy=(truck.position_x, truck.position_y),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=7,
                alpha=0.7,
            )

    min_x, min_y, max_x, max_y = dump_polygon.bounds
    pad_x = (max_x - min_x) * 0.08
    pad_y = (max_y - min_y) * 0.08

    axis.set_xlim(min_x - pad_x, max_x + pad_x)
    axis.set_ylim(min_y - pad_y, max_y + pad_y)
    axis.set_aspect("equal", adjustable="box")

    truck_count = len(trucks)
    axis.set_title(f"Autonomous Dump Simulation - Step {step} ({truck_count} trucks)")
    axis.set_xlabel("X Coordinate")
    axis.set_ylabel("Y Coordinate")
    axis.grid(True, alpha=0.15)
    axis.legend(loc="upper right", fontsize=10)

    plt.tight_layout()
    plt.show()
