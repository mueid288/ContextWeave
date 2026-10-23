# Pre-registration: H3 order-risk signal

**Status:** **PASS** (2026-10-23) — in-sample replay banked  
`artifacts/h3-order-risk-2026-10-23/`.  
**Not a G2 redo.** G2 FAIL stands. Phase 2 not opened.

## One question

Using only **CPU-visible** chunk-order features on the banked Phase 1 oracle
JSONL, can a rule predict C3 failures with precision ≥0.9 such that
“C3 if safe else C0” keeps contains ≥0.95 and cuts **mean** TTFT ≥20% vs C0?

## Result

| Field | Value |
|---|---|
| Rule | refuse C3 if order ∈ {ACB, BAC} (unknown → refuse) |
| Precision / recall | **1.0 / 1.0** |
| Policy mean_q | **1.0** |
| Mean TTFT reduction vs C0 | **40%** |
| `pass_heuristic` | **true** |

## Caveat

Fit and evaluated on the same 20-request suite (pattern is deterministic there).
Production needs the real doc permutation exposed to the planner.

## Next (done — superseded for policy)

GPU confirm on fresh golds: **FAIL** —
`Docs/pre-reg/pre-reg-h3-gpu-confirm.md`, `artifacts/h3-confirm-2026-10-23/`.
Order-only H3 is **not** production policy. Planner: C1 else C0. **PAUSED.**
