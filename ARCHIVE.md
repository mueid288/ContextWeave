# Phase 0/1 research archive

**Tag:** `v0.1.0-phase01-archive`  
**Branch:** `archive/phase0-1-research`  
**Do not reopen** PIC / EPIC / CacheBlend / H3 / H4 / fingerprint / oracle work without a new thesis.

This snapshot preserves the full research harness that lived on `main` before the C1-kit minimization.

## What lives here

| Area | Contents |
|------|----------|
| Scripts | `scripts/g1/` (CacheBlend, EPIC, matched), `scripts/phase1/` (oracle, H3, H4, FP), `scripts/smoke/` |
| Packages | `planner/`, `oracle/`, `risk/`, `provenance/`, `fingerprints/`, `compatibility/`, `costmodel/`, `runtime_adapters/` |
| Docs | `Docs/Reviews/`, `Docs/Research/`, `Docs/gates/`, `Docs/plans/`, research `pre-reg/`, `Docs/core/`, `Docs/results/` |
| Artifacts | `g1-*`, `h3-*`, `h4-*`, `fp-*`, `phase1-oracle-*` banks |
| Entry points | `cw-plan-demo`, `cw-fingerprint-example`, `cw-cost-model` |

## Product kit (active)

The Canonical Order **C1** evaluation kit + field dogfood live on **`main`** (see root README and `Docs/product/CLAIMS.md`).

```bash
git checkout main          # C1 kit + field G0
git checkout v0.1.0-phase01-archive   # this research snapshot
```
