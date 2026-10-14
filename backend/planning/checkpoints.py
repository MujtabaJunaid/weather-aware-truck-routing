"""Sampling of a route at a fixed mile interval, with interpolated position and elapsed time.
Each checkpoint is attributed the stretch of road midway to its neighbours, so the per-level
mileage of a route sums to its true length regardless of the interval chosen.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

from core.geo import Point, interpolate
from providers.valhalla import RouteGeometry

ALLOWED_INTERVALS_MILES = (10, 25, 50)


@dataclass(frozen=True)
class Checkpoint:
    sequence: int
    miles_from_origin: float
    segment_miles: float
    point: Point
    elapsed_seconds: float


def _locate(geometry: RouteGeometry, target_miles: float) -> tuple[Point, float]:
    distances = geometry.cumulative_miles
    seconds = geometry.cumulative_seconds

    position = bisect_left(distances, target_miles)
    if position <= 0:
        return geometry.points[0], seconds[0]
    if position >= len(distances):
        return geometry.points[-1], seconds[-1]

    span = distances[position] - distances[position - 1]
    fraction = (target_miles - distances[position - 1]) / span if span > 0 else 0.0
    point = interpolate(geometry.points[position - 1], geometry.points[position], fraction)
    elapsed = seconds[position - 1] + (seconds[position] - seconds[position - 1]) * fraction
    return point, elapsed


def sample(geometry: RouteGeometry, interval_miles: int) -> list[Checkpoint]:
    total_miles = geometry.cumulative_miles[-1]

    targets = [0.0]
    cursor = float(interval_miles)
    while cursor < total_miles:
        targets.append(cursor)
        cursor += interval_miles
    if total_miles > 0 and targets[-1] < total_miles:
        targets.append(total_miles)

    checkpoints: list[Checkpoint] = []
    for index, target in enumerate(targets):
        previous_edge = (targets[index - 1] + target) / 2 if index > 0 else targets[0]
        next_edge = (target + targets[index + 1]) / 2 if index < len(targets) - 1 else targets[-1]
        point, elapsed = _locate(geometry, target)
        checkpoints.append(
            Checkpoint(
                sequence=index,
                miles_from_origin=target,
                segment_miles=max(0.0, next_edge - previous_edge),
                point=point,
                elapsed_seconds=elapsed,
            )
        )

    return checkpoints
