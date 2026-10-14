/**
 * Query hooks for planning, corridor heatmaps and place lookup.
 * The heatmap is a separate deferred query so routes paint as soon as they arrive instead of
 * waiting on the slower 48 hour corridor forecast.
 */

import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { fetchHeatmap, planTrip, searchPlaces } from "../api/client";
import type { HeatmapRequest, PlanRequest } from "../api/types";

export function useTripPlan() {
  return useMutation({ mutationFn: (payload: PlanRequest) => planTrip(payload) });
}

export function useHeatmap(payload: HeatmapRequest | null, enabled: boolean) {
  return useQuery({
    queryKey: ["heatmap", payload?.polyline.slice(0, 64), payload?.departure_time, payload?.load_weight_lb, payload?.hours],
    queryFn: () => fetchHeatmap(payload as HeatmapRequest),
    enabled: enabled && payload !== null,
    staleTime: 10 * 60 * 1000,
    gcTime: 30 * 60 * 1000,
    retry: 1,
    placeholderData: keepPreviousData,
  });
}

export function useDebounced<T>(value: T, delay = 300): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}

export function usePlaceSearch(term: string) {
  const debounced = useDebounced(term.trim());

  return useQuery({
    queryKey: ["places", debounced],
    queryFn: ({ signal }) => searchPlaces(debounced, signal),
    enabled: debounced.length >= 3,
    staleTime: 5 * 60 * 1000,
    retry: false,
  });
}
