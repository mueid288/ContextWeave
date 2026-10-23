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

After H3: **C1** if prefix; else **C3** when non-prefix artifacts and
`chunk_order` is H3-safe (not ACB/BAC; unknown → refuse); else **C0**. **C4** still
refused. G2 FAIL unchanged — H3 optimizes **mean** TTFT, not p95 oracle upside.

Module: `src/contextweave/planner/v0.py`. Tests: `tests/unit/test_planner_v0.py`.
Thesis: `Docs/status/g1-closeout-thesis.md`.
