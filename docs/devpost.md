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

## TL;DR

- **Who:** event vendors who must stock before the crowd arrives
- **Problem:** they only know the event name, so stock is a guess
- **Solution:** an agent asks Qloo *who the crowd is* and *what else they like*, then picks products. Every decision cites Qloo data
- **Proof:** vs the same agent without Qloo, it wins **17 of 20** runs, **+NT$552** mean profit (95% CI +311 to +793), **92%** of decisions cite verified Qloo data, **0** invented citations (simulated demand)

## Try it in 1 minute

1. Open https://demo.jxdtw.com/tasteshift/ (no login)
2. Tab **Agent (Qloo vs none)** → **Run both arms** (about 1 minute)
3. Compare: the left column cites Qloo for each product; the right column guesses

## How the agent uses Qloo

| Step | Qloo API | What the agent learns |
|---|---|---|
| Resolve | `find_tags` | event concepts → taste tags |
| Recommend | `recommend`, `rank` | films this crowd loves, in Taipei |
| Profile | `audience_demographics` | age and gender skew |
| Cross-domain | `entity_tags` | food, brands, styles they also like |

Then the agent scores 12 products with cited reasons, and a deterministic optimizer sets quantities within budget. The LLM never sets numbers.

## Example: what Qloo changed

- **Qloo says:** the Taipei anime-festival audience over-indexes at 35–44 (+0.60), under-indexes at 24 and younger (−0.19), and likes Cafe and Fashion
- **Agent does:** kids' sticker books ↓, band tees and tote bags ↑, each with its Qloo citation

## Also in the app

Culture comparison of two events · 3 risk plans + what-if (rain, attendance, cost) · live restock · audit trail + purchase-order CSV

## Built with

Python / FastAPI · Next.js · Qloo harness · function-calling LLM · 36 tests · nginx

## Limits and next

- Demand is simulated → next: real point-of-sale data from vendors
- Code (MIT): https://github.com/seantw0301/tasteshift
