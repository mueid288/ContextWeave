# Planner v0 (CPU)

PRD §7.6 rule-based planner. **No model load.**

```bash
python -c "
from contextweave.planner import plan, RequestView
print(plan(RequestView(
    has_validated_nonprefix_artifacts=True,
    keydev_score=0.05, keydev_threshold=0.5,
)).to_dict())
"
```

## Rules (short)

1. Invalid / unknown artifacts → no non-prefix reuse.
2. Exact prefix → **C1**.
3. **C3 (EPIC):**  
   - If `keydev_threshold` set: allow iff score &lt; T (runtime Stage-1).  
   - Else if `slice_calibration` marks `(order, fact)` safe on **exact** serve distro.  
   - Else refuse.
4. **C4 (CacheBlend):** refused (G1 quality).
5. Else → **C0** full prefill.

Module: `src/contextweave/planner/v0.py`.  
Pre-reg: `Docs/pre-reg/pre-reg-h3-keydev.md`.
