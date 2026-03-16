"""Flask API server for dump simulator visualization."""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from pathlib import Path
import numpy as np
import json
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig

app = Flask(__name__)
CORS(app)

# Global simulation state
simulation_state = {
    'engine': None,
    'is_running': False,
    'current_step': 0,
    'zones': [],
    'metadata': None,
    'polygon': None,
}

def initialize_simulation():
    """Initialize a new simulation."""
    try:
        project_root = Path(__file__).resolve().parent
        polygon_path = project_root / "data" / "dump_polygon.json"
        
        dump_polygon = load_dump_polygon(polygon_path)
        zone_config = ZoneGenerationConfig(zone_count=5, random_seed=42)
        generator_config = TruckGeneratorConfig(
            spawn_interval=2,
            truck_speed=0.5,
            entrance_x=dump_polygon.bounds[0],
            entrance_y=dump_polygon.bounds[1],
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
        simulation_state['current_step'] = 0
        
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
    success = initialize_simulation()
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
    
    return jsonify({
        'status': 'success',
        'step': simulation_state['current_step'],
        'trucks': trucks,
        'dump_cells': dump_cells,
        'metrics': {
            'packing_density': float(summary.get('packing_density', 0)),
            'fleet_utilization': float(summary.get('fleet_utilization', 0)),
            'total_dumps': int(summary.get('total_dumps', 0)),
            'layer_growth_events': int(summary.get('layer_growth_events', 0)),
            'max_pile_height': float(summary.get('max_pile_height', 0)),
            'average_pile_slope': float(summary.get('average_pile_slope', 0)),
        },
        'zones_count': len(simulation_state['zones']),
        'active_trucks': len(engine.trucks),
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
    success = initialize_simulation()
    if success:
        return jsonify({'status': 'success', 'message': 'Simulation reset'})
    return jsonify({'status': 'error', 'message': 'Failed to reset'})

if __name__ == '__main__':
    print("Starting Dump Simulator Server on http://localhost:5000")
    app.run(debug=True, host='localhost', port=5000)
