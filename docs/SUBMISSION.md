# TasteShift: Submission

## Problem

Event souvenir vendors decide what to stock before a crowd arrives. Two events with the same crowd size and the same budget can have very different buying patterns, so a single standard stock plan misses demand. TasteShift picks products and quantities for each event and shows why.

Scope: one souvenir merchant, 12 SKUs, two 8,000-person Taipei events.

## Qloo use

| Workflow | Used for | Status |
|---|---|---|
| `find_tags` | Resolve each event concept (e.g. `anime`, `family`) to a Qloo tag URN | Live |
| `recommend` | One call per event, all seed-concept tags plus the event location, returns movies with affinity | Live, shown as evidence |
| `rank` | Not used. It ranks named entities, not concepts | Not used |

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

Run the stack (see Setup), then open http://localhost:3000/.

- **Culture comparison**: Qloo On and Off per event, with decision audit and purchase-order CSV.
- **Plans & what-if**: three risk plans and scenarios (rain, attendance, cost).
- **Live ops (simulated)**: mid-event restock, calibration, multi-day restock.

Screenshots: to be captured before submission, with no credentials visible.

## Setup (clean environment)

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
- **Qloo recommend is evidence only.** It is not connected to pricing or stock.
- **Simulated demand and prices.** Catalog, prices, reach and conversion are assumptions. Demand is simulated, not measured.
- **Tag coverage.** SKU concepts such as `tea` and `spicy` now have confirmed URNs, but the decision engine does not use them for Qloo signals yet.
- **Movie target.** `recommend` targets movies because artist results were mostly CJK names. The output is English only after filtering.
- **Single event snapshot.** Recommend results are cached per event for the life of the backend process.
