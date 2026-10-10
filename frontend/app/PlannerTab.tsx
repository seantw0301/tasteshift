"use client";

import { useEffect, useState } from "react";
import { API_BASE, api, nt, pct, type EventInfo, type FullPlan, type MerchantInfo } from "./types";

const LEVERS = [
  { key: "rain", label: "Afternoon rain", patch: { rain: true } },
  { key: "att", label: "Attendance −30%", patch: { attendance_factor: 0.7 } },
  { key: "cost", label: "Unit cost +15%", patch: { cost_factor: 1.15 } },
  { key: "rival", label: "Rival stalls (traffic −20%)", patch: { competitor_factor: 0.8 } },
  { key: "moq", label: "Supplier MOQ ×2", patch: { moq_factor: 2 } },
];
type Replan = { before: FullPlan; after: FullPlan; why: string[]; profit_change: number };

export default function PlannerTab({ merchants, events, onAudit }: {
  merchants: MerchantInfo[]; events: EventInfo[]; onAudit: (id: string) => void;
}) {
  const [merchant, setMerchant] = useState(merchants[0]?.id);
  const [event, setEvent] = useState(events[0]?.id);
  const [risk, setRisk] = useState("balanced");
  const [on, setOn] = useState<string[]>([]);
  const [plans, setPlans] = useState<Record<string, FullPlan> | null>(null);
  const [re, setRe] = useState<Replan | null>(null);

  useEffect(() => {
    const scenario = Object.assign({}, ...LEVERS.filter((l) => on.includes(l.key)).map((l) => l.patch));
    const body = { event_id: event, merchant_id: merchant, risk, scenario: on.length ? scenario : null };
    let stale = false;
    Promise.all([api<Record<string, FullPlan>>("/api/optimize/plans", body), api<Replan>("/api/scenarios/replan", body)])
      .then(([p, r]) => { if (!stale) { setPlans(p); setRe(r); } });
    return () => { stale = true; };
  }, [merchant, event, risk, on]);

  const sel = "rounded-md border border-stone-300 bg-white px-2 py-1";
  return (
    <div className="mt-6 space-y-5">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <select className={sel} value={merchant} onChange={(e) => setMerchant(e.target.value)}>
          {merchants.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        <select className={sel} value={event} onChange={(e) => setEvent(e.target.value)}>
          {events.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
        </select>
        {LEVERS.map((l) => (
          <label key={l.key} className="flex items-center gap-1.5">
            <input type="checkbox" checked={on.includes(l.key)}
              onChange={() => setOn(on.includes(l.key) ? on.filter((k) => k !== l.key) : [...on, l.key])} />{l.label}
          </label>
        ))}
      </div>

      {plans && (
        <div className="grid gap-4 md:grid-cols-3">
          {Object.entries(plans).map(([name, p]) => (
            <button key={name} onClick={() => setRisk(name)}
              className={`rounded-xl border bg-white p-4 text-left ${risk === name ? "border-teal-600 ring-1 ring-teal-600" : "border-stone-200"}`}>
              <div className="text-sm font-semibold capitalize">{name}</div>
              <div className="mt-1 text-2xl font-bold tabular-nums">{nt(p.metrics.expected_profit)}</div>
              <div className="text-xs text-stone-500">expected profit · worst 10% {nt(p.metrics.profit_p10)}</div>
              <div className="mt-2 grid grid-cols-3 gap-1 text-xs text-stone-600">
                <span>Spend<br /><b className="text-stone-900">{nt(p.total_cost)}</b></span>
                <span>Stockout<br /><b className="text-stone-900">{pct(p.metrics.avg_stockout_rate)}</b></span>
                <span>Leftover<br /><b className="text-stone-900">{p.metrics.expected_leftover_units.toFixed(0)} u</b></span>
              </div>
            </button>
          ))}
        </div>
      )}
      {plans && plans.balanced.total_cost === plans.aggressive.total_cost && (
        <p className="text-xs text-stone-500">Balanced and Aggressive match here because the budget is already fully used.</p>
      )}

      {re && (
        <div className="grid gap-5 lg:grid-cols-3">
          <section className="rounded-xl border border-stone-200 bg-white p-5 lg:col-span-2">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold capitalize">{risk} purchase order</h2>
              <div className="flex gap-2 text-xs">
                <a className="rounded-md border border-stone-300 px-2.5 py-1" href={`${API_BASE}/api/decisions/${re.after.decision_id}/purchase-order.csv`}>Purchase order CSV</a>
                <button className="rounded-md border border-stone-300 px-2.5 py-1" onClick={() => onAudit(re.after.decision_id)}>Decision audit</button>
              </div>
            </div>
            {re.why.length > 0 && (
              <div className="mt-3 rounded-md bg-amber-50 p-2 text-sm text-amber-900">
                {re.why.map((w) => <div key={w}>{w}</div>)}
                <div className="mt-1 font-medium">Expected profit {re.profit_change >= 0 ? "+" : "−"}{nt(Math.abs(re.profit_change))} vs no scenario, same budget and limits.</div>
              </div>
            )}
            <table className="mt-3 w-full text-sm">
              <thead className="text-left text-xs text-stone-500"><tr>
                <th className="pb-2 font-medium">SKU</th><th className="pb-2 text-right font-medium">Demand p10–p90</th>
                <th className="pb-2 text-right font-medium">Stock</th><th className="pb-2 text-right font-medium">Cost</th>
                <th className="pb-2 text-right font-medium">Stockout</th></tr></thead>
              <tbody>{re.after.skus.map((s, i) => {
                const d = s.stock_qty - re.before.skus[i].stock_qty;
                return (
                  <tr key={s.sku_id} className={`border-t border-stone-100 ${s.stock_qty ? "" : "text-stone-400"}`}>
                    <td className="py-1.5">{s.name}{s.excluded_reason && <span className="ml-2 text-xs text-amber-700">{s.excluded_reason}</span>}</td>
                    <td className="text-right tabular-nums">{Math.round(s.demand_p10)}–{Math.round(s.demand_p90)}</td>
                    <td className="text-right font-semibold tabular-nums">{s.stock_qty}
                      {d !== 0 && <span className={`ml-1 text-xs font-normal ${d > 0 ? "text-teal-700" : "text-rose-600"}`}>{d > 0 ? "+" : ""}{d}</span>}</td>
                    <td className="text-right tabular-nums">{nt(s.cost)}</td>
                    <td className="text-right tabular-nums">{pct(s.stockout_risk)}</td>
                  </tr>);
              })}</tbody>
            </table>
          </section>
          <section className="rounded-xl border border-stone-200 bg-white p-5 text-sm">
            <h2 className="font-semibold">Capacity and ingredients</h2>
            <p className="mt-2 text-stone-600">{re.after.capacity_note ?? "No production capacity limit for this merchant."}</p>
            {re.after.ingredients.length > 0 ? (
              <table className="mt-3 w-full"><tbody>{re.after.ingredients.map((i) => (
                <tr key={i.ingredient} className="border-t border-stone-100">
                  <td className="py-1">{i.ingredient}</td>
                  <td className="text-right tabular-nums">{i.quantity} {i.unit}</td></tr>))}</tbody></table>
            ) : <p className="mt-3 text-stone-400">No recipes: items are bought finished.</p>}
            <p className="mt-3 text-xs text-stone-400">Ingredient amounts include each recipe&apos;s waste allowance. Recipes and capacity figures are synthetic.</p>
          </section>
        </div>
      )}
    </div>
  );
}
