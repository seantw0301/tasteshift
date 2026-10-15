
## Live results after coverage attempt (PR #3)

- Candidate films: 103, all from Taipei recommend calls; keyword rule (whole-word, Qloo description) assigns anchors.
- Coverage: anime event 2 concepts, family event 3, lunar event 0. Known SKUs: 5 of 12 per event.
- Ablation (Qloo On − Off, profit): anime **−625** (win 0.30); family **−811** (win 0.23); lunar 0.
- Known false positives from the rule: `eco` → "Kim Ji-young: Born 1982"; `music_live` → "Cold War".
- Structural limit: `rank` only scores entities inside the location's affinity set. Brand and artist probes kept only a few entities (Starbucks, Taylor Swift); food and merchandise concepts (tea, sweet, matcha, spicy) have no film anchors at all.

Conclusion: option B does not improve the demo's Qloo On result on this catalogue. Do not merge it as a demo driver.
