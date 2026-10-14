/**
 * Recommendation panel showing the deterministic reason and the narrated driver briefing.
 * The reason is always the authority; the briefing is prose generated from that decision.
 */

import type { TripPlan } from "../api/types";

export function Briefing({ plan }: { plan: TripPlan }) {
  const recommended = plan.routes.find((route) => route.id === plan.recommended_route_id);
  const narrated = plan.briefing_source === "groq" && plan.briefing !== plan.recommendation_reason;

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4">
      <header className="flex items-baseline justify-between gap-2">
        <h2 className="text-sm font-semibold text-slate-900">Recommendation</h2>
        {recommended && <span className="text-xs font-medium text-sky-700">{recommended.label}</span>}
      </header>

      <p className="mt-2 text-sm leading-relaxed text-slate-700">{plan.recommendation_reason}</p>

      {narrated && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">Driver briefing</p>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">{plan.briefing}</p>
        </div>
      )}
    </section>
  );
}
