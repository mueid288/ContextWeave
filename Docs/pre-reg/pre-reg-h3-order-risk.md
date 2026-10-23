# Pre-registration: H3 order-risk signal (parked)

**Status:** PARKED — do not run until owner explicitly starts.  
**Date written:** 2026-10-23  
**Not a G2 redo.** G2 FAIL stands. Phase 2 not opened.

## One question

Using only **CPU-visible features** of a multi-doc request (chunk order permutation
id, question type, optional cheap embedding/hash features — **no** model forward
for the signal itself), can a rule or tiny classifier trained on
`artifacts/phase1-oracle-2026-10-23/oracle_trials.jsonl` predict C3 quality failure
with **precision ≥0.9** on held-out fails (ACB/BAC pattern) such that a policy
“C3 if predicted safe else C0” keeps **contains ≥0.95** while cutting **mean**
TTFT by ≥20% vs always-C0 on a replay of that suite?

## Fixed

| Item | Value |
|---|---|
| Data | Banked oracle JSONL only for v0; optional one GPU confirm later |
| Positive class | C3 `quality < 1` rows |
| Metric | Precision on fails; mean TTFT of policy vs C0; **not** G2 p95 bar |
| Out of scope | Recomp sweeps, CacheBlend, ResolventKV, claiming G2 PASS |

## Pass / fail

| Outcome | Next |
|---|---|
| PASS on replay | Optional thin planner rule; still no Phase 2 auto |
| FAIL | Keep C3 refused; archive H3 |
| Need more labels | One capped GPU collect pre-reg — separate memo |

## Procedure (when approved)

Desk-first: train/eval on banked trials; document features. GPU only if replay
is insufficient and owner opens a new session.
