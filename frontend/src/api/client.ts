/**
 * Thin typed wrapper around the planning API.
 * Normalises backend validation and provider errors into a single ApiError so the UI can
 * surface an actionable message instead of a status code.
 */

import type { Heatmap, HeatmapRequest, Place, PlanRequest, TripPlan } from "./types";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function describe(status: number, body: unknown): string {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    if (typeof record.error === "string") {
      return record.error;
    }
    const firstField = Object.entries(record).find(([, value]) => Array.isArray(value) || typeof value === "string");
    if (firstField) {
      const [field, value] = firstField;
      const text = Array.isArray(value) ? String(value[0]) : String(value);
      return field === "detail" ? text : `${field.replace(/_/g, " ")}: ${text}`;
    }
  }
  if (status === 503) {
    return "A weather or routing service is temporarily unavailable. Try again in a moment.";
  }
  return `Request failed with status ${status}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError("Could not reach the planning service. Check your connection and try again.", 0);
  }

  const text = await response.text();
  const body = text ? (JSON.parse(text) as unknown) : null;

  if (!response.ok) {
    throw new ApiError(describe(response.status, body), response.status);
  }
  return body as T;
}

export function planTrip(payload: PlanRequest): Promise<TripPlan> {
  return request<TripPlan>("/trips/plan", { method: "POST", body: JSON.stringify(payload) });
}

export function fetchHeatmap(payload: HeatmapRequest): Promise<Heatmap> {
  return request<Heatmap>("/trips/heatmap", { method: "POST", body: JSON.stringify(payload) });
}

export function searchPlaces(query: string, signal?: AbortSignal): Promise<{ results: Place[] }> {
  const params = new URLSearchParams({ q: query, limit: "6" });
  return request<{ results: Place[] }>(`/places?${params.toString()}`, signal ? { signal } : {});
}
