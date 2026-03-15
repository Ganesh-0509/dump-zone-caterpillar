"""Generate Voronoi zones clipped to a dump polygon."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.spatial import Voronoi
from shapely.geometry import MultiPolygon, Point, Polygon


@dataclass(frozen=True)
class ZoneGenerationConfig:
    """Configuration for Voronoi zone generation."""

    zone_count: int = 8
    random_seed: int = 42


def _sample_points_in_polygon(
    polygon: Polygon,
    point_count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Sample random points uniformly from a polygon bounding box via rejection sampling."""
    if point_count < 1:
        raise ValueError("point_count must be at least 1.")

    min_x, min_y, max_x, max_y = polygon.bounds
    points: list[tuple[float, float]] = []

    max_attempts = max(1000, point_count * 500)
    attempts = 0

    while len(points) < point_count and attempts < max_attempts:
        x = rng.uniform(min_x, max_x)
        y = rng.uniform(min_y, max_y)
        if polygon.contains(Point(x, y)):
            points.append((x, y))
        attempts += 1

    if len(points) < point_count:
        raise RuntimeError(
            "Unable to sample enough points inside polygon. "
            "Try a simpler polygon or lower zone_count."
        )

    return np.asarray(points)


def _voronoi_finite_polygons_2d(vor: Voronoi, radius: float | None = None) -> tuple[list[list[int]], np.ndarray]:
    """Reconstruct finite Voronoi regions from scipy Voronoi output."""
    if vor.points.shape[1] != 2:
        raise ValueError("Voronoi input must be 2D.")

    new_regions: list[list[int]] = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = np.ptp(vor.points, axis=0).max() * 2.0

    all_ridges: dict[int, list[tuple[int, int, int]]] = {}
    for (point_a, point_b), (vertex_a, vertex_b) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(point_a, []).append((point_b, vertex_a, vertex_b))
        all_ridges.setdefault(point_b, []).append((point_a, vertex_a, vertex_b))

    for point_index, region_index in enumerate(vor.point_region):
        vertices = vor.regions[region_index]

        if all(vertex >= 0 for vertex in vertices):
            new_regions.append(vertices)
            continue

        region_ridges = all_ridges[point_index]
        new_region = [vertex for vertex in vertices if vertex >= 0]

        for other_point_index, vertex_a, vertex_b in region_ridges:
            if vertex_a < 0 and vertex_b < 0:
                continue
            if vertex_a >= 0 and vertex_b >= 0:
                continue

            finite_vertex = vertex_a if vertex_a >= 0 else vertex_b

            tangent = vor.points[other_point_index] - vor.points[point_index]
            tangent /= np.linalg.norm(tangent)
            normal = np.array([-tangent[1], tangent[0]])

            midpoint = vor.points[[point_index, other_point_index]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, normal)) * normal
            far_point = vor.vertices[finite_vertex] + direction * radius

            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        ordered_vertices = np.asarray([new_vertices[vertex] for vertex in new_region])
        region_center = ordered_vertices.mean(axis=0)
        angles = np.arctan2(ordered_vertices[:, 1] - region_center[1], ordered_vertices[:, 0] - region_center[0])
        new_region = np.asarray(new_region)[np.argsort(angles)].tolist()

        new_regions.append(new_region)

    return new_regions, np.asarray(new_vertices)


def generate_voronoi_zones(polygon: Polygon, config: ZoneGenerationConfig) -> list[Polygon]:
    """Generate Voronoi zones and clip them to the given polygon."""
    if config.zone_count < 2:
        raise ValueError("zone_count must be at least 2 for Voronoi partitioning.")

    rng = np.random.default_rng(config.random_seed)
    seed_points = _sample_points_in_polygon(polygon, config.zone_count, rng)

    voronoi = Voronoi(seed_points)
    regions, vertices = _voronoi_finite_polygons_2d(voronoi)

    clipped_zones: list[Polygon] = []
    for region in regions:
        candidate = Polygon(vertices[region])
        clipped = candidate.intersection(polygon)

        if clipped.is_empty:
            continue

        if isinstance(clipped, Polygon):
            if clipped.area > 0:
                clipped_zones.append(clipped)
            continue

        if isinstance(clipped, MultiPolygon):
            largest = max(clipped.geoms, key=lambda g: g.area)
            if largest.area > 0:
                clipped_zones.append(largest)

    return clipped_zones
