# TasteShift P0 — architecture

Source spec: `TasteShift_Competitive_Advantages_Differentiation_v2` (project library). This file records what P0 actually implements.

## 12-layer summary

| L | Layer | P0 answer |
|---|---|---|
| 1 | Business | Event vendors decide what to sell and how much. KPI: profit, stockout, leftover vs a no-culture baseline. MVP: Qloo hackathon demo (due 2026-10-30 23:45 EDT). |
| 2 | Product | Three tabs: culture comparison (Qloo On/Off, audit), plans & what-if (three risk plans, scenarios, BOM, capacity), live ops (simulated restock, calibration, multi-day). |
| 3 | AI strategy | Qloo supplies cultural evidence. An LLM agent turns a free-text request plus Qloo results into per-SKU fit scores. Demand, cost and optimization are deterministic code. |
| 4 | Workflow | fixtures → event DNA → SKU affinity → demand scenarios → optimizer → plan → trace; ablation re-scores On and Off plans. |
| 5 | Data flow | Every input carries an origin tag (`qloo_live`, `merchant_input`, `synthetic`, `model_estimate`, …). Missing = `unknown`, never 0. No personal data. |
| 6 | State | Stateless requests. Decision id = hash of inputs + seed + model version, so a plan is reproducible. |
| 7 | Memory | In-process trace store and Qloo response cache only. No persistence yet. |
| 8 | Tools | Qloo Evidence Gateway (mock today). |
| 9 | Agents | One tool-calling agent (`agent_loop.py`): `list_events`, `find_tags`, `recommend_films`, `rank_films`, `submit_plan`. It outputs fit scores with cited Qloo films; quantities still come from the optimizer. See [agent-evaluation.md](agent-evaluation.md). |
| 10 | Services | `backend` (FastAPI) and `frontend` (Next.js). |
| 11 | Events | N/A — synchronous request/response. |
| 12 | Infra | Local dev, plus a public sub-path deployment ([deploy.md](deploy.md)). |

## API

- `GET /api/fixtures`
- `POST /api/events/analyze`
- `POST /api/optimize/stock` — `{event_id, attendance?, budget?, qloo_on, seed}`
- `POST /api/evaluation/ablation`
- `GET /api/decisions/{id}/audit`

- `POST /api/optimize/plans` — conservative / balanced / aggressive
- `POST /api/scenarios/replan` — same constraints, returns before/after and why
- `GET /api/decisions/{id}/purchase-order.csv`
- `POST /api/sales/simulate`, `POST /api/sales/restock`, `POST /api/calibration`
- `POST /api/restock/multiday`

Not built from the spec: catalog import, `/api/qloo/affinity`, `/api/forecast/demand` (folded into optimize).

## Model

- **Affinity**: mean event-DNA affinity over a SKU's proxy concept tags. Tags with no evidence are skipped; all missing → `unknown`.
- **Demand**: `attendance × booth_reach × conversion × units_per_buyer`, split across SKUs. Qloo On tilts the split by `exp(beta × (affinity − mean))`; unknown affinity is neutral. Affinity is never read as a purchase rate.
- **Scenarios**: 4,000 seeded draws, lognormal SKU noise × shared crowd shock.
- **Optimizer**: greedy marginal expected profit per dollar. Per SKU `qty = 0` or `MOQ ≤ qty ≤ max_stock` in lot steps; total cost ≤ budget; unlicensed SKUs excluded.
- **Ablation**: On and Off plans scored on the same 40 hidden demand environments whose tilt differs from the planner's and which add taste noise the planner cannot see. Reports mean delta, win rate and range, including losses.

## P1

- **Risk plans**: conservative penalises downside (mean minus worst-10% profit, weight 0.5); aggressive penalises lost sales (0.6 x margin). Balanced is plain expected profit. When the budget already binds, balanced and aggressive coincide.
- **What-if**: rain (crowd x0.7 plus per-SKU `rain_factor`), attendance, unit cost, price, rival stalls, supplier MOQ. Price changes do not feed back into demand.
- **Capacity** (juice prep line, sausage grill): demand is capped hour by hour against units/hour; peak-hour overflow is lost.
- **BOM**: ingredient need = stock x qty per unit x (1 + waste rate); countable items round up.

## P2 (all simulated)

- **Restock from sales**: forecast blended with run rate (prior worth 25% of the event); a sell-out is a lower bound, never a reason to cut. Restock budget defaults to unspent budget plus revenue so far.
- **Calibration**: weight = sqrt(actual / forecast), clipped to 0.5–2, fed to the next plan as `weight_overrides`. Partial-event sales are projected at the current run rate.
- **Multi-day**: daily order-up-to levels from the newsvendor critical fractile, shelf-life ageing (oldest sold first), last-day clearance at salvage value. Budget applies to the firm day-1 order only; no lead time.
- **Supplier hand-off**: purchase-order CSV. No POS or supplier system is connected.

## Limits

- Mock mode: affinities are hand-written synthetic values with `mock:` ids. They are not Qloo data.
- The hidden environment assumes affinity moves demand, so the ablation shows the mechanism, not real-world lift.
- Live Qloo: `find_tags` (tag resolution) and `recommend` (one call per event over all seed-concept tags plus location) are wired. Recommend output is shown as evidence only. Stock decisions still use the synthetic culture profile. `rank` is not used: it ranks named entities, not concepts.
- Catalog, prices, reach and conversion are assumptions, not measurements.

## Live Qloo setup

Supported surface is `qloo exec` from `@qloo/qloo-harness` (Node ≥ 22.19, harness ≥ 0.1.26). The key stays in the harness's private config, never in this repo or the browser.

```bash
npm install --global @qloo/qloo-harness
qloo setup --qloo        # enter the event key yourself
qloo setup --status      # expect "Qloo data: ready"
scripts/qloo_resolve_tags.sh
```

The backend defaults `QLOO_BASE_URL` to `https://hackathon.api.qloo.com`. The resolver saves tag candidates for review; a candidate is not a confirmed match. Only URNs listed under `confirmed` in `backend/app/fixtures/qloo_tag_candidates.json` are used.

Submission needs (kit `docs/SUBMISSION.md`): problem statement, workflows used and why, redacted request-to-result walkthrough with tag choices, demo/screenshots without credentials, clean-environment setup steps, known limitations.
