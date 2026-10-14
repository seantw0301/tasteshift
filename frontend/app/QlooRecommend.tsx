"use client";

import { useEffect, useState } from "react";
import { api, type RecEnvelope } from "./types";

// Affinity is relative within this one call (top result ~1.0); do not compare across events.
export default function QlooRecommend({ eventId }: { eventId: string }) {
  const [env, setEnv] = useState<RecEnvelope | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    setEnv(null);
    api<RecEnvelope>("/api/qloo/recommend", { event_id: eventId })
      .then(setEnv)
      .catch((e) => setErr((e as Error).message));
  }, [eventId]);

  if (err) return <p className="text-xs text-rose-700">Qloo recommend failed ({err}).</p>;
  if (!env) return <p className="text-xs text-stone-400">Loading Qloo recommendations…</p>;
  if (env.status !== "ok") return <p className="text-xs text-amber-700">{env.summary ?? env.status}</p>;

  return (
    <div>
      <div className="text-xs font-medium uppercase tracking-wide text-stone-500">Qloo evidence · live recommendations (not used in stock math)</div>
      <ul className="mt-2 space-y-1">
        {env.results.map((r) => (
          <li key={r.entity_id} className="flex items-center gap-2 text-sm">
            <span className="w-40 truncate" title={r.name}>{r.name}</span>
            <div className="h-1.5 flex-1 rounded bg-stone-200">
              <div className="h-1.5 rounded bg-teal-600" style={{ width: `${(r.affinity ?? 0) * 100}%` }} />
            </div>
            <span className="w-10 text-right text-xs tabular-nums">{r.affinity?.toFixed(2) ?? "–"}</span>
          </li>
        ))}
      </ul>
      <p className="mt-1 text-xs text-stone-400">Evidence only. Scores are relative within this list and do not change prices or stock.</p>
    </div>
  );
}
