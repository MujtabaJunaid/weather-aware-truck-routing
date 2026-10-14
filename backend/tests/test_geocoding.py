"""Tests for region-hint handling, caching and the address fallback in place lookup.
The hint logic is what keeps "Springfield, IL" from resolving to Springfield, Missouri, so
each branch of it is pinned down with stubbed upstream payloads.
"""

from __future__ import annotations

from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from core.errors import LocationNotFound, ProviderUnavailable
from core.http import _RETRY
from core.geo import Place
from providers import geocoding

SPRINGFIELDS = {
    "results": [
        {"name": "Springfield", "admin1": "Missouri", "country": "United States", "latitude": 37.2, "longitude": -93.3},
        {"name": "Springfield", "admin1": "Illinois", "country": "United States", "latitude": 39.8, "longitude": -89.6},
    ]
}


class HintTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_state_abbreviation_selects_the_matching_city(self):
        with patch("providers.geocoding._candidates", return_value=SPRINGFIELDS["results"]):
            place = geocoding.resolve("Springfield, IL")
        self.assertEqual(place.label, "Springfield, Illinois, United States")
        self.assertAlmostEqual(place.lat, 39.8)

    def test_full_state_name_also_matches(self):
        with patch("providers.geocoding._candidates", return_value=SPRINGFIELDS["results"]):
            place = geocoding.resolve("Springfield, Illinois")
        self.assertAlmostEqual(place.lat, 39.8)

    def test_without_a_hint_the_first_result_wins(self):
        with patch("providers.geocoding._candidates", return_value=SPRINGFIELDS["results"]):
            place = geocoding.resolve("Springfield")
        self.assertAlmostEqual(place.lat, 37.2)

    def test_unmatched_hint_keeps_all_candidates(self):
        with patch("providers.geocoding._candidates", return_value=SPRINGFIELDS["results"]):
            results = geocoding.search("Springfield, ZZ", limit=5)
        self.assertEqual(len(results), 2)


class FallbackTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_nominatim_is_used_when_the_primary_returns_nothing(self):
        address = Place("1600 Pennsylvania Avenue, Washington", 38.89, -77.03)
        with patch("providers.geocoding._candidates", return_value=[]), patch(
            "providers.geocoding.nominatim.search", return_value=[address]
        ) as nominatim_search:
            place = geocoding.resolve("1600 Pennsylvania Avenue")

        self.assertEqual(place, address)
        nominatim_search.assert_called_once()

    def test_nominatim_is_used_when_the_primary_fails(self):
        address = Place("Somewhere", 1.0, 2.0)
        with patch("providers.geocoding._candidates", side_effect=ProviderUnavailable("x", "down")), patch(
            "providers.geocoding.nominatim.search", return_value=[address]
        ):
            self.assertEqual(geocoding.resolve("anywhere"), address)

    def test_no_result_anywhere_raises_location_not_found(self):
        with patch("providers.geocoding._candidates", return_value=[]), patch(
            "providers.geocoding.nominatim.search", return_value=[]
        ):
            with self.assertRaises(LocationNotFound):
                geocoding.resolve("nowhere at all")

    def test_a_fallback_outage_reads_as_no_match_rather_than_an_outage(self):
        with patch("providers.geocoding._candidates", return_value=[]), patch(
            "providers.geocoding.nominatim.search", side_effect=ProviderUnavailable("nominatim", "timed out")
        ):
            with self.assertRaises(LocationNotFound):
                geocoding.resolve("zzqqxx not a real place 12345")

    def test_blank_query_returns_no_results(self):
        self.assertEqual(geocoding.search("   "), [])


class CacheTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_repeat_lookups_do_not_hit_the_provider_again(self):
        with patch("providers.geocoding._candidates", return_value=SPRINGFIELDS["results"]) as candidates:
            geocoding.resolve("Springfield, IL")
            geocoding.resolve("springfield, il")

        self.assertEqual(candidates.call_count, 1)


class RetryPolicyTests(SimpleTestCase):
    def test_read_timeouts_are_not_retried(self):
        self.assertEqual(_RETRY.read, 0)
        self.assertGreater(_RETRY.connect, 0)
