# Project pause (H3 slice-cal GPU confirm FAIL)

**Effective:** 2026-10-23  
**State:** **PAUSED**  
**G2:** FAIL · **H3 order confirm:** FAIL · **H3 slice-cal LOO:** PASS (local) ·
**H3 slice-cal GPU (seed99→100):** **FAIL**

## Policy (shipped)

**C1** if exact prefix, else **C0**. C3/C4 refused by default.

C3 only if a table was probed on the **exact** serve distribution (same golds
**and** same filler/session). Cross-filler reuse is **not** trusted
(`artifacts/h3-slice-cal-gpu-2026-10-23/`).

## Frozen

Phase 2, ResolventKV, G2 re-attack, order-only rules, cross-filler slice tables,
further EPIC quality-rule fishing without a new signal class + pre-reg.

## Resume

1. Stay paused / archive — **default**  
2. New pre-reg only for a **different** risk class (e.g. runtime key deviation)  
3. Partner trace — optional  
