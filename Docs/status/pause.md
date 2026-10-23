# Project state after H3 PASS (replay)

**G2:** FAIL (stands) — `artifacts/phase1-oracle-2026-10-23/`  
**H3 order-risk:** **PASS** (replay) — `artifacts/h3-order-risk-2026-10-23/`  
**Closeout:** [`closeout-g2.md`](closeout-g2.md) (G2 not reopened)

## Policy

| Situation | Choice |
|---|---|
| Exact prefix | **C1** |
| Non-prefix + `chunk_order` safe (not ACB/BAC) | **C3** (EPIC fork) |
| Non-prefix + unsafe/unknown order | **C0** |
| CacheBlend | Refused |

## Frozen

| Item | Status |
|---|---|
| Phase 2 / G3 | Not opened |
| ResolventKV | Blocked |
| G2 re-attack | Do not |
| GPU | Idle unless new pre-reg |

## Resume

1. Stay desk-idle / archive — default  
2. Optional GPU confirm of H3 on new seeds — needs new pre-reg  
3. Partner trace — optional  
