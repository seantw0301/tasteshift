# TasteShift: Submission

- **Live demo**: https://demo.jxdtw.com/tasteshift/ (no login)
- **Code**: https://github.com/seantw0301/tasteshift (MIT)

## Problem

Event souvenir vendors decide what to stock before a crowd arrives. Two events with the same crowd size and the same budget can have very different buying patterns, so a single standard stock plan misses demand. TasteShift picks products and quantities for each event and shows why.

Scope: one souvenir merchant, 12 SKUs, two 8,000-person Taipei events.

## Qloo use

| Workflow | Used for | Status |
|---|---|---|
| `find_tags` | Resolve each event concept (e.g. `anime`, `family`) to a Qloo tag URN | Live |
| `recommend` | One call per event, all seed-concept tags plus the event location, returns movies with affinity | Live, shown as evidence |
| `rank` | Agent tool `rank_films`: re-ranks the recommended films for the event location | Live, agent only |
| `audience_demographics` | Agent tool `audience_profile`: age bands and gender skew of the audiences of the top films | Live, agent only |
| `entity_tags` | Agent tool `taste_tags`: cross-domain tastes (food, brands, styles) of those audiences | Live, agent only |

## Why the agent needs Qloo

A vendor's question is "who is coming, and what else do they like?". An LLM alone answers from stereotypes. Qloo answers from observed taste data for this audience in this city.

What Qloo returned for the three Taipei events (top 3 recommended films per event, live calls on 2026-10-22; positive = over-indexed):

| Event | Age skew from `audience_demographics` | Cross-domain tastes from `entity_tags` |
|---|---|---|
| Anime music festival | 35–44 +0.60; 24 and younger −0.19 | Cafe, Afternoon Tea Set, Fashion |
| Family weekend fair | 25–29 +0.20, 55 and older +0.22; 35–44 −0.37 | Cafe, Picanha Steak, Family Business |
| Lunar new year market | 24 and younger +0.22; female +0.30 | Salad, Health & Beauty, Group Outings, Tourist attraction |

