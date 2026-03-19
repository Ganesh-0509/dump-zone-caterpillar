"""Flask API server for dump simulator visualization."""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from pathlib import Path
from math import sqrt
import numpy as np
import json
from shapely.geometry import Polygon, Point
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig
from planning.dump_spot_selector import select_dump_spot

app = Flask(__name__)
CORS(app)


def calculate_dynamic_zones(polygon: Polygon) -> int:
    """
    Calculate optimal number of zones based on polygon shape and size.
    Uses aspect ratio and area to determine zone count for efficient filling.
    """
    min_x, min_y, max_x, max_y = polygon.bounds
    width = max_x - min_x
    height = max_y - min_y
    area = polygon.area
    
    # Aspect ratio (always >= 1)
    aspect_ratio = max(width, height) / max(min(width, height), 0.001)
    
    # More conservative base zone count based on area
    # Use sqrt for less aggressive scaling
    base_zones = int(3 + (area ** 0.5) / 5)  # More conservative scaling
    base_zones = min(base_zones, 8)   # Cap base at 8 zones
    base_zones = max(base_zones, 3)   # Ensure at least 3 zones
    
    # Adjust based on aspect ratio
    # More elongated shapes get slightly more zones
    if aspect_ratio > 3.0:
        # Very elongated (like a long rectangle)
        zone_multiplier = 1.3
    elif aspect_ratio > 2.0:
        # Moderately elongated
        zone_multiplier = 1.15
    elif aspect_ratio > 1.5:
        # Slightly elongated
        zone_multiplier = 1.05
    else:
        # Nearly square
        zone_multiplier = 1.0
    
    dynamic_zones = int(base_zones * zone_multiplier)
    
    # Cap at 9 zones for reasonable visual clarity
    return min(max(dynamic_zones, 3), 9)


# Global simulation state
simulation_state = {
    'engine': None,
    'is_running': False,
    'current_step': 0,
    'zones': [],
    'metadata': None,
    'polygon': None,
    # FEATURE 1 + FEATURE 2 CHANGE: store user-defined polygon + entry in session state.
    'polygon_points': None,
    'entry_point': None,
    'rescored_spots': [],
}

def _build_polygon_from_points(points):
    """FEATURE 1 CHANGE: validate and construct a Shapely polygon from client points."""
    if not isinstance(points, list) or len(points) < 3:
        raise ValueError('Polygon requires at least 3 points')

    normalized = []
    for pt in points:
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            raise ValueError('Each point must be [x, y]')
        normalized.append((float(pt[0]), float(pt[1])))

    polygon = Polygon(normalized)
    if polygon.is_empty or polygon.area <= 0:
        raise ValueError('Polygon area must be greater than zero')

    if not polygon.is_valid:
        polygon = polygon.buffer(0)
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError('Polygon is invalid and could not be repaired')

    return polygon, normalized


def _rescore_dump_spots_from_entry(engine, entry_x, entry_y):
    """FEATURE 2 CHANGE: re-score potential dump spots using entry distance preference."""
    if not engine:
        return []

    # Furthest-from-entry first: invert distance weight so farther cells score higher.
    if engine.slope_validator.distance_weight >= 0:
        engine.slope_validator.distance_weight = -abs(engine.slope_validator.distance_weight or 1.0)

    rescored = []
    for zone_index, zone in enumerate(engine.zones):
        try:
            grid_x, grid_y = select_dump_spot(
                zone,
                engine.occupancy_grid,
                engine.metadata,
                height_grid=engine.height_map,
                truck_position=(float(entry_x), float(entry_y)),
                slope_validator=engine.slope_validator,
            )
            world_x = engine.metadata.origin_x + grid_x * engine.metadata.cell_size
            world_y = engine.metadata.origin_y + grid_y * engine.metadata.cell_size
            rescored.append({
                'zone_index': int(zone_index),
                'grid_x': int(grid_x),
                'grid_y': int(grid_y),
                'x': float(world_x),
                'y': float(world_y),
            })
        except ValueError:
            continue

    simulation_state['rescored_spots'] = rescored
    return rescored


def _compute_avg_spacing(total_dumps):
    """FEATURE 3 CHANGE: compute dump spacing as sqrt(polygon_area / total_dumps)."""
    polygon = simulation_state.get('polygon')
    if polygon is None or total_dumps <= 0:
        return 0.0
    return float(sqrt(float(polygon.area) / float(total_dumps)))


