# TasteShift P0 — architecture

Source spec: `TasteShift_Competitive_Advantages_Differentiation_v2` (project library). This file records what P0 actually implements.

## 12-layer summary

| L | Layer | P0 answer |
|---|---|---|
| 1 | Business | Event vendors decide what to sell and how much. KPI: profit, stockout, leftover vs a no-culture baseline. MVP: Qloo hackathon demo (due 2026-10-30 23:45 EDT). |
| 2 | Product | One page: two events side by side, Qloo On/Off, decision audit. Out of scope: what-if replans, three risk plans, BOM, POS import (P1/P2). |
| 3 | AI strategy | Qloo supplies cultural affinity only. Demand, cost and optimization are deterministic code. No LLM in P0. |
| 4 | Workflow | fixtures → event DNA → SKU affinity → demand scenarios → optimizer → plan → trace; ablation re-scores On and Off plans. |
| 5 | Data flow | Every input carries an origin tag (`qloo_live`, `merchant_input`, `synthetic`, `model_estimate`, …). Missing = `unknown`, never 0. No personal data. |
| 6 | State | Stateless requests. Decision id = hash of inputs + seed + model version, so a plan is reproducible. |
| 7 | Memory | In-process trace store and Qloo response cache only. No persistence yet. |
| 8 | Tools | Qloo Evidence Gateway (mock today). |
| 9 | Agents | N/A in P0 — the spec's four agents arrive with the LLM layer; numbers never come from an LLM. |
| 10 | Services | `backend` (FastAPI) and `frontend` (Next.js). |
| 11 | Events | N/A — synchronous request/response. |
| 12 | Infra | Local dev only. Public deployment not chosen yet. |

## API

- `GET /api/fixtures`
- `POST /api/events/analyze`
- `POST /api/optimize/stock` — `{event_id, attendance?, budget?, qloo_on, seed}`
- `POST /api/evaluation/ablation`
- `GET /api/decisions/{id}/audit`

Not built yet from the spec: catalog import, `/api/qloo/affinity`, `/api/forecast/demand` (folded into optimize), `/api/scenarios/replan`.

## Model

- **Affinity**: mean event-DNA affinity over a SKU's proxy concept tags. Tags with no evidence are skipped; all missing → `unknown`.
- **Demand**: `attendance × booth_reach × conversion × units_per_buyer`, split across SKUs. Qloo On tilts the split by `exp(beta × (affinity − mean))`; unknown affinity is neutral. Affinity is never read as a purchase rate.
- **Scenarios**: 4,000 seeded draws, lognormal SKU noise × shared crowd shock.
- **Optimizer**: greedy marginal expected profit per dollar. Per SKU `qty = 0` or `MOQ ≤ qty ≤ max_stock` in lot steps; total cost ≤ budget; unlicensed SKUs excluded.
- **Ablation**: On and Off plans scored on the same 40 hidden demand environments whose tilt differs from the planner's and which add taste noise the planner cannot see. Reports mean delta, win rate and range, including losses.

## Limits

- Mock mode: affinities are hand-written synthetic values with `mock:` ids. They are not Qloo data.
- The hidden environment assumes affinity moves demand, so the ablation shows the mechanism, not real-world lift.
- Live Qloo client is not implemented; setting `QLOO_API_KEY` currently falls back to mock with a visible note.
- Catalog, prices, reach and conversion are assumptions, not measurements.
