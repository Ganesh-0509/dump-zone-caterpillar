"""Load and validate dump polygons from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from shapely.geometry import Polygon

REQUIRED_KEY = "dump_polygon"

def _validate_coordinate_pairs(coordinates: Iterable[Iterable[float]]) -> list[tuple[float, float]]:
    """Validate coordinate pairs and return them as a list of tuples."""
    parsed: list[tuple[float, float]] = []
    for index, point in enumerate(coordinates):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError(f"Point at index {index} must be a pair [x, y].")

        x, y = point
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(f"Point at index {index} must contain numeric values.")

        parsed.append((float(x), float(y)))

    if len(parsed) < 3:
        raise ValueError("A polygon requires at least 3 coordinate pairs.")

    return parsed


def load_dump_polygon(json_path: str | Path) -> Polygon:
    """Load a dump polygon from JSON and return it as a shapely Polygon."""
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Polygon JSON file does not exist: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if REQUIRED_KEY not in data:
        raise KeyError(f"Missing '{REQUIRED_KEY}' key in JSON file: {path}")

    coordinates = _validate_coordinate_pairs(data[REQUIRED_KEY])
    polygon = Polygon(coordinates)

    if not polygon.is_valid:
        raise ValueError("Loaded polygon is invalid (self-intersecting or malformed).")
    if polygon.area <= 0:
        raise ValueError("Loaded polygon has zero area.")

    return polygon
