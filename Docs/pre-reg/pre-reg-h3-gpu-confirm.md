# Pre-registration: H3 GPU confirm (fresh prompts)

**Status:** **FAIL** (2026-10-23) — `artifacts/h3-confirm-2026-10-23/`  
**Depends on:** H3 replay PASS (suite-specific; superseded for policy)  
**Not a G2 redo.** Phase 2 not opened.

## Result

| Field | Value |
|---|---|
| Golds | Lisbon / 2021 / BETA-4242 |
| C3 mean_q | **0.50** |
| Rule precision (ACB/BAC) | **0.50** |
| Policy mean_q | **0.67** |
| `pass_heuristic` | **false** |

Fails moved: **code** on CAB/CBA; BAC year still bad; **ACB city OK** (was fail on Phase1).

## Decision

Archive order-only H3 for **policy**. Keep module for research notes. Planner:
**C1 if prefix else C0** (C3/C4 refused).
