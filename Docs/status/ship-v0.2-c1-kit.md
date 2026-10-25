# Ship — ContextWeave v0.2 C1 evaluation kit

**Date:** 2026-10-25  
**Tag:** `v0.2.0-c1-kit` · package version `0.2.0`

## What shipped

Lab-facing **Canonical Order C1** evaluation kit (not SaaS, not cw-field):

| Piece | Path |
|---|---|
| Claims (can / cannot) | `Docs/product/CLAIMS.md` |
| Integrator guide | `Docs/product/integrators.md` |
| Library | `src/contextweave/product/` |
| Shim | `cw-serve-order` · `Docs/product/live-shim.md` |
| Evidence | TTFT / quality / field A/B / field G0 (see CLAIMS) |

## Audience

Inference and RAG platform engineers evaluating prefix-cache amplification via
document order policy.

## Non-goals this tag

- PyPI publish  
- Multi-tenant cloud  
- Field Layer 2 TTFT  
- Reopening PIC / C3 research  

## How to point labs

1. Tag `v0.2.0-c1-kit`  
2. README → CLAIMS → integrators  
3. Ask them to measure on **their** replay with prefix caching on  

## Default next

Outbound with the kit. Open Layer 2 or PyPI only on explicit ask.