- **It replaces guesses with data.** Without Qloo the agent has no audience data and reasons from the event name. With Qloo it sees that the Taipei audience for these films under-indexes at 24 and younger and over-indexes at 35–44, and cites that in its reasons (for example: kids' sticker books fit poorly because "the audience under-indexes for ages 24 and younger").
- **It is cross-domain.** Souvenir SKUs (tea, tote bags, tees) are not films. `entity_tags` links the film audience to food, brand and style tastes, which the agent maps to SKUs.
- **It is checkable.** Every cited film and signal must appear in what Qloo returned; the server drops anything else and counts it as invalid.
- **Without it, the tools disappear.** The no-Qloo arm has only `list_events` and `submit_plan`. Same model, same prompt shape, no audience data.

## Agent

The "Agent (Qloo vs none)" tab runs a tool-calling LLM agent on a free-text request (about 1 minute per comparison).

1. `list_events` picks the event that matches the request.
2. `find_tags` resolves the audience concepts to Qloo tag URNs.
3. `recommend_films` and `rank_films` fetch the films this audience likes in the event city.
4. `audience_profile` and `taste_tags` describe who that audience is (age, gender) and what else it likes (food, brands, styles).
5. `submit_plan` returns a fit score (0–1) and a one-sentence reason for each of the 12 SKUs, with the Qloo films and signals that support it. Citations are checked server-side.
6. The deterministic optimizer turns the fit scores into quantities. The LLM never sets quantities or prices.

The same request also runs without Qloo tools, and both plans are scored on the same 40 simulated demand environments. Results over 20 runs: with Qloo wins 17 of 20 runs, mean +552 NT$, 95% CI (+311, +793); 92% of SKU decisions cite verified Qloo data, 0 invalid citations. Demand is simulated, so this is not a measured sales gain; see [agent-evaluation.md](agent-evaluation.md).

Why `recommend` is one call per event: affinity values are only comparable within one call. Per-concept calls produce scores that cannot be compared.

## Confirmed tag choices

Each concept maps to one owner-confirmed URN. The full list with alternatives is in [qloo-tag-review.md](qloo-tag-review.md). Examples used in the walkthrough:

| Concept | URN |
|---|---|
| anime | `urn:tag:genre:qloo:anime` |
| j-pop | `urn:tag:genre:music:j_pop` |
| cosplay | `urn:tag:interests:qloo:cosplay` |

## Request-to-result walkthrough

1. Event: `evt_anime_music` (Anime Music Festival, Taipei, 8,000 attendees).
2. Backend reads the seed concepts `anime`, `j-pop`, `cosplay` and their confirmed URNs.
3. `POST /api/qloo/recommend` sends one `recommend` call: `target_type: movie`, the three URNs as `signal_tags`, `signal_location: Taipei`, `limit: 20`.
4. Entities whose names use CJK, Hangul or fullwidth characters are dropped. The top 10 remain.
5. Result (sample, first five): Cherry Magic! Thirty Years of Virginity Can Make You a Wizard?!: The Movie (0.93), Your Name Engraved Herein (0.92), Kingdom (0.92), Till We Meet Again (0.92), Café Funiculi Funicula (0.92).
6. The frontend shows this list as Qloo evidence. It does not change prices or stock.
7. Stock for the same event is computed from the synthetic culture profile (`mock:` ids). That profile is labelled as synthetic on screen.

## Demo

Open the live demo, or run the stack locally (see Setup) and open http://localhost:3000/.

- **Culture comparison**: Qloo On and Off per event, with decision audit and purchase-order CSV.
- **Plans & what-if**: three risk plans and scenarios (rain, attendance, cost).
- **Live ops (simulated)**: mid-event restock, calibration, multi-day restock.

Screenshots (captured from the running demo, no credentials visible):

- [01_culture_comparison.png](screenshots/01_culture_comparison.png): Qloo evidence panel, synthetic culture profile, Qloo On vs Off.
- [02_plans_what_if.png](screenshots/02_plans_what_if.png): three risk plans and scenarios.
- [03_live_ops.png](screenshots/03_live_ops.png): mid-event restock and multi-day restock.
- [04_agent_compare.png](screenshots/04_agent_compare.png): agent with Qloo vs without Qloo, tool calls and cited films.

## Built during the hackathon

The project started on 2026-10-10, inside the submission period. All code, the Qloo integration and the agent were written during the period (see the git history).

## Setup (clean environment)

Verified on the live deployment on 2026-10-22: fixtures, recommend, agent run and agent compare all return 200.

Requirements: Python 3, Node 22.19 or later, npm.

1. Clone the repository and install dependencies:

   ```bash
   scripts/install.sh
   ```

2. Install the Qloo harness:

   ```bash
   npm install --global @qloo/qloo-harness
   ```

3. Create `.env` in the repo root (not committed) with the event key and the hackathon endpoint:

   ```bash
   cp .env.example .env
   ```

   Set `QLOO_API_KEY`, `QLOO_BASE_URL=https://hackathon.api.qloo.com` and `QLOO_TRUSTED_BASE_URL=https://hackathon.api.qloo.com`.
   For the Agent tab, also set `LLM_BASE_URL`, `LLM_MODEL` and `LLM_API_KEY` (any OpenAI-compatible endpoint with function calling). Without them the Agent tab shows "Agent unavailable"; the other tabs still work.

4. Check Qloo connectivity:

   ```bash
   qloo doctor --network
   ```

5. Start the stack:

   ```bash
   scripts/dev.sh
   ```

6. Run the tests and the API check (with the stack running):

   ```bash
   scripts/smoke.sh
   ```

## Known limitations

- **Culture profile is synthetic.** The stock decisions use hand-written affinity values (`mock:` ids). The "Qloo On vs Off" profit difference therefore reflects the synthetic profile, not Qloo data.
- **Qloo recommend is evidence only in the Culture comparison tab.** There it is not connected to pricing or stock. In the Agent tab, Qloo results shape the per-SKU fit and therefore stock.
- **Agent effect measured on simulated demand only.** The profit gain (n = 20, one event, one model) is against synthetic hidden demand, not real sales.
- **Simulated demand and prices.** Catalog, prices, reach and conversion are assumptions. Demand is simulated, not measured.
- **Tag coverage.** SKU concepts such as `tea` and `spicy` now have confirmed URNs, but the decision engine does not use them for Qloo signals yet.
- **Movie target.** `recommend` targets movies because artist results were mostly CJK names. The output is English only after filtering.
- **Single event snapshot.** Recommend results are cached per event for the life of the backend process.
