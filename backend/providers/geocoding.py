"""Place lookup backed by the Open-Meteo geocoder, falling back to Nominatim for addresses.
A trailing region hint such as the "IL" in "Chicago, IL" is matched against the state or
country of each candidate, which keeps same-named cities from resolving to the wrong state.
"""

from __future__ import annotations

from django.conf import settings
from django.core.cache import cache

from core.cache import cache_key
from core.errors import LocationNotFound, ProviderError
from core.geo import Place
from core.http import get_json

from . import nominatim

PROVIDER = "open-meteo-geocoding"
CACHE_SECONDS = 86_400

US_STATE_ABBREVIATIONS: dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DC": "Washington, D.C.", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def _split_hint(query: str) -> tuple[str, str | None]:
    if "," not in query:
        return query.strip(), None
    head, _, tail = query.rpartition(",")
    hint = tail.strip()
    return (head.strip() or query.strip()), (hint or None)


def _expand(hint: str) -> str:
    return US_STATE_ABBREVIATIONS.get(hint.upper(), hint)


def _label(entry: dict) -> str:
    parts = [entry.get("name"), entry.get("admin1"), entry.get("country")]
    seen: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.append(str(part))
    return ", ".join(seen)


def _matches_hint(entry: dict, hint: str) -> bool:
    expanded = _expand(hint).casefold()
    fields = [entry.get("admin1"), entry.get("admin2"), entry.get("country"), entry.get("country_code")]
    return any(field and str(field).casefold() == expanded for field in fields)


def _candidates(name: str, count: int) -> list[dict]:
    params = {"name": name, "count": max(count, 10), "language": "en", "format": "json"}
    payload = get_json(PROVIDER, settings.OPEN_METEO_GEOCODING_URL, params=params, timeout=20.0)
    return payload.get("results") or []


def search(query: str, limit: int = 5) -> list[Place]:
    cleaned = query.strip()
    if not cleaned:
        return []

    key = cache_key("geocode", cleaned.casefold(), limit)
    cached = cache.get(key)
    if cached is not None:
        return cached

    name, hint = _split_hint(cleaned)
    places: list[Place] = []

    try:
        entries = _candidates(name, limit)
    except ProviderError:
        entries = []

    if entries:
        if hint:
            preferred = [entry for entry in entries if _matches_hint(entry, hint)]
            entries = preferred + [entry for entry in entries if entry not in preferred]
        places = [
            Place(label=_label(entry), lat=float(entry["latitude"]), lon=float(entry["longitude"]))
            for entry in entries[:limit]
            if entry.get("latitude") is not None and entry.get("longitude") is not None
        ]

    if not places:
        try:
            places = nominatim.search(cleaned, limit)
        except ProviderError:
            places = []

    if places:
        cache.set(key, places, CACHE_SECONDS)
    return places


def resolve(query: str) -> Place:
    results = search(query, limit=1)
    if not results:
        raise LocationNotFound(PROVIDER, f"no location matched {query!r}")
    return results[0]
