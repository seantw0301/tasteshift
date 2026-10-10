# TasteShift

Know your crowd. Choose your products. Stock with confidence.

P0 demo: one souvenir merchant, 12 SKUs, two 8,000-person events with different cultures.
It picks products and quantities under budget/MOQ/licence limits, compares Qloo On vs Off, and exposes a decision audit.

```bash
scripts/install.sh
scripts/dev.sh      # backend :8000, web :3000
scripts/smoke.sh    # tests + API check
```

Runs in **mock mode** today: cultural signals are synthetic, not live Qloo data. See [docs/](docs/).

- [docs/architecture.md](docs/architecture.md) — 12-layer summary, model, assumptions, limits

License: [MIT](LICENSE)
