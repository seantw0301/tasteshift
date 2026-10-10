/* eslint-disable @typescript-eslint/no-explicit-any */
export default function AuditPanel({ trace, onClose }: { trace: any; onClose: () => void }) {
  const stocked = trace.skus.filter((s: any) => s.stock_qty > 0 || s.excluded_reason);
  return (
    <div className="fixed inset-0 z-10 flex justify-end bg-black/30" onClick={onClose}>
      <aside className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 text-sm" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Decision audit</h3>
          <button onClick={onClose} className="text-stone-500">Close</button>
        </div>
        <p className="mt-1 font-mono text-xs text-stone-500">
          {trace.decision_id} · model {trace.model_version} · seed {trace.scenario_seed} · {trace.n_scenarios} scenarios
        </p>
        <p className="mt-2 rounded bg-amber-50 p-2 text-xs text-amber-900">
          Qloo {trace.qloo.on ? "on" : "off"} · mode <b>{trace.qloo.mode}</b>. {trace.qloo.fallback_note ?? ""} {trace.limits}
        </p>

        <h4 className="mt-5 font-semibold">Inputs and where they came from</h4>
        <table className="mt-1 w-full">
          <tbody>{trace.inputs.map((i: any) => (
            <tr key={i.field} className="border-t border-stone-100">
              <td className="py-1">{i.field}</td><td className="tabular-nums">{String(i.value)}</td>
              <td className="text-right"><span className="rounded bg-stone-100 px-1.5 py-0.5 font-mono text-xs">{i.origin}</span></td>
            </tr>))}</tbody>
        </table>

        <h4 className="mt-5 font-semibold">Demand assumptions (model_estimate)</h4>
        <ul className="mt-1 grid grid-cols-2 gap-x-4 font-mono text-xs">
          {Object.entries(trace.assumptions).map(([k, v]: any) => <li key={k}>{k} = {v.value}</li>)}
        </ul>

        <h4 className="mt-5 font-semibold">Constraints</h4>
        <p className="mt-1 text-stone-600">{trace.constraints.rule}</p>
        <p>Spend {trace.constraints.total_cost} ≤ budget {trace.constraints.budget}</p>

        <h4 className="mt-5 font-semibold">Per-SKU trace</h4>
        {stocked.map((s: any) => (
          <div key={s.sku_id} className="mt-2 rounded border border-stone-200 p-2">
            <div className="flex justify-between"><b>{s.name}</b><span>stock {s.stock_qty} (MOQ {s.moq}, max {s.max_stock})</span></div>
            <div className="text-xs text-stone-600">
              Proxy concepts: {s.mapping.join(", ")} · affinity {s.affinity == null ? "unknown" : s.affinity.toFixed(2)} ({s.affinity_status})
              · demand p10/p50/p90 {s.demand_p10}/{s.demand_p50}/{s.demand_p90}
            </div>
            {s.excluded_reason && <div className="text-xs text-amber-700">Excluded: {s.excluded_reason}</div>}
            <div className="font-mono text-xs text-stone-400">{s.evidence_ids.join("  ") || "no evidence used"}</div>
          </div>
        ))}
      </aside>
    </div>
  );
}
