"""Shaping of planning dataclasses into the JSON payloads the frontend consumes.
Isolated from the service layer so response field names can change without touching the
routing, weather or risk logic.
"""

from __future__ import annotations

from core.geo import Place
from risk.rules import RiskLevel

from .services import Heatmap, ScoredCheckpoint, ScoredRoute, TripPlan


def place(value: Place) -> dict:
    return {"label": value.label, "lat": value.lat, "lon": value.lon}


def _checkpoint(scored: ScoredCheckpoint) -> dict:
    return {
        "sequence": scored.checkpoint.sequence,
        "miles_from_origin": round(scored.checkpoint.miles_from_origin, 2),
        "segment_miles": round(scored.checkpoint.segment_miles, 2),
        "lat": round(scored.checkpoint.point.lat, 5),
        "lon": round(scored.checkpoint.point.lon, 5),
        "eta": scored.eta.isoformat(),
        "level": scored.risk.overall.slug,
        "driver": scored.risk.driver,
        "levels": {
            "wind": scored.risk.wind.slug,
            "rain": scored.risk.rain.slug,
            "snow": scored.risk.snow.slug,
            "load": scored.risk.load.slug,
        },
        "weather": {
            "wind_mph": round(scored.weather.wind_mph, 1),
            "wind_gust_mph": round(scored.weather.wind_gust_mph, 1),
            "rain_in_hr": round(scored.weather.rain_in_hr, 3),
            "snow_in_hr": round(scored.weather.snow_in_hr, 3),
        },
    }


def _route(route: ScoredRoute, recommended_id: str) -> dict:
    metrics = route.metrics
    return {
        "id": route.identifier,
        "label": route.geometry.label,
        "polyline": route.geometry.display_polyline,
        "distance_miles": round(metrics.total_miles, 1),
        "duration_seconds": round(metrics.duration_seconds),
        "arrival_time": route.arrival.isoformat(),
        "has_toll": route.geometry.has_toll,
        "has_highway": route.geometry.has_highway,
        "is_recommended": route.identifier == recommended_id,
        "is_blocked": metrics.is_blocked,
        "worst_level": metrics.worst_level.slug,
        "average_risk": round(metrics.average_risk, 3),
        "miles_by_level": {level.slug: round(metrics.miles_by_level[level], 1) for level in RiskLevel},
        "checkpoints": [_checkpoint(scored) for scored in route.checkpoints],
    }


def trip_plan(plan: TripPlan) -> dict:
    return {
        "origin": place(plan.origin),
        "destination": place(plan.destination),
        "departure_time": plan.departure.isoformat(),
        "load_weight_lb": plan.load_weight_lb,
        "checkpoint_interval_miles": plan.interval_miles,
        "recommended_route_id": plan.recommended_id,
        "recommendation_reason": plan.reason,
        "briefing": plan.briefing,
        "briefing_source": plan.briefing_source,
        "routes": [_route(route, plan.recommended_id) for route in plan.routes],
    }


def heatmap(value: Heatmap) -> dict:
    return {
        "hours": [moment.isoformat() for moment in value.hours],
        "points": [
            {
                "lat": round(cell.corridor_point.point.lat, 4),
                "lon": round(cell.corridor_point.point.lon, 4),
                "miles_from_origin": round(cell.corridor_point.miles_from_origin, 1),
                "lateral_miles": cell.corridor_point.lateral_miles,
                "levels": cell.levels,
            }
            for cell in value.cells
        ],
    }
