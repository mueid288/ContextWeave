# Planner v0 (CPU)

PRD §7.6 rule-based planner. **No model load.**

```bash
python -c "from contextweave.planner import plan, RequestView; print(plan(RequestView(has_validated_nonprefix_artifacts=True)).to_dict())"
```

## Rules (short)

1. Invalid / unknown artifacts → no non-prefix reuse.
2. Exact prefix → **C1**.
3. Else consider calibrated methods: **C3** EPIC (EPIC@12k PASS) and **C4** CacheBlend (G1-DIAG #2).
4. Discard if quality drop &gt; 2 points or predicted TTFT not ≤ 0.85× prefill.
5. Else pick lowest predicted TTFT; if none remain → **C0** full prefill.

With shipped calibrations, non-prefix + valid artifacts → **C3** (C4 refused on quality).
C3 assumes an **EPIC fork** runtime — not the CacheBlend pin set.

Module: `src/contextweave/planner/v0.py`. Tests: `tests/unit/test_planner_v0.py`.
Thesis: `Docs/status/g1-closeout-thesis.md`.
