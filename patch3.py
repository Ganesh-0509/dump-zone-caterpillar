import re

with open('visualization/plot_environment.py', 'r') as f:
    text = f.read()

old_draw = """            # Draw A* path
            if getattr(truck, "path", None) and truck.current_path_index < len(truck.path):
                # Path contains grid coords (x,y) or (x,y,t). Extract just (x,y).
                path_world_coords = [(truck.position_x, truck.position_y)]
                for node in truck.path[truck.current_path_index:]:
                    grid_x, grid_y = node[0], node[1]
                    wx, wy = grid_to_world(grid_x, grid_y, metadata.origin_x, metadata.origin_y, metadata.cell_size)
                    path_world_coords.append((wx + metadata.cell_size / 2, wy + metadata.cell_size / 2))
                
                if len(path_world_coords) > 1:
                    px, py = zip(*path_world_coords)
                    axis.plot(px, py, color="red", linestyle="--", linewidth=1.0, alpha=0.6, zorder=4)"""

new_draw = """            # Draw path
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
                    axis.plot(px, py, color="red", linestyle="--", linewidth=1.0, alpha=0.6, zorder=4)"""

if old_draw in text:
    text = text.replace(old_draw, new_draw)

with open('visualization/plot_environment.py', 'w') as f:
    f.write(text)
