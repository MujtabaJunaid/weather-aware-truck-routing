/**
 * Shapes returned by the planning API, mirrored from the backend presenters.
 * Kept free of UI concerns so components depend on the wire contract and nothing else.
 */

export const RISK_LEVELS = ["low", "moderate", "high", "severe", "no_travel"] as const;

export type RiskLevel = (typeof RISK_LEVELS)[number];

export type RiskDriver = "none" | "wind" | "rain" | "snow" | "load";

export interface Place {
  label: string;
  lat: number;
  lon: number;
}

export interface CheckpointWeather {
  wind_mph: number;
  wind_gust_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
}

export interface Checkpoint {
  sequence: number;
  miles_from_origin: number;
  segment_miles: number;
  lat: number;
  lon: number;
  eta: string;
  level: RiskLevel;
  driver: RiskDriver;
  levels: Record<"wind" | "rain" | "snow" | "load", RiskLevel>;
  weather: CheckpointWeather;
}

export interface Route {
  id: string;
  label: string;
  polyline: string;
  distance_miles: number;
  duration_seconds: number;
  arrival_time: string;
  has_toll: boolean;
  has_highway: boolean;
  is_recommended: boolean;
  is_blocked: boolean;
  worst_level: RiskLevel;
  average_risk: number;
  miles_by_level: Record<RiskLevel, number>;
  checkpoints: Checkpoint[];
}

export interface TripPlan {
  origin: Place;
  destination: Place;
  departure_time: string;
  load_weight_lb: number;
  checkpoint_interval_miles: number;
  recommended_route_id: string;
  recommendation_reason: string;
  briefing: string;
  briefing_source: "groq" | "deterministic";
  routes: Route[];
}

export interface HeatmapPoint {
  lat: number;
  lon: number;
  miles_from_origin: number;
  lateral_miles: number;
  levels: number[];
}

export interface Heatmap {
  hours: string[];
  points: HeatmapPoint[];
}

export interface PlanRequest {
  origin?: string;
  origin_lat?: number;
  origin_lon?: number;
  destination?: string;
  destination_lat?: number;
  destination_lon?: number;
  departure_time: string;
  load_weight_lb: number;
  checkpoint_interval_miles: number;
}

export interface HeatmapRequest {
  polyline: string;
  departure_time: string;
  load_weight_lb: number;
  hours: number;
}
