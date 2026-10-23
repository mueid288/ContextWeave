# Phase 1 oracle — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-phase1-oracle.md`  
**Session:** `cw-phase1-oracle` (Colab A100)  
**Verdict:** **G2 FAIL**

## Headline

| Metric | Value |
|---|---|
| N requests | 20 @ ~12k tokens |
| Feasible configs | C0, C3 (C1 infeasible on EPIC Path A) |
| C0 mean quality | **1.0** |
| C3 mean quality | **0.70** (6/20 fails) |
| Best fixed | **C0** |
| Oracle mean quality | 1.0 (falls back to C0 on C3 fails) |
| Oracle vs fixed p95 TTFT | **0%** reduction (same p95 — failures force C0) |
| Quality upside vs C0 | **0** points |
| `g2_pass` | **false** |

## C3 failure pattern

Always on orders **ACB** (city) and **BAC** (year) — model denies the fact exists.
Other orders (ABC/BCA/CAB/CBA) C3 quality OK and ~2–4× faster.

## Files

- `oracle_trials.jsonl`
- `oracle_report.json`
- `pip_freeze.txt`

## Decision

Per go memo: **no Phase 2**. Thin policy = prefer **C0** (or C1 when prefix) until an
order-aware risk signal can refuse unsafe C3. Planner C3 calibration updated to refuse.
