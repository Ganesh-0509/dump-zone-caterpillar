"""A* Path planning on occupancy grids."""

from __future__ import annotations

import heapq

from typing import TYPE_CHECKING

import numpy as np

from mapping.occupancy_grid import CELL_EMPTY

if TYPE_CHECKING:
    from planning.traffic_manager import TrafficManager


def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Calculate Euclidean distance heuristic for A*."""
    # (dx**2 + dy**2)**0.5
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def get_neighbors(
    grid_x: int,
    grid_y: int,
    grid_width: int,
    grid_height: int,
    occupancy_grid: np.ndarray,
    timestep: int,
    traffic_manager: TrafficManager | None = None,
) -> list[tuple[int, int]]:
    """Get valid 8-connected neighbors."""
    neighbors = []
    directions = [
        (0, 1), (1, 0), (0, -1), (-1, 0),  # Cardinal directions
        (-1, -1), (1, 1), (-1, 1), (1, -1) # Diagonal directions
    ]
    
    for dx, dy in directions:
        nx, ny = grid_x + dx, grid_y + dy
        
        # Check bounds
        if 0 <= nx < grid_width and 0 <= ny < grid_height:
            # Check obstacles (must be CELL_EMPTY to traverse)
            # Currently ignoring CELL_TRUCK for simplicity, but strictly avoiding Piles/Invalid
            if occupancy_grid[ny, nx] == CELL_EMPTY:
                # Check traffic manager reservation
                if traffic_manager is None or traffic_manager.check_cell_available((nx, ny), timestep + 1):
                    neighbors.append((nx, ny))
                
    # We can also add an option to wait in place if that's valid, but omitting for simplicity here.
    return neighbors


def plan_path(
    start_cell: tuple[int, int],
    goal_cell: tuple[int, int],
    occupancy_grid: np.ndarray,
    start_time: int = 0,
    traffic_manager: TrafficManager | None = None,
) -> list[tuple[int, int]]:
    """Find shortest path from start_cell to goal_cell using A*.
    
    Returns a list of (x, y) grid coordinates. Returns empty list if no path found.
    """
    if start_cell == goal_cell:
        return [start_cell]
        
    grid_height, grid_width = occupancy_grid.shape
    
    # Priority queue: (f_score, counter, (x, y, timestep))
    # counter is used to break ties when f_scores are equal
    open_set = []
    counter = 0
    start_node = (start_cell[0], start_cell[1], start_time)
    heapq.heappush(open_set, (0, counter, start_node))
    
    # Keep track of where we came from
    came_from = {}
    
    # Cost from start to node 
    g_score = {start_node: 0.0}
    
    # Estimated total cost from start to goal through node
    f_score = {start_node: heuristic(start_cell, goal_cell)}
    
    # Keep track of nodes in open_set for faster lookup
    open_set_hash = {start_node}
    
    # Fallback / limit to prevent infinite search on unreachable goals
    max_iterations = 5000
    iterations = 0
    
    while open_set and iterations < max_iterations:
        iterations += 1
        current_node = heapq.heappop(open_set)[2]
        open_set_hash.remove(current_node)
        
        current_cell = (current_node[0], current_node[1])
        current_t = current_node[2]
        
        if current_cell == goal_cell:
            # Reconstruct path
            path = []
            curr = current_node
            while curr in came_from:
                path.append((curr[0], curr[1]))
                curr = came_from[curr]
            path.append((start_node[0], start_node[1]))
            return path[::-1]  # Reverse to get start -> goal
            
        current_g = g_score[current_node]
        
        for neighbor_cell in get_neighbors(current_cell[0], current_cell[1], grid_width, grid_height, occupancy_grid, current_t, traffic_manager):
            neighbor_t = current_t + 1
            neighbor_node = (neighbor_cell[0], neighbor_cell[1], neighbor_t)
            
            # Cost is 1 for cardinal, 1.414 for diagonal
            dx = neighbor_cell[0] - current_cell[0]
            dy = neighbor_cell[1] - current_cell[1]
            step_cost = 1.0 if dx == 0 or dy == 0 else 1.41421356
            
            tentative_g_score = current_g + step_cost
            
            if neighbor_node not in g_score or tentative_g_score < g_score[neighbor_node]:
                # This path is better than any previous one
                came_from[neighbor_node] = current_node
                g_score[neighbor_node] = tentative_g_score
                
                h = heuristic(neighbor_cell, goal_cell)
                f_score[neighbor_node] = tentative_g_score + h
                
                if neighbor_node not in open_set_hash:
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor_node], counter, neighbor_node))
                    open_set_hash.add(neighbor_node)
                    
    # No path found
    return []
