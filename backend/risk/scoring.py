"""Classification of a single weather sample into a risk level for a given load weight.
Applies the per-condition bands first, then the load escalation rules, and reports which
condition drove the final level so the UI can explain every checkpoint.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rules import (
    LOAD_RULES,
    RAIN_BANDS_IN_HR,
    SNOW_BANDS_IN_HR,
    WIND_BANDS_MPH,
    RiskLevel,
    classify_value,
)


@dataclass(frozen=True)
class WeatherSample:
    wind_mph: float
    wind_gust_mph: float
    rain_in_hr: float
    snow_in_hr: float


@dataclass(frozen=True)
class RiskAssessment:
    overall: RiskLevel
    wind: RiskLevel
    rain: RiskLevel
    snow: RiskLevel
    load: RiskLevel
    driver: str


def _load_level(wind_mph: float, load_weight_lb: float) -> RiskLevel:
    level = RiskLevel.LOW
    for rule in LOAD_RULES:
        if rule.applies(wind_mph, load_weight_lb) and rule.level > level:
            level = rule.level
    return level


def assess(sample: WeatherSample, load_weight_lb: float) -> RiskAssessment:
    wind = classify_value(sample.wind_mph, WIND_BANDS_MPH)
    rain = classify_value(sample.rain_in_hr, RAIN_BANDS_IN_HR)
    snow = classify_value(sample.snow_in_hr, SNOW_BANDS_IN_HR)
    load = _load_level(sample.wind_mph, load_weight_lb)

    contributions = (("wind", wind), ("rain", rain), ("snow", snow), ("load", load))
    driver, overall = max(contributions, key=lambda item: item[1])
    if overall == RiskLevel.LOW:
        driver = "none"
    return RiskAssessment(overall=overall, wind=wind, rain=rain, snow=snow, load=load, driver=driver)
