"""Adapter for the public FOSSGIS Valhalla instance, used for truck-profile routing.
Three distinct truck costing profiles plus Valhalla's own alternates are queried in
parallel and de-duplicated, because a single request rarely returns three usable routes.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from django.conf import settings
from django.core.cache import cache

from core.cache import cache_key
from core.errors import NoRouteFound, ProviderError
from core.geo import Point, decode_polyline, encode_polyline, haversine_miles, simplify
from core.http import get_json

PROVIDER = "valhalla"
POUNDS_PER_METRIC_TONNE = 2204.62
DISPLAY_TOLERANCE_DEGREES = 0.0004
CACHE_SECONDS = 900


@dataclass(frozen=True)
class CostingProfile:
    label: str
    options: dict[str, object] = field(default_factory=dict)


COSTING_PROFILES: tuple[CostingProfile, ...] = (
    CostingProfile("Fastest", {}),
    CostingProfile("Toll-free", {"use_tolls": 0}),
    CostingProfile("Shortest", {"shortest": True}),
)


@dataclass(frozen=True)
class RouteGeometry:
    label: str
    miles: float
    seconds: float
    points: list[Point]
    cumulative_miles: list[float]
    cumulative_seconds: list[float]
    display_polyline: str
    has_toll: bool
    has_highway: bool


def _time_profile(points: list[Point], maneuvers: list[dict]) -> tuple[list[float], list[float]]:
    distances = [0.0]
    for previous, current in zip(points, points[1:]):
        distances.append(distances[-1] + haversine_miles(previous, current))

    seconds = [0.0] * len(points)
    for maneuver in maneuvers:
        start = maneuver.get("begin_shape_index", 0)
        end = min(maneuver.get("end_shape_index", start), len(points) - 1)
        span_miles = distances[end] - distances[start]
        span_seconds = float(maneuver.get("time", 0.0))
        for index in range(start, end):
            leg_miles = distances[index + 1] - distances[index]
            share = (leg_miles / span_miles) if span_miles > 0 else (1.0 / max(1, end - start))
            seconds[index + 1] = seconds[index] + span_seconds * share

    for index in range(1, len(seconds)):
        if seconds[index] < seconds[index - 1]:
            seconds[index] = seconds[index - 1]

    return distances, seconds


def _to_geometry(trip: dict, label: str) -> RouteGeometry | None:
    legs = trip.get("legs") or []
    if not legs:
        return None

    points: list[Point] = []
    maneuvers: list[dict] = []
    for leg in legs:
        shape = decode_polyline(leg.get("shape", ""), precision=6)
        if not shape:
            continue
        shift = len(points)
        if points and shape and points[-1].lat == shape[0].lat and points[-1].lon == shape[0].lon:
            shape = shape[1:]
            shift -= 1
        points.extend(shape)
        for maneuver in leg.get("maneuvers", []):
            shifted = dict(maneuver)
            shifted["begin_shape_index"] = maneuver.get("begin_shape_index", 0) + max(0, shift)
            shifted["end_shape_index"] = maneuver.get("end_shape_index", 0) + max(0, shift)
            maneuvers.append(shifted)

    if len(points) < 2:
        return None

    distances, seconds = _time_profile(points, maneuvers)
    summary = trip.get("summary", {})
    return RouteGeometry(
        label=label,
        miles=float(summary.get("length", distances[-1])),
        seconds=float(summary.get("time", seconds[-1])),
        points=points,
        cumulative_miles=distances,
        cumulative_seconds=seconds,
        display_polyline=encode_polyline(simplify(points, DISPLAY_TOLERANCE_DEGREES), precision=6),
        has_toll=bool(summary.get("has_toll", False)),
        has_highway=bool(summary.get("has_highway", False)),
    )


def _signature(points: list[Point]) -> tuple:
    step = max(1, len(points) // 24)
    return tuple((round(p.lat, 2), round(p.lon, 2)) for p in points[::step])


def _is_duplicate(candidate: RouteGeometry, kept: list[RouteGeometry]) -> bool:
    signature = _signature(candidate.points)
    for existing in kept:
        if signature == _signature(existing.points):
            return True
        if abs(candidate.miles - existing.miles) < 0.5 and abs(candidate.seconds - existing.seconds) < 60:
            return True
    return False


def _request(origin: Point, destination: Point, weight_lb: float, profile: CostingProfile) -> list[RouteGeometry]:
    truck_options: dict[str, object] = {"weight": round(weight_lb / POUNDS_PER_METRIC_TONNE, 2)}
    truck_options.update(profile.options)

    body = {
        "locations": [
            {"lat": origin.lat, "lon": origin.lon},
            {"lat": destination.lat, "lon": destination.lon},
        ],
        "costing": "truck",
        "costing_options": {"truck": truck_options},
        "alternates": 2,
        "directions_options": {"units": "miles"},
    }

    query = {"json": json.dumps(body, separators=(",", ":"))}
    key = cache_key("valhalla", profile.label, query["json"])
    cached = cache.get(key)
    if cached is not None:
        return cached

    payload = get_json(PROVIDER, settings.VALHALLA_URL, params=query, timeout=40.0)
    trips = []
    if payload.get("trip"):
        trips.append(payload["trip"])
    for alternate in payload.get("alternates", []):
        if alternate.get("trip"):
            trips.append(alternate["trip"])

    geometries = []
    for index, trip in enumerate(trips):
        label = profile.label if index == 0 else f"{profile.label} alternate {index}"
        geometry = _to_geometry(trip, label)
        if geometry:
            geometries.append(geometry)

    cache.set(key, geometries, CACHE_SECONDS)
    return geometries


def fetch_routes(origin: Point, destination: Point, weight_lb: float, limit: int = 3) -> list[RouteGeometry]:
    errors: list[str] = []
    collected: list[RouteGeometry] = []

    with ThreadPoolExecutor(max_workers=len(COSTING_PROFILES)) as pool:
        futures = [pool.submit(_request, origin, destination, weight_lb, profile) for profile in COSTING_PROFILES]
        for future in futures:
            try:
                collected.extend(future.result())
            except ProviderError as exc:
                errors.append(exc.message)

    if not collected:
        raise NoRouteFound(PROVIDER, "; ".join(errors) or "no route between the given points")

    collected.sort(key=lambda geometry: geometry.seconds)
    unique: list[RouteGeometry] = []
    for candidate in collected:
        if not _is_duplicate(candidate, unique):
            unique.append(candidate)
        if len(unique) == limit:
            break

    return unique
