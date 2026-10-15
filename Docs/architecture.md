# Architecture (Phase 0 view)

Phase 0 does **not** implement the full Part II architecture. It prepares evidence for gates G0 and G1.

```text
[Synthetic or real trace JSONL]
            |
            v
   PrefixCacheSimulator (exact prefix)
            |
            v
   DemandMetrics / Gate G0 report
            |
            v  (only if G0 interesting)
   GPU baseline reproduction (LMCache / CacheBlend / EPIC)
            |
            v
         Gate G1
```

Deferred until later gates (see PRD §14): planner, provenance validator, artifact registry, position transform, repair engine, control-plane API.

Package stubs under `src/contextweave/` reserve those seams without implementing them.
