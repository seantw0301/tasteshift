"use client";

import { useCallback, useEffect, useState } from "react";
import AuditPanel from "./AuditPanel";
import EventColumn from "./EventColumn";
import { api, type Ablation, type EventInfo, type EventResult, type Plan } from "./types";

export default function Home() {
  const [events, setEvents] = useState<EventInfo[]>([]);
  const [merchant, setMerchant] = useState("");
  const [attendance, setAttendance] = useState(8000);
  const [budget, setBudget] = useState(20000);
  const [qlooOn, setQlooOn] = useState(true);
  const [results, setResults] = useState<Record<string, EventResult>>({});
  const [mode, setMode] = useState("");
  const [error, setError] = useState("");
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [trace, setTrace] = useState<any>(null);

  const run = useCallback(async (evs: EventInfo[], att: number, bud: number) => {
    try {
      const out: Record<string, EventResult> = {};
      await Promise.all(evs.map(async (e) => {
        const body = { event_id: e.id, attendance: att, budget: bud };
        const [on, off, ablation] = await Promise.all([
          api<Plan>("/api/optimize/stock", { ...body, qloo_on: true }),
          api<Plan>("/api/optimize/stock", { ...body, qloo_on: false }),
          api<Ablation>("/api/evaluation/ablation", body),
        ]);
        out[e.id] = { on, off, ablation };
      }));
      setResults(out);
      setError("");
    } catch (e) {
      setError(`Backend not reachable (${(e as Error).message}). Start it with scripts/dev.sh.`);
    }
  }, []);

  useEffect(() => {
    api<{ events: EventInfo[]; merchant: { name: string; skus: unknown[] }; qloo_mode: string }>("/api/fixtures")
      .then((f) => {
        setEvents(f.events);
        setMerchant(`${f.merchant.name} · ${f.merchant.skus.length} SKUs`);
        setMode(f.qloo_mode);
        run(f.events, 8000, 20000);
      })
      .catch((e) => setError(`Backend not reachable (${e.message}). Start it with scripts/dev.sh.`));
  }, [run]);

  return (
    <main className="mx-auto max-w-7xl px-6 py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">TasteShift</h1>
          <p className="text-stone-600">Same merchant, same crowd size, same budget. Different culture, different purchase order.</p>
          <p className="mt-1 text-sm text-stone-500">{merchant}</p>
        </div>
        <div className="flex flex-wrap items-end gap-3 text-sm">
          <label>Attendance
            <input type="number" value={attendance} onChange={(e) => setAttendance(+e.target.value)}
              className="mt-1 block w-28 rounded-md border border-stone-300 bg-white px-2 py-1" /></label>
          <label>Budget (NT$)
            <input type="number" value={budget} onChange={(e) => setBudget(+e.target.value)}
              className="mt-1 block w-28 rounded-md border border-stone-300 bg-white px-2 py-1" /></label>
          <button onClick={() => run(events, attendance, budget)} className="rounded-md bg-stone-900 px-4 py-1.5 text-white">Analyze</button>
          <button onClick={() => setQlooOn(!qlooOn)} aria-pressed={qlooOn}
            className={`rounded-md px-4 py-1.5 font-medium ${qlooOn ? "bg-teal-600 text-white" : "bg-stone-200 text-stone-700"}`}>
            Qloo {qlooOn ? "On" : "Off"}</button>
        </div>
      </header>

      {mode === "mock" && (
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
          Mock mode: cultural signals are a synthetic stand-in, not live Qloo responses. All demand and profit figures are simulated.
        </p>
      )}
      {error && <p className="mt-4 rounded-md bg-rose-50 px-3 py-2 text-sm text-rose-800">{error}</p>}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {events.filter((e) => results[e.id]).map((e) => (
          <EventColumn key={e.id} event={e} r={results[e.id]} qlooOn={qlooOn}
            onAudit={(id) => api(`/api/decisions/${id}/audit`).then(setTrace)} />
        ))}
      </div>
      {trace && <AuditPanel trace={trace} onClose={() => setTrace(null)} />}
    </main>
  );
}
