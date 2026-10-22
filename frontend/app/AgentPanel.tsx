"use client";

import { useState } from "react";
import { api } from "./types";

type AgentResp = {
  plan: { skus: { sku_id: string; name: string; affinity: number | null; stock_qty: number }[]; total_cost: number; expected_profit: number };
  reasons: Record<string, string>;
  evidence_films: string[];
};

// Qloo-grounded agent: the LLM scores each SKU's fit using Qloo recommendations, and the planner uses that fit.
export default function AgentPanel({ eventId }: { eventId: string }) {
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<AgentResp | null>(null);
  const [err, setErr] = useState("");

  const run = () => {
    setBusy(true);
    setErr("");
    api<AgentResp>("/api/agent/stock", { event_id: eventId })
      .then(setRes)
      .catch((e) => setErr((e as Error).message))
      .finally(() => setBusy(false));
  };

  return (
    <div className="rounded-lg border border-stone-200 p-3">
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium uppercase tracking-wide text-stone-500">Qloo-grounded agent</div>
        <button onClick={run} disabled={busy} className="rounded-md bg-stone-900 px-3 py-1 text-xs text-white disabled:opacity-50">
          {busy ? "Running…" : "Run agent"}
        </button>
      </div>
      {err && <p className="mt-2 text-xs text-rose-700">Agent unavailable ({err}). Set LLM settings in .env.</p>}
      {res && (
        <>
          <p className="mt-2 text-xs text-stone-500">Evidence films: {res.evidence_films.join(", ") || "none"}</p>
          <ul className="mt-2 space-y-1 text-sm">
            {res.plan.skus.map((s) => (
              <li key={s.sku_id}>
                <b>{s.name}</b> · stock {s.stock_qty}
                {s.affinity != null && <span className="text-stone-500"> · fit {s.affinity.toFixed(2)}</span>}
                <div className="text-xs text-stone-500">{res.reasons[s.sku_id]}</div>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-stone-400">Agent plan profit NT${Math.round(res.plan.expected_profit).toLocaleString()} (simulated).</p>
        </>
      )}
    </div>
  );
}
