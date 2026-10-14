"""End-to-end tests of the planning endpoints with every upstream provider stubbed.
Exercises validation, orchestration, the deterministic recommendation and the shape of the
payload the frontend depends on, without touching the network.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase
from django.utils import timezone

from core.geo import Place, Point

from .factories import flat_series, straight_route

STORMY_LATITUDE = 45.0
CALM_LATITUDE = 35.0


def _routes():
    stormy = straight_route("Fastest", Point(STORMY_LATITUDE, -100.0), Point(STORMY_LATITUDE, -96.0), mph=60.0)
    calm = straight_route("Shortest", Point(CALM_LATITUDE, -100.0), Point(CALM_LATITUDE, -96.0), mph=45.0)
    return [stormy, calm]


def _series_for(points, start, end):
    anchor = timezone.now() - timedelta(hours=24)
    series = []
    for point in points:
        if point.lat > 42.0:
            series.append(flat_series(anchor, wind_mph=50.0, gust_mph=62.0))
        else:
            series.append(flat_series(anchor, wind_mph=6.0, gust_mph=9.0))
    return series


class PlanEndpointTests(SimpleTestCase):
    url = "/api/v1/trips/plan"

    def setUp(self):
        cache.clear()
        self.payload = {
            "origin": "Chicago, IL",
            "destination": "Denver, CO",
            "departure_time": (timezone.now() + timedelta(hours=2)).isoformat(),
            "load_weight_lb": 25_000,
            "checkpoint_interval_miles": 25,
        }

    def _post(self, overrides=None):
        body = {**self.payload, **(overrides or {})}
        with patch("planning.services.geocoding.resolve", side_effect=lambda q: Place(q, 41.0, -87.0)), patch(
            "planning.services.valhalla.fetch_routes", return_value=_routes()
        ), patch("planning.services.open_meteo.fetch_hourly", side_effect=_series_for), patch(
            "planning.services.groq.generate_briefing", return_value=None
        ):
            return self.client.post(self.url, body, content_type="application/json")

    def test_lower_risk_route_is_recommended_over_the_faster_one(self):
        response = self._post()
        self.assertEqual(response.status_code, 200)

        body = response.json()
        recommended = next(route for route in body["routes"] if route["is_recommended"])
        self.assertEqual(recommended["id"], body["recommended_route_id"])
        self.assertEqual(recommended["label"], "Shortest")
        self.assertEqual(recommended["miles_by_level"]["severe"], 0.0)

    def test_stormy_route_is_scored_severe_by_wind(self):
        body = self._post().json()
        stormy = next(route for route in body["routes"] if route["label"] == "Fastest")
        self.assertEqual(stormy["worst_level"], "severe")
        self.assertGreater(stormy["miles_by_level"]["severe"], 0.0)
        self.assertEqual(stormy["checkpoints"][0]["driver"], "wind")

    def test_heavy_load_blocks_the_stormy_route(self):
        body = self._post({"load_weight_lb": 45_000}).json()
        stormy = next(route for route in body["routes"] if route["label"] == "Fastest")
        self.assertTrue(stormy["is_blocked"])
        self.assertEqual(stormy["worst_level"], "no_travel")

    def test_mileage_by_level_sums_to_route_distance(self):
        for route in self._post().json()["routes"]:
            with self.subTest(route=route["label"]):
                total = sum(route["miles_by_level"].values())
                self.assertAlmostEqual(total, route["distance_miles"], delta=0.2)

    def test_checkpoints_carry_eta_weather_and_levels(self):
        checkpoint = self._post().json()["routes"][0]["checkpoints"][0]
        self.assertIn("eta", checkpoint)
        self.assertIn("wind_mph", checkpoint["weather"])
        self.assertEqual(set(checkpoint["levels"]), {"wind", "rain", "snow", "load"})

    def test_reason_is_returned_and_briefing_falls_back_without_a_key(self):
        body = self._post().json()
        self.assertIn("severe", body["recommendation_reason"])
        self.assertEqual(body["briefing_source"], "deterministic")
        self.assertEqual(body["briefing"], body["recommendation_reason"])

    def test_arrival_time_follows_departure(self):
        body = self._post().json()
        for route in body["routes"]:
            self.assertGreater(route["arrival_time"], body["departure_time"])


class ValidationTests(SimpleTestCase):
    url = "/api/v1/trips/plan"

    def setUp(self):
        cache.clear()
        self.base = {
            "origin": "Chicago, IL",
            "destination": "Denver, CO",
            "departure_time": (timezone.now() + timedelta(hours=2)).isoformat(),
            "load_weight_lb": 25_000,
        }

    def _post(self, overrides):
        return self.client.post(self.url, {**self.base, **overrides}, content_type="application/json")

    def test_missing_destination_is_rejected(self):
        response = self.client.post(
            self.url,
            {key: value for key, value in self.base.items() if key != "destination"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("destination", response.json())

    def test_unsupported_interval_is_rejected(self):
        self.assertEqual(self._post({"checkpoint_interval_miles": 30}).status_code, 400)

    def test_departure_beyond_forecast_window_is_rejected(self):
        far = (timezone.now() + timedelta(days=30)).isoformat()
        self.assertEqual(self._post({"departure_time": far}).status_code, 400)

    def test_negative_load_is_rejected(self):
        self.assertEqual(self._post({"load_weight_lb": -1}).status_code, 400)

    def test_coordinates_satisfy_the_origin_requirement(self):
        body = {key: value for key, value in self.base.items() if key != "origin"}
        body.update({"origin_lat": 41.0, "origin_lon": -87.0})
        with patch("planning.services.geocoding.resolve", side_effect=lambda q: Place(q, 39.0, -104.0)), patch(
            "planning.services.valhalla.fetch_routes", return_value=_routes()
        ), patch("planning.services.open_meteo.fetch_hourly", side_effect=_series_for), patch(
            "planning.services.groq.generate_briefing", return_value=None
        ):
            self.assertEqual(self.client.post(self.url, body, content_type="application/json").status_code, 200)


class HeatmapEndpointTests(SimpleTestCase):
    url = "/api/v1/trips/heatmap"

    def setUp(self):
        cache.clear()
        self.route = straight_route("x", Point(CALM_LATITUDE, -100.0), Point(CALM_LATITUDE, -96.0))

    def test_returns_an_hourly_level_grid(self):
        body = {
            "polyline": self.route.display_polyline,
            "departure_time": (timezone.now() + timedelta(hours=1)).isoformat(),
            "load_weight_lb": 20_000,
            "hours": 48,
        }
        with patch("planning.services.open_meteo.fetch_hourly", side_effect=_series_for):
            response = self.client.post(self.url, body, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["hours"]), 49)
        self.assertGreater(len(payload["points"]), 0)
        for point in payload["points"]:
            self.assertEqual(len(point["levels"]), 49)
            self.assertTrue(all(0 <= level <= 4 for level in point["levels"]))

    def test_hours_above_the_cap_are_rejected(self):
        body = {
            "polyline": self.route.display_polyline,
            "departure_time": timezone.now().isoformat(),
            "load_weight_lb": 20_000,
            "hours": 96,
        }
        self.assertEqual(self.client.post(self.url, body, content_type="application/json").status_code, 400)


class PlaceEndpointTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_search_returns_labelled_places(self):
        with patch("planning.views.geocoding.search", return_value=[Place("Chicago, Illinois", 41.88, -87.63)]):
            response = self.client.get("/api/v1/places", {"q": "chicago"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["label"], "Chicago, Illinois")

    def test_short_query_is_rejected(self):
        self.assertEqual(self.client.get("/api/v1/places", {"q": "c"}).status_code, 400)

    def test_health_is_open(self):
        self.assertEqual(self.client.get("/api/v1/health").json(), {"status": "ok"})


class TieBreakWordingTests(SimpleTestCase):
    url = "/api/v1/trips/plan"

    def setUp(self):
        cache.clear()

    def test_equal_risk_routes_are_explained_by_travel_time(self):
        calm_fast = straight_route("Fastest", Point(CALM_LATITUDE, -100.0), Point(CALM_LATITUDE, -96.0), mph=60.0)
        calm_slow = straight_route("Shortest", Point(CALM_LATITUDE, -99.9), Point(CALM_LATITUDE, -95.9), mph=40.0)
        body = {
            "origin": "Chicago, IL",
            "destination": "Denver, CO",
            "departure_time": (timezone.now() + timedelta(hours=2)).isoformat(),
            "load_weight_lb": 20_000,
            "checkpoint_interval_miles": 50,
        }

        with patch("planning.services.geocoding.resolve", side_effect=lambda q: Place(q, 41.0, -87.0)), patch(
            "planning.services.valhalla.fetch_routes", return_value=[calm_fast, calm_slow]
        ), patch("planning.services.open_meteo.fetch_hourly", side_effect=_series_for), patch(
            "planning.services.groq.generate_briefing", return_value=None
        ):
            payload = self.client.post(self.url, body, content_type="application/json").json()

        self.assertIn("ties the other routes on weather risk", payload["recommendation_reason"])
        self.assertEqual(payload["recommended_route_id"], "route-1")

    def test_a_negligible_risk_gap_is_not_cited_as_the_reason(self):
        heavy = straight_route("Fastest", Point(CALM_LATITUDE, -100.0), Point(CALM_LATITUDE, -96.0), mph=60.0)
        light = straight_route("Shortest", Point(CALM_LATITUDE, -99.9), Point(CALM_LATITUDE, -95.9), mph=40.0)
        body = {
            "origin": "Chicago, IL",
            "destination": "Denver, CO",
            "departure_time": (timezone.now() + timedelta(hours=2)).isoformat(),
            "load_weight_lb": 20_000,
            "checkpoint_interval_miles": 50,
        }

        with patch("planning.services.geocoding.resolve", side_effect=lambda q: Place(q, 41.0, -87.0)), patch(
            "planning.services.valhalla.fetch_routes", return_value=[heavy, light]
        ), patch("planning.services.open_meteo.fetch_hourly", side_effect=_series_for), patch(
            "planning.services.groq.generate_briefing", return_value=None
        ):
            payload = self.client.post(self.url, body, content_type="application/json").json()

        reason = payload["recommendation_reason"]
        self.assertNotIn("0.00 against 0.00", reason)
        self.assertNotIn("0 against 0", reason)
