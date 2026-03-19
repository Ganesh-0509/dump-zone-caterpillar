import numpy as np
from shapely.geometry import Point

import planning.dump_spot_selector as dss
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import create_grid_from_polygon, CELL_DUMP_PILE
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig

dss._debug_print_selected_spot = lambda *args, **kwargs: None


def nn_stats(coords):
    if len(coords) < 2:
        return None
    arr = np.asarray(coords, dtype=np.float64)
    dmins = []
    for i in range(arr.shape[0]):
        diff = arr - arr[i]
        dist = np.sqrt(np.sum(diff * diff, axis=1))
        dist[i] = np.inf
        dmins.append(np.min(dist))
    d = np.asarray(dmins)
    return float(d.mean()), float(np.median(d)), float(np.percentile(d, 10)), float(np.percentile(d, 90)), float(d.min()), float(d.max())

poly = load_dump_polygon('data/dump_polygon.json')
entry = poly.representative_point()
rows = []
for seed in (42, 84, 126):
    zones = generate_voronoi_zones(poly, ZoneGenerationConfig(zone_count=5, random_seed=seed))
    grid, meta = create_grid_from_polygon(poly, cell_size=0.5)
    h = initialize_height_map(grid.shape)
    cfg = TruckGeneratorConfig(spawn_interval=2, truck_speed=0.5, entrance_x=float(entry.x), entrance_y=float(entry.y), initial_payload=1.0)
    eng = SimulationEngine(zones, SimulationConfig(max_steps=700, generator_config=cfg), grid, h, meta)

    for _ in range(700):
        eng.step()

    ys, xs = np.where(eng.occupancy_grid == CELL_DUMP_PILE)
    coords = []
    for y, x in zip(ys, xs):
        wx = meta.origin_x + x * meta.cell_size
        wy = meta.origin_y + y * meta.cell_size
        if poly.contains(Point(wx, wy)):
            coords.append((wx, wy))

    s = nn_stats(coords)
    print(f'seed={seed} piles={len(coords)} total_dumps={eng.analytics.total_dumps}')
    if s is None:
        print('  insufficient for NN stats')
        continue
    mean, median, p10, p90, dmin, dmax = s
    print(f'  mean={mean:.3f} median={median:.3f} p10={p10:.3f} p90={p90:.3f} min={dmin:.3f} max={dmax:.3f}')
    rows.append((mean, median, p10, p90, dmin, dmax))

if rows:
    a = np.asarray(rows)
    m = a.mean(axis=0)
    print(f'aggregate mean={m[0]:.3f} median={m[1]:.3f} p10={m[2]:.3f} p90={m[3]:.3f} min={m[4]:.3f} max={m[5]:.3f}')
