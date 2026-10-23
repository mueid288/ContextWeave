# Planner v0 (CPU)

PRD §7.6 rule-based planner. **No model load.**

```bash
python -c "from contextweave.planner import plan, RequestView; print(plan(RequestView(has_validated_nonprefix_artifacts=True, chunk_order='BCA')).to_dict())"
```

## Rules (short)

1. Invalid / unknown artifacts → no non-prefix reuse.
2. Exact prefix → **C1**.
3. Else consider calibrated methods; discard on quality / latency policy.
4. **C3 (EPIC):** refused after H3 GPU confirm FAIL (order-only gate does not
   generalize). `chunk_order` may still be passed for experiments.
5. **C4 (CacheBlend):** refused (G1 quality).
6. Else → **C0** full prefill.

Module: `src/contextweave/planner/v0.py`.  
Evidence: `artifacts/phase1-oracle-2026-10-23/`, `artifacts/h3-confirm-2026-10-23/`.
