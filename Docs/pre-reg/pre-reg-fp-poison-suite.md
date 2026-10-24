# Pre-registration: Build-context poisoning suite (CPU)

**Status:** **PASS — implementation conformance (self-authored)** (2026-10-24) — `artifacts/fp-poison-2026-10-24/`  
**Not security evidence. Not G2/H3/H4. No new GPU.**

## Result

| Metric | Value |
|---|---|
| n_cases | 8 |
| refuse_rate | **1.0** |
| `pass_heuristic` | **true** |

Attacker-prefix artifacts with identical chunk tokens are refused by
`fingerprints_compatible` and by planner when `request_build_context_hash` ≠
provenance hash.

## Decision

Ship `RequestView.request_build_context_hash` mismatch refuse. **PAUSED.**
