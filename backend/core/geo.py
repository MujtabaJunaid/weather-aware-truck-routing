"""Great-circle geometry, polyline decoding and distance/time interpolation along a route.
Distances are statute miles throughout to match the imperial thresholds in the risk rules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EARTH_RADIUS_MILES = 3958.7613


@dataclass(frozen=True)
class Point:
    lat: float
    lon: float


@dataclass(frozen=True)
class Place:
    label: str
    lat: float
    lon: float

    @property
    def point(self) -> Point:
        return Point(self.lat, self.lon)


def haversine_miles(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    delta_lat = lat2 - lat1
    delta_lon = math.radians(b.lon - a.lon)
    h = math.sin(delta_lat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(min(1.0, h)))


def decode_polyline(encoded: str, precision: int = 6) -> list[Point]:
    points: list[Point] = []
    index = lat = lon = 0
    factor = 10**precision
    length = len(encoded)

    while index < length:
        for axis in range(2):
            shift = result = 0
            while index < length:
                byte = ord(encoded[index]) - 63
                index += 1
                result |= (byte & 0x1F) << shift
                shift += 5
                if byte < 0x20:
                    break
            delta = ~(result >> 1) if result & 1 else result >> 1
            if axis == 0:
                lat += delta
            else:
                lon += delta
        points.append(Point(lat / factor, lon / factor))

    return points


def cumulative_miles(points: list[Point]) -> list[float]:
    totals = [0.0]
    for previous, current in zip(points, points[1:]):
        totals.append(totals[-1] + haversine_miles(previous, current))
    return totals


def interpolate(a: Point, b: Point, fraction: float) -> Point:
    return Point(a.lat + (b.lat - a.lat) * fraction, a.lon + (b.lon - a.lon) * fraction)


def initial_bearing(a: Point, b: Point) -> float:
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    delta_lon = math.radians(b.lon - a.lon)
    y = math.sin(delta_lon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(delta_lon)
    return math.degrees(math.atan2(y, x)) % 360.0


def offset(origin: Point, bearing_degrees: float, distance_miles: float) -> Point:
    angular = distance_miles / EARTH_RADIUS_MILES
    bearing = math.radians(bearing_degrees)
    lat1, lon1 = math.radians(origin.lat), math.radians(origin.lon)

    lat2 = math.asin(math.sin(lat1) * math.cos(angular) + math.cos(lat1) * math.sin(angular) * math.cos(bearing))
    lon2 = lon1 + math.atan2(
        math.sin(bearing) * math.sin(angular) * math.cos(lat1),
        math.cos(angular) - math.sin(lat1) * math.sin(lat2),
    )
    return Point(math.degrees(lat2), (math.degrees(lon2) + 540.0) % 360.0 - 180.0)


def encode_polyline(points: list[Point], precision: int = 6) -> str:
    factor = 10**precision
    chunks: list[str] = []
    previous_lat = previous_lon = 0

    for point in points:
        lat = round(point.lat * factor)
        lon = round(point.lon * factor)
        for delta in (lat - previous_lat, lon - previous_lon):
            value = ~(delta << 1) if delta < 0 else delta << 1
            while value >= 0x20:
                chunks.append(chr((0x20 | (value & 0x1F)) + 63))
                value >>= 5
            chunks.append(chr(value + 63))
        previous_lat, previous_lon = lat, lon

    return "".join(chunks)


def simplify(points: list[Point], tolerance_degrees: float) -> list[Point]:
    if len(points) < 3:
        return list(points)

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    squared_tolerance = tolerance_degrees * tolerance_degrees

    while stack:
        start, end = stack.pop()
        if end <= start + 1:
            continue

        ax, ay = points[start].lon, points[start].lat
        dx, dy = points[end].lon - ax, points[end].lat - ay
        norm = dx * dx + dy * dy

        furthest_index, furthest_distance = start, -1.0
        for index in range(start + 1, end):
            px, py = points[index].lon, points[index].lat
            if norm > 0:
                position = ((px - ax) * dx + (py - ay) * dy) / norm
                position = min(1.0, max(0.0, position))
                cx, cy = ax + position * dx, ay + position * dy
            else:
                cx, cy = ax, ay
            distance = (px - cx) ** 2 + (py - cy) ** 2
            if distance > furthest_distance:
                furthest_index, furthest_distance = index, distance

        if furthest_distance > squared_tolerance:
            keep[furthest_index] = True
            stack.append((start, furthest_index))
            stack.append((furthest_index, end))

    return [point for point, kept in zip(points, keep) if kept]
