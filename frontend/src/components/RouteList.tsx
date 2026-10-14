/**
 * Selectable summary cards for the returned routes.
 * Each card carries the figures the ranking is based on, so the recommendation can be
 * checked against the alternatives rather than taken on trust.
 */

import type { Route } from "../api/types";
import { dateTime, duration, miles } from "../lib/format";
import { RISK_ORDER, riskStyle } from "../lib/risk";

interface RouteListProps {
  routes: Route[];
  selectedId: string;
  onSelect: (routeId: string) => void;
}

function MileageBar({ route }: { route: Route }) {
  const total = route.distance_miles || 1;

  return (
    <div className="flex h-1.5 overflow-hidden rounded-full bg-slate-100">
      {RISK_ORDER.map((level) => {
        const share = (route.miles_by_level[level] / total) * 100;
        if (share <= 0) {
          return null;
        }
        return (
          <span
            key={level}
            title={`${riskStyle(level).label}: ${miles(route.miles_by_level[level])}`}
            style={{ width: `${share}%`, backgroundColor: riskStyle(level).line }}
          />
        );
      })}
    </div>
  );
}

export function RouteList({ routes, selectedId, onSelect }: RouteListProps) {
  return (
    <ul className="space-y-2">
      {routes.map((route) => {
        const selected = route.id === selectedId;
        const worst = riskStyle(route.worst_level);

        return (
          <li key={route.id}>
            <button
              type="button"
              onClick={() => onSelect(route.id)}
              aria-pressed={selected}
              className={`w-full rounded-xl border p-3 text-left transition ${
                selected
                  ? "border-sky-600 bg-sky-50/70 ring-1 ring-sky-200"
                  : "border-slate-200 bg-white hover:border-slate-300"
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-slate-900">{route.label}</p>
                  <p className="mt-0.5 text-xs text-slate-500">
                    {miles(route.distance_miles)} · {duration(route.duration_seconds)} · arrives{" "}
                    {dateTime(route.arrival_time)}
                  </p>
                </div>
                {route.is_recommended && (
                  <span className="shrink-0 rounded-full bg-sky-600 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                    Best
                  </span>
                )}
              </div>

              <div className="mt-2.5 space-y-2">
                <MileageBar route={route} />
                <div className="flex flex-wrap items-center gap-1.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-medium ring-1 ring-inset ${worst.badge}`}
                  >
                    worst {worst.label.toLowerCase()}
                  </span>
                  <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">
                    avg risk {route.average_risk.toFixed(2)}
                  </span>
                  {route.miles_by_level.severe > 0 && (
                    <span className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] text-red-700">
                      {miles(route.miles_by_level.severe)} severe
                    </span>
                  )}
                  {route.miles_by_level.high > 0 && (
                    <span className="rounded-full bg-orange-50 px-2 py-0.5 text-[10px] text-orange-700">
                      {miles(route.miles_by_level.high)} high
                    </span>
                  )}
                  {route.has_toll && (
                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] text-slate-600">tolls</span>
                  )}
                </div>

                {route.is_blocked && (
                  <p className="rounded-lg bg-violet-50 px-2 py-1 text-[11px] font-medium text-violet-800">
                    Contains {miles(route.miles_by_level.no_travel)} where conditions and this load prohibit travel.
                  </p>
                )}
              </div>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
