# 🚜 Dump Simulator Frontend

A modern web-based visualization dashboard for the Caterpillar Dump Simulator with real-time metrics, truck tracking, and interactive controls.

## Features

### 🎨 Real-time Visualization
- **Live Canvas Rendering** - Watch trucks move and dump materials in real-time
- **Zone Boundaries** - Color-coded dump zones with clear visualization
- **Pile Heights** - Visual representation of material accumulation
- **Truck States** - Different colors for moving, dumping, and returning states
  - 🟢 Green: Moving
  - 🟠 Orange: Dumping
  - 🔵 Blue: Returning

### 📊 Live Metrics Dashboard
- **Packing Density** - Percentage of zone filled with material
- **Fleet Utilization** - Percentage of trucks actively working
- **Total Dumps** - Cumulative dump events
- **Layer Growth Events** - Terrain formation events
- **Max Pile Height** - Highest material accumulation
- **Average Pile Slope** - Terrain stability metric

### 🎮 Interactive Controls
- **Initialize** - Set up fresh simulation
- **Play** - Run simulation at selected speed
- **Pause** - Pause execution
- **Step** - Advance one step at a time
- **Reset** - Clear and restart
- **Speed Control** - Adjust simulation speed (1x - 100x)

### 📈 Fleet Status Panel
- Active truck count
- Total zones
- Individual truck tracking showing:
  - Truck ID
  - Current state
  - Payload status

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements-frontend.txt
```

Or manually:
```bash
pip install flask flask-cors
```

### 2. Run the Frontend

```bash
python run_frontend.py
```

The browser will automatically open to `http://localhost:5000`

## Usage

### Getting Started
1. Click **Initialize** to create a new simulation
2. Click **Play** to start (runs continuously)
3. Use **Speed slider** to control execution rate
4. Click **Pause** to temporarily stop
5. Click **Step** to advance one simulation step
6. Click **Reset** to start over

### Reading the Dashboard

**Left Panel (Visualization)**
- Watch trucks (circles with IDs) move through the dump zones
- Brown squares represent piles of dumped material
- Yellow lines show zone boundaries

**Right Panel (Metrics & Controls)**
- Top section: Performance metrics updating in real-time
- Middle section: Active fleet status with truck list
- Bottom section: Speed control and legend

## API Reference

### Endpoints

#### `POST /api/init`
Initialize a new simulation.

**Response:**
```json
{
  "status": "success",
  "message": "Simulation initialized"
}
```

#### `GET /api/metadata`
Get simulation configuration and bounds.

**Response:**
```json
{
  "status": "success",
  "bounds": {
    "min_x": 0,
    "min_y": 0,
    "max_x": 100,
    "max_y": 100
  },
  "grid": {
    "width": 200,
    "height": 200,
    "cell_size": 0.5
  },
  "zones": 5
}
```

#### `POST /api/step`
Execute one simulation step.

**Response:**
```json
{
  "status": "success",
  "step": 42,
  "trucks": [
    {
      "id": 1,
      "x": 20.5,
      "y": 30.2,
      "state": "MOVING_TO_ZONE",
      "payload": 1.0,
      "dump_grid_x": -1,
      "dump_grid_y": -1
    }
  ],
  "dump_cells": [
    {
      "x": 50.0,
      "y": 60.0,
      "grid_x": 100,
      "grid_y": 120,
      "height": 2.5
    }
  ],
  "metrics": {
    "packing_density": 0.0125,
    "fleet_utilization": 0.75,
    "total_dumps": 42,
    "layer_growth_events": 38,
    "max_pile_height": 2.5,
    "average_pile_slope": 0.15
  },
  "zones_count": 5,
  "active_trucks": 8
}
```

#### `GET /api/state`
Get current simulation state (same as POST /api/step response).

#### `POST /api/reset`
Reset simulation to initial state.

**Response:**
```json
{
  "status": "success",
  "message": "Simulation reset"
}
```

## Performance Tips

### For Smooth Visualization
1. Keep speed slider at 1x-10x for best visual experience
2. Use higher speeds (50x-100x) for rapid testing
3. Browser performance depends on truck count and dump locations

### Optimization Settings
- Trucks spawn at intervals (default: every 2 steps)
- Maximum simulation steps: 500
- Grid cell size: 0.5 meters

### Testing Features
The dashboard includes a built-in test suite demonstrating:
- ✅ Deadlock detection and resolution
- ✅ Slope-aware dump site selection
- ✅ Mixed-fleet truck dimensions
- ✅ Access isolation prevention
- ✅ Real-time metrics collection

## Architecture

### Backend (Flask)
- `app.py` - Flask server with REST API endpoints
- Handles simulation state management
- Processes step calculations
- Manages truck and metric data

### Frontend (HTML/CSS/JavaScript)
- `templates/dashboard.html` - Single-page application
- Canvas-based 2D visualization
- Real-time metrics updates
- Interactive control panel

### SimulationEngine Integration
- Connects to existing SimulationEngine class
- Uses DeadlockManager, SlopeValidator, TrafficManager
- Maintains analytics and metrics
- Manages multi-agent truck coordination

## Troubleshooting

### Port Already in Use
If port 5000 is already in use:
```bash
# Edit app.py and change port:
app.run(host='localhost', port=5001)
```

### Flask Not Found
```bash
pip install flask flask-cors
```

### Browser Won't Open Automatically
Manually visit: `http://localhost:5000`

### Slow Performance
- Reduce speed slider
- Check browser console for errors (F12)
- Ensure no other heavy processes running

## System Requirements

- Python 3.8+
- 2GB RAM minimum
- Modern web browser (Chrome, Firefox, Edge, Safari)
- Network: Localhost connections only

## Future Enhancements

- [ ] 3D visualization with Three.js
- [ ] Export metrics to CSV
- [ ] Heatmap of zone utilization
- [ ] Truck path tracing
- [ ] Collision visualization
- [ ] Performance profiling
- [ ] Historical data storage
- [ ] Configuration file UI

## License

Part of Caterpillar Optimal Dump Packing System

## Support

For issues or questions:
1. Check the browser console (F12) for errors
2. Review system logs
3. Restart the server
4. Reset the simulation
