/**
 * MapLibre view of the candidate routes, their checkpoints and the corridor weather heatmap.
 * Sources are created once and updated through setData, so changing the hour or the selected
 * route repaints without rebuilding the style or refitting the camera.
 */

import maplibregl from "maplibre-gl";
import type { GeoJSONSource, MapLayerMouseEvent } from "maplibre-gl";
import { useCallback, useEffect, useRef } from "react";
import type { FeatureCollection, LineString, Point as GeoPoint } from "geojson";

import type { Heatmap, TripPlan } from "../api/types";
import { checkpointFeatures, boundsOf, routeOutline, routeRiskSegments } from "../lib/geometry";
import { clockTime, rate } from "../lib/format";
import { DRIVER_LABELS, RISK_STYLES, riskStyle } from "../lib/risk";

const STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

const SOURCES = {
  heatmap: "corridor-heatmap",
  outlines: "route-outlines",
  risk: "route-risk",
  checkpoints: "route-checkpoints",
  endpoints: "trip-endpoints",
} as const;

const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

const LEVEL_COLOR_EXPRESSION = [
  "match",
  ["get", "level"],
  "low",
  RISK_STYLES.low.line,
  "moderate",
  RISK_STYLES.moderate.line,
  "high",
  RISK_STYLES.high.line,
  "severe",
  RISK_STYLES.severe.line,
  "no_travel",
  RISK_STYLES.no_travel.line,
  "#64748b",
];

interface RouteMapProps {
  plan: TripPlan | null;
  selectedRouteId: string;
  heatmap: Heatmap | null;
  heatmapHour: number;
  showHeatmap: boolean;
  onSelectRoute: (routeId: string) => void;
}

function heatmapCollection(heatmap: Heatmap | null, hour: number): FeatureCollection<GeoPoint> {
  if (!heatmap) {
    return { type: "FeatureCollection", features: [] };
  }

  return {
    type: "FeatureCollection",
    features: heatmap.points
      .map((point) => ({ point, level: point.levels[hour] ?? 0 }))
      .filter((entry) => entry.level > 0)
      .map(({ point, level }) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [point.lon, point.lat] },
        properties: { level, weight: level / 4 },
      })),
  };
}

