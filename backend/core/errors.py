"""Exception types for upstream provider failures and unresolvable planning requests.
Views map these onto explicit HTTP responses so a provider outage or an unknown address
never surfaces to the client as an unhandled server error.
"""

from __future__ import annotations


class ProviderError(Exception):
    def __init__(self, provider: str, message: str) -> None:
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.message = message


class ProviderUnavailable(ProviderError):
    pass


class NoRouteFound(ProviderError):
    pass


class LocationNotFound(ProviderError):
    pass
