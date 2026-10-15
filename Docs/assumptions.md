# Phase 0 Assumptions (locked defaults)

Date locked: 2026-10-11  
Source: Phase 0 Kickoff plan + [prd/contextweave_prd_v2.md](prd/contextweave_prd_v2.md)

| Assumption | Value |
|---|---|
| Workload for G0 | Synthetic multi-document RAG (`configs/workloads/synthetic_rag_default.yaml`) |
| G0 status | **Provisional** until a real serving trace is analyzed |
| G0 thresholds | ≥30% post-prefix recurring non-prefix tokens; median chunk ≥512 |
| Primary serving model (0B) | Llama-3.1-8B-Instruct (llama3 scaled RoPE) |
| Preferred model for Case A/B | Qwen3-8B (`rope_scaling: null`) |
| Secondary model (0B) | Qwen3-8B |
| Runtime pins | vLLM ≥ 0.26.0 + LMCache v0.5.2 (candidate) |
| Runtime host | vLLM + LMCache (CacheBlend path) |
| GPU | None yet — rent only after G0 note + reproduction runbooks exist |
| Local model load | **Forbidden** on laptop (`docs/local-safety.md`); allow-flag only on rented GPU |
| PRD amendments | v2.1 binding (`Docs/prd/contextweave_prd_v2.1_amendments.md`) — Gemini gaps |
| G0 working-set | LRU @ 128 GB default; use `--require-working-set` for decision gate |
| Artifact build | Mode A canonical-isolated only (no mid-prompt harvest) |
| Phase 0 GPU buffer | Plan **350–400** GPU-hours (was ~200) |
| MVP training | Training-free |
| Novelty claims | Forbidden without dedicated prior-art / legal review |

## Non-goals this week

- Planner product implementation beyond stubs
- RoPE CUDA/Triton kernels
- Distributed artifact store / multi-tenant API
- Training or LoRA
