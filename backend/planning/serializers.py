"""Request validation for the planning endpoints.
Keeps the forecast window, load limits and checkpoint intervals enforced at the edge so the
service layer can assume well-formed input.
"""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .checkpoints import ALLOWED_INTERVALS_MILES

FORECAST_PAST_LIMIT = timedelta(hours=12)
FORECAST_FUTURE_LIMIT = timedelta(days=13)
MAX_LOAD_WEIGHT_LB = 200_000
MAX_HEATMAP_HOURS = 48


def _validate_window(value):
    now = timezone.now()
    if value < now - FORECAST_PAST_LIMIT:
        raise serializers.ValidationError("departure time is too far in the past for a forecast")
    if value > now + FORECAST_FUTURE_LIMIT:
        raise serializers.ValidationError("departure time is beyond the available forecast window")
    return value


class PlanRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(required=False, allow_blank=True, max_length=250)
    origin_lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    origin_lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    destination = serializers.CharField(required=False, allow_blank=True, max_length=250)
    destination_lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    destination_lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    departure_time = serializers.DateTimeField(validators=[_validate_window])
    load_weight_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_WEIGHT_LB)
    checkpoint_interval_miles = serializers.ChoiceField(choices=ALLOWED_INTERVALS_MILES, default=25)

    def validate(self, attrs):
        for end in ("origin", "destination"):
            has_text = bool(attrs.get(end))
            has_coords = attrs.get(f"{end}_lat") is not None and attrs.get(f"{end}_lon") is not None
            if not has_text and not has_coords:
                raise serializers.ValidationError({end: "provide a place name or a latitude and longitude pair"})
        return attrs


class HeatmapRequestSerializer(serializers.Serializer):
    polyline = serializers.CharField(max_length=2_000_000)
    departure_time = serializers.DateTimeField(validators=[_validate_window])
    load_weight_lb = serializers.FloatField(min_value=0, max_value=MAX_LOAD_WEIGHT_LB)
    hours = serializers.IntegerField(required=False, default=MAX_HEATMAP_HOURS, min_value=1, max_value=MAX_HEATMAP_HOURS)


class PlaceSearchSerializer(serializers.Serializer):
    q = serializers.CharField(min_length=2, max_length=250)
    limit = serializers.IntegerField(required=False, default=5, min_value=1, max_value=10)
