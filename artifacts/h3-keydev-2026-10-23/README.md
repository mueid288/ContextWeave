# H3 runtime keydev — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-h3-keydev.md`  
**Verdict:** **FAIL**

Isolated Layer-0 seam discontinuity; fit T on seed 99 → test seed 100 (Lisbon golds).

| Metric | Value |
|---|---|
| Train fit | **untrainable** (no T with prec ≥0.9) |
| Test precision (refuse-all fallback) | **0.33** |
| Policy mean_q | 1.0 (always C0) |
| Mean TTFT red vs C0 | **0** |
| `pass_heuristic` | **false** |

## Why

Only ~3 distinct keydev values (~0.132–0.133), **tied to chunk order**, not quality.
Fails and oks share the same scores; signal does not separate C3 contains.

**Conclusion:** isolated-seam discontinuity is not a usable H3 gate on this EPIC pin.
