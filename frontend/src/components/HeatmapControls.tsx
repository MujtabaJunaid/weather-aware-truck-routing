/**
 * Toggle and 0-48 hour scrubber for the corridor weather heatmap.
 * Scrubbing only changes the selected hour; the forecast itself is fetched once per route.
 */

import type { Heatmap } from "../api/types";
import { clockTime } from "../lib/format";

interface HeatmapControlsProps {
  heatmap: Heatmap | null;
  hour: number;
  enabled: boolean;
  isLoading: boolean;
  onToggle: (enabled: boolean) => void;
  onHourChange: (hour: number) => void;
}

export function HeatmapControls({
  heatmap,
  hour,
  enabled,
  isLoading,
  onToggle,
  onHourChange,
}: HeatmapControlsProps) {
  const maxHour = heatmap ? heatmap.hours.length - 1 : 48;
  const active = heatmap?.hours[Math.min(hour, maxHour)];

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Corridor heatmap</h2>
          <p className="text-xs text-slate-500">48 hour outlook around the selected route</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          onClick={() => onToggle(!enabled)}
          className={`relative h-6 w-11 shrink-0 rounded-full transition ${
            enabled ? "bg-sky-600" : "bg-slate-300"
          }`}
        >
          <span
            className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-all ${
              enabled ? "left-[22px]" : "left-0.5"
            }`}
          />
        </button>
      </div>

      {enabled && (
        <div className="mt-3">
          {isLoading && !heatmap && <p className="text-xs text-slate-500">Loading 48 hour forecast…</p>}

          {heatmap && (
            <>
              <div className="flex items-baseline justify-between text-xs">
                <span className="font-medium text-slate-700">
                  {hour === 0 ? "At departure" : `+${hour} h`}
                </span>
                {active && <span className="text-slate-500">{clockTime(active)}</span>}
              </div>
              <input
                type="range"
                min={0}
                max={maxHour}
                step={1}
                value={Math.min(hour, maxHour)}
                onChange={(event) => onHourChange(Number(event.target.value))}
                className="mt-1.5 w-full accent-sky-600"
                aria-label="Forecast hour offset"
              />
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>now</span>
                <span>+12 h</span>
                <span>+24 h</span>
                <span>+36 h</span>
                <span>+48 h</span>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