def initialize_simulation(custom_polygon_points=None):
    """Initialize a new simulation."""
    try:
        # FEATURE 1 CHANGE: allow simulation boot from user-drawn polygon points.
        if custom_polygon_points is not None:
            dump_polygon, normalized_points = _build_polygon_from_points(custom_polygon_points)
        elif simulation_state.get('polygon_points'):
            dump_polygon, normalized_points = _build_polygon_from_points(simulation_state['polygon_points'])
        else:
            project_root = Path(__file__).resolve().parent
            polygon_path = project_root / "data" / "dump_polygon.json"
            dump_polygon = load_dump_polygon(polygon_path)
            normalized_points = [(float(x), float(y)) for x, y in list(dump_polygon.exterior.coords)[:-1]]

        # FEATURE 2 CHANGE: use session entry point as truck entrance when present.
        entry_point = simulation_state.get('entry_point')
        if entry_point:
            entrance_x = float(entry_point['x'])
            entrance_y = float(entry_point['y'])
        else:
            default_entry = dump_polygon.representative_point()
            entrance_x = float(default_entry.x)
            entrance_y = float(default_entry.y)

        # DYNAMIC ZONES: Calculate optimal zone count based on polygon shape and size
        dynamic_zone_count = calculate_dynamic_zones(dump_polygon)
        zone_config = ZoneGenerationConfig(zone_count=dynamic_zone_count, random_seed=42)
        generator_config = TruckGeneratorConfig(
            spawn_interval=1,
            truck_speed=1.0,
            entrance_x=entrance_x,
            entrance_y=entrance_y,
            initial_payload=1.0,
        )
        
        zones = generate_voronoi_zones(dump_polygon, zone_config)
        grid, metadata = create_grid_from_polygon(dump_polygon, cell_size=0.5)
        height_map = initialize_height_map(grid.shape)
        
        sim_config = SimulationConfig(max_steps=500, generator_config=generator_config)
        engine = SimulationEngine(zones, sim_config, grid, height_map, metadata)
        
        simulation_state['engine'] = engine
        simulation_state['zones'] = zones
        simulation_state['metadata'] = metadata
        simulation_state['polygon'] = dump_polygon
        simulation_state['polygon_points'] = [[x, y] for x, y in normalized_points]
        simulation_state['current_step'] = 0

        if entry_point:
            _rescore_dump_spots_from_entry(engine, entrance_x, entrance_y)
        
        return True
    except Exception as e:
        print(f"Error initializing simulation: {e}")
        return False

@app.route('/')
def index():
    """Serve main dashboard."""
    return render_template('dashboard.html')

@app.route('/api/init', methods=['POST'])
def api_init():
    """Initialize simulation."""
    success = initialize_simulation(simulation_state.get('polygon_points'))
    if success:
        return jsonify({'status': 'success', 'message': 'Simulation initialized'})
    return jsonify({'status': 'error', 'message': 'Failed to initialize'})

