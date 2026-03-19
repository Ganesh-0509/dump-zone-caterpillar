"""Grid-based dump allocation system for organized zone filling."""

import numpy as np
from shapely.geometry import Polygon, Point, box
from mapping.occupancy_grid import world_to_grid, grid_to_world


class ZoneGridCell:
    """Represents a 3m x 3m grid cell within a zone."""
    
    def __init__(self, grid_x: int, grid_y: int, world_x: float, world_y: float, 
                 cell_size: float = 3.0):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.world_x = world_x  # Center of cell
        self.world_y = world_y
        self.cell_size = cell_size
        self.filled = False  # 0 = empty, 1 = filled
        self.dump_count = 0
        
    def get_bounds(self) -> tuple[float, float, float, float]:
        """Get (min_x, min_y, max_x, max_y) bounds of cell."""
        half = self.cell_size / 2
        return (
            self.world_x - half,
            self.world_y - half,
            self.world_x + half,
            self.world_y + half,
        )
        
    def __repr__(self):
        return f"Cell({self.grid_x},{self.grid_y})={'F' if self.filled else 'E'}"


class ZoneGridManager:
    """Manages 3m grid allocation for each zone."""
    
    GRID_CELL_SIZE = 3.0  # meters
    
    def __init__(self, zones: list[Polygon]):
        """Initialize grid system for all zones."""
        self.zones = zones
        self.zone_grids: dict[int, dict] = {}  # zone_id -> grid info
        self.zone_distance_cache: dict[int, float] = {}  # zone_id -> distance from entry
        self._initialize_grids()
        
    def _initialize_grids(self):
        """Create 3m grids for each zone."""
        for zone_id, zone in enumerate(self.zones):
            min_x, min_y, max_x, max_y = zone.bounds
            width = max_x - min_x
            height = max_y - min_y
            
            # Calculate grid dimensions
            grid_cols = max(1, int(np.ceil(width / self.GRID_CELL_SIZE)))
            grid_rows = max(1, int(np.ceil(height / self.GRID_CELL_SIZE)))
            
            # Create grid cells
            cells = {}
            for row in range(grid_rows):
                for col in range(grid_cols):
                    # Cell center in world coordinates
                    cell_x = min_x + (col + 0.5) * self.GRID_CELL_SIZE
                    cell_y = min_y + (row + 0.5) * self.GRID_CELL_SIZE
                    
                    # Only create cell if it's within the zone
                    if zone.contains(Point(cell_x, cell_y)):
                        cell = ZoneGridCell(col, row, cell_x, cell_y, self.GRID_CELL_SIZE)
                        cells[(col, row)] = cell
            
            print(f"[GRID] Zone {zone_id}: {len(cells)} cells created (grid {grid_cols}x{grid_rows}, bounds {min_x:.1f}-{max_x:.1f}, {min_y:.1f}-{max_y:.1f})")
            
            self.zone_grids[zone_id] = {
                'zone': zone,
                'bounds': zone.bounds,
                'cells': cells,
                'grid_rows': grid_rows,
                'grid_cols': grid_cols,
            }
    
    def set_zone_distances(self, entry_x: float, entry_y: float):
        """Calculate distance from entry point to each zone centroid."""
        entry_point = Point(entry_x, entry_y)
        for zone_id, zone in enumerate(self.zones):
            centroid = zone.centroid
            distance = entry_point.distance(centroid)
            self.zone_distance_cache[zone_id] = distance
    
    def get_zone_priority_order(self) -> list[int]:
        """Return zone IDs sorted by distance (farthest first)."""
        if not self.zone_distance_cache:
            # If distances not set, sort by centroid y coordinate (top = far)
            return sorted(range(len(self.zones)), 
                        key=lambda i: -self.zones[i].centroid.y)
        
        return sorted(range(len(self.zones)), 
                     key=lambda i: -self.zone_distance_cache.get(i, 0))
    
    def get_next_dump_location(self, zone_id: int) -> tuple[float, float] | None:
        """Get next available dump location in zone (farthest empty cell)."""
        if zone_id not in self.zone_grids:
            return None
        
        grid_info = self.zone_grids[zone_id]
        cells = grid_info['cells']
        
        # Find empty cells
        empty_cells = [cell for cell in cells.values() if not cell.filled]
        
        if not empty_cells:
            return None  # Zone is full
        
        # Sort by distance from zone centroid (prefer edges, corners first)
        zone_centroid = grid_info['zone'].centroid
        empty_cells.sort(
            key=lambda c: -(
                (c.world_x - zone_centroid.x)**2 + 
                (c.world_y - zone_centroid.y)**2
            )
        )
        
        # Return farthest empty cell (edges first)
        selected = empty_cells[0]
        return selected.world_x, selected.world_y
    
    def mark_cell_filled(self, zone_id: int, world_x: float, world_y: float):
        """Mark a grid cell as filled after truck dumps there."""
        if zone_id not in self.zone_grids:
            return
        
        cells = self.zone_grids[zone_id]['cells']
        
        # Find cell containing this point
        for cell in cells.values():
            bounds = cell.get_bounds()
            if (bounds[0] <= world_x <= bounds[2] and 
                bounds[1] <= world_y <= bounds[3]):
                cell.filled = True
                cell.dump_count += 1
                return
    
    def get_zone_fill_percentage(self, zone_id: int) -> float:
        """Get percentage of zone cells that are filled."""
        if zone_id not in self.zone_grids:
            return 0.0
        
        cells = self.zone_grids[zone_id]['cells']
        if not cells:
            return 0.0
        
        filled = sum(1 for cell in cells.values() if cell.filled)
        return 100.0 * filled / len(cells)
    
    def get_zone_grid_visual(self, zone_id: int) -> str:
        """Get ASCII grid visualization of zone (for debugging)."""
        if zone_id not in self.zone_grids:
            return "Zone not found"
        
        grid_info = self.zone_grids[zone_id]
        rows = grid_info['grid_rows']
        cols = grid_info['grid_cols']
        cells = grid_info['cells']
        
        # Build grid visualization
        grid = [['.' for _ in range(cols)] for _ in range(rows)]
        
        for (col, row), cell in cells.items():
            if row < rows and col < cols:
                grid[row][col] = '█' if cell.filled else ' '
        
        lines = [f"Zone {zone_id} ({cols}x{rows}) [{self.get_zone_fill_percentage(zone_id):.0f}%]"]
        lines.extend([''.join(row) for row in grid])
        return '\n'.join(lines)
    
    def get_all_zones_status(self) -> list[dict]:
        """Get status of all zones for UI display."""
        status = []
        for zone_id in range(len(self.zones)):
            filled_count = sum(1 for cell in self.zone_grids[zone_id]['cells'].values() if cell.filled)
            total_count = len(self.zone_grids[zone_id]['cells'])
            status.append({
                'zone_id': zone_id,
                'grid_cells': total_count,
                'filled_cells': filled_count,
                'fill_percentage': 100.0 * filled_count / total_count if total_count > 0 else 0,
            })
        return status
