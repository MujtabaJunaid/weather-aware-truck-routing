/**
 * Application shell wiring the trip form, map, route comparison and heatmap together.
 * Holds the small amount of cross-component state: the submitted request, the selected route
 * and the heatmap hour offset.
 */

import { useMemo, useState } from "react";

import type { HeatmapRequest, PlanRequest, TripPlan } from "./api/types";
import { Briefing } from "./components/Briefing";
import { CheckpointTable } from "./components/CheckpointTable";
import { HeatmapControls } from "./components/HeatmapControls";
import { RiskLegend } from "./components/RiskLegend";
import { RouteList } from "./components/RouteList";
import { RouteMap } from "./components/RouteMap";
import { TripForm } from "./components/TripForm";
import { useHeatmap, useTripPlan } from "./hooks/usePlanning";
import { toLocalInputValue } from "./lib/format";

function defaultDeparture(): string {
  const date = new Date();
  date.setMinutes(0, 0, 0);
  date.setHours(date.getHours() + 2);
  return toLocalInputValue(date);
}

export default function App() {
  const plan = useTripPlan();
  const [request, setRequest] = useState<PlanRequest | null>(null);
  const [selectedRouteId, setSelectedRouteId] = useState("");
  const [showHeatmap, setShowHeatmap] = useState(true);
  const [heatmapHour, setHeatmapHour] = useState(0);

  const data: TripPlan | null = plan.data ?? null;
  const selectedRoute = useMemo(() => {
    if (!data) {
      return null;
    }
    return data.routes.find((route) => route.id === selectedRouteId) ?? data.routes[0] ?? null;
  }, [data, selectedRouteId]);

  const heatmapRequest: HeatmapRequest | null =
    selectedRoute && request
      ? {
          polyline: selectedRoute.polyline,
          departure_time: request.departure_time,
          load_weight_lb: request.load_weight_lb,
          hours: 48,
        }
      : null;

  const heatmap = useHeatmap(heatmapRequest, showHeatmap);

  const submit = (payload: PlanRequest) => {
    setRequest(payload);
    setHeatmapHour(0);
    plan.mutate(payload, {
      onSuccess: (result) => setSelectedRouteId(result.recommended_route_id),
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[1600px] flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-4 py-3">
          <h1 className="text-base font-semibold tracking-tight">Weather-Aware Truck Routing</h1>
          <p className="text-xs text-slate-500">
            Routes weighed by forecast risk at each checkpoint, load weight and travel time
          </p>
        </div>
      </header>

      <main className="mx-auto grid max-w-[1600px] gap-4 p-4 lg:grid-cols-[360px_minmax(0,1fr)]">
        <aside className="space-y-4">
          <section className="rounded-xl border border-slate-200 bg-white p-4">
            <TripForm defaultDeparture={defaultDeparture()} isPending={plan.isPending} onSubmit={submit} />
          </section>

          {plan.isError && (
            <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {plan.error instanceof Error ? plan.error.message : "Planning failed."}
            </p>
          )}

          <section className="rounded-xl border border-slate-200 bg-white p-4">
            <h2 className="mb-2 text-sm font-semibold text-slate-900">Risk levels</h2>
            <RiskLegend />
          </section>
        </aside>

        <section className="min-w-0 space-y-4">
          <div className="h-[52vh] min-h-[360px] overflow-hidden rounded-xl border border-slate-200 bg-white">
            <RouteMap
              plan={data}
              selectedRouteId={selectedRoute?.id ?? ""}
              heatmap={heatmap.data ?? null}
              heatmapHour={heatmapHour}
              showHeatmap={showHeatmap}
              onSelectRoute={setSelectedRouteId}
            />
          </div>

          {data && (
            <div className="grid gap-4 xl:grid-cols-2">
              <div className="space-y-4">
                <Briefing plan={data} />
                <section>
                  <h2 className="mb-2 text-sm font-semibold text-slate-900">
                    Route options
                    <span className="ml-1.5 font-normal text-slate-500">
                      ranked by severe miles, then high miles, then average risk, then time
                    </span>
                  </h2>
                  <RouteList
                    routes={data.routes}
                    selectedId={selectedRoute?.id ?? ""}
                    onSelect={setSelectedRouteId}
                  />
                </section>
              </div>

              <div className="space-y-4">
                <HeatmapControls
                  heatmap={heatmap.data ?? null}
                  hour={heatmapHour}
                  enabled={showHeatmap}
                  isLoading={heatmap.isFetching}
                  onToggle={setShowHeatmap}
                  onHourChange={setHeatmapHour}
                />
                {selectedRoute && <CheckpointTable route={selectedRoute} />}
              </div>
            </div>
          )}
        </section>
      </main>

      <footer className="mx-auto max-w-[1600px] px-4 pb-6 text-[11px] leading-relaxed text-slate-400">
        Routing by Valhalla (FOSSGIS) on OpenStreetMap data · forecasts and geocoding by Open-Meteo ·
        address fallback by Nominatim · basemap by OpenFreeMap. Forecasts are guidance only; the driver
        remains responsible for the go or no-go decision.
      </footer>
    </div>
  );
}
