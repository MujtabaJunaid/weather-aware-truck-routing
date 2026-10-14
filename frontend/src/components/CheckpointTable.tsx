/**
 * Checkpoint-by-checkpoint detail for the selected route.
 * Lists the arrival time, risk level and the readings behind it, which is what makes a
 * recommendation auditable rather than a black box.
 */

import type { Route } from "../api/types";
import { clockTime, preciseMiles } from "../lib/format";
import { DRIVER_LABELS, riskStyle } from "../lib/risk";

export function CheckpointTable({ route }: { route: Route }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white">
      <header className="flex items-baseline justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <h2 className="text-sm font-semibold text-slate-900">Checkpoints</h2>
        <span className="text-xs text-slate-500">
          {route.checkpoints.length} samples on {route.label}
        </span>
      </header>

      <div className="max-h-80 overflow-auto">
        <table className="w-full text-left text-xs">
          <thead className="sticky top-0 bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-2 font-medium">Mile</th>
              <th className="px-2 py-2 font-medium">ETA</th>
              <th className="px-2 py-2 font-medium">Risk</th>
              <th className="px-2 py-2 font-medium">Wind</th>
              <th className="px-2 py-2 font-medium">Rain</th>
              <th className="px-4 py-2 font-medium">Snow</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((checkpoint) => {
              const style = riskStyle(checkpoint.level);
              return (
                <tr key={checkpoint.sequence} className="border-t border-slate-100">
                  <td className="px-4 py-1.5 font-medium text-slate-700">
                    {preciseMiles(checkpoint.miles_from_origin)}
                  </td>
                  <td className="px-2 py-1.5 text-slate-600">{clockTime(checkpoint.eta)}</td>
                  <td className="px-2 py-1.5">
                    <span
                      title={DRIVER_LABELS[checkpoint.driver] ?? ""}
                      className={`inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 font-medium ring-1 ring-inset ${style.badge}`}
                    >
                      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} aria-hidden />
                      {style.label}
                    </span>
                  </td>
                  <td className="px-2 py-1.5 text-slate-600">
                    {checkpoint.weather.wind_mph.toFixed(0)}
                    <span className="text-slate-400"> / {checkpoint.weather.wind_gust_mph.toFixed(0)}</span>
                  </td>
                  <td className="px-2 py-1.5 text-slate-600">{checkpoint.weather.rain_in_hr.toFixed(2)}</td>
                  <td className="px-4 py-1.5 text-slate-600">{checkpoint.weather.snow_in_hr.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <footer className="border-t border-slate-100 px-4 py-2 text-[11px] text-slate-400">
        Wind shown as sustained / gust in mph. Rain and snow in inches per hour.
      </footer>
    </section>
  );
}
