import re

with open('simulation/truck_agent.py', 'r') as f:
    text = f.read()

# Match the old compute_path return True block
old1 = """        if planned_path:
            self.path = planned_path
            self.current_path_index = 0
            if traffic_manager:
                traffic_manager.reserve_path(self.truck_id, self.path, current_step)
            return True"""

new1 = """        if planned_path:
            self.path = planned_path
            self.current_path_index = 0
            if traffic_manager:
                traffic_manager.reserve_path(self.truck_id, self.path, current_step)
                
            smoother = PathSmoother()
            reduced = smoother.reduce_waypoints(self.path)
            self.smoothed_path = smoother.smooth_path(reduced, resolution=5, metadata=metadata)
            self.current_smoothed_index = 0
            
            return True"""

if old1 in text:
    text = text.replace(old1, new1)

# Match move_along_path
old2 = """    def move_along_path(self, metadata: GridMetadata) -> bool:
        \"\"\"Move truck one step along its computed path.

        Returns True if final target reached, False otherwise.
        \"\"\"
        if not self.path or self.current_path_index >= len(self.path):
            # No path or reached end
            return True

        # Get target cell
        target_grid_node = self.path[self.current_path_index]
        target_world_x, target_world_y = grid_to_world(
            target_grid_node[0],
            target_grid_node[1],
            metadata.origin_x,
            metadata.origin_y,
            metadata.cell_size,
        )

        # We target the center of the cell for smoother movement
        target_world_x += metadata.cell_size / 2.0
        target_world_y += metadata.cell_size / 2.0

        dx = target_world_x - self.position_x
        dy = target_world_y - self.position_y
        distance = np.sqrt(dx**2 + dy**2)

        if distance < self.speed:
            # Reached this waypoint
            self.position_x = target_world_x
            self.position_y = target_world_y
            self.distance_traveled += distance
            self.current_path_index += 1

            # Check if we're done
            if self.current_path_index >= len(self.path):
                return True

        else:
            # Move toward waypoint
            self.position_x += self.speed * (dx / distance)
            self.position_y += self.speed * (dy / distance)
            self.distance_traveled += self.speed

        return False"""

new2 = """    def move_along_path(self, metadata: GridMetadata) -> bool:
        \"\"\"Move truck one step along its computed path.

        Returns True if final target reached, False otherwise.
        \"\"\"
        if getattr(self, "smoothed_path", None):
            path_to_follow = self.smoothed_path
            idx = self.current_smoothed_index
        else:
            path_to_follow = self.path
            idx = self.current_path_index

        if not path_to_follow or idx >= len(path_to_follow):
            # No path or reached end
            return True

        if getattr(self, "smoothed_path", None):
            target_world_x, target_world_y = path_to_follow[idx]
        else:
            # Get target cell
            target_grid_node = path_to_follow[idx]
            target_world_x, target_world_y = grid_to_world(
                target_grid_node[0],
                target_grid_node[1],
                metadata.origin_x,
                metadata.origin_y,
                metadata.cell_size,
            )

            # We target the center of the cell for smoother movement
            target_world_x += metadata.cell_size / 2.0
            target_world_y += metadata.cell_size / 2.0

        dx = target_world_x - self.position_x
        dy = target_world_y - self.position_y
        distance = np.sqrt(dx**2 + dy**2)

        if distance < self.speed:
            # Reached this waypoint
            self.position_x = target_world_x
            self.position_y = target_world_y
            self.distance_traveled += distance
            if getattr(self, "smoothed_path", None):
                self.current_smoothed_index += 1
            else:
                self.current_path_index += 1
        else:
            # Move toward waypoint
            self.position_x += self.speed * (dx / distance)
            self.position_y += self.speed * (dy / distance)
            self.distance_traveled += self.speed
            
        # Update current_path_index based on grid position for collision detection purposes
        if self.path:
            grid_x, grid_y = world_to_grid(
                self.position_x,
                self.position_y,
                metadata.origin_x,
                metadata.origin_y,
                metadata.cell_size,
            )
            
            # Find closest matching node looking forward to not backtrack
            for i in range(self.current_path_index, len(self.path)):
                node_x, node_y = self.path[i][0], self.path[i][1]
                if node_x == grid_x and node_y == grid_y:
                    self.current_path_index = i
                    break

        if getattr(self, "smoothed_path", None):
            return self.current_smoothed_index >= len(path_to_follow)
        else:
            return self.current_path_index >= len(self.path)"""

if old2 in text:
    text = text.replace(old2, new2)

with open('simulation/truck_agent.py', 'w') as f:
    f.write(text)
