"""HTTP endpoints for place search, trip planning and the corridor heatmap.
Each view validates input, delegates to the service layer and returns a presented payload;
upstream failures are translated by the project exception handler.
"""

from __future__ import annotations

from rest_framework.response import Response
from rest_framework.views import APIView

from providers import geocoding

from . import presenters, services
from .serializers import HeatmapRequestSerializer, PlaceSearchSerializer, PlanRequestSerializer


class HealthView(APIView):
    throttle_classes = ()

    def get(self, request):
        return Response({"status": "ok"})


class PlaceSearchView(APIView):
    def get(self, request):
        form = PlaceSearchSerializer(data=request.query_params)
        form.is_valid(raise_exception=True)
        results = geocoding.search(form.validated_data["q"], form.validated_data["limit"])
        return Response({"results": [presenters.place(result) for result in results]})


class TripPlanView(APIView):
    def post(self, request):
        form = PlanRequestSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data

        plan = services.plan_trip(
            origin_query=data.get("origin"),
            destination_query=data.get("destination"),
            departure=data["departure_time"],
            load_weight_lb=data["load_weight_lb"],
            interval_miles=data["checkpoint_interval_miles"],
            origin_lat=data.get("origin_lat"),
            origin_lon=data.get("origin_lon"),
            destination_lat=data.get("destination_lat"),
            destination_lon=data.get("destination_lon"),
        )
        return Response(presenters.trip_plan(plan))


class HeatmapView(APIView):
    def post(self, request):
        form = HeatmapRequestSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data

        result = services.build_heatmap(
            polyline=data["polyline"],
            departure=data["departure_time"],
            load_weight_lb=data["load_weight_lb"],
            hours=data["hours"],
        )
        return Response(presenters.heatmap(result))
