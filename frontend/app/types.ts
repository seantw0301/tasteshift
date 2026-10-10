export type Evidence = { id: string; tag_id: string; tag: string; affinity: number | null; origin: string; query_id: string; note: string | null };

export type SkuPlan = {
  sku_id: string; name: string; affinity: number | null; affinity_status: string; evidence_ids: string[];
  demand_p10: number; demand_p50: number; demand_p90: number; stock_qty: number; cost: number;
  expected_profit: number; stockout_risk: number | null; leftover_units: number; excluded_reason: string | null;
};

export type Plan = {
  decision_id: string; event_id: string; qloo_on: boolean; qloo_mode: string; attendance: number; budget: number;
  total_cost: number; expected_profit: number; skus: SkuPlan[]; event_dna: Evidence[];
};

export type Score = {
  expected_profit: number; avg_stockout_rate: number; expected_leftover_units: number; lost_sales_units: number;
  total_cost: number; decision_id: string;
};

export type Ablation = {
  qloo_on: Score; qloo_off: Score; delta: Record<string, number>; changed_skus: string[];
  n_environments: number; qloo_on_win_rate: number; profit_delta_range: [number, number]; caveat: string;
};

export type EventInfo = { id: string; name: string; theme: string; attendance: number };
export type EventResult = { on: Plan; off: Plan; ablation: Ablation };

const API = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(API + path, body
    ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
    : undefined);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}
