"""Spatial index to accelerate neighbor queries for trucks."""

from __future__ import annotations

class SpatialIndex:
    """Manages a spatial index for fast proximity queries."""

    def __init__(self) -> None:
        # Dictionary mapping (x, y) -> list of truck_ids
        self.cell_index: dict[tuple[int, int], list[int]] = {}

    def add_truck(self, truck_id: int, cell: tuple[int, int]) -> None:
        """Adds a truck to the spatial index."""
        if cell not in self.cell_index:
            self.cell_index[cell] = []
        if truck_id not in self.cell_index[cell]:
            self.cell_index[cell].append(truck_id)

    def remove_truck(self, truck_id: int, cell: tuple[int, int]) -> None:
        """Removes a truck from the spatial index at the given cell."""
        if cell in self.cell_index:
            if truck_id in self.cell_index[cell]:
                self.cell_index[cell].remove(truck_id)
            if not self.cell_index[cell]:
                del self.cell_index[cell]

    def update_truck(self, truck_id: int, old_cell: tuple[int, int], new_cell: tuple[int, int]) -> None:
        """Moves a truck between cells in the index."""
        if old_cell != new_cell:
            self.remove_truck(truck_id, old_cell)
            self.add_truck(truck_id, new_cell)

    def get_nearby_trucks(self, cell: tuple[int, int]) -> list[int]:
        """Returns trucks in the cell and its 8 neighboring cells."""
        cx, cy = cell
        nearby_trucks = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor = (cx + dx, cy + dy)
                if neighbor in self.cell_index:
                    nearby_trucks.extend(self.cell_index[neighbor])
        return nearby_trucks
