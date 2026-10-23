# Pre-registration: H3 slice-cal GPU confirm (same golds)

**Status:** **FAIL** (2026-10-23) — `artifacts/h3-slice-cal-gpu-2026-10-23/`  
**Depends on:** H3 slice-cal LOO **PASS** (same-filler only; this run bounds it)  
**Not a G2 redo.** Phase 2 / ResolventKV still closed.

## Result

Calibrate seed **99** → serve seed **100**, golds Lisbon/2021/BETA-4242.

| Metric | Value |
|---|---|
| Precision | **0.33** |
| Policy mean_q | **0.83** |
| Mean TTFT red vs C0 | 28% |
| `pass_heuristic` | **false** |

Cells flipped: ABC/city 1→0; CAB/code & CBA/code 0→1.

## Decision

Slice-cal is **same-filler / same-session LOO only**. Do not reuse a table across
filler text even with identical golds. Default planner: no table ⇒ refuse C3.
