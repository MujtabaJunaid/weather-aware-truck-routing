"""Adapter for Nominatim, the OpenStreetMap geocoder, used as the street-address fallback.
Nominatim is keyless but asks callers to identify themselves and stay under one request a
second, so this module serialises its own calls behind a minimum interval.
"""

from __future__ import annotations

import time
from threading import Lock

from django.conf import settings

from core.geo import Place
from core.http import get_json

PROVIDER = "nominatim"
MIN_INTERVAL_SECONDS = 1.0

_lock = Lock()
_last_call = 0.0


def _throttle() -> None:
    global _last_call
    with _lock:
        wait = MIN_INTERVAL_SECONDS - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _label(entry: dict) -> str:
    address = entry.get("address") or {}
    road = " ".join(filter(None, [address.get("house_number"), address.get("road")])).strip()
    locality = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("hamlet")
        or address.get("county")
    )
    candidates = [entry.get("name") or None, road or None, locality, address.get("state"), address.get("country")]

    parts: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in parts:
            parts.append(candidate)
    return ", ".join(parts) or str(entry.get("display_name", ""))


def search(query: str, limit: int = 5) -> list[Place]:
    _throttle()
    params = {"q": query, "format": "jsonv2", "limit": limit, "addressdetails": 1}
    payload = get_json(PROVIDER, settings.NOMINATIM_URL, params=params, timeout=12.0)

    places: list[Place] = []
    for entry in payload if isinstance(payload, list) else []:
        if entry.get("lat") is None or entry.get("lon") is None:
            continue
        places.append(Place(label=_label(entry), lat=float(entry["lat"]), lon=float(entry["lon"])))
    return places
