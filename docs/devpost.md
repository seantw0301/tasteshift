# Devpost submission text

Paste-ready fields for https://qloo.devpost.com/. Numbers match [agent-evaluation.md](agent-evaluation.md) and [SUBMISSION.md](SUBMISSION.md).

## Project name

TasteShift

## Elevator pitch (≤ 200 characters)

An agent that asks Qloo who the crowd is and what else they like, then tells event vendors what to stock — every product decision cites Qloo data.

## Links

- Live demo: https://demo.jxdtw.com/tasteshift/
- Code (MIT): https://github.com/seantw0301/tasteshift
- Video: https://youtu.be/S46jVXv6DEk

## Built with

python, fastapi, next.js, react, typescript, tailwindcss, qloo, llm, function-calling, nginx

## About the project

### Inspiration

Event vendors decide what to stock before the crowd arrives. Two events with the same 8,000 people and the same budget buy very different things, but a vendor only knows the event name. Today that decision is a guess, and the cost of guessing is unsold stock or empty shelves.

### What it does

TasteShift turns a plain-language request into a stock plan.

1. A vendor types: *"I am running a souvenir booth at an 8,000-person anime music festival in Taipei. What should I stock?"*
2. A tool-calling agent asks Qloo about the crowd:
   - `find_tags` resolves the event's concepts to Qloo tags
   - `recommend` and `rank` return the films this audience loves in Taipei
   - `audience_demographics` tells it who they are (age bands, gender skew)
   - `entity_tags` tells it what else they like: food, brands, styles
3. For each of the 12 products, the agent gives a fit score and a one-line reason that cites Qloo films and signals. The server checks every citation against what Qloo returned and drops anything invented.
4. A deterministic optimizer turns fit into quantities within budget. The LLM never sets quantities or prices.

The same request also runs **without** Qloo tools, and both plans are scored on the same 40 simulated demand environments, so the vendor sees what Qloo changed.

The app also covers the rest of the job: culture comparison between events, three risk plans with what-if scenarios (rain, attendance, cost), mid-event restock, calibration, multi-day restock, a decision audit trail and a purchase-order CSV.

### Why it needs Qloo

Without Qloo the agent reasons from the event name. With Qloo it learns things it cannot guess. For the Taipei anime music festival, Qloo shows the audience over-indexes at ages 35–44 (+0.60) and under-indexes at 24 and younger (−0.19), and also likes Cafe, Fashion and Afternoon Tea Set. The agent then lowers kids' sticker books ("audience under-indexes for ages 24 and younger") and raises band-style tees and tote bags (citing Fashion, Urban Chic, Cafe).

Results over 20 runs on the live server, same model and prompt:

| | Value |
|---|---|
| Runs where the Qloo agent beat the no-Qloo agent | 17 of 20 |
| Mean profit difference | +NT$552 (95% CI +311 to +793) |
| Product decisions backed by a verified Qloo citation | 92% (221 of 240) |
| Invented citations | 0 |

Demand is simulated, so this measures better-grounded decisions, not real sales.

### How we built it

- Backend: Python, FastAPI. Qloo is called through the Qloo harness workflows (`find_tags`, `recommend`, `rank`, `audience_demographics`, `entity_tags`), with caching per process.
- Agent: an OpenAI-compatible function-calling loop with seven tools and server-side citation checks.
- Optimizer and simulator: deterministic code with lot sizes, MOQ, budget and license constraints; Monte Carlo demand environments for fair with/without comparisons.
- Frontend: Next.js static export, Tailwind.
- Deployed on a Linux server behind nginx; 36 unit tests.

### Challenges we ran into

- Qloo affinity is only comparable within one call, so we make one `recommend` call per event over all its tags.
- Our first agent cited Qloo films for only 39% of products and its gain was not statistically clear. Adding audience demographics and cross-domain taste tags raised citation coverage to 92% and made the gain clear.
- An earlier attempt to derive affinity directly from `rank` scores made results worse; we measured it, documented it and dropped it.

### Accomplishments that we're proud of

- Every product decision is traceable to Qloo data, and the server rejects invented citations.
- An honest, reproducible with/without evaluation (`scripts/agent_eval.py`).

### What we learned

Cross-domain taste (what a film audience also likes in food and fashion) is what connects cultural data to physical products. Films alone were not enough.

### What's next

- Replace simulated demand with real point-of-sale data from vendors.
- More event types and cities, and Qloo signals for food and drink vendors.

## Testing instructions

No login needed. Open https://demo.jxdtw.com/tasteshift/ and choose the **Agent (Qloo vs none)** tab, then click **Run both arms** (about one minute). The other three tabs work instantly.
