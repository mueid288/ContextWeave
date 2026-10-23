# Architecture (Phase 0 view)

Phase 0 does **not** implement the full Part II architecture. It prepares evidence for gates G0 and G1.

```text
[Synthetic or real / Path C trace JSONL]
            |
            v
   PrefixCacheSimulator (exact prefix; sink carve-out)
            |
            v
   DemandMetrics / Gate G0 (+ working-set LRU)
            |
            v  (provisional G0 already PASS)
   GPU baselines: full prefill | prefix | CacheBlend | EPIC
   + answer-preservation vs full prefill (multi-hop)
            |
            v
         Gate G1
            |
            v  (only if gap remains after best fixed config)
   Candidate: ResolventKV spectral causal closure
   (see Docs/Research/ResolventKV-adoption.md)
```

**Adopted contracts (not new modules yet):** causal-closure quality bar, provenance-bound fingerprints, Mode A canonical builds, sink/prefix carve-out.

Deferred until later gates (see PRD §14): planner, provenance validator, artifact registry, position transform, repair engine (CacheBlend first; ResolventKV only if G1 gap), control-plane API.

Package stubs under `src/contextweave/` reserve those seams without implementing them.
