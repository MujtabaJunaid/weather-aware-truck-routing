"""Root URL configuration mounting the versioned planning API.
"""

from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("api/v1/", include("planning.urls")),
]
