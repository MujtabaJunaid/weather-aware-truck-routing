"""Deterministic stand-ins for route geometry and hourly forecasts used by the tests.
Routes are straight great-circle lines with a constant speed, which makes interpolated
mileage and arrival times exactly predictable.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from core.geo import Point, cumulative_miles, encode_polyline, interpolate
from providers.open_meteo import HourlySeries
from providers.valhalla import RouteGeometry


def straight_route(label: str, start: Point, end: Point, mph: float = 55.0, nodes: int = 200) -> RouteGeometry:
    points = [interpolate(start, end, index / (nodes - 1)) for index in range(nodes)]
    distances = cumulative_miles(points)
    seconds = [mile / mph * 3600 for mile in distances]

    return RouteGeometry(
        label=label,
        miles=distances[-1],
        seconds=seconds[-1],
        points=points,
        cumulative_miles=distances,
        cumulative_seconds=seconds,
        display_polyline=encode_polyline(points),
        has_toll=False,
        has_highway=True,
    )


def flat_series(
    anchor: datetime,
    hours: int = 96,
    wind_mph: float = 5.0,
    gust_mph: float = 8.0,
    rain_in_hr: float = 0.0,
    snow_in_hr: float = 0.0,
) -> HourlySeries:
    start = anchor.replace(minute=0, second=0, microsecond=0, tzinfo=None)
    return HourlySeries(
        times=[start + timedelta(hours=step) for step in range(hours)],
        wind_mph=[wind_mph] * hours,
        gust_mph=[gust_mph] * hours,
        rain_in_hr=[rain_in_hr] * hours,
        snow_in_hr=[snow_in_hr] * hours,
    )
