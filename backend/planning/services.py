"""Orchestration for trip planning and corridor heatmaps.
Routes, checkpoint weather and risk scoring are combined here; the recommendation is decided
entirely by the deterministic risk engine, and the language model only narrates the result.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from core.geo import Place, cumulative_miles, decode_polyline
from providers import geocoding, groq, open_meteo, valhalla
from providers.open_meteo import HourlySeries
from providers.valhalla import RouteGeometry
from risk.recommendation import RiskSegment, RouteRiskMetrics, best_index, ranking_key, summarize
from risk.scoring import RiskAssessment, WeatherSample, assess

from .checkpoints import Checkpoint, sample
from .corridor import CorridorPoint, build

HEATMAP_HOURS = 48


@dataclass(frozen=True)
class ScoredCheckpoint:
    checkpoint: Checkpoint
    eta: datetime
    weather: WeatherSample
    risk: RiskAssessment


@dataclass(frozen=True)
class ScoredRoute:
    identifier: str
    geometry: RouteGeometry
    checkpoints: list[ScoredCheckpoint]
    metrics: RouteRiskMetrics
    arrival: datetime


@dataclass(frozen=True)
class TripPlan:
    origin: Place
    destination: Place
    departure: datetime
    load_weight_lb: float
    interval_miles: int
    routes: list[ScoredRoute]
    recommended_id: str
    reason: str
    briefing: str
    briefing_source: str


@dataclass(frozen=True)
class HeatmapCell:
    corridor_point: CorridorPoint
    levels: list[int]


@dataclass(frozen=True)
class Heatmap:
    hours: list[datetime]
    cells: list[HeatmapCell]


def _resolve(value: str | None, lat: float | None, lon: float | None) -> Place:
    if lat is not None and lon is not None:
        return Place(label=value or f"{lat:.4f}, {lon:.4f}", lat=lat, lon=lon)
    return geocoding.resolve(value or "")


def _criterion_reason(best: RouteRiskMetrics, runner_up: RouteRiskMetrics, label: str) -> str:
    comparisons = (
        ("fewest no-travel miles", best.no_travel_miles, runner_up.no_travel_miles, 0.5, "{:.0f}"),
        ("fewest severe-risk miles", best.severe_miles, runner_up.severe_miles, 0.5, "{:.0f}"),
        ("fewest high-risk miles", best.high_miles, runner_up.high_miles, 0.5, "{:.0f}"),
        ("the lowest average risk", best.average_risk, runner_up.average_risk, 0.01, "{:.2f}"),
    )
    for phrase, mine, theirs, tolerance, fmt in comparisons:
        if theirs - mine > tolerance:
            return (
                f"{label} is recommended on {phrase} "
                f"({fmt.format(mine)} against {fmt.format(theirs)} on the next-best route)."
            )

    hours = best.duration_seconds / 3600
    return (
        f"{label} is recommended: it ties the other routes on weather risk and is the quickest "
        f"of those at {hours:.1f} h."
    )


def _briefing_context(plan_routes: list[ScoredRoute], recommended: ScoredRoute, reason: str, load_weight_lb: float) -> str:
    lines = [
        f"Load weight: {load_weight_lb:,.0f} lb",
        f"Deterministic decision: {reason}",
        "",
        "Route options:",
    ]
    for route in plan_routes:
        metrics = route.metrics
        marker = " (RECOMMENDED)" if route.identifier == recommended.identifier else ""
        lines.append(
            f"- {route.geometry.label}{marker}: {metrics.total_miles:.0f} mi, "
            f"{metrics.duration_seconds / 3600:.1f} h, worst {metrics.worst_level.slug}, "
            f"avg risk {metrics.average_risk:.2f}, severe {metrics.severe_miles:.0f} mi, "
            f"high {metrics.high_miles:.0f} mi"
        )

    worst = sorted(
        recommended.checkpoints,
        key=lambda scored: (scored.risk.overall, scored.weather.wind_mph),
        reverse=True,
    )[:4]
    lines.extend(["", "Worst checkpoints on the recommended route:"])
    for scored in worst:
        lines.append(
            f"- mile {scored.checkpoint.miles_from_origin:.0f} at {scored.eta:%Y-%m-%d %H:%M} UTC: "
            f"{scored.risk.overall.slug} (driver {scored.risk.driver}), wind {scored.weather.wind_mph:.0f} mph "
            f"gusting {scored.weather.wind_gust_mph:.0f}, rain {scored.weather.rain_in_hr:.2f} in/hr, "
            f"snow {scored.weather.snow_in_hr:.2f} in/hr"
        )

    return "\n".join(lines)


def plan_trip(
    origin_query: str | None,
    destination_query: str | None,
    departure: datetime,
    load_weight_lb: float,
    interval_miles: int,
    origin_lat: float | None = None,
    origin_lon: float | None = None,
    destination_lat: float | None = None,
    destination_lon: float | None = None,
) -> TripPlan:
    with ThreadPoolExecutor(max_workers=2) as pool:
        origin_task = pool.submit(_resolve, origin_query, origin_lat, origin_lon)
        destination_task = pool.submit(_resolve, destination_query, destination_lat, destination_lon)
        origin = origin_task.result()
        destination = destination_task.result()

    geometries = valhalla.fetch_routes(origin.point, destination.point, load_weight_lb, limit=3)
    sampled = [sample(geometry, interval_miles) for geometry in geometries]

    longest_seconds = max(geometry.seconds for geometry in geometries)
    flattened = [checkpoint.point for checkpoints in sampled for checkpoint in checkpoints]
    series = open_meteo.fetch_hourly(flattened, departure, departure + timedelta(seconds=longest_seconds))

    routes: list[ScoredRoute] = []
    cursor = 0
    for index, (geometry, checkpoints) in enumerate(zip(geometries, sampled)):
        scored_checkpoints: list[ScoredCheckpoint] = []
        segments: list[RiskSegment] = []

        for checkpoint in checkpoints:
            forecast: HourlySeries = series[cursor]
            cursor += 1
            eta = departure + timedelta(seconds=checkpoint.elapsed_seconds)
            weather = forecast.sample_at(eta)
            risk = assess(weather, load_weight_lb)
            scored_checkpoints.append(
                ScoredCheckpoint(checkpoint=checkpoint, eta=eta, weather=weather, risk=risk)
            )
            segments.append(RiskSegment(miles=checkpoint.segment_miles, level=risk.overall))

        metrics = summarize(segments, geometry.seconds)
        routes.append(
            ScoredRoute(
                identifier=f"route-{index + 1}",
                geometry=geometry,
                checkpoints=scored_checkpoints,
                metrics=metrics,
                arrival=departure + timedelta(seconds=geometry.seconds),
            )
        )

    chosen = best_index(route.metrics for route in routes)
    recommended = routes[chosen]

    ordered = sorted(routes, key=lambda route: ranking_key(route.metrics))
    runner_up = ordered[1].metrics if len(ordered) > 1 else recommended.metrics
    reason = _criterion_reason(recommended.metrics, runner_up, recommended.geometry.label)

    briefing = groq.generate_briefing(_briefing_context(routes, recommended, reason, load_weight_lb))
    return TripPlan(
        origin=origin,
        destination=destination,
        departure=departure,
        load_weight_lb=load_weight_lb,
        interval_miles=interval_miles,
        routes=routes,
        recommended_id=recommended.identifier,
        reason=reason,
        briefing=briefing or reason,
        briefing_source="groq" if briefing else "deterministic",
    )


def build_heatmap(polyline: str, departure: datetime, load_weight_lb: float, hours: int = HEATMAP_HOURS) -> Heatmap:
    points = decode_polyline(polyline, precision=6)
    distances = cumulative_miles(points)
    corridor = build(points, distances)

    anchor = departure.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    timeline = [anchor + timedelta(hours=step) for step in range(hours + 1)]
    series = open_meteo.fetch_hourly([entry.point for entry in corridor], timeline[0], timeline[-1])

    cells: list[HeatmapCell] = []
    for corridor_point, forecast in zip(corridor, series):
        levels = [int(assess(forecast.sample_at(moment), load_weight_lb).overall) for moment in timeline]
        cells.append(HeatmapCell(corridor_point=corridor_point, levels=levels))

    return Heatmap(hours=timeline, cells=cells)
