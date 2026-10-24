# Build-context poison suite — 2026-10-24

**Pre-reg:** `Docs/pre-reg/pre-reg-fp-poison-suite.md`  
**Verdict:** **PASS**

8 injected cases: same chunk tokens, attacker vs victim build prefix.

| Check | Result |
|---|---|
| `fingerprints_compatible` refuse | **8/8** (`build_context_hash_mismatch`) |
| Planner C0 when request hash ≠ provenance | **8/8** |
| `refuse_rate` | **1.0** |

Planner now takes `RequestView.request_build_context_hash`.