@app.route('/api/step', methods=['POST'])
def api_step():
    """Execute one simulation step."""
    if not simulation_state['engine']:
        return jsonify({'status': 'error', 'message': 'Simulation not initialized'})
    
    engine = simulation_state['engine']
    engine.step()
    simulation_state['current_step'] += 1
    
    return get_state()

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current simulation state."""
    if not simulation_state['engine']:
        return jsonify({'status': 'error', 'message': 'Simulation not initialized'})
    
    engine = simulation_state['engine']
    
    # Get truck positions and states
    trucks = []
    for truck in engine.trucks:
        trucks.append({
            'id': int(truck.truck_id),
            'x': float(truck.position_x),
            'y': float(truck.position_y),
            'state': str(truck.state).split('.')[-1],
            'payload': float(truck.payload),
            'dump_grid_x': int(truck.dump_grid_x) if truck.dump_grid_x is not None else None,
            'dump_grid_y': int(truck.dump_grid_y) if truck.dump_grid_y is not None else None,
        })
    
    # Get dump locations (CELL_DUMP_PILE cells)
    dump_cells = []
    dump_pile_mask = (engine.occupancy_grid == 1)  # CELL_DUMP_PILE = 1
    for y, x in np.argwhere(dump_pile_mask):
        height = float(engine.height_map[y, x])
        world_x = engine.metadata.origin_x + x * engine.metadata.cell_size
        world_y = engine.metadata.origin_y + y * engine.metadata.cell_size
        dump_cells.append({
            'x': world_x,
            'y': world_y,
            'grid_x': int(x),
            'grid_y': int(y),
            'height': height
        })
    
    # Get metrics
    summary = engine.analytics.get_summary()
    total_dumps = int(summary.get('total_dumps', 0))
    avg_spacing = _compute_avg_spacing(total_dumps)
    
    return jsonify({
        'status': 'success',
        'step': simulation_state['current_step'],
        'trucks': trucks,
        'dump_cells': dump_cells,
        'metrics': {
            'packing_density': float(summary.get('packing_density', 0)),
            'fleet_utilization': float(summary.get('fleet_utilization', 0)),
            'total_dumps': total_dumps,
            'layer_growth_events': int(summary.get('layer_growth_events', 0)),
            'max_pile_height': float(summary.get('max_pile_height', 0)),
            'average_pile_slope': float(summary.get('average_pile_slope', 0)),
            # FEATURE 3 CHANGE: include spacing metric in metrics payload.
            'avg_spacing': avg_spacing,
        },
        # FEATURE 3 CHANGE: include spacing metric at response root for /api/step consumers.
        'avg_spacing': avg_spacing,
        'zones_count': len(simulation_state['zones']),
        'active_trucks': len(engine.trucks),
    })


@app.route('/api/set_polygon', methods=['POST'])
def api_set_polygon():
    """FEATURE 1 CHANGE: accept a client-drawn yard polygon and reset simulation."""
    data = request.get_json(silent=True) or {}
    points = data.get('points')

    try:
        _, normalized_points = _build_polygon_from_points(points)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Invalid polygon: {e}'})

    # Drawing a new yard resets simulation state and clears entry until reselected.
    simulation_state['entry_point'] = None
    simulation_state['polygon_points'] = [[float(x), float(y)] for x, y in normalized_points]
    simulation_state['is_running'] = False
    simulation_state['current_step'] = 0

    success = initialize_simulation(simulation_state['polygon_points'])
    if not success:
        return jsonify({'status': 'error', 'message': 'Failed to initialize from polygon'})

    return jsonify({
        'status': 'success',
        'message': 'Polygon set and simulation reset',
        'points_count': len(simulation_state['polygon_points']),
    })


@app.route('/api/set_entry', methods=['POST'])
def api_set_entry():
    """FEATURE 2 CHANGE: set dynamic entry point and re-score dump spots."""
    if not simulation_state['engine'] or simulation_state['polygon'] is None:
        return jsonify({'status': 'error', 'message': 'Simulation not initialized'})

    data = request.get_json(silent=True) or {}
    if 'x' not in data or 'y' not in data:
        return jsonify({'status': 'error', 'message': 'Body must include x and y'})

    try:
        entry_x = float(data['x'])
        entry_y = float(data['y'])
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Entry point must be numeric'})

    polygon = simulation_state['polygon']
    point = Point(entry_x, entry_y)
    if not (polygon.contains(point) or polygon.touches(point)):
        return jsonify({'status': 'error', 'message': 'Entry point must be inside polygon'})

    simulation_state['entry_point'] = {'x': entry_x, 'y': entry_y}

    engine = simulation_state['engine']
    engine.config.generator_config.entrance_x = entry_x
    engine.config.generator_config.entrance_y = entry_y
    rescored = _rescore_dump_spots_from_entry(engine, entry_x, entry_y)

    return jsonify({
        'status': 'success',
        'message': 'Entry point set',
        'entry_point': simulation_state['entry_point'],
        'rescored_count': len(rescored),
    })

@app.route('/api/metadata', methods=['GET'])
def get_metadata():
    """Get simulation metadata."""
    if not simulation_state['metadata']:
        return jsonify({'status': 'error'})
    
    meta = simulation_state['metadata']
    polygon = simulation_state['polygon']
    
    return jsonify({
        'status': 'success',
        'bounds': {
            'min_x': float(polygon.bounds[0]),
            'min_y': float(polygon.bounds[1]),
            'max_x': float(polygon.bounds[2]),
            'max_y': float(polygon.bounds[3]),
        },
        'grid': {
            'width': meta.grid_width,
            'height': meta.grid_height,
            'cell_size': meta.cell_size,
        },
        'zones': len(simulation_state['zones']),
    })

@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset simulation."""
    success = initialize_simulation(simulation_state.get('polygon_points'))
    if success:
        return jsonify({'status': 'success', 'message': 'Simulation reset'})
    return jsonify({'status': 'error', 'message': 'Failed to reset'})

@app.route('/api/play', methods=['POST'])
def api_play():
    """Start simulation loop."""
    if not simulation_state['engine']:
        return jsonify({'status': 'error', 'message': 'Simulation not initialized'})
    
    simulation_state['is_running'] = True
    return jsonify({'status': 'success', 'message': 'Simulation playing'})

@app.route('/api/pause', methods=['POST'])
def api_pause():
    """Pause simulation loop."""
    simulation_state['is_running'] = False
    return jsonify({'status': 'success', 'message': 'Simulation paused'})
@app.route('/api/zone_grid_status', methods=['GET'])
def api_zone_grid_status():
    """Get grid-based zone filling status."""
    if not simulation_state['engine']:
        return jsonify({'status': 'error', 'message': 'Simulation not initialized'})
    
    engine = simulation_state['engine']
    zone_status = engine.zone_grid_manager.get_all_zones_status()
    
    return jsonify({
        'status': 'success',
        'zones': zone_status,
        'grid_cell_size_meters': 3.0,
        'total_zones': len(engine.zones),
    })

if __name__ == '__main__':
    print("Starting Dump Simulator Server on http://localhost:5000")
    app.run(debug=True, host='localhost', port=5000)
