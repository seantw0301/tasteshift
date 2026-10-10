# TasteShift

Know your crowd. Choose your products. Stock with confidence.

Given an event, a vendor, a catalog and constraints, it picks products and quantities, and shows why.

- **Culture comparison**: one souvenir merchant, 12 SKUs, two 8,000-person events; Qloo On vs Off; decision audit
- **Plans & what-if**: three risk plans, rain/attendance/cost scenarios, juice recipes, sausage grill capacity
- **Live ops (simulated)**: restock from sales, calibration, multi-day new-year restock

```bash
scripts/install.sh
scripts/dev.sh      # backend :8000, web :3000
scripts/smoke.sh    # tests + API check
```

Runs in **mock mode** today: cultural signals are synthetic, not live Qloo data. See [docs/](docs/).

- [docs/architecture.md](docs/architecture.md) — 12-layer summary, model, assumptions, limits
- [docs/deploy.md](docs/deploy.md) — sub-path deployment

License: [MIT](LICENSE)
