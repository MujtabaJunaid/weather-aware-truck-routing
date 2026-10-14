"""Tests for checkpoint sampling, segment attribution and arrival-time interpolation.
A constant-speed straight route makes every expected value closed-form, so interpolation
errors show up immediately.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from core.geo import Point
from planning.checkpoints import sample

from .factories import straight_route


class SamplingTests(SimpleTestCase):
    def setUp(self):
        self.route = straight_route("test", Point(40.0, -100.0), Point(40.0, -90.0), mph=50.0)

    def test_origin_and_destination_are_always_sampled(self):
        checkpoints = sample(self.route, 50)
        self.assertEqual(checkpoints[0].miles_from_origin, 0.0)
        self.assertAlmostEqual(checkpoints[-1].miles_from_origin, self.route.cumulative_miles[-1], places=4)

    def test_interval_spacing_is_respected(self):
        checkpoints = sample(self.route, 25)
        interior = [point.miles_from_origin for point in checkpoints[:-1]]
        for index, miles in enumerate(interior):
            self.assertAlmostEqual(miles, index * 25.0, places=6)

    def test_segment_miles_sum_to_route_length(self):
        for interval in (10, 25, 50):
            with self.subTest(interval=interval):
                checkpoints = sample(self.route, interval)
                total = sum(point.segment_miles for point in checkpoints)
                self.assertAlmostEqual(total, self.route.cumulative_miles[-1], places=4)

    def test_smaller_interval_produces_more_checkpoints(self):
        counts = [len(sample(self.route, interval)) for interval in (50, 25, 10)]
        self.assertEqual(counts, sorted(counts))

    def test_elapsed_time_matches_constant_speed(self):
        for checkpoint in sample(self.route, 25):
            expected_hours = checkpoint.miles_from_origin / 50.0
            self.assertAlmostEqual(checkpoint.elapsed_seconds / 3600.0, expected_hours, places=3)

    def test_sampled_points_stay_on_the_route_latitude(self):
        for checkpoint in sample(self.route, 10):
            self.assertAlmostEqual(checkpoint.point.lat, 40.0, places=4)
