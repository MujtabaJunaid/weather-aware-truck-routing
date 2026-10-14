/**
 * Polyline decoding and risk-segmented GeoJSON construction for the map layers.
 * The route line is split at checkpoint mileage so each stretch can be drawn in the colour
 * of the risk the driver will actually meet there.
 */

import type { Feature, FeatureCollection, LineString, Point } from "geojson";

import type { Checkpoint, RiskLevel, Route } from "../api/types";
import { RISK_ORDER } from "./risk";

const EARTH_RADIUS_MILES = 3958.7613;

export type Coordinate = [number, number];

export function decodePolyline(encoded: string, precision = 6): Coordinate[] {
  const coordinates: Coordinate[] = [];
  const factor = 10 ** precision;
  let index = 0;
  let lat = 0;
  let lon = 0;

  while (index < encoded.length) {
    for (let axis = 0; axis < 2; axis += 1) {
      let shift = 0;
      let result = 0;
      let byte = 0;
      do {
        byte = encoded.charCodeAt(index) - 63;
        index += 1;
        result |= (byte & 0x1f) << shift;
        shift += 5;
      } while (byte >= 0x20 && index < encoded.length);

      const delta = result & 1 ? ~(result >> 1) : result >> 1;
      if (axis === 0) {
        lat += delta;
      } else {
        lon += delta;
      }
    }
    coordinates.push([lon / factor, lat / factor]);
  }

  return coordinates;
}

function haversineMiles(a: Coordinate, b: Coordinate): number {
  const toRadians = Math.PI / 180;
  const lat1 = a[1] * toRadians;
  const lat2 = b[1] * toRadians;
  const deltaLat = lat2 - lat1;
  const deltaLon = (b[0] - a[0]) * toRadians;
  const h =
    Math.sin(deltaLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(deltaLon / 2) ** 2;
  return 2 * EARTH_RADIUS_MILES * Math.asin(Math.sqrt(Math.min(1, h)));
}

function cumulativeMiles(coordinates: Coordinate[]): number[] {
  const totals = [0];
  for (let index = 1; index < coordinates.length; index += 1) {
    const previous = coordinates[index - 1];
    const current = coordinates[index];
    if (!previous || !current) {
      continue;
    }
    totals.push((totals[index - 1] ?? 0) + haversineMiles(previous, current));
  }
  return totals;
}

function worstOf(first: RiskLevel, second: RiskLevel): RiskLevel {
  return RISK_ORDER.indexOf(first) >= RISK_ORDER.indexOf(second) ? first : second;
}

function sliceBetween(
  coordinates: Coordinate[],
  totals: number[],
  fromMiles: number,
  toMiles: number,
): Coordinate[] {
  const slice: Coordinate[] = [];
  for (let index = 0; index < coordinates.length; index += 1) {
    const distance = totals[index] ?? 0;
    if (distance >= fromMiles && distance <= toMiles) {
      const coordinate = coordinates[index];
      if (coordinate) {
        slice.push(coordinate);
      }
    }
    if (distance > toMiles) {
      break;
    }
  }
  return slice;
}

export function routeRiskSegments(route: Route): FeatureCollection<LineString> {
  const coordinates = decodePolyline(route.polyline);
  const totals = cumulativeMiles(coordinates);
  const scale = route.distance_miles > 0 ? (totals[totals.length - 1] ?? 0) / route.distance_miles : 1;
  const features: Feature<LineString>[] = [];

  for (let index = 0; index < route.checkpoints.length - 1; index += 1) {
    const start = route.checkpoints[index];
    const end = route.checkpoints[index + 1];
    if (!start || !end) {
      continue;
    }

    const slice = sliceBetween(
      coordinates,
      totals,
      start.miles_from_origin * scale,
      end.miles_from_origin * scale,
    );
    if (slice.length < 2) {
      continue;
    }

    features.push({
      type: "Feature",
      geometry: { type: "LineString", coordinates: slice },
      properties: {
        routeId: route.id,
        level: worstOf(start.level, end.level),
        fromMiles: start.miles_from_origin,
        toMiles: end.miles_from_origin,
      },
    });
  }

  if (features.length === 0 && coordinates.length >= 2) {
    features.push({
      type: "Feature",
      geometry: { type: "LineString", coordinates },
      properties: { routeId: route.id, level: route.worst_level },
    });
  }

  return { type: "FeatureCollection", features };
}

export function routeOutline(route: Route): Feature<LineString> {
  return {
    type: "Feature",
    geometry: { type: "LineString", coordinates: decodePolyline(route.polyline) },
    properties: { routeId: route.id, label: route.label, recommended: route.is_recommended },
  };
}

export function checkpointFeatures(route: Route): FeatureCollection<Point> {
  return {
    type: "FeatureCollection",
    features: route.checkpoints.map((checkpoint: Checkpoint) => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [checkpoint.lon, checkpoint.lat] },
      properties: {
        routeId: route.id,
        sequence: checkpoint.sequence,
        level: checkpoint.level,
        miles: checkpoint.miles_from_origin,
        eta: checkpoint.eta,
        driver: checkpoint.driver,
        windMph: checkpoint.weather.wind_mph,
        gustMph: checkpoint.weather.wind_gust_mph,
        rainInHr: checkpoint.weather.rain_in_hr,
        snowInHr: checkpoint.weather.snow_in_hr,
      },
    })),
  };
}

export function boundsOf(routes: Route[]): [[number, number], [number, number]] | null {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;

  for (const route of routes) {
    for (const [lon, lat] of decodePolyline(route.polyline)) {
      west = Math.min(west, lon);
      east = Math.max(east, lon);
      south = Math.min(south, lat);
      north = Math.max(north, lat);
    }
  }

  if (!Number.isFinite(west) || !Number.isFinite(south)) {
    return null;
  }
  return [
    [west, south],
    [east, north],
  ];
}
