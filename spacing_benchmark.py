"""Deterministic spacing benchmark harness for calibration loops.

This script runs short simulation batches across seeds and reports:
- nearest-neighbor spacing stats
- percent of nearest-neighbor distances inside target band
- per-seed PASS/FAIL summary

It does not modify simulation logic or persistent state.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import statistics

import numpy as np
from shapely.geometry import Point

import planning.dump_spot_selector as dump_spot_selector
from geometry.polygon_loader import load_dump_polygon
from geometry.zone_generator import ZoneGenerationConfig, generate_voronoi_zones
from mapping.occupancy_grid import CELL_DUMP_PILE, create_grid_from_polygon
from mapping.terrain_map import initialize_height_map
from simulation.simulation_engine import SimulationConfig, SimulationEngine
from simulation.truck_generator import TruckGeneratorConfig


@dataclass
class SeedResult:
    seed: int
    total_dumps: int
    pile_cells: int
    nn_count: int
    nn_mean: float | None
    nn_median: float | None
    nn_p10: float | None
    nn_p90: float | None
    nn_min: float | None
    nn_max: float | None
    in_band_pct: float | None
    pass_flag: bool
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run spacing calibration benchmark.")
    parser.add_argument("--steps", type=int, default=250, help="Simulation steps per seed.")
    parser.add_argument("--seeds", type=str, default="42,84,126", help="Comma-separated random seeds.")
    parser.add_argument("--zone-count", type=int, default=5, help="Number of generated zones.")
    parser.add_argument("--cell-size", type=float, default=0.5, help="Grid cell size in meters.")
    parser.add_argument("--band-min", type=float, default=3.0, help="Target NN spacing band min (m).")
    parser.add_argument("--band-max", type=float, default=3.5, help="Target NN spacing band max (m).")
    parser.add_argument("--min-dumps", type=int, default=2, help="Minimum dumps required for pass.")
    parser.add_argument("--min-in-band-pct", type=float, default=50.0, help="Minimum %% in target band for pass.")
    parser.add_argument("--max-median", type=float, default=3.8, help="Maximum median NN spacing for pass.")
    parser.add_argument("--min-median", type=float, default=2.8, help="Minimum median NN spacing for pass.")
    return parser.parse_args()


def nearest_neighbor_distances(coords: list[tuple[float, float]]) -> np.ndarray:
    arr = np.asarray(coords, dtype=np.float64)
    if arr.shape[0] < 2:
        return np.asarray([], dtype=np.float64)

    dmins = []
    for i in range(arr.shape[0]):
        diff = arr - arr[i]
        dist = np.sqrt(np.sum(diff * diff, axis=1))
        dist[i] = np.inf
        dmins.append(float(np.min(dist)))

    return np.asarray(dmins, dtype=np.float64)


def run_seed(
    seed: int,
    steps: int,
    zone_count: int,
    cell_size: float,
    band_min: float,
    band_max: float,
    min_dumps: int,
    min_in_band_pct: float,
    min_median: float,
    max_median: float,
) -> SeedResult:
    np.random.seed(seed)

    polygon = load_dump_polygon("data/dump_polygon.json")
    zones = generate_voronoi_zones(
        polygon,
        ZoneGenerationConfig(zone_count=zone_count, random_seed=seed),
    )

    grid, metadata = create_grid_from_polygon(polygon, cell_size=cell_size)
    height_map = initialize_height_map(grid.shape)

    entry = polygon.representative_point()
    generator_config = TruckGeneratorConfig(
        spawn_interval=2,
        truck_speed=0.5,
        entrance_x=float(entry.x),
        entrance_y=float(entry.y),
        initial_payload=1.0,
    )

    engine = SimulationEngine(
        zones,
        SimulationConfig(max_steps=steps, generator_config=generator_config),
        grid,
        height_map,
        metadata,
    )

    for _ in range(steps):
        engine.step()

    ys, xs = np.where(engine.occupancy_grid == CELL_DUMP_PILE)
    coords: list[tuple[float, float]] = []
    for y, x in zip(ys, xs):
        wx = metadata.origin_x + x * metadata.cell_size
        wy = metadata.origin_y + y * metadata.cell_size
        if polygon.contains(Point(wx, wy)):
            coords.append((float(wx), float(wy)))

    nn = nearest_neighbor_distances(coords)

    if nn.size == 0:
        return SeedResult(
            seed=seed,
            total_dumps=int(engine.analytics.total_dumps),
            pile_cells=len(coords),
            nn_count=0,
            nn_mean=None,
            nn_median=None,
            nn_p10=None,
            nn_p90=None,
            nn_min=None,
            nn_max=None,
            in_band_pct=None,
            pass_flag=False,
            reason="insufficient_piles",
        )

    in_band = (nn >= band_min) & (nn <= band_max)
    in_band_pct = 100.0 * float(np.mean(in_band))
    median = float(np.median(nn))

    pass_flag = (
        int(engine.analytics.total_dumps) >= min_dumps
        and in_band_pct >= min_in_band_pct
        and min_median <= median <= max_median
    )

    if int(engine.analytics.total_dumps) < min_dumps:
        reason = "low_dump_count"
    elif in_band_pct < min_in_band_pct:
        reason = "low_in_band_pct"
    elif median < min_median:
        reason = "too_tight"
    elif median > max_median:
        reason = "too_sparse"
    else:
        reason = "ok"

    return SeedResult(
        seed=seed,
        total_dumps=int(engine.analytics.total_dumps),
        pile_cells=len(coords),
        nn_count=int(nn.size),
        nn_mean=float(np.mean(nn)),
        nn_median=median,
        nn_p10=float(np.percentile(nn, 10)),
        nn_p90=float(np.percentile(nn, 90)),
        nn_min=float(np.min(nn)),
        nn_max=float(np.max(nn)),
        in_band_pct=in_band_pct,
        pass_flag=pass_flag,
        reason=reason,
    )


def fmt(val: float | None) -> str:
    if val is None:
        return "n/a"
    return f"{val:.3f}"


def main() -> None:
    args = parse_args()

    # Keep benchmark logs concise.
    dump_spot_selector.DEBUG_SELECTION_LOG = False

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    results: list[SeedResult] = []
    for seed in seeds:
        results.append(
            run_seed(
                seed=seed,
                steps=args.steps,
                zone_count=args.zone_count,
                cell_size=args.cell_size,
                band_min=args.band_min,
                band_max=args.band_max,
                min_dumps=args.min_dumps,
                min_in_band_pct=args.min_in_band_pct,
                min_median=args.min_median,
                max_median=args.max_median,
            )
        )

    print("=== Spacing Benchmark ===")
    print(
        "config: "
        f"steps={args.steps} seeds={seeds} "
        f"band=[{args.band_min:.2f}, {args.band_max:.2f}] "
        f"pass(min_dumps={args.min_dumps}, min_in_band_pct={args.min_in_band_pct:.1f}, "
        f"median_range=[{args.min_median:.2f}, {args.max_median:.2f}])"
    )

    print("\nPer-seed:")
    for r in results:
        status = "PASS" if r.pass_flag else "FAIL"
        print(
            f"seed={r.seed} {status} reason={r.reason} "
            f"dumps={r.total_dumps} piles={r.pile_cells} nn_n={r.nn_count} "
            f"mean={fmt(r.nn_mean)} median={fmt(r.nn_median)} "
            f"p10={fmt(r.nn_p10)} p90={fmt(r.nn_p90)} "
            f"min={fmt(r.nn_min)} max={fmt(r.nn_max)} in_band_pct={fmt(r.in_band_pct)}"
        )

    valid = [r for r in results if r.nn_count > 0]
    pass_count = sum(1 for r in results if r.pass_flag)

    print("\nSummary:")
    print(f"pass_rate={pass_count}/{len(results)} ({(100.0 * pass_count / max(1, len(results))):.1f}%)")

    if valid:
        print(
            "aggregate_valid: "
            f"mean={statistics.fmean(r.nn_mean for r in valid if r.nn_mean is not None):.3f} "
            f"median={statistics.fmean(r.nn_median for r in valid if r.nn_median is not None):.3f} "
            f"p10={statistics.fmean(r.nn_p10 for r in valid if r.nn_p10 is not None):.3f} "
            f"p90={statistics.fmean(r.nn_p90 for r in valid if r.nn_p90 is not None):.3f} "
            f"in_band_pct={statistics.fmean(r.in_band_pct for r in valid if r.in_band_pct is not None):.3f}"
        )
    else:
        print("aggregate_valid: n/a")


if __name__ == "__main__":
    main()
