"""Tests for the geometry helpers that underpin mileage, bearings and map payload size.
Polyline codecs are checked for exact round-tripping because a precision mismatch would
silently move every route on the map.
"""

from __future__ import annotations

from django.test import SimpleTestCase

from core.geo import (
    Point,
    cumulative_miles,
    decode_polyline,
    encode_polyline,
    haversine_miles,
    initial_bearing,
    interpolate,
    offset,
    simplify,
)

CHICAGO = Point(41.8781, -87.6298)
DENVER = Point(39.7392, -104.9903)


class DistanceTests(SimpleTestCase):
    def test_known_great_circle_distance(self):
        self.assertAlmostEqual(haversine_miles(CHICAGO, DENVER), 918.2, delta=2.0)

    def test_distance_is_symmetric_and_zero_at_a_point(self):
        self.assertEqual(haversine_miles(CHICAGO, CHICAGO), 0.0)
        self.assertAlmostEqual(haversine_miles(CHICAGO, DENVER), haversine_miles(DENVER, CHICAGO), places=9)

    def test_cumulative_miles_is_monotonic(self):
        totals = cumulative_miles([CHICAGO, DENVER, CHICAGO])
        self.assertEqual(totals[0], 0.0)
        self.assertEqual(totals, sorted(totals))


class BearingTests(SimpleTestCase):
    def test_due_east_bearing(self):
        self.assertAlmostEqual(initial_bearing(Point(0.0, 0.0), Point(0.0, 1.0)), 90.0, places=6)

    def test_due_north_bearing(self):
        self.assertAlmostEqual(initial_bearing(Point(0.0, 0.0), Point(1.0, 0.0)), 0.0, places=6)

    def test_offset_round_trips_to_the_requested_distance(self):
        moved = offset(CHICAGO, 90.0, 100.0)
        self.assertAlmostEqual(haversine_miles(CHICAGO, moved), 100.0, places=3)

    def test_negative_offset_mirrors_the_bearing(self):
        east = offset(CHICAGO, 90.0, 50.0)
        west = offset(CHICAGO, 90.0, -50.0)
        self.assertGreater(east.lon, CHICAGO.lon)
        self.assertLess(west.lon, CHICAGO.lon)


class PolylineTests(SimpleTestCase):
    def test_round_trip_is_lossless_at_precision_six(self):
        points = [Point(40.0 + index * 0.001, -100.0 - index * 0.002) for index in range(250)]
        decoded = decode_polyline(encode_polyline(points, 6), 6)
        self.assertEqual(len(decoded), len(points))
        for original, restored in zip(points, decoded):
            self.assertAlmostEqual(original.lat, restored.lat, places=6)
            self.assertAlmostEqual(original.lon, restored.lon, places=6)

    def test_decodes_the_canonical_precision_five_example(self):
        decoded = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@", 5)
        self.assertEqual(len(decoded), 3)
        self.assertAlmostEqual(decoded[0].lat, 38.5, places=5)
        self.assertAlmostEqual(decoded[2].lon, -126.453, places=5)

    def test_empty_input_decodes_to_nothing(self):
        self.assertEqual(decode_polyline("", 6), [])


class SimplifyTests(SimpleTestCase):
    def test_collinear_points_collapse_to_the_endpoints(self):
        line = [interpolate(Point(40.0, -100.0), Point(40.0, -90.0), index / 99) for index in range(100)]
        self.assertEqual(len(simplify(line, 0.0005)), 2)

    def test_detail_above_tolerance_is_preserved(self):
        zigzag = [Point(40.0 + (index % 2) * 0.05, -100.0 + index * 0.01) for index in range(60)]
        self.assertEqual(len(simplify(zigzag, 0.0005)), 60)

    def test_short_inputs_are_returned_unchanged(self):
        pair = [CHICAGO, DENVER]
        self.assertEqual(simplify(pair, 0.01), pair)
