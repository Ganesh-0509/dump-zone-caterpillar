"""Traffic manager to coordinate multi-truck path planning."""

from __future__ import annotations

from shapely.geometry import Point, Polygon


class TrafficManager:
    """Manages grid cell reservations across time steps."""

    def __init__(self) -> None:
        # Dictionary mapping timestep -> { (x, y): truck_id }
        self.reservations: dict[int, dict[tuple[int, int], int]] = {}

    def reserve_path(self, truck_id: int, path: list[tuple[int, int]], start_time: int) -> None:
        """Reserve all cells in the path for future timesteps."""
        for i, cell in enumerate(path):
            t = start_time + i
            if t not in self.reservations:
                self.reservations[t] = {}
            self.reservations[t][cell] = truck_id

    def reserve_footprint_path(
        self,
        truck_id: int,
        path: list[tuple[float, float]],
        start_time: int,
        truck_length: float,
        truck_width: float,
        turning_radius: float,
        cell_size: float,
    ) -> None:
        """Reserve cells based on truck footprint along path.
        
        Args:
            truck_id: ID of truck
            path: List of (x, y) world coordinates
            start_time: Start timestep
            truck_length: Truck length in meters
            truck_width: Truck width in meters
            turning_radius: Truck turning radius in meters
            cell_size: Size of grid cells
        """
        from simulation.truck_agent import Truck
        
        # Create a temporary truck to get footprint polygons at each point
        for i, (world_x, world_y) in enumerate(path):
            t = start_time + i
            if t not in self.reservations:
                self.reservations[t] = {}
            
            # For each step, reserve cells covered by footprint
            # Use simple circular buffer around truck position
            buffer_radius = max(truck_length, truck_width) / 2.0
            buffer_cells = int((buffer_radius / cell_size) + 1)
            
            grid_x = int(world_x / cell_size)
            grid_y = int(world_y / cell_size)
            
            # Reserve all cells within buffer radius
            for dy in range(-buffer_cells, buffer_cells + 1):
                for dx in range(-buffer_cells, buffer_cells + 1):
                    cell = (grid_x + dx, grid_y + dy)
                    # Only reserve if truck_id not already there (avoid overwriting earlier reservations)
                    if cell not in self.reservations[t]:
                        self.reservations[t][cell] = truck_id

    def check_cell_available(self, cell: tuple[int, int], timestep: int) -> bool:
        """Check if the cell is available at the given timestep."""
        if timestep in self.reservations:
            if cell in self.reservations[timestep]:
                return False
        return True

    def check_footprint_available(
        self,
        world_x: float,
        world_y: float,
        timestep: int,
        truck_length: float,
        truck_width: float,
        cell_size: float,
    ) -> bool:
        """Check if truck footprint is available at position and timestep.
        
        Returns False if any cell in footprint is reserved by another truck.
        """
        buffer_radius = max(truck_length, truck_width) / 2.0
        buffer_cells = int((buffer_radius / cell_size) + 1)
        
        grid_x = int(world_x / cell_size)
        grid_y = int(world_y / cell_size)
        
        if timestep in self.reservations:
            for dy in range(-buffer_cells, buffer_cells + 1):
                for dx in range(-buffer_cells, buffer_cells + 1):
                    cell = (grid_x + dx, grid_y + dy)
                    if cell in self.reservations[timestep]:
                        return False
        return True

    def release_reservations(self, truck_id: int) -> None:
        """Remove all reservations for a specific truck."""
        empty_times = []
        for t, cells in self.reservations.items():
            # Find cells reserved by this truck
            to_remove = [c for c, tid in cells.items() if tid == truck_id]
            for c in to_remove:
                del cells[c]
            if not cells:
                empty_times.append(t)
                
        for t in empty_times:
            del self.reservations[t]
