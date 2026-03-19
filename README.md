# 🚜 Caterpillar Autonomous Dump Zone Simulator

## 1. Overview

This project is a real-time, multi-agent simulation of autonomous mining trucks filling a dump site. It implements an intelligent system for zone planning, dynamic dump location selection, and efficient fleet coordination, inspired by Caterpillar's autonomous hauling solutions. The primary goal is to demonstrate how algorithmic planning can increase dump packing density and operational efficiency compared to naive strategies.

The simulation is visualized through a web-based dashboard that provides real-time insights into truck movements, dump pile formation, and key performance indicators (KPIs).

## 2. Features

- **Dynamic Zone Generation**: The dump site is automatically partitioned into an optimal number of zones based on the site's geometry (area and aspect ratio).
- **Intelligent Truck Dispatch**: Trucks are dispatched using a **"farthest-zone-first"** strategy to ensure the dump site is filled systematically from the back to the front.
- **Grid-Based Dumping**: Each zone is divided into a 3x3 meter grid. Trucks are assigned to the farthest available grid cell within their designated zone, promoting an edge-first filling pattern for maximum compaction.
- **A* Pathfinding**: Trucks navigate the site using the A* algorithm to find the shortest path on a discrete occupancy grid, with considerations for traffic.
- **Real-time Visualization**: An interactive web dashboard built with HTML5 Canvas and JavaScript renders truck positions, states, dump piles, and zone boundaries in real-time.
- **REST API**: A Flask-based backend provides a comprehensive set of API endpoints to control the simulation (initialize, step, play, pause, reset) and retrieve state data.
- **Collision Avoidance**: A basic collision avoidance system prevents trucks from overlapping by applying separation forces.
- **Detailed Analytics**: The simulation tracks and displays key metrics suchs as packing density, fleet utilization, and dump throughput.

## 3. Technology Stack

- **Backend**:
    - **Python 3.11+**
    - **Flask**: For the REST API server.
    - **Shapely**: For all geometric operations (polygons, points, etc.).
    - **NumPy**: For efficient numerical operations, especially on the occupancy and height grids.
    - **SciPy**: Used for Voronoi diagram calculations in zone generation.

- **Frontend**:
    - **HTML5 / CSS3**
    - **Vanilla JavaScript**: For all frontend logic, including rendering on the HTML5 Canvas and communicating with the backend API.

## 4. System Architecture

The system is composed of a Python backend that runs the core simulation logic and a JavaScript frontend that visualizes the simulation state.

1.  **Flask Web Server (`app.py`)**: Exposes REST API endpoints for the frontend to control and query the simulation. It manages the main `SimulationEngine` instance.
2.  **Simulation Engine (`simulation/simulation_engine.py`)**: The heart of the simulation. It manages the main simulation loop, orchestrates all agents and managers, and updates the state at each time step.
3.  **Truck Agent (`simulation/truck_agent.py`)**: Represents an individual autonomous truck with its own state machine (e.g., `MOVING_TO_ZONE`, `DUMPING`, `RETURNING`).
4.  **Truck Generator (`simulation/truck_generator.py`)**: Responsible for spawning new trucks and assigning them to zones based on the "farthest-zone-first" strategy.
5.  **Zone and Grid Managers**:
    - **`geometry/zone_generator.py`**: Partitions the dump polygon into Voronoi zones.
    - **`planning/zone_grid_manager.py`**: Manages the 3m grid within each zone, tracks filled cells, and determines the next optimal dump spot.
6.  **Pathfinding and Traffic**:
    - **`planning/path_planner.py`**: Implements the A* algorithm for pathfinding.
    - **`planning/traffic_manager.py`**: Manages path reservations to avoid collisions (though the current implementation is basic).
7.  **Frontend (`templates/dashboard.html`)**: A single-page application that fetches data from the backend API and renders the simulation on an HTML5 Canvas.

## 5. Core Algorithms & Formulas

### Dynamic Zone Calculation

To avoid a fixed number of zones, the optimal number is calculated based on the dump polygon's shape and size.

-   **Formula**:
    1.  **Base Zones**: `3 + sqrt(Area) / 5` (capped between 3 and 8). This provides a conservative starting point that scales with the site area.
    2.  **Aspect Ratio Multiplier**: The base number is adjusted by a multiplier based on the polygon's aspect ratio (`max(width, height) / min(width, height)`). Elongated shapes get more zones to improve coverage.
        -   `1.3x` for aspect ratio > 3.0
        -   `1.15x` for aspect ratio > 2.0
        -   `1.05x` for aspect ratio > 1.5
    3.  **Final Count**: `int(Base Zones * Multiplier)`, capped at a maximum of 9 for visual clarity.

