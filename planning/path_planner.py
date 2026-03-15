"""A* Path planning on occupancy grids."""

from __future__ import annotations

import heapq

import numpy as np

from mapping.occupancy_grid import CELL_EMPTY


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
                neighbors.append((nx, ny))
                
    return neighbors


def plan_path(
    start_cell: tuple[int, int],
    goal_cell: tuple[int, int],
    occupancy_grid: np.ndarray,
) -> list[tuple[int, int]]:
    """Find shortest path from start_cell to goal_cell using A*.
    
    Returns a list of (x, y) grid coordinates. Returns empty list if no path found.
    """
    if start_cell == goal_cell:
        return [start_cell]
        
    grid_height, grid_width = occupancy_grid.shape
    
    # Priority queue: (f_score, counter, (x, y))
    # counter is used to break ties when f_scores are equal
    open_set = []
    counter = 0
    heapq.heappush(open_set, (0, counter, start_cell))
    
    # Keep track of where we came from
    came_from = {}
    
    # Cost from start to node 
    g_score = {start_cell: 0.0}
    
    # Estimated total cost from start to goal through node
    f_score = {start_cell: heuristic(start_cell, goal_cell)}
    
    # Keep track of nodes in open_set for faster lookup
    open_set_hash = {start_cell}
    
    while open_set:
        current = heapq.heappop(open_set)[2]
        open_set_hash.remove(current)
        
        if current == goal_cell:
            # Reconstruct path
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start_cell)
            return path[::-1]  # Reverse to get start -> goal
            
        current_g = g_score[current]
        
        for neighbor in get_neighbors(current[0], current[1], grid_width, grid_height, occupancy_grid):
            # Cost is 1 for cardinal, 1.414 for diagonal
            dx = neighbor[0] - current[0]
            dy = neighbor[1] - current[1]
            step_cost = 1.0 if dx == 0 or dy == 0 else 1.41421356
            
            tentative_g_score = current_g + step_cost
            
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                # This path is better than any previous one
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                
                # We want to give a slight penalty to turns:
                # But since true turning penalty requires tracking previous direction,
                # Euclidean distance naturally looks pretty good
                h = heuristic(neighbor, goal_cell)
                f_score[neighbor] = tentative_g_score + h
                
                if neighbor not in open_set_hash:
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                    open_set_hash.add(neighbor)
                    
    # No path found
    return []
