# Control plane — north star (not yet shippable)

**Status:** Approved product direction (2026-10-26). **Not** a claim. **Not** on PyPI.

**Thesis:** [../plans/2026-10-26-revolutionary-product-thesis.md](../plans/2026-10-26-revolutionary-product-thesis.md)

## One sentence

ContextWeave becomes a **fail-closed reuse control plane**: fingerprints + quality
margin + cost model choose among full prefill, canonical order + prefix, or
bounded blend — and **refuse** when validity or quality is unknown.

## Relationship to C1

| Layer | Role |
|---|---|
| C1 kit (`reorder_documents`) | Strategy **C1** inside the planner (shipped, scoped claims) |
| Control plane | Product we are falsifying via Gate **R1** → R2 |

Do not market C1 as the revolutionary product. Do not claim control-plane wins
until R1/R2 gates pass and CLAIMS is updated.

## Current gate

- **R0** — thesis + docs (this file)  
- **R1** — oracle upside harness — [../plans/2026-10-26-r1-oracle-harness.md](../plans/2026-10-26-r1-oracle-harness.md)  
- **R2+** — only if R1 passes  

## Workload

Primary: **enterprise multi-doc RAG** (cw-field dogfood). Multi-agent deferred.
