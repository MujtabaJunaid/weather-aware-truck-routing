/**
 * Legend mapping each risk level to its colour, plus the thresholds behind the levels.
 * Shown beside the map so a colour on the route can be read without opening a checkpoint.
 */

import { RISK_ORDER, RISK_STYLES } from "../lib/risk";

const THRESHOLDS = [
  { level: "Low", wind: "<25", rain: "<0.10", snow: "<0.5" },
  { level: "Moderate", wind: "25–34", rain: "0.10–0.25", snow: "0.5–1.0" },
  { level: "High", wind: "35–44", rain: "0.25–0.50", snow: "1.0–2.0" },
  { level: "Severe", wind: "45–54", rain: "0.50–1.00", snow: "2.0–3.0" },
  { level: "No travel", wind: "≥55", rain: ">1.00", snow: ">3.0" },
];

export function RiskLegend() {
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-x-4 gap-y-2">
        {RISK_ORDER.map((level) => (
          <span key={level} className="flex items-center gap-1.5 text-xs text-slate-600">
            <span
              className="h-2.5 w-5 rounded-full"
              style={{ backgroundColor: RISK_STYLES[level].line }}
              aria-hidden
            />
            {RISK_STYLES[level].label}
          </span>
        ))}
      </div>

      <details className="group">
        <summary className="cursor-pointer text-xs font-medium text-sky-700 hover:text-sky-900">
          Thresholds and load rules
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[22rem] text-left text-[11px] text-slate-600">
            <thead className="text-slate-500">
              <tr>
                <th className="py-1 pr-3 font-medium">Level</th>
                <th className="py-1 pr-3 font-medium">Wind (mph)</th>
                <th className="py-1 pr-3 font-medium">Rain (in/hr)</th>
                <th className="py-1 font-medium">Snow (in/hr)</th>
              </tr>
            </thead>
            <tbody>
              {THRESHOLDS.map((row) => (
                <tr key={row.level} className="border-t border-slate-100">
                  <td className="py-1 pr-3 font-medium text-slate-700">{row.level}</td>
                  <td className="py-1 pr-3">{row.wind}</td>
                  <td className="py-1 pr-3">{row.rain}</td>
                  <td className="py-1">{row.snow}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <ul className="mt-2 space-y-0.5 text-[11px] text-slate-500">
            <li>Wind at or above 55 mph is no travel for any load.</li>
            <li>Wind 45–54 mph with more than 30,000 lb is no travel.</li>
            <li>Wind 35–44 mph with more than 40,000 lb is severe.</li>
          </ul>
        </div>
      </details>
    </div>
  );
}