### Voronoi Zone Generation

The dump polygon is partitioned into zones using Voronoi diagrams.

-   **Process**:
    1.  Random seed points are sampled uniformly within the polygon.
    2.  A Voronoi diagram is computed from these seed points using `scipy.spatial.Voronoi`.
    3.  The resulting infinite Voronoi cells are clipped against the main dump polygon boundary.
    4.  The final clipped polygons become the dump zones.

### A* Pathfinding

Trucks find their way across the site using the A* search algorithm on a 2D occupancy grid.

-   **Heuristic Function**: Euclidean distance is used as the heuristic (`h(n)`).
    -   `h(a, b) = sqrt((a.x - b.x)² + (a.y - b.y)²) `
-   **Cost Function**: The cost to move between adjacent cells (`g(n)`) is `1.0` for cardinal directions and `1.414` (sqrt(2)) for diagonal directions.
-   **Constraints**: The path planner only considers `CELL_EMPTY` cells as traversable, avoiding obstacles and already dumped material.

### Grid-Based Dumping Strategy

This is the core intelligent algorithm for filling the dump site efficiently.

1.  **Farthest-Zone-First Dispatch**:
    -   When a new truck is spawned, it is assigned to the available (not full) zone whose centroid is farthest from the site's entry point.
    -   This ensures that the back of the dump site is filled first, preventing trucks from having to navigate through already-dumped material later on.
    -   Zone priority is pre-calculated and sorted in descending order of distance from the entry.

2.  **Farthest-Cell-First Dumping**:
    -   Once a truck is assigned to a zone, it requests a specific dump location from the `ZoneGridManager`.
    -   The manager maintains a 3x3 meter grid for the zone.
    -   It identifies all empty cells and selects the one that is **farthest from the zone's own centroid**.
    -   This strategy forces filling to start at the outer edges and corners of a zone, working inwards and maximizing material compaction.

## 6. How to Run

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements-frontend.txt
    ```

2.  **Start the Server**:
    ```bash
    python app.py
    ```
    This will start the Flask backend server on `http://localhost:5000`.

3.  **Open the Frontend**:
    -   Open a web browser and navigate to `http://localhost:5000`.
    -   Alternatively, use the provided `start_frontend.bat` script on Windows, which will start the server and open the browser automatically.

4.  **Use the Dashboard**:
    -   Click **Initialize** to set up the simulation.
    -   Click **Play** to start the real-time simulation.
    -   Use **Pause**, **Step**, and **Reset** to control the flow.

## 7. API Endpoints

-   `GET /`: Serves the main `dashboard.html` page.
-   `POST /api/init`: Initializes a new simulation.
-   `POST /api/step`: Advances the simulation by a single step.
-   `GET /api/state`: Returns the complete current state of the simulation, including all truck positions, dump cells, and metrics.
-   `POST /api/set_polygon`: Allows setting a custom-drawn polygon for the dump yard.
-   `POST /api/set_entry`: Allows setting a custom entry point for the trucks.
-   `GET /api/metadata`: Returns static metadata about the simulation, like grid dimensions and bounds.
-   `POST /api/reset`: Resets the simulation to its initial state.
-   `POST /api/play`: Sets the simulation to run continuously.
-   `POST /api/pause`: Pauses the continuous simulation.
-   `GET /api/zone_grid_status`: Returns the fill status of the 3m grid for each zone.

## 8. File Structure

```
/
├── app.py                  # Flask Backend Server
├── requirements.txt        # Python Dependencies
├── start_frontend.bat      # Windows startup script
│
├── templates/
│   └── dashboard.html      # Frontend HTML, CSS, and JS
│
├── data/
│   └── dump_polygon.json   # Default dump site geometry
│
├── geometry/
│   ├── polygon_loader.py   # Loads polygon from file
│   └── zone_generator.py   # Creates Voronoi zones
│
├── mapping/
│   ├── occupancy_grid.py   # Manages the main 2D grid
│   └── terrain_map.py      # Manages the height map
│
├── planning/
│   ├── path_planner.py     # A* pathfinding implementation
│   ├── zone_grid_manager.py# Manages the 3m dumping grid
│   └── ...                 # Other planning modules
│
└── simulation/
    ├── simulation_engine.py# Core simulation orchestrator
    ├── truck_agent.py      # Defines truck behavior
    └── truck_generator.py  # Spawns and dispatches trucks
```