export function RouteMap({
  plan,
  selectedRouteId,
  heatmap,
  heatmapHour,
  showHeatmap,
  onSelectRoute,
}: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const readyRef = useRef(false);
  const fittedRef = useRef<string>("");

  const setData = useCallback((id: string, data: FeatureCollection) => {
    const map = mapRef.current;
    if (!map || !readyRef.current) {
      return;
    }
    const source = map.getSource(id) as GeoJSONSource | undefined;
    source?.setData(data);
  }, []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) {
      return;
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center: [-98.5, 39.5],
      zoom: 3.4,
      attributionControl: { compact: true },
    });
    mapRef.current = map;
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "imperial" }), "bottom-left");

    map.on("load", () => {
      for (const id of Object.values(SOURCES)) {
        map.addSource(id, { type: "geojson", data: EMPTY });
      }

      map.addLayer({
        id: "heatmap-layer",
        type: "heatmap",
        source: SOURCES.heatmap,
        paint: {
          "heatmap-weight": ["get", "weight"],
          "heatmap-intensity": 1,
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 3, 34, 5, 62, 7, 110, 10, 190],
          "heatmap-opacity": 0.7,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(0,0,0,0)",
            0.1,
            "rgba(22,163,74,0.45)",
            0.25,
            "rgba(234,179,8,0.7)",
            0.5,
            "rgba(249,115,22,0.8)",
            0.75,
            "rgba(220,38,38,0.88)",
            1,
            "rgba(124,58,237,0.95)",
          ],
        },
      });

      map.addLayer({
        id: "outline-layer",
        type: "line",
        source: SOURCES.outlines,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": "#64748b",
          "line-width": ["case", ["get", "selected"], 0, 3],
          "line-opacity": 0.45,
          "line-dasharray": [2, 1.5],
        },
      });

      map.addLayer({
        id: "risk-casing",
        type: "line",
        source: SOURCES.risk,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": "#0f172a", "line-width": 7, "line-opacity": 0.35 },
      });

      map.addLayer({
        id: "risk-layer",
        type: "line",
        source: SOURCES.risk,
        layout: { "line-cap": "round", "line-join": "round" },
        paint: { "line-color": LEVEL_COLOR_EXPRESSION as never, "line-width": 4.5 },
      });

      map.addLayer({
        id: "checkpoint-layer",
        type: "circle",
        source: SOURCES.checkpoints,
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3.2, 7, 6],
          "circle-color": LEVEL_COLOR_EXPRESSION as never,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1.2,
        },
      });

      map.addLayer({
        id: "endpoint-layer",
        type: "circle",
        source: SOURCES.endpoints,
        paint: {
          "circle-radius": 7,
          "circle-color": ["case", ["get", "isOrigin"], "#0f172a", "#0ea5e9"],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2.5,
        },
      });

      readyRef.current = true;
      map.resize();
    });

    const showCheckpoint = (event: MapLayerMouseEvent) => {
      const feature = event.features?.[0];
      if (!feature) {
        return;
      }
      const properties = feature.properties as Record<string, string | number>;
      const level = riskStyle(String(properties.level) as never);
      const driver = DRIVER_LABELS[String(properties.driver)] ?? "—";

      new maplibregl.Popup({ closeButton: false, offset: 12, maxWidth: "260px" })
        .setLngLat(event.lngLat)
        .setHTML(
          `<div style="font:12px/1.45 system-ui,sans-serif">
             <strong style="font-size:13px">Mile ${Number(properties.miles).toFixed(0)}</strong><br/>
             <span style="color:${level.line};font-weight:600">${level.label}</span>
             &middot; ${clockTime(String(properties.eta))}<br/>
             Wind ${Number(properties.windMph).toFixed(0)} mph (gust ${Number(properties.gustMph).toFixed(0)})<br/>
             Rain ${rate(Number(properties.rainInHr), "in/hr")} &middot; Snow ${rate(Number(properties.snowInHr), "in/hr")}<br/>
             <span style="color:#64748b">Driven by: ${driver}</span>
           </div>`,
        )
        .addTo(map);
    };

    map.on("click", "checkpoint-layer", showCheckpoint);
    map.on("click", "outline-layer", (event) => {
      const routeId = event.features?.[0]?.properties?.routeId;
      if (typeof routeId === "string") {
        onSelectRoute(routeId);
      }
    });

    for (const layer of ["checkpoint-layer", "outline-layer"]) {
      map.on("mouseenter", layer, () => {
        map.getCanvas().style.cursor = "pointer";
      });
      map.on("mouseleave", layer, () => {
        map.getCanvas().style.cursor = "";
      });
    }

    return () => {
      readyRef.current = false;
      map.remove();
      mapRef.current = null;
    };
  }, [onSelectRoute]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const paint = () => {
      if (!plan) {
        setData(SOURCES.outlines, EMPTY);
        setData(SOURCES.risk, EMPTY);
        setData(SOURCES.checkpoints, EMPTY);
        setData(SOURCES.endpoints, EMPTY);
        return;
      }

      const outlines: FeatureCollection<LineString> = {
        type: "FeatureCollection",
        features: plan.routes.map((route) => {
          const feature = routeOutline(route);
          return {
            ...feature,
            properties: { ...feature.properties, selected: route.id === selectedRouteId },
          };
        }),
      };
      setData(SOURCES.outlines, outlines);

      const selected = plan.routes.find((route) => route.id === selectedRouteId) ?? plan.routes[0];
      if (selected) {
        setData(SOURCES.risk, routeRiskSegments(selected));
        setData(SOURCES.checkpoints, checkpointFeatures(selected));
      }

      setData(SOURCES.endpoints, {
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [plan.origin.lon, plan.origin.lat] },
            properties: { isOrigin: true, label: plan.origin.label },
          },
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [plan.destination.lon, plan.destination.lat] },
            properties: { isOrigin: false, label: plan.destination.label },
          },
        ],
      });

      const signature = `${plan.origin.label}|${plan.destination.label}|${plan.routes.length}`;
      const bounds = boundsOf(plan.routes);
      if (bounds && fittedRef.current !== signature) {
        fittedRef.current = signature;
        map.fitBounds(bounds, { padding: 64, duration: 700, maxZoom: 9 });
      }
    };

    if (readyRef.current) {
      paint();
    } else {
      map.once("load", paint);
    }
  }, [plan, selectedRouteId, setData]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    const paint = () => {
      setData(SOURCES.heatmap, showHeatmap ? heatmapCollection(heatmap, heatmapHour) : EMPTY);
      if (map.getLayer("heatmap-layer")) {
        map.setLayoutProperty("heatmap-layer", "visibility", showHeatmap ? "visible" : "none");
      }
    };

    if (readyRef.current) {
      paint();
    } else {
      map.once("load", paint);
    }
  }, [heatmap, heatmapHour, showHeatmap, setData]);

  const activeHour = heatmap?.hours[heatmapHour];

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />

      {showHeatmap && activeHour && (
        <div className="pointer-events-none absolute left-3 top-3 rounded-lg bg-white/90 px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm ring-1 ring-slate-200">
          Corridor risk at {clockTime(activeHour)}
          {heatmapCollection(heatmap, heatmapHour).features.length === 0 && (
            <span className="ml-1 font-normal text-slate-500">· all clear</span>
          )}
        </div>
      )}

      {!plan && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <p className="rounded-xl bg-white/90 px-4 py-2 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
            Enter a trip to compare routes.
          </p>
        </div>
      )}
    </div>
  );
}
