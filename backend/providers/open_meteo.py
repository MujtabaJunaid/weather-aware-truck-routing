"""Adapter for the Open-Meteo hourly forecast API, requested directly in imperial units.
Upstream cost is roughly constant per location rather than per byte, so lookups are snapped
to a shared grid, cached per cell and batched across a small number of parallel requests.
"""

from __future__ import annotations

from bisect import bisect_left
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from django.conf import settings
from django.core.cache import cache

from core.cache import cache_key
from core.errors import ProviderUnavailable
from core.geo import Point
from core.http import get_json
from risk.scoring import WeatherSample

PROVIDER = "open-meteo"
HOURLY_FIELDS = "wind_speed_10m,wind_gusts_10m,rain,snowfall"
MAX_COORDS_PER_REQUEST = 30
MAX_PARALLEL_REQUESTS = 3
CACHE_SECONDS = 900
HOUR_FORMAT = "%Y-%m-%dT%H:00"


@dataclass(frozen=True)
class HourlySeries:
    times: list[datetime]
    wind_mph: list[float]
    gust_mph: list[float]
    rain_in_hr: list[float]
    snow_in_hr: list[float]

    def index_at(self, when: datetime) -> int:
        if not self.times:
            raise ProviderUnavailable(PROVIDER, "empty forecast series")

        target = when.astimezone(timezone.utc).replace(tzinfo=None)
        position = bisect_left(self.times, target)
        if position == 0:
            return 0
        if position >= len(self.times):
            return len(self.times) - 1

        before, after = self.times[position - 1], self.times[position]
        return position - 1 if (target - before) <= (after - target) else position

    def sample_at(self, when: datetime) -> WeatherSample:
        index = self.index_at(when)
        return WeatherSample(
            wind_mph=self.wind_mph[index],
            wind_gust_mph=self.gust_mph[index],
            rain_in_hr=self.rain_in_hr[index],
            snow_in_hr=self.snow_in_hr[index],
        )


def _snap(point: Point) -> tuple[float, float]:
    step = settings.WEATHER_SNAP_DEGREES
    return (round(round(point.lat / step) * step, 4), round(round(point.lon / step) * step, 4))


def _floats(values: list) -> list[float]:
    return [float(value) if value is not None else 0.0 for value in values]


def _parse(block: dict) -> HourlySeries:
    hourly = block.get("hourly") or {}
    return HourlySeries(
        times=[datetime.fromisoformat(stamp) for stamp in hourly.get("time", [])],
        wind_mph=_floats(hourly.get("wind_speed_10m", [])),
        gust_mph=_floats(hourly.get("wind_gusts_10m", [])),
        rain_in_hr=_floats(hourly.get("rain", [])),
        snow_in_hr=_floats(hourly.get("snowfall", [])),
    )


def _cache_key(cell: tuple[float, float], start: str, end: str) -> str:
    return cache_key("open-meteo", cell[0], cell[1], start, end)


def _fetch_chunk(cells: list[tuple[float, float]], start: str, end: str) -> list[HourlySeries]:
    params = {
        "latitude": ",".join(f"{lat:.4f}" for lat, _ in cells),
        "longitude": ",".join(f"{lon:.4f}" for _, lon in cells),
        "hourly": HOURLY_FIELDS,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC",
        "start_hour": start,
        "end_hour": end,
    }
    payload = get_json(PROVIDER, settings.OPEN_METEO_URL, params=params, timeout=90.0)
    blocks = payload if isinstance(payload, list) else [payload]
    series = [_parse(block) for block in blocks]

    if len(series) != len(cells):
        raise ProviderUnavailable(PROVIDER, f"expected {len(cells)} forecast series, received {len(series)}")
    return series


def fetch_hourly(points: list[Point], start: datetime, end: datetime) -> list[HourlySeries]:
    if not points:
        return []

    window_start = start.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    window_end = (end.astimezone(timezone.utc) + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    start_hour = window_start.strftime(HOUR_FORMAT)
    end_hour = max(window_end, window_start + timedelta(hours=1)).strftime(HOUR_FORMAT)

    cells = [_snap(point) for point in points]
    resolved: dict[tuple[float, float], HourlySeries] = {}
    missing: list[tuple[float, float]] = []

    for cell in dict.fromkeys(cells):
        cached = cache.get(_cache_key(cell, start_hour, end_hour))
        if cached is not None:
            resolved[cell] = cached
        else:
            missing.append(cell)

    if missing:
        size = min(MAX_COORDS_PER_REQUEST, -(-len(missing) // MAX_PARALLEL_REQUESTS))
        chunks = [missing[index : index + size] for index in range(0, len(missing), size)]
        with ThreadPoolExecutor(max_workers=min(MAX_PARALLEL_REQUESTS, len(chunks))) as pool:
            results = list(pool.map(lambda chunk: _fetch_chunk(chunk, start_hour, end_hour), chunks))

        for chunk, chunk_series in zip(chunks, results):
            for cell, series in zip(chunk, chunk_series):
                resolved[cell] = series
                cache.set(_cache_key(cell, start_hour, end_hour), series, CACHE_SECONDS)

    return [resolved[cell] for cell in cells]
