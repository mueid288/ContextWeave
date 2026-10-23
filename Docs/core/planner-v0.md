# Planner v0 (CPU)

PRD §7.6 rule-based planner. **No model load.**

```bash
python -c "
from contextweave.planner import plan, RequestView
from contextweave.risk import SliceCalibration
cal = SliceCalibration.from_c3_observations([('BCA','year',1.0)])
print(plan(RequestView(
    has_validated_nonprefix_artifacts=True,
    chunk_order='BCA', fact_type='year', slice_calibration=cal,
)).to_dict())
"
```

## Rules (short)

1. Invalid / unknown artifacts → no non-prefix reuse.
2. Exact prefix → **C1**.
3. **C3 (EPIC):** only if `slice_calibration.is_safe(order, fact)` **and** the
   table was probed on this exact serve distribution (same golds **and** filler).
   Cross-filler tables FAIL GPU confirm. No table ⇒ refuse.
4. **C4 (CacheBlend):** refused (G1 quality).
5. Else → **C0** full prefill.

Module: `src/contextweave/planner/v0.py`.  
Evidence: `artifacts/h3-slice-cal-2026-10-23/`, `artifacts/h3-slice-cal-gpu-2026-10-23/`.
