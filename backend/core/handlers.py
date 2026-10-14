"""DRF exception handler that maps provider failures onto meaningful status codes.
An unresolvable address or routing request is a 422, an upstream outage is a 503, and
anything unrecognised falls through to the default handler.
"""

from __future__ import annotations

import logging

from rest_framework.response import Response
from rest_framework.views import exception_handler

from .errors import LocationNotFound, NoRouteFound, ProviderError

logger = logging.getLogger(__name__)


def api_exception_handler(exc, context):
    handled = exception_handler(exc, context)
    if handled is not None:
        return handled

    if isinstance(exc, (LocationNotFound, NoRouteFound)):
        return Response({"error": exc.message, "provider": exc.provider}, status=422)

    if isinstance(exc, ProviderError):
        logger.warning("upstream provider failure: %s", exc)
        return Response({"error": exc.message, "provider": exc.provider}, status=503)

    return None
