"""Distance-weighted route risk metrics and the ranking that picks the recommended route.
Ranking follows the spec order (fewest severe miles, then high miles, then average risk,
then travel time) with no-travel mileage promoted above severe as a hard viability gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .rules import RiskLevel


@dataclass(frozen=True)
class RiskSegment:
    miles: float
    level: RiskLevel


@dataclass(frozen=True)
class RouteRiskMetrics:
    total_miles: float
    duration_seconds: float
    average_risk: float
    miles_by_level: dict[RiskLevel, float]

    @property
    def no_travel_miles(self) -> float:
        return self.miles_by_level[RiskLevel.NO_TRAVEL]

    @property
    def severe_miles(self) -> float:
        return self.miles_by_level[RiskLevel.SEVERE]

    @property
    def high_miles(self) -> float:
        return self.miles_by_level[RiskLevel.HIGH]

    @property
    def is_blocked(self) -> bool:
        return self.no_travel_miles > 0

    @property
    def worst_level(self) -> RiskLevel:
        present = [level for level, miles in self.miles_by_level.items() if miles > 0]
        return max(present) if present else RiskLevel.LOW


def summarize(segments: Sequence[RiskSegment], duration_seconds: float) -> RouteRiskMetrics:
    miles_by_level = {level: 0.0 for level in RiskLevel}
    for segment in segments:
        miles_by_level[segment.level] += segment.miles

    total_miles = sum(miles_by_level.values())
    weighted = sum(segment.miles * int(segment.level) for segment in segments)
    average_risk = weighted / total_miles if total_miles else 0.0

    return RouteRiskMetrics(
        total_miles=total_miles,
        duration_seconds=duration_seconds,
        average_risk=average_risk,
        miles_by_level=miles_by_level,
    )


def ranking_key(metrics: RouteRiskMetrics) -> tuple[float, float, float, float, float]:
    return (
        metrics.no_travel_miles,
        metrics.severe_miles,
        metrics.high_miles,
        metrics.average_risk,
        metrics.duration_seconds,
    )


def best_index(all_metrics: Iterable[RouteRiskMetrics]) -> int:
    indexed = list(enumerate(all_metrics))
    if not indexed:
        raise ValueError("cannot recommend a route from an empty set")
    return min(indexed, key=lambda item: ranking_key(item[1]))[0]
