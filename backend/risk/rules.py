"""Weather risk thresholds and load-based escalation rules defined by the assessment spec.
Pure domain data with no I/O and no framework or provider imports, so the published
thresholds stay readable in one place and are the single source of truth for scoring.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def slug(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Band:
    minimum: float
    level: RiskLevel
    inclusive: bool = True

    def matches(self, value: float) -> bool:
        return value >= self.minimum if self.inclusive else value > self.minimum


WIND_BANDS_MPH: tuple[Band, ...] = (
    Band(55.0, RiskLevel.NO_TRAVEL),
    Band(45.0, RiskLevel.SEVERE),
    Band(35.0, RiskLevel.HIGH),
    Band(25.0, RiskLevel.MODERATE),
    Band(0.0, RiskLevel.LOW),
)

RAIN_BANDS_IN_HR: tuple[Band, ...] = (
    Band(1.00, RiskLevel.NO_TRAVEL, inclusive=False),
    Band(0.50, RiskLevel.SEVERE),
    Band(0.25, RiskLevel.HIGH),
    Band(0.10, RiskLevel.MODERATE),
    Band(0.0, RiskLevel.LOW),
)

SNOW_BANDS_IN_HR: tuple[Band, ...] = (
    Band(3.0, RiskLevel.NO_TRAVEL, inclusive=False),
    Band(2.0, RiskLevel.SEVERE),
    Band(1.0, RiskLevel.HIGH),
    Band(0.5, RiskLevel.MODERATE),
    Band(0.0, RiskLevel.LOW),
)


@dataclass(frozen=True)
class LoadRule:
    wind_minimum_mph: float
    wind_maximum_mph: float | None
    weight_above_lb: float | None
    level: RiskLevel

    def applies(self, wind_mph: float, load_weight_lb: float) -> bool:
        if wind_mph < self.wind_minimum_mph:
            return False
        if self.wind_maximum_mph is not None and wind_mph >= self.wind_maximum_mph:
            return False
        if self.weight_above_lb is not None and load_weight_lb <= self.weight_above_lb:
            return False
        return True


LOAD_RULES: tuple[LoadRule, ...] = (
    LoadRule(55.0, None, None, RiskLevel.NO_TRAVEL),
    LoadRule(45.0, 55.0, 30_000.0, RiskLevel.NO_TRAVEL),
    LoadRule(35.0, 45.0, 40_000.0, RiskLevel.SEVERE),
)


def classify_value(value: float, bands: tuple[Band, ...]) -> RiskLevel:
    for band in bands:
        if band.matches(value):
            return band.level
    return RiskLevel.LOW
