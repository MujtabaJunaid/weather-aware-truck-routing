/**
 * Presentation metadata for the five risk levels.
 * One table drives the map colours, legend, badges and heatmap ramp so a level always looks
 * the same wherever it appears.
 */

import type { RiskLevel } from "../api/types";

interface RiskStyle {
  label: string;
  line: string;
  badge: string;
  dot: string;
}

export const RISK_STYLES: Record<RiskLevel, RiskStyle> = {
  low: {
    label: "Low",
    line: "#16a34a",
    badge: "bg-emerald-100 text-emerald-900 ring-emerald-300",
    dot: "bg-emerald-500",
  },
  moderate: {
    label: "Moderate",
    line: "#eab308",
    badge: "bg-amber-100 text-amber-900 ring-amber-300",
    dot: "bg-amber-400",
  },
  high: {
    label: "High",
    line: "#f97316",
    badge: "bg-orange-100 text-orange-900 ring-orange-300",
    dot: "bg-orange-500",
  },
  severe: {
    label: "Severe",
    line: "#dc2626",
    badge: "bg-red-100 text-red-900 ring-red-300",
    dot: "bg-red-500",
  },
  no_travel: {
    label: "No travel",
    line: "#7c3aed",
    badge: "bg-violet-100 text-violet-900 ring-violet-300",
    dot: "bg-violet-500",
  },
};

export const RISK_ORDER: RiskLevel[] = ["low", "moderate", "high", "severe", "no_travel"];

export function riskStyle(level: RiskLevel): RiskStyle {
  return RISK_STYLES[level];
}

export const DRIVER_LABELS: Record<string, string> = {
  none: "No notable conditions",
  wind: "Wind speed",
  rain: "Rainfall rate",
  snow: "Snowfall rate",
  load: "Wind combined with load weight",
};
