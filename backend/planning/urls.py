"""URL routes for the planning API.
Paths are versioned by the including module so the frontend contract can evolve safely.
"""

from __future__ import annotations

from django.urls import path

from .views import HealthView, HeatmapView, PlaceSearchView, TripPlanView

urlpatterns = [
    path("health", HealthView.as_view(), name="health"),
    path("places", PlaceSearchView.as_view(), name="places"),
    path("trips/plan", TripPlanView.as_view(), name="trip-plan"),
    path("trips/heatmap", HeatmapView.as_view(), name="trip-heatmap"),
]
