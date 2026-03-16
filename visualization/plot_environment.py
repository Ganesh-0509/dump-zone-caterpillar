"""Visualize the dump polygon, zones, occupancy grid, and trucks."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon, Rectangle
from shapely.geometry import Polygon

from mapping.occupancy_grid import GridMetadata, CELL_EMPTY, CELL_INVALID, CELL_DUMP_PILE, grid_to_world

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

            if cell_state == CELL_DUMP_PILE:
                rect_color = "darkred"
                alpha = 0.7
            elif cell_state == CELL_EMPTY:
                rect_color = "lightgray"
                alpha = 0.4
            else:
                rect_color = "gray"
                alpha = 0.3

            rect = Rectangle(
                (world_x, world_y),
                metadata.cell_size,
                metadata.cell_size,
                facecolor=rect_color,
                edgecolor="gray",
                linewidth=0.3,
                alpha=alpha,
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
    height_map: np.ndarray | None = None,
    step: int = 0,
    block: bool = True,
    analytics_summary: dict | None = None,
) -> None:
    """Plot simulation state including trucks."""
    # To support animation, we use the current figure and axis
    fig = plt.gcf()
    fig.set_size_inches(13, 9)
    axis = plt.gca()
    
    # We MUST clear the axis completely, otherwise adding thousands of overlapping 
    # patches over multiple frames causes matplotlib to crash or hang
    axis.clear()

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
        
        # Zone utilization label
        if analytics_summary and "zone_utilization" in analytics_summary:
            utilization = analytics_summary["zone_utilization"].get(index, 0.0)
            centroid = zone.centroid
            axis.text(
                centroid.x,
                centroid.y,
                f"Zone {index + 1}\n{utilization * 100:.0f}% full",
                ha="center",
                va="center",
                fontsize=8,
                color="black",
                bbox=dict(facecolor="white", alpha=0.6, edgecolor="none", pad=1),
                zorder=10
            )

    # Plot grid
    for grid_y in range(metadata.grid_height):
        for grid_x in range(metadata.grid_width):
            cell_state = occupancy_grid[grid_y, grid_x]

            if cell_state == CELL_INVALID:
                continue

            world_x = metadata.origin_x + grid_x * metadata.cell_size
            world_y = metadata.origin_y + grid_y * metadata.cell_size

            if cell_state == CELL_DUMP_PILE:
                rect_color = "darkred"
                alpha = 0.7
            elif cell_state == CELL_EMPTY:
                rect_color = "lightgray"
                alpha = 0.2
            else:
                rect_color = "gray"
                alpha = 0.3

            rect = Rectangle(
                (world_x, world_y),
                metadata.cell_size,
                metadata.cell_size,
                facecolor=rect_color,
                edgecolor="gray",
                linewidth=0.2,
                alpha=alpha,
            )
            axis.add_patch(rect)

    # Plot dump height heatmap
    if height_map is not None:
        heatmap_data = np.ma.masked_where(height_map == 0, height_map)
        min_x = metadata.origin_x
        max_x = metadata.origin_x + metadata.grid_width * metadata.cell_size
        min_y = metadata.origin_y
        max_y = metadata.origin_y + metadata.grid_height * metadata.cell_size
        axis.imshow(
            heatmap_data,
            extent=[min_x, max_x, min_y, max_y],
            origin="lower",
            cmap="hot",
            alpha=0.4,
            zorder=3,
        )

    # Plot boundary
    boundary_x, boundary_y = dump_polygon.exterior.xy
    axis.plot(boundary_x, boundary_y, color="black", linewidth=2.5, label="Dump Boundary")

    # Plot trucks
    if trucks:
        truck_x = [t.position_x for t in trucks]
        truck_y = [t.position_y for t in trucks]
        axis.scatter(truck_x, truck_y, color="red", s=100, marker="o", label="Trucks", zorder=5)

        # Label trucks and draw paths
        for truck in trucks:
            axis.annotate(
                f"T{truck.truck_id}",
                xy=(truck.position_x, truck.position_y),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=7,
                alpha=0.7,
            )
            
            # Draw path
            if getattr(truck, "smoothed_path", None) and getattr(truck, "current_smoothed_index", 0) < len(truck.smoothed_path):
                path_world_coords = [(truck.position_x, truck.position_y)]
                for wx, wy in truck.smoothed_path[truck.current_smoothed_index:]:
                    path_world_coords.append((wx, wy))
                if len(path_world_coords) > 1:
                    px, py = zip(*path_world_coords)
                    axis.plot(px, py, color="red", linestyle="-", linewidth=1.5, alpha=0.8, zorder=4)
            elif getattr(truck, "path", None) and truck.current_path_index < len(truck.path):
                # Fallback to grid path
                path_world_coords = [(truck.position_x, truck.position_y)]
                for node in truck.path[truck.current_path_index:]:
                    grid_x, grid_y = node[0], node[1]
                    wx, wy = grid_to_world(grid_x, grid_y, metadata.origin_x, metadata.origin_y, metadata.cell_size)
                    path_world_coords.append((wx + metadata.cell_size / 2, wy + metadata.cell_size / 2))
                
                if len(path_world_coords) > 1:
                    px, py = zip(*path_world_coords)
                    axis.plot(px, py, color="red", linestyle="--", linewidth=1.0, alpha=0.6, zorder=4)

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

    # Add statistics panel
    if analytics_summary:
        stats_text = (
            f"Packing Density: {analytics_summary.get('packing_density', 0.0):.2f}\n"
            f"Average Cycle Time: {analytics_summary.get('average_cycle_time', 0.0):.1f}\n"
            f"Fleet Utilization: {analytics_summary.get('fleet_utilization', 0.0):.2f}\n"
            f"Total Dumps: {analytics_summary.get('total_dumps', 0)}"
        )
        axis.text(
            0.02, 0.98,
            stats_text,
            transform=axis.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
        )

    plt.tight_layout()
    if block:
        plt.show()
