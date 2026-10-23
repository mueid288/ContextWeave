# Project pause (H3 confirm FAIL)

**Effective:** 2026-10-23  
**State:** **PAUSED**  
**G2:** FAIL · **H3 replay:** suite-only · **H3 GPU confirm:** **FAIL**

## Policy (shipped)

**C1** if exact prefix, else **C0**. C3 and C4 refused.

## Why

Order∈{ACB,BAC} predicted Phase1 fails but **does not transfer** to fresh golds
(`artifacts/h3-confirm-2026-10-23/`). Do not trust order-only H3 for routing.

## Frozen

Phase 2, ResolventKV, G2 re-attack, further EPIC order-rule fishing without a
new signal class (and new pre-reg).

## Resume

1. Stay paused / archive — **default**  
2. New pre-reg only if a **different** risk feature is proposed (not ACB/BAC redo)  
3. Partner trace — optional  
