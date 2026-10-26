# R1 GPU collect (not on laptop)

CPU analysis: `cw-r1-oracle --input trials.jsonl --report out.json`

GPU collector `collect_oracle_lmcache.py` is **not** checked in yet. Until it is:

1. Rent a GPU host ([Docs/runbooks/local-safety.md](../../Docs/runbooks/local-safety.md)).
2. Install vLLM + LMCache with prefix caching + CacheBlend.
3. Emit JSONL rows: `request_id`, `config` ∈ {C0,C1,C3}, `quality`, `ttft_ms`,
   optional `slice_id`, `feasible`.
4. Copy trials to this repo and run `cw-r1-oracle`.

See [Docs/plans/2026-10-26-r1-oracle-harness.md](../../Docs/plans/2026-10-26-r1-oracle-harness.md).
