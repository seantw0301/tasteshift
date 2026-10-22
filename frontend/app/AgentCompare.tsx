"use client";

import { useState } from "react";
import { api } from "./types";

type Arm = { trace: { tool?: string; note?: string; result?: string }[]; reasons: Record<string, string>; evidence_films: string[] };
type Compare = {
  event_id: string;
  with_qloo: Arm;
  without_qloo: Arm;
  evaluation: {
    delta_profit: number; grounded_win_rate: number; changed_skus: string[]; n_environments: number;
    grounded: { expected_profit: number }; ungrounded: { expected_profit: number };
  };
};

const DEFAULT = "I am running a souvenir booth at an 8,000-person anime music festival in Taipei. What should I stock?";

function ArmView({ title, arm }: { title: string; arm: Arm }) {
  const tools = arm.trace.filter((t) => t.tool).map((t) => t.tool);
  return (
    <div className="rounded-lg border border-stone-200 p-3">
      <div className="text-xs font-medium uppercase tracking-wide text-stone-500">{title}</div>
      <p className="mt-2 text-xs text-stone-500">Tool calls: {tools.join(" → ") || "none"}</p>
      <p className="mt-1 text-xs text-stone-500">Qloo films used: {arm.evidence_films.join(", ") || "none"}</p>
      <ul className="mt-2 space-y-1 text-xs">
        {Object.entries(arm.reasons).map(([sku, r]) => (
          <li key={sku}><b>{sku}</b>: {r}</li>
        ))}
      </ul>
    </div>
  );
}

export default function AgentCompare() {
  const [text, setText] = useState(DEFAULT);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<Compare | null>(null);
  const [err, setErr] = useState("");

  const run = () => {
    setBusy(true);
    setErr("");
    api<Compare>("/api/agent/compare", { request: text })
      .then(setRes)
      .catch((e) => setErr((e as Error).message))
      .finally(() => setBusy(false));
  };

  return (
    <section className="mt-6 rounded-xl border border-stone-200 bg-white p-5">
      <h2 className="text-lg font-semibold">Agent: with Qloo vs without Qloo</h2>
      <p className="mt-1 text-sm text-stone-500">Same request, same tools except Qloo. Both plans are scored on the same simulated environments.</p>
      <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2}
        className="mt-3 w-full rounded-md border border-stone-300 px-3 py-2 text-sm" />
      <button onClick={run} disabled={busy} className="mt-2 rounded-md bg-stone-900 px-4 py-1.5 text-sm text-white disabled:opacity-50">
        {busy ? "Agent running… (about 1 minute)" : "Run both arms"}
      </button>
      {err && <p className="mt-3 text-sm text-rose-700">Agent unavailable ({err}).</p>}
      {res && (
        <div className="mt-4 space-y-3">
          <p className="text-sm">Event chosen: <b>{res.event_id}</b></p>
          <div className="grid gap-3 md:grid-cols-2">
            <ArmView title="With Qloo" arm={res.with_qloo} />
            <ArmView title="Without Qloo" arm={res.without_qloo} />
          </div>
          <div className="rounded-lg bg-stone-50 px-3 py-2 text-sm">
            Profit with Qloo − without: <b className={res.evaluation.delta_profit >= 0 ? "text-teal-700" : "text-rose-600"}>
              NT${Math.round(res.evaluation.delta_profit).toLocaleString()}</b>.
            With Qloo wins in {Math.round(res.evaluation.grounded_win_rate * 100)}% of {res.evaluation.n_environments} simulated environments.
            Stock changed for {res.evaluation.changed_skus.length} SKUs. Environments are synthetic.
          </div>
        </div>
      )}
    </section>
  );
}
