"""Tests for distance-weighted route metrics and the spec ranking order.
Each case isolates one tie-breaker so the precedence of severe miles over high miles over
average risk over travel time is pinned down.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from risk.recommendation import RiskSegment, best_index, summarize
from risk.rules import RiskLevel


def metrics(segments, duration_seconds):
    return summarize([RiskSegment(miles, level) for miles, level in segments], duration_seconds)


class SummaryTests(SimpleTestCase):
    def test_mileage_is_grouped_by_level(self):
        result = metrics([(10.0, RiskLevel.LOW), (5.0, RiskLevel.HIGH), (5.0, RiskLevel.LOW)], 3_600)
        self.assertEqual(result.total_miles, 20.0)
        self.assertEqual(result.miles_by_level[RiskLevel.LOW], 15.0)
        self.assertEqual(result.high_miles, 5.0)

    def test_average_risk_is_distance_weighted(self):
        result = metrics([(90.0, RiskLevel.LOW), (10.0, RiskLevel.SEVERE)], 3_600)
        self.assertAlmostEqual(result.average_risk, 0.3)

    def test_blocked_when_any_no_travel_mileage(self):
        self.assertTrue(metrics([(1.0, RiskLevel.NO_TRAVEL)], 60).is_blocked)
        self.assertFalse(metrics([(1.0, RiskLevel.SEVERE)], 60).is_blocked)

    def test_worst_level_ignores_empty_levels(self):
        self.assertEqual(metrics([(5.0, RiskLevel.MODERATE)], 60).worst_level, RiskLevel.MODERATE)


class RankingTests(SimpleTestCase):
    def test_fewest_severe_miles_wins_over_speed(self):
        fast_but_severe = metrics([(90.0, RiskLevel.LOW), (10.0, RiskLevel.SEVERE)], 3_600)
        slow_but_clear = metrics([(100.0, RiskLevel.LOW)], 36_000)
        self.assertEqual(best_index([fast_but_severe, slow_but_clear]), 1)

    def test_fewest_high_miles_breaks_equal_severe(self):
        more_high = metrics([(50.0, RiskLevel.HIGH), (50.0, RiskLevel.LOW)], 3_600)
        less_high = metrics([(10.0, RiskLevel.HIGH), (90.0, RiskLevel.LOW)], 7_200)
        self.assertEqual(best_index([more_high, less_high]), 1)

    def test_average_risk_breaks_equal_high_and_severe(self):
        more_moderate = metrics([(100.0, RiskLevel.MODERATE)], 3_600)
        mostly_low = metrics([(90.0, RiskLevel.LOW), (10.0, RiskLevel.MODERATE)], 7_200)
        self.assertEqual(best_index([more_moderate, mostly_low]), 1)

    def test_travel_time_breaks_identical_risk(self):
        slower = metrics([(100.0, RiskLevel.LOW)], 9_000)
        faster = metrics([(100.0, RiskLevel.LOW)], 3_600)
        self.assertEqual(best_index([slower, faster]), 1)

    def test_no_travel_mileage_outranks_severe_mileage(self):
        blocked = metrics([(1.0, RiskLevel.NO_TRAVEL), (99.0, RiskLevel.LOW)], 3_600)
        severe = metrics([(60.0, RiskLevel.SEVERE), (40.0, RiskLevel.LOW)], 36_000)
        self.assertEqual(best_index([blocked, severe]), 1)

    def test_empty_set_is_rejected(self):
        with self.assertRaises(ValueError):
            best_index([])
