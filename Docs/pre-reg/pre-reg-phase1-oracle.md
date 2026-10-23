# Pre-registration: Phase 1 oracle upside (scoped {C0, C1, C3})

**Status:** READY — CPU harness first; GPU only when owner opens session.  
**Date written:** 2026-10-23  
**Go memo:** [`Docs/status/phase1-go-memo.md`](../status/phase1-go-memo.md)  
**Not** CacheBlend reopen. **Not** Phase 2.

## One question

On Colab A100 with the **EPIC fast-path** stack and `Mistral-7B-Instruct-v0.2`,
for a fixed set of **N≥20** multi-doc reorder requests (~12k tokens), does
**per-request oracle** choice among **C0** (full prefill), **C1** (exact prefix when
the prompt is prefix-aligned), and **C3** (LegoLink-8) beat the **best single fixed**
config by the ratified G2 bar (≥15% lower p95 TTFT at equal quality, or ≥+3 quality
points at equal p95 TTFT)?

## Fixed

| Item | Value |
|---|---|
| Session | `cw-phase1-oracle` |
| Time cap | **120 min** wall |
| Install | Path A EPIC only |
| Model | `mistralai/Mistral-7B-Instruct-v0.2` |
| N requests | ≥20 (synthetic multi-doc; document seeds) |
| Context | `--target-context-tokens 12000` where applicable |
| Configs | C0 full; C3 kvlink-8; C1 only on prefix-aligned variants of the same docs |
| Quality | gold-contains (suite facts) per request |
| Latency | p50/p95 TTFT per config per request; n≥3 timed after warmup |
| Analysis | `python scripts/phase1/run_oracle_study.py --input …` (CPU) |

## Pass / fail (G2)

| Outcome | Next |
|---|---|
| G2 PASS | Log; optional Phase 2 go memo (separate) |
| G2 FAIL | Pivot to thin policy around best fixed (likely C3 or C1); no Phase 2 |
| Cannot run C1 fairly on EPIC fork | Report C0 vs C3 only; mark C1 as calibration-import; do not fake prefix |

## Collect

- Per-request JSONL (`request_id`, `config`, `quality`, `ttft_ms`, `feasible`, `runtime_id`)
- Aggregate oracle report JSON
- `pip freeze`; bank `artifacts/phase1-oracle-YYYY-MM-DD/` before `colab stop`
