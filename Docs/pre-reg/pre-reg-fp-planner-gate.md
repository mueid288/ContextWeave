# Pre-registration: Fingerprint / provenance gate in planner v0

**Status:** **PASS** (2026-10-24) — desk unit tests  
**Depends on:** FR-13 trust module + planner v0  
**Not G2 / H3 / H4. No new GPU.**

## Result

Planner refuses C3/C4 unless `assert_reuse_allowed` passes **and** a quality
clear exists. Missing / quarantined / untrusted provenance → `artifact_invalid`
even when keydev would clear.

Evidence: `tests/unit/test_planner_provenance_gate.py` (all cases green).

## Decision

Validity-checked non-prefix path is wired. Default without signals remains
**C1 else C0**. **PAUSED** pending a new thesis (not H3/H4 redo).
