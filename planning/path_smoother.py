import numpy as np
import math

class PathSmoother:
    def __init__(self, min_turn_radius: float = 2.0):
        self.min_turn_radius = min_turn_radius

    def reduce_waypoints(self, path: list[tuple]) -> list[tuple]:
        """
        Remove intermediate nodes that lie on the same straight line.
        path is a list of (grid_x, grid_y) or (grid_x, grid_y, t).
        """
        if len(path) <= 2:
            return path

        reduced = [path[0]]
        
        for i in range(1, len(path) - 1):
            prev_node = reduced[-1]
            curr_node = path[i]
            next_node = path[i + 1]

            v1_x = curr_node[0] - prev_node[0]
            v1_y = curr_node[1] - prev_node[1]
            v2_x = next_node[0] - curr_node[0]
            v2_y = next_node[1] - curr_node[1]
            
            # Cross product to check collinearity
            cross_product = v1_x * v2_y - v1_y * v2_x
            if cross_product != 0:
                # Not a straight line, keep current node
                reduced.append(curr_node)
                
        reduced.append(path[-1])
        return reduced

    def smooth_path(self, waypoints: list[tuple], resolution: int = 5, metadata=None) -> list[tuple[float, float]]:
        """
        Smooth corners using Catmull-Rom spline interpolation.
        Returns a list of world coordinates (x, y).
        """
        if not waypoints:
            return []
            
        # First, convert waypoints to world coordinates
        world_pts = []
        for wp in waypoints:
            grid_x, grid_y = wp[0], wp[1]
            if metadata:
                wx = metadata.origin_x + grid_x * metadata.cell_size + metadata.cell_size / 2.0
                wy = metadata.origin_y + grid_y * metadata.cell_size + metadata.cell_size / 2.0
            else:
                wx, wy = float(grid_x), float(grid_y)
            world_pts.append((wx, wy))
            
        if len(world_pts) < 3:
            return world_pts
            
        # For Catmull-Rom, we need boundary points (duplicate start and end)
        pts = [world_pts[0]] + world_pts + [world_pts[-1]]
        
        smoothed = []
        for i in range(1, len(pts) - 2):
            p0, p1, p2, p3 = pts[i-1], pts[i], pts[i+1], pts[i+2]
            
            # Check turn radius between p0, p1, p2
            # If the angle is sharp, Catmull-Rom might still be a bit too sharp.
            # We can optionally handle min_turn_radius by adjusting control points or evaluating curvature, 
            # but standard Catmull-Rom provides a basic spline.
            # The prompt says: "If a curve segment is tighter than this radius, expand the curve slightly"
            
            # Generate interpolated points
            for t in range(resolution):
                t_normalized = t / float(resolution)
                t2 = t_normalized * t_normalized
                t3 = t2 * t_normalized

                # Catmull-Rom blending functions
                b0 = -t3 + 2.0*t2 - t_normalized
                b1 = 3.0*t3 - 5.0*t2 + 2.0
                b2 = -3.0*t3 + 4.0*t2 + t_normalized
                b3 = t3 - t2

                x = 0.5 * (p0[0]*b0 + p1[0]*b1 + p2[0]*b2 + p3[0]*b3)
                y = 0.5 * (p0[1]*b0 + p1[1]*b1 + p2[1]*b2 + p3[1]*b3)
                smoothed.append((x, y))
                
        smoothed.append(world_pts[-1])
        
        # Enforce minimum turn radius by moving points outwards at sharp corners
        # A simple approximation: if the distance from mid point to line segment is too small...
        # Let's apply a post-processing step for min_turn_radius.
        smoothed = self._enforce_turn_radius(smoothed)
        
        return smoothed

    def _enforce_turn_radius(self, path: list[tuple[float, float]]) -> list[tuple[float, float]]:
        """
        Expands the curve if it is tighter than min_turn_radius.
        """
        if len(path) < 3:
            return path
            
        smoothed = [path[0]]
        for i in range(1, len(path) - 1):
            p_prev = smoothed[-1]
            p_curr = path[i]
            p_next = path[i+1]
            
            # Vector previous to current
            v1_x = p_curr[0] - p_prev[0]
            v1_y = p_curr[1] - p_prev[1]
            l1 = math.hypot(v1_x, v1_y)
            
            # Vector current to next
            v2_x = p_next[0] - p_curr[0]
            v2_y = p_next[1] - p_curr[1]
            l2 = math.hypot(v2_x, v2_y)
            
            if l1 > 0.001 and l2 > 0.001:
                # Compute angle change
                dot = (v1_x * v2_x + v1_y * v2_y) / (l1 * l2)
                dot = max(-1.0, min(1.0, dot))
                angle = math.acos(dot)
                
                # Turn radius approximation R = length / angle
                # (For small segments passing a curve)
                avg_len = (l1 + l2) / 2.0
                if angle > 0.05: # non-negligible turn
                    r_current = avg_len / angle
                    if r_current < self.min_turn_radius:
                        # Need to expand curve: push point outward from the corner
                        # Bisector vector
                        b_x = (v1_x/l1 - v2_x/l2)
                        b_y = (v1_y/l1 - v2_y/l2)
                        b_len = math.hypot(b_x, b_y)
                        
                        if b_len > 0:
                            # Push amount proportional to how much radius deficit there is
                            push_dist = (self.min_turn_radius - r_current) * angle
                            p_curr = (p_curr[0] + (b_x/b_len)*push_dist, p_curr[1] + (b_y/b_len)*push_dist)
            
            smoothed.append(p_curr)
            
        smoothed.append(path[-1])
        return smoothed
