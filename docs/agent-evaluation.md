# Agent evaluation: with Qloo vs without Qloo

Status: measured on the live demo server (`demo.jxdtw.com/tasteshift`), 20 repetitions per version, one event, model `claude-sonnet-5-5`. Reproduce with `scripts/agent_eval.py <api_base> 20`.

## Setup

- Request: "I am running a souvenir booth at an 8,000-person anime music festival in Taipei. What should I stock?"
- Two arms, same tool-calling agent and same prompt shape:
  - With Qloo (v2, current): `list_events`, `find_tags`, `recommend_films`, `rank_films`, `audience_profile` (`audience_demographics`), `taste_tags` (`entity_tags`), `submit_plan`. Each SKU cites Qloo films and signals; the server checks every citation.
  - With Qloo (v1, earlier): the same without `audience_profile` and `taste_tags`.
  - Without Qloo: `list_events`, `submit_plan` only.
- Both arms produce per-SKU fit scores; the existing optimizer turns them into stock. Both plans are scored on the same 40 synthetic hidden-demand environments.

## Results (n = 20 each)

| Measure | v2: + audience and taste tools | v1: films only |
|---|---|---|
| Profit difference, with − without Qloo (mean) | **+552 NT$** | +319 NT$ |
| Standard deviation | 549 | 734 |
| 95% CI of the mean | **(+311, +793)** | (−3, +640) |
| Runs positive / negative / zero | 17 / 2 / 1 | 11 / 6 / 3 |
| Mean win rate across environments | 0.70 | 0.54 |
| Mean SKUs whose stock changed | 3.1 of 12 | 2.2 of 12 |
| Valid / invalid film citations | 325 / 0 | 117 / 0 |
| Valid / invalid audience and taste citations | 393 / 0 | n/a |
| SKUs with at least one valid Qloo citation | **221 of 240 (92%)** | 94 of 240 (39%) |

## Interpretation

- Adding Qloo audience demographics and cross-domain taste tags made the with-Qloo arm better on every measure. The 95% interval of the profit difference no longer includes zero.
- Almost every SKU decision now rests on a checked Qloo citation (92%, up from 39%). No citation was invented.
- Profit differences cluster at discrete values (for example +1,011), because stock quantities move in lot sizes.
- LLM output is not repeatable even at temperature 0, so repeated runs vary.

## Limits

- Hidden demand is synthetic. The result measures agreement between agent fit and the assumed demand model, not real sales.
- One event, one request wording, one model.
- A valid citation does not prove the cited signal changed the decision.

## Claim for the submission

With Qloo audience and taste data, the agent's plans beat the same agent without Qloo in 17 of 20 runs on simulated demand (mean +552 NT$, 95% CI +311 to +793), and 92% of SKU decisions cite verified Qloo data. The demand is simulated, so this is evidence of better-grounded decisions, not a measured sales gain.
