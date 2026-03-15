PROJECT TITLE
Autonomous Dump Zone Planning and Multi-Truck Simulation

PROJECT GOAL
Build a software simulation that models how autonomous mining trucks fill a dump site efficiently using intelligent zone planning and dynamic dump location selection.

The goal of this project is to simulate a planning system similar to those used in modern autonomous mining fleets. The simulation should show how trucks arrive at a dump area, get assigned zones, select optimal dumping spots, move safely, and gradually fill the dump area.

The final system should demonstrate that algorithmic planning increases dump density compared to naive dumping strategies.

The project will be built incrementally in phases.

---

TECH STACK

Language
Python 3.11+

Core Libraries
numpy
shapely
scipy
matplotlib

Future Libraries (not needed yet)
mesa (multi-agent simulation)
plotly
PythonRobotics (Hybrid A* path planning)

Development Environment
Windows 11
Visual Studio Code
GitHub Copilot

---

SYSTEM CONCEPT

A dump site is represented as a polygon.

Inside the polygon we divide the space into zones.
Trucks will later be assigned to these zones and dump material in optimized positions.

For now we are only building the **geometric environment**.

---

PHASE 1 OBJECTIVE

Build the geometric foundation of the simulation.

This phase must implement:

1 Dump polygon loading
2 Polygon validation
3 Voronoi zone partitioning
4 Visualization of dump zones

This phase does NOT include trucks or path planning.

---

PHASE 1 REQUIRED FEATURES

1. Dump Polygon Loader

Load a polygon from a JSON file.

Example data format

{
"dump_polygon": [
[0,0],
[120,0],
[120,80],
[40,100],
[0,60]
]
}

Convert the coordinates into a shapely Polygon object.

---

2. Polygon Visualization

Display the polygon using matplotlib so we can verify the environment.

---

3. Zone Generation

Divide the polygon into zones using Voronoi partitioning.

Steps

1 generate random seed points inside the polygon
2 compute Voronoi diagram using scipy.spatial.Voronoi
3 clip Voronoi cells with the dump polygon
4 return a list of zone polygons

---

4. Zone Visualization

Plot the zones inside the polygon with different colors.

Output should clearly show

* dump boundary
* generated zones

---

PROJECT STRUCTURE FOR PHASE 1

Create the following folders and files

project_root

data/
dump_polygon.json

geometry/
polygon_loader.py
zone_generator.py

visualization/
plot_environment.py

main.py

---

PROGRAM FLOW FOR PHASE 1

main.py should

1 load dump polygon
2 generate zones
3 visualize the dump area with zones

---

CODING REQUIREMENTS

Use modular functions.
Add clear docstrings.
Write readable code.

Each module should contain only one responsibility.

---

FIRST TASK FOR COPILOT

Generate

polygon_loader.py
zone_generator.py
plot_environment.py
main.py

The program should run and display the dump polygon and zones.
