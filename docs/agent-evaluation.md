# Agent evaluation: with Qloo vs without Qloo

Status: measured on the live demo server (`demo.jxdtw.com/tasteshift`), 20 repetitions, one event.

## Setup

- Request: "I am running a souvenir booth at an 8,000-person anime music festival in Taipei. What should I stock?"
- Two arms, same tool-calling agent and same prompt shape:
  - With Qloo: `list_events`, `find_tags`, `recommend_films`, `rank_films`, `submit_plan`. The per-SKU fit must cite films returned by `recommend_films`.
  - Without Qloo: `list_events`, `submit_plan` only.
- Both arms produce per-SKU fit scores; the existing optimizer turns them into stock. Both plans are scored on the same 40 synthetic hidden-demand environments.

## Results (n = 20)

| Measure | Value |
|---|---|
| Profit difference, with − without Qloo (mean) | +319 NT$ |
| Standard deviation | 734 |
| 95% CI of the mean | (−3, +640) |
| Runs positive / negative / zero | 11 / 6 / 3 |
| Mean win rate across environments | 0.54 |
| Mean SKUs whose stock changed | 2.2 of 12 |
| Valid film citations | 117 (0 invalid) |
| SKUs with at least one valid Qloo citation | 94 of 240 (39%) |

Earlier smaller runs (n = 5, and a single run) showed the same pattern: differences in both directions.

## Interpretation

- The mean difference is positive, but its 95% interval touches zero. This is not a statistically clear benefit.
- About 40% of SKU decisions cite a Qloo film. Citations are always valid (they match films Qloo returned), but many SKUs are decided without Qloo evidence.
- Profit differences cluster at discrete values (for example ±1,136), because stock quantities move in lot sizes.
- LLM output is not repeatable even at temperature 0 with a fixed seed, so repeated runs vary.

## Limits

- Hidden demand is synthetic. The result measures agreement between agent fit and the assumed demand model, not real sales.
- One event, one request wording, one model.
- A valid citation does not prove the film changed the decision.

## Claim for the submission

Qloo grounding is used in the agent's reasoning and is verifiable (cited films are checked against Qloo output). The measured effect on simulated profit is positive on average but not statistically clear, so the submission should not claim a proven profit gain.
