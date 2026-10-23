# Phase 1 go memo

**Date:** 2026-10-23  
**Decision:** **GO Phase 1** (scoped) — owner move after EPIC multi-fact quality PASS.  
**Supersedes:** “Phase 1 not opened” hold in [`phase0-exit-decision.md`](phase0-exit-decision.md)
for the scoped plan below only.

## Why go now

| Gate | Evidence |
|---|---|
| G0 | PASS — recurring non-prefix demand (~76% working-set) |
| G1 CacheBlend | CLOSED — engaged, failed quality/latency bar |
| G1 EPIC | PASS @12k latency + multi-fact quality (contains 1.0; ≥1.98× all cases) |

PRD Phase 1 tests **H2** (oracle selection upside) before building a heavier planner.
We now have one Tier-1 PIC method (EPIC/C3) that clears the bar on the measured
slice, plus prefix (C1) and full prefill (C0). That is enough to open a **scoped**
oracle study — not a full C0–C6 sweep and not ResolventKV.

## Scope (binding)

| In | Out |
|---|---|
| Config set **{C0, C1, C3}** | C4 CacheBlend (refused), C2/C5/C6 until separately calibrated |
| Oracle upside vs best **fixed** config in that set | Claiming EPIC fork = production runtime |
| CPU harness + one GPU pre-reg | ResolventKV kernels |
| Ratify G2 thresholds below | Auto-open Phase 2 / G3 |

**Runtime honesty:** C3 measurements require the **EPIC vLLM fork** Path A stack.
C0/C1 on that stack are same-fork fair for PIC vs full; native-prefix C1 on vLLM 0.18
remains a separate pin (already measured ~2.57× @6k) and may be imported as a
calibration row, not mixed blindly into one JSON without a `runtime_id`.

## G2–G4 thresholds (ratified this memo)

Timestamp: **2026-10-23**. Same proposed numbers as PRD §3 unless noted.

| Gate | Ratified bar |
|---|---|
| **G2** | Oracle vs best fixed in {C0,C1,C3}: ≥**+3** quality points at equal p95 TTFT, **or** ≥**15%** lower p95 TTFT at equal quality (before selector overhead) |
| **G3** | Deferred — not opened by this memo |
| **G4** | Deferred |

## First deliverables (ordered)

1. CPU oracle upside module + CLI — **done**.
2. Pre-reg + GPU collect — **done** (`artifacts/phase1-oracle-2026-10-23/`).
3. **G2 result: FAIL** — thin policy C0; Phase 2 **not** opened.

## Explicit non-goals

- Reopening CacheBlend G1 or pin-shim fishing.
- ResolventKV / custom kernels.
- Partner trace (still optional).
