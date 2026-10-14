"""Boundary tests for the published risk thresholds and the load escalation rules.
Every band edge in the specification table is asserted explicitly, because an off-by-one
here silently changes every recommendation the service makes.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from risk.rules import (
    RAIN_BANDS_IN_HR,
    SNOW_BANDS_IN_HR,
    WIND_BANDS_MPH,
    RiskLevel,
    classify_value,
)
from risk.scoring import WeatherSample, assess


class WindBandTests(SimpleTestCase):
    def test_band_edges(self):
        cases = [
            (0.0, RiskLevel.LOW),
            (24.99, RiskLevel.LOW),
            (25.0, RiskLevel.MODERATE),
            (34.99, RiskLevel.MODERATE),
            (35.0, RiskLevel.HIGH),
            (44.99, RiskLevel.HIGH),
            (45.0, RiskLevel.SEVERE),
            (54.99, RiskLevel.SEVERE),
            (55.0, RiskLevel.NO_TRAVEL),
            (120.0, RiskLevel.NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(wind=value):
                self.assertEqual(classify_value(value, WIND_BANDS_MPH), expected)


class RainBandTests(SimpleTestCase):
    def test_band_edges(self):
        cases = [
            (0.0, RiskLevel.LOW),
            (0.099, RiskLevel.LOW),
            (0.10, RiskLevel.MODERATE),
            (0.249, RiskLevel.MODERATE),
            (0.25, RiskLevel.HIGH),
            (0.499, RiskLevel.HIGH),
            (0.50, RiskLevel.SEVERE),
            (1.00, RiskLevel.SEVERE),
            (1.001, RiskLevel.NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(rain=value):
                self.assertEqual(classify_value(value, RAIN_BANDS_IN_HR), expected)


class SnowBandTests(SimpleTestCase):
    def test_band_edges(self):
        cases = [
            (0.49, RiskLevel.LOW),
            (0.5, RiskLevel.MODERATE),
            (0.99, RiskLevel.MODERATE),
            (1.0, RiskLevel.HIGH),
            (1.99, RiskLevel.HIGH),
            (2.0, RiskLevel.SEVERE),
            (3.0, RiskLevel.SEVERE),
            (3.01, RiskLevel.NO_TRAVEL),
        ]
        for value, expected in cases:
            with self.subTest(snow=value):
                self.assertEqual(classify_value(value, SNOW_BANDS_IN_HR), expected)


class LoadRuleTests(SimpleTestCase):
    def _wind_only(self, wind_mph: float, weight_lb: float):
        return assess(WeatherSample(wind_mph, wind_mph + 5, 0.0, 0.0), weight_lb)

    def test_any_load_blocked_above_55(self):
        self.assertEqual(self._wind_only(55.0, 1_000).overall, RiskLevel.NO_TRAVEL)

    def test_heavy_load_blocked_in_45_to_54_band(self):
        self.assertEqual(self._wind_only(47.0, 30_001).overall, RiskLevel.NO_TRAVEL)

    def test_light_load_stays_severe_in_45_to_54_band(self):
        self.assertEqual(self._wind_only(47.0, 30_000).overall, RiskLevel.SEVERE)

    def test_very_heavy_load_escalates_high_to_severe(self):
        self.assertEqual(self._wind_only(38.0, 40_001).overall, RiskLevel.SEVERE)

    def test_moderate_load_stays_high_in_35_to_44_band(self):
        self.assertEqual(self._wind_only(38.0, 40_000).overall, RiskLevel.HIGH)

    def test_load_rules_do_not_apply_below_35(self):
        self.assertEqual(self._wind_only(30.0, 80_000).overall, RiskLevel.MODERATE)


class DriverTests(SimpleTestCase):
    def test_worst_condition_is_reported_as_driver(self):
        assessment = assess(WeatherSample(10.0, 14.0, 0.05, 2.4), 10_000)
        self.assertEqual(assessment.overall, RiskLevel.SEVERE)
        self.assertEqual(assessment.driver, "snow")

    def test_calm_weather_has_no_driver(self):
        assessment = assess(WeatherSample(4.0, 6.0, 0.0, 0.0), 80_000)
        self.assertEqual(assessment.overall, RiskLevel.LOW)
        self.assertEqual(assessment.driver, "none")

    def test_load_is_reported_when_it_escalates(self):
        assessment = assess(WeatherSample(47.0, 55.0, 0.0, 0.0), 45_000)
        self.assertEqual(assessment.overall, RiskLevel.NO_TRAVEL)
        self.assertEqual(assessment.driver, "load")
