import type { EventInfo, EventResult, SkuPlan } from "./types";

const nt = (n: number) => "NT$" + Math.round(n).toLocaleString();
const pct = (n: number | null) => (n == null ? "–" : Math.round(n * 100) + "%");

function Affinity({ s }: { s: SkuPlan }) {
  if (s.affinity == null) return <span className="text-xs text-stone-400">unknown</span>;
  return (
    <div className="flex items-center gap-2" title={s.affinity_status}>
      <div className="h-1.5 w-16 rounded bg-stone-200">
        <div className="h-1.5 rounded bg-teal-600" style={{ width: `${s.affinity * 100}%` }} />
      </div>
      <span className="text-xs tabular-nums">{s.affinity.toFixed(2)}{s.affinity_status === "partial" ? "*" : ""}</span>
    </div>
  );
}

export default function EventColumn({ event, r, qlooOn, onAudit }: {
  event: EventInfo; r: EventResult; qlooOn: boolean; onAudit: (id: string) => void;
}) {
  const plan = qlooOn ? r.on : r.off;
  const other = qlooOn ? r.off : r.on;
  const a = r.ablation;
  const gain = a.delta.expected_profit;
  return (
    <section className="rounded-xl border border-stone-200 bg-white p-5">
      <div className="flex items-baseline justify-between">
        <h2 className="text-lg font-semibold">{event.name}</h2>
        <span className="text-sm text-stone-500">{plan.attendance.toLocaleString()} attendees</span>
      </div>

      <div className="mt-3 flex min-h-14 flex-wrap content-start gap-1.5">
        {qlooOn ? plan.event_dna.slice(0, 8).map((e) => (
          <span key={e.id} title={`${e.id} · ${e.origin}`} className="rounded-full bg-teal-50 px-2 py-0.5 text-xs text-teal-800">
            {e.tag.replace("_", " ")} {e.affinity?.toFixed(2)}
          </span>
        )) : <span className="text-xs text-stone-400">Qloo off: event culture is not used, only crowd size and catalog.</span>}
      </div>

      <table className="mt-4 w-full text-sm">
        <thead className="text-left text-xs text-stone-500">
          <tr><th className="pb-2 font-medium">SKU</th><th className="pb-2 font-medium">Affinity</th>
            <th className="pb-2 text-right font-medium">Demand</th><th className="pb-2 pl-3 text-right font-medium">Stock</th>
            <th className="pb-2 pl-3 text-right font-medium">Stockout</th></tr>
        </thead>
        <tbody>
          {plan.skus.map((s, i) => {
            const diff = s.stock_qty - other.skus[i].stock_qty;
            return (
              <tr key={s.sku_id} className={`border-t border-stone-100 ${s.stock_qty === 0 ? "text-stone-400" : ""}`}>
                <td className="py-1.5">{s.name}
                  {s.excluded_reason && <div className="text-xs text-amber-700">{s.excluded_reason}</div>}</td>
                <td><Affinity s={s} /></td>
                <td className="whitespace-nowrap text-right tabular-nums">{Math.round(s.demand_p10)}–{Math.round(s.demand_p90)}</td>
                <td className="pl-3 text-right font-semibold tabular-nums whitespace-nowrap">{s.stock_qty}
                  {diff !== 0 && <span className={`ml-1 text-xs font-normal ${diff > 0 ? "text-teal-700" : "text-rose-600"}`}>
                    {diff > 0 ? "+" : ""}{diff}</span>}</td>
                <td className="pl-3 text-right tabular-nums">{pct(s.stockout_risk)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-stone-400">Coloured number = difference vs Qloo {qlooOn ? "off" : "on"}. * = some concept tags have no evidence.</p>

      <div className="mt-4 flex items-center justify-between rounded-lg bg-stone-50 px-3 py-2 text-sm">
        <span>Spend <b>{nt(plan.total_cost)}</b> of {nt(plan.budget)}</span>
        <button onClick={() => onAudit(plan.decision_id)} className="rounded-md border border-stone-300 px-2.5 py-1 text-xs hover:bg-white">
          Decision audit
        </button>
      </div>

      <div className="mt-4 rounded-lg border border-stone-200 p-3">
        <div className="text-xs font-medium uppercase tracking-wide text-stone-500">Qloo on vs off · same hidden demand</div>
        <div className="mt-2 grid grid-cols-3 gap-2 text-sm">
          {([["Profit", nt(a.qloo_on.expected_profit), nt(a.qloo_off.expected_profit)],
            ["Stockout rate", pct(a.qloo_on.avg_stockout_rate), pct(a.qloo_off.avg_stockout_rate)],
            ["Leftover units", a.qloo_on.expected_leftover_units.toFixed(0), a.qloo_off.expected_leftover_units.toFixed(0)],
          ] as const).map(([label, on, off]) => (
            <div key={label}><div className="text-xs text-stone-500">{label}</div>
              <div className="tabular-nums"><b>{on}</b> <span className="text-stone-400">vs {off}</span></div></div>
          ))}
        </div>
        <p className="mt-2 text-sm">
          Qloo on is <b className={gain >= 0 ? "text-teal-700" : "text-rose-600"}>{gain >= 0 ? "+" : "−"}{nt(Math.abs(gain))}</b> on
          average and ahead in {Math.round(a.qloo_on_win_rate * 100)}% of {a.n_environments} simulated environments
          (range {nt(a.profit_delta_range[0])} to {nt(a.profit_delta_range[1])}).
        </p>
      </div>
    </section>
  );
}
