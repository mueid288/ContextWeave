# Research archive pointer

Phase 0/1 research (G1 CacheBlend/EPIC, G2 oracle, H3/H4, fingerprints, PIC
planner, Reviews, gates) was **removed from `main`** to keep the repo focused
on the Canonical Order **C1** kit + field dogfood — until a new product thesis
reopened the planner path.

## Where to find it

| Ref | What |
|---|---|
| Branch `archive/phase0-1-research` | Full tree + `ARCHIVE.md` at tip |
| Tag `v0.1.1-phase01-full` | Annotated snapshot for that tip |
| Tag `v0.1.0-phase01-archive` | Older CPU-gate lock (subset; prefer `v0.1.1-phase01-full`) |

```bash
git fetch origin
git checkout v0.1.1-phase01-full
# or: git checkout archive/phase0-1-research
```

## Policy

**Default:** do not reopen PIC / EPIC / CacheBlend / H3 / ResolventKV casually.

**Authorized reopen (2026-10-26):** planner / PIC **evaluation** only under the
approved thesis
[Docs/plans/2026-10-26-revolutionary-product-thesis.md](../plans/2026-10-26-revolutionary-product-thesis.md)
— fail-closed reuse **control plane**, Gate **R1** oracle first.

| Allowed now | Still blocked |
|---|---|
| R1 oracle among {C0, C1-order+prefix, C3-LMCache-CacheBlend} | New repair kernels / ResolventKV |
| Restore CPU oracle / fingerprint / planner stubs for R1–R2 | Claiming PIC product wins |
| Bank new artifacts under `artifacts/r1-*` | Re-running EPIC-only G2 as “done” |

Negative results (still binding evidence):
[Docs/Reports/phase01-negative-results.md](../Reports/phase01-negative-results.md).

Active C1 claims: [Docs/product/CLAIMS.md](../product/CLAIMS.md).  
North star: [Docs/product/control-plane-north-star.md](../product/control-plane-north-star.md).
