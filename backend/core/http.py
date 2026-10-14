"""Shared HTTP session with retries, timeouts and a descriptive user agent.
Every upstream call goes through this module so retry and timeout policy is set once and
the public OSM-based services can attribute traffic to this application.
"""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .errors import ProviderUnavailable

USER_AGENT = "weather-aware-truck-routing/1.0 (+https://github.com/MujtabaJunaid)"

_RETRY = Retry(
    total=3,
    backoff_factor=0.6,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset({"GET", "POST"}),
    raise_on_status=False,
)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    adapter = HTTPAdapter(max_retries=_RETRY, pool_connections=16, pool_maxsize=16)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


_SESSION = build_session()


def get_json(provider: str, url: str, params: dict[str, Any] | None = None, timeout: float = 25.0) -> Any:
    try:
        response = _SESSION.get(url, params=params, timeout=timeout)
    except requests.RequestException as exc:
        raise ProviderUnavailable(provider, f"request failed: {exc}") from exc

    if response.status_code >= 400:
        raise ProviderUnavailable(provider, f"HTTP {response.status_code}: {response.text[:200]}")

    try:
        return response.json()
    except ValueError as exc:
        raise ProviderUnavailable(provider, "response was not valid JSON") from exc


def post_json(provider: str, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None, timeout: float = 30.0) -> Any:
    try:
        response = _SESSION.post(url, json=payload, headers=headers, timeout=timeout)
    except requests.RequestException as exc:
        raise ProviderUnavailable(provider, f"request failed: {exc}") from exc

    if response.status_code >= 400:
        raise ProviderUnavailable(provider, f"HTTP {response.status_code}: {response.text[:200]}")

    try:
        return response.json()
    except ValueError as exc:
        raise ProviderUnavailable(provider, "response was not valid JSON") from exc
