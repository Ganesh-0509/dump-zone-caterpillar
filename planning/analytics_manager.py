"""Analytics manager for tracking simulation performance metrics."""

from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon, Point

from simulation.truck_agent import TruckState
from mapping.occupancy_grid import CELL_DUMP_PILE, GridMetadata


class AnalyticsManager:
    """Tracks key performance metrics during the simulation."""

    def __init__(self) -> None:
        self.total_payload_dumped = 0.0
        self.spawn_times: dict[int, int] = {}
        self.cycle_times: list[int] = []

        self.current_step = 1
        self.packing_density = 0.0
        self.fleet_utilization = 0.0
        self.dump_throughput = 0.0
        self.total_dumps = 0
        self.zone_utilization: dict[int, float] = {}

        # Slope and layering metrics
        self.pile_slopes: list[float] = []
        self.max_pile_height = 0.0
        self.average_pile_slope = 0.0
        self.layer_growth_events = 0

        # Cached masks for fast computations
        self.zone_masks: dict[int, np.ndarray] = {}
        self.zone_total_cells: dict[int, int] = {}

    def record_truck_spawn(self, truck_id: int, step: int) -> None:
        """Called when a truck is spawned."""
        self.spawn_times[truck_id] = step

    def record_dump(self, truck_id: int, zone_id: int, payload: float, step: int) -> None:
        """Called when a truck dumps material."""
        self.total_payload_dumped += payload
        self.total_dumps += 1

    def record_truck_return(self, truck_id: int, step: int) -> None:
        """Called when a truck returns to entrance."""
        if truck_id in self.spawn_times:
            cycle_time = step - self.spawn_times[truck_id]
            self.cycle_times.append(cycle_time)
            # Remove to track strictly per-cycle metrics if trucks are reused
            del self.spawn_times[truck_id]

    def _initialize_masks(self, occupancy_grid: np.ndarray, zones: list[Polygon], metadata: GridMetadata) -> None:
        """Precomputes boolean array masks representing zone spatial bounds."""
        height, width = occupancy_grid.shape

        for i, zone in enumerate(zones):
            mask = np.zeros((height, width), dtype=bool)
            minx, miny, maxx, maxy = zone.bounds
            
            min_gx = int((minx - metadata.origin_x) / metadata.cell_size) - 1
            max_gx = int((maxx - metadata.origin_x) / metadata.cell_size) + 1
            min_gy = int((miny - metadata.origin_y) / metadata.cell_size) - 1
            max_gy = int((maxy - metadata.origin_y) / metadata.cell_size) + 1

            min_gx, max_gx = max(0, min_gx), min(width - 1, max_gx)
            min_gy, max_gy = max(0, min_gy), min(height - 1, max_gy)

            for y in range(min_gy, max_gy + 1):
                for x in range(min_gx, max_gx + 1):
                    wx = metadata.origin_x + x * metadata.cell_size
                    wy = metadata.origin_y + y * metadata.cell_size
                    if zone.contains(Point(wx, wy)):
                        mask[y, x] = True

            self.zone_masks[i] = mask
            self.zone_total_cells[i] = np.count_nonzero(mask)

    def update_metrics(self, occupancy_grid: np.ndarray, zones: list[Polygon], trucks: list, metadata: GridMetadata, step: int) -> None:
        """Updates packing density, zone utilization, throughput, and fleet utilization."""
        self.current_step = max(1, step)

        if not self.zone_masks:
            self._initialize_masks(occupancy_grid, zones, metadata)

        # Packing Density
        total_valid_cells = np.count_nonzero(occupancy_grid >= 0)
        dump_cells = np.count_nonzero(occupancy_grid == CELL_DUMP_PILE)
        self.packing_density = dump_cells / total_valid_cells if total_valid_cells > 0 else 0.0

        # Zone Utilization
        for i, _ in enumerate(zones):
            if self.zone_total_cells[i] > 0:
                zone_dump = np.count_nonzero((occupancy_grid == CELL_DUMP_PILE) & self.zone_masks[i])
                self.zone_utilization[i] = zone_dump / self.zone_total_cells[i]
            else:
                self.zone_utilization[i] = 0.0

        # Fleet Utilization
        if trucks:
            active_states = {TruckState.MOVING_TO_ZONE, TruckState.DUMPING, TruckState.RETURNING}
            active_trucks = sum(1 for t in trucks if t.state in active_states)
            self.fleet_utilization = active_trucks / len(trucks)
        else:
            self.fleet_utilization = 0.0

        # Dump Throughput
        self.dump_throughput = self.total_payload_dumped / self.current_step

    def record_layer_growth(self, avg_slope: float, max_height: float) -> None:
        """Record statistics after a dump operation."""
        self.pile_slopes.append(avg_slope)
        self.max_pile_height = max(self.max_pile_height, max_height)
        self.layer_growth_events += 1
        
        if self.pile_slopes:
            self.average_pile_slope = sum(self.pile_slopes) / len(self.pile_slopes)

    def get_summary(self) -> dict:
        """Returns a dictionary containing the tracked metrics."""
        avg_cycle_time = sum(self.cycle_times) / len(self.cycle_times) if self.cycle_times else 0.0
        return {
            "packing_density": self.packing_density,
            "average_cycle_time": avg_cycle_time,
            "fleet_utilization": self.fleet_utilization,
            "dump_throughput": self.dump_throughput,
            "total_dumps": self.total_dumps,
            "zone_utilization": self.zone_utilization.copy(),
            "average_pile_slope": self.average_pile_slope,
            "max_pile_height": self.max_pile_height,
            "layer_growth_events": self.layer_growth_events,
        }
