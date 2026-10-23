# Pre-registration: H3 runtime seam key-deviation (EPIC)

**Status:** **FAIL** (2026-10-23) — `artifacts/h3-keydev-2026-10-23/`  
**Depends on:** Static H3 transfers FAIL  
**Not a G2 redo.** Phase 2 / ResolventKV still closed.

## Result

Isolated Layer-0 seam discontinuity; fit on seed 99 → test seed 100.

| Field | Value |
|---|---|
| Train fit | untrainable (no T with prec ≥0.9) |
| Test precision | **0.33** (refuse-all) |
| Policy mean_q / TTFT red | 1.0 / **0** |
| `pass_heuristic` | **false** |

Scores collapse to ~3 order-tied values (~0.132–0.133); no quality separation.
(Joint seam re-forward CUDA-IMA’d on Path A — not used.)

## Decision

Archive isolated-seam keydev for policy. Keep C3 refused by default.
Do not reopen static H3 fishing. **PAUSED.**
