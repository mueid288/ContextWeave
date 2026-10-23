# Project state — Phase 1 G2 FAIL

**Phase 1 oracle:** **G2 FAIL** — `artifacts/phase1-oracle-2026-10-23/`  
**Go memo:** [`phase1-go-memo.md`](phase1-go-memo.md) (scoped {C0,C1,C3})  
**Decision now:** thin policy around **C0** (C1 when prefix); **no Phase 2**

## Finding

C3 (EPIC) is fast when correct but **mean contains 0.70** on the 20-request
reorder suite (systematic fails on ACB/BAC). Best fixed config is **C0**.
Oracle recovers quality by falling back to C0, so p95 TTFT upside vs C0 is **0**.

## Frozen

| Item | Status |
|---|---|
| CacheBlend / C4 | CLOSED / refused |
| EPIC / C3 as default | **Refused** in planner v0 (quality risk) |
| Phase 2 / G3 | Not opened |
| ResolventKV | Blocked |

## Optional next (owner pick)

1. Stay paused / archive
2. Desk: order-aware risk signal (H3) pre-reg — only if pursuing C3 selectively
3. Partner trace (optional)
