# Pre-registration: H4 MFU-prior check (supersedes misspecified H4)

**Status:** **Consistent with MFU prior — not a validation** (2026-10-24) —
`artifacts/h4-mfu-2026-10-24/`  
**Supersedes:** `Docs/pre-reg/pre-reg-h4-cost-model.md` (**MISSPECIFIED** — used 450 TFLOP/s > A100 bf16 peak)  
**Not a G2 redo. No new GPU. Do not label PASS.**

## Result

Implied effective TFLOP/s from banked C0 ≈ **177–182** on all four suites; MFU ≈
**57–58%** of peak 312 → inside band **[124.8, 202.8]**. Caveats: MFU range was
fixed after measured ~58% was known (post hoc); band is wide; check is C0
prefill FLOP/TTFT only (not load costs or C3 break-even).

## One question

Does the **measured** effective prefill throughput implied by banked EPIC A100
C0 TTFT @~12k (Mistral-7B FLOP model) fall inside a **pre-registered** MFU prior
of **40–65%** of A100 dense bf16 peak (**312** TFLOP/s)?

Peak band: effective TFLOP/s ∈ `[312×0.40, 312×0.65]` = `[124.8, 202.8]`.

## Pass heuristic

For each banked suite (oracle, confirm99, keydev99, keydev100): implied
`effective_tflops = prefill_flops(N) / (mean_C0_s × 1e12)` lies in `[124.8, 202.8]`.
All suites must pass.

## Fail ⇒

Report as out-of-prior; do not treat §7.5 tables as calibrated without a new prior.
