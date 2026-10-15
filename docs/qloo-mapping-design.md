# Qloo → decision mapping: design options

Status: **proposal, not implemented.** Owner decision needed before any engine change.

## What the engine consumes today

- `engine.sku_affinity(sku, dna)`: mean affinity over a SKU's proxy `concept_tags`. Tags without evidence are skipped; no evidence = `unknown`.
- `engine.shares(...)`: demand tilt `base_weight × exp(beta × (affinity − mean))`. Unknown affinity gets a neutral tilt of 1.0.
- `dna` is a list of `QlooEvidence(tag, affinity ∈ [0,1])`.

So any mapping only needs to produce **one comparable affinity per concept in [0, 1] per event**. The engine does not change.

## What the live probes showed (2026-10-15)

| Probe | Result | Consequence |
|---|---|---|
| `recommend`, one tag per call | Affinity is normalized within each call (top ≈ 1.0). Tag effects are small or absent for many concepts. | Per-concept calls are not comparable. |
| `recommend`, all tags in one call | Comparable within the call, but returns movies/artists, not concepts. | Needs a second step to reach concepts. |
| `entity_tags` on the recommended movies (limit 20) | Returns generic tags (e.g. "Fashion", "Family-Oriented"). **None of the 32 confirmed concept URNs appear.** Affinity is 1 for all tags. | The entity-tag route cannot map to our concept taxonomy. |
| `rank` | Ranks named options (≤10) under entity/location/demographic signals. Signals are entities, not tags; tags only filter. | Usable for comparison within one call, but needs entities as signals. |

Conclusion: the Qloo hackathon surface gives **entity-level** outputs. Our taxonomy is **concept-level**. A bridge is needed, and it is an assumption either way.

## Options

### A. Entity-tag bridge (rejected by probe)
Recommend list → entity_tags → share of entities carrying each concept, weighted by affinity.
- Blocked: no confirmed concept URN appears in the returned tags.

### B. Curated anchors, scored in one call per event (recommended)
- Fixed assumption table: each concept maps to 1 anchor entity (a movie or artist, UUID verified), listed in a reviewable file (`backend/app/fixtures/qloo_anchors.json`).
- One `rank` call per event with ≤10 anchors as `options`, the event's seed entities and `signal_location` as signals. All options scored in one call, so the scores are comparable.
- `concept affinity = rank score of its anchor`. Concepts without an anchor stay unknown.
- Output feeds the existing `QlooEvidence` list with `origin = "qloo_live"`. Engine unchanged.
- Limits: 10 options per call caps the concept count at 10 per call; anchor choice drives the result; signals must be entities, so the event needs seed entities (new assumption table).

### C. Event-level multiplier (simplest, coarsest)
- One `recommend` call per event; take the mean affinity of the top 10 as an event "fandom intensity" in [0,1].
- Fixed assumption table maps each concept to a sensitivity coefficient; SKU demand is scaled by `intensity × sensitivity`.
- Honest but does not distinguish concepts from Qloo data; it is the same signal for every SKU in a family.

## Recommendation

Use **B** if a per-concept comparison is needed for the demo; use **C** if time is short and the demo only needs to show Qloo moving demand at event level. Both keep the engine interface. Either way the mapping tables are **assumptions** and must be shown on screen and in SUBMISSION.md, next to the synthetic demand model.

## Assumptions to label on screen

1. Concept → anchor entity (B) or concept → sensitivity (C).
2. Affinity → demand elasticity (`beta` in `engine.shares`). This is synthetic; the ablation already shows the mechanism, not real lift.
3. Event seed entities (B only).

## Decisions needed

1. B or C?
2. Who approves the anchor or sensitivity table (owner review, as with tag URNs)?
3. Keep the "Qloo On vs Off" headline, now driven by the mapped signal? It must say the effect comes from the assumed elasticity.
