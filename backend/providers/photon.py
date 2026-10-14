"""Adapter for the Photon geocoder, used as the street-address fallback.
Photon is keyless and OpenStreetMap-backed and resolves full addresses, but it answers an
order of magnitude slower than the primary geocoder, so it is only queried on a miss.
"""

from __future__ import annotations

from django.conf import settings

from core.geo import Place
from core.http import get_json

PROVIDER = "photon"


def _label(properties: dict) -> str:
    street = " ".join(filter(None, [properties.get("housenumber"), properties.get("street")])).strip()
    candidates = [
        properties.get("name"),
        street or None,
        properties.get("city") or properties.get("county"),
        properties.get("state"),
        properties.get("country"),
    ]

    parts: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in parts:
            parts.append(candidate)
    return ", ".join(parts)


def search(query: str, limit: int = 5) -> list[Place]:
    payload = get_json(PROVIDER, f"{settings.PHOTON_URL}/api", params={"q": query, "limit": limit}, timeout=8.0)

    places: list[Place] = []
    for feature in payload.get("features", []):
        coordinates = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coordinates) != 2:
            continue
        places.append(
            Place(label=_label(feature.get("properties") or {}), lat=coordinates[1], lon=coordinates[0])
        )
    return places
