# Research archive pointer

Phase 0/1 research (G1 CacheBlend/EPIC, G2 oracle, H3/H4, fingerprints, PIC
planner, Reviews, gates) was **removed from `main`** to keep this repo focused
on the Canonical Order **C1** kit + field dogfood.

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

Do **not** reopen PIC / EPIC / CacheBlend / H3 / ResolventKV without a new written
thesis and explicit product decision. Negative results:
[Docs/Reports/phase01-negative-results.md](../Reports/phase01-negative-results.md).

Active product path: [Docs/product/CLAIMS.md](../product/CLAIMS.md).
