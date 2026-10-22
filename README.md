# TasteShift

Know your crowd. Choose your products. Stock with confidence.

Given an event, a vendor, a catalog and constraints, it picks products and quantities, and shows why.

- **Culture comparison**: one souvenir merchant, 12 SKUs, two 8,000-person events; Qloo On vs Off; decision audit
- **Plans & what-if**: three risk plans, rain/attendance/cost scenarios, juice recipes, sausage grill capacity
- **Live ops (simulated)**: restock from sales, calibration, multi-day new-year restock
- **Agent (Qloo vs none)**: tool-calling LLM agent that cites Qloo films, audience demographics and taste tags per SKU, compared with the same agent without Qloo

Live demo: https://demo.jxdtw.com/tasteshift/

```bash
scripts/install.sh
scripts/dev.sh      # backend :8000, web :3000
scripts/smoke.sh    # tests + API check
```

Qloo calls (`find_tags`, `recommend`, `rank`) are live. The culture profile behind the Culture comparison tab is synthetic. See [docs/](docs/).

- [docs/SUBMISSION.md](docs/SUBMISSION.md) — hackathon submission, setup, limits
- [docs/agent-evaluation.md](docs/agent-evaluation.md) — with vs without Qloo, 20 runs
- [docs/architecture.md](docs/architecture.md) — 12-layer summary, model, assumptions, limits
- [docs/deploy.md](docs/deploy.md) — sub-path deployment

License: [MIT](LICENSE)
