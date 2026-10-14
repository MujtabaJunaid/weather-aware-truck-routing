"""Construction of the sampling grid used by the trip-corridor weather heatmap.
Points are laid out along the route and offset perpendicular to the local bearing, with the
along-track spacing derived from the route length so the grid never exceeds its point budget.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

from core.geo import Point, initial_bearing, interpolate, offset

DEFAULT_LATERAL_OFFSETS_MILES = (-30.0, 0.0, 30.0)
DEFAULT_MAX_POINTS = 48
MIN_ALONG_SPACING_MILES = 25.0


@dataclass(frozen=True)
class CorridorPoint:
    point: Point
    miles_from_origin: float
    lateral_miles: float


def _locate(distances: list[float], points: list[Point], target_miles: float) -> tuple[Point, float]:
    position = bisect_left(distances, target_miles)
    if position <= 0:
        return points[0], initial_bearing(points[0], points[min(1, len(points) - 1)])
    if position >= len(distances):
        return points[-1], initial_bearing(points[max(0, len(points) - 2)], points[-1])

    span = distances[position] - distances[position - 1]
    fraction = (target_miles - distances[position - 1]) / span if span > 0 else 0.0
    located = interpolate(points[position - 1], points[position], fraction)
    return located, initial_bearing(points[position - 1], points[position])


def build(
    points: list[Point],
    distances: list[float],
    lateral_offsets_miles: tuple[float, ...] = DEFAULT_LATERAL_OFFSETS_MILES,
    max_points: int = DEFAULT_MAX_POINTS,
) -> list[CorridorPoint]:
    total_miles = distances[-1]
    along_budget = max(2, max_points // len(lateral_offsets_miles))
    spacing = max(MIN_ALONG_SPACING_MILES, total_miles / (along_budget - 1)) if total_miles > 0 else 0.0

    targets: list[float] = [0.0]
    if spacing > 0:
        cursor = spacing
        while cursor < total_miles:
            targets.append(cursor)
            cursor += spacing
    if total_miles > 0 and targets[-1] < total_miles:
        targets.append(total_miles)

    corridor: list[CorridorPoint] = []
    for target in targets:
        located, bearing = _locate(distances, points, target)
        for lateral in lateral_offsets_miles:
            if lateral == 0.0:
                shifted = located
            else:
                shifted = offset(located, (bearing + 90.0) % 360.0, lateral)
            corridor.append(
                CorridorPoint(point=shifted, miles_from_origin=target, lateral_miles=lateral)
            )

    return corridor
