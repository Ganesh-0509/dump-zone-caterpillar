"""Traffic manager to coordinate multi-truck path planning."""

from __future__ import annotations


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

    def check_cell_available(self, cell: tuple[int, int], timestep: int) -> bool:
        """Check if the cell is available at the given timestep."""
        if timestep in self.reservations:
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
