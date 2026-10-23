# Prior Art Matrix (Phase 0B desk work)

Status: desk review updated 2026-10-23 (post G1 CacheBlend closeout).  
Reported claims are authors' numbers unless marked **measured**.  
Verification policy: see PRD Appendix C.  
Runtime pins: [runtime-pins.md](runtime-pins.md).  
Phase 0 exit: [phase0-exit-decision.md](phase0-exit-decision.md) (**pivot**; Phase 1 not opened).  
ResolventKV: **blocked** until quality-preserving PIC win — [Research/ResolventKV-adoption.md](Research/ResolventKV-adoption.md).

**Tier 1 = must reproduce or adopt. Tier 2 = reproduce if code exists / time allows. Tier 3 = desk only.**

### Evaluation contracts we adopt from recent PIC literature

| Contract | Meaning for our G1/G2 runs |
|---|---|
| **Causal closure** (SAFE-KV) | Reusing composed chunk KV without repairing downstream history is not “full-prefill equivalent”; report **answer preservation** vs full prefill |
| **Routing vs values** (ATTUNER) | Quality loss can be mostly attention routing; don’t stop at “cached values look sane” |
| **Sink / first-chunk carve-out** (Irminsul) | Pin system preamble on exact prefix cache; only movable docs use non-prefix reuse |
| **Receiver necessity** | Prefer multi-hop / doc-dependent tasks; parametric-only benchmarks understate cache value |

## Tier 1

| Work | Venue / ID | Type | Training | Code / license notes | Runtime pins (to confirm) | Gap after our workload |
|---|---|---|---|---|---|---|
| vLLM / PagedAttention | arXiv 2309.06180 | Native prefix caching | None | https://github.com/vllm-project/vllm — Apache-2.0 | **≥ 0.26.0** with LMCache 0.5.2 | Baseline only |
| SGLang / RadixAttention | arXiv 2312.07104 | Prefix reuse | None | https://github.com/sgl-project/sglang — Apache-2.0 | Optional alternate host | Baseline only |
| LMCache | arXiv 2510.09665 | KV-cache layer; CacheBlend host | None | https://github.com/LMCache/LMCache — **Apache-2.0** | **v0.5.2** (+ explicit `kv_connector_module_path`) | Integration host |
| CacheBlend | arXiv 2405.16444, EuroSys 2025 | Selective recompute by KV deviation | None | Via LMCache; verify non-prefix hits (issue #3238 risk) | **Measured** Colab A100, vLLM 0.18 + lmcache 0.4.2 in-process | **Engages** (BAC); quality agree 0.67; ~1.10× not ≥1.15×; CBA miss — **closed** for our bar |
| EPIC (LegoLink) | arXiv 2410.15332 | PIC + sink mitigation | None | https://github.com/DerekHJH/epic — **Apache-2.0** | Often older vLLM; 1-week time-box | **Toy-scale only** (~500 tok) — not a fair G1 close; optional new pre-reg @12k |
| Independent CLC comparison | arXiv 2603.20218 | Eval + PSR combo | None (PSR) | Methodology reference | N/A | Evaluation protocol |
| HijackKV | arXiv 2607.19957 | Build-context poisoning | n/a | Threat model for Phase 2 tests | N/A | Fingerprint / canonical build |

## Tier 1.5 — must *desk-verify* before claiming a gap (quality contracts)

| Work | Venue / ID | Why it matters to us | Action |
|---|---|---|---|
| **SAFE-KV** | arXiv 2610.15186 | Proves prefix-conditioned PIC fails multi-hop without causal suffix repair; suffix repair ≈ full prefill cost | Cite for G1 quality bar; optional reproduce after CacheBlend |
| **ATTUNER** | arXiv 2609.36722 | PIC failure ≈ attention routing; LoRA on queries (training) | Desk + optional ablation; not MVP path (training) |
| **Irminsul / Leyline** | arXiv 2605.05696 / 2606.01065 | Δ-RoPE + CDC for shifted agentic tokens; **no** causal-history repair | Use sink carve-out + position fix only; not sufficient alone |
| **CacheTune** | arXiv 2605.24022 | Cross-chunk deps in low-frequency KV modes; still token recompute | Desk; informs spectral hypotheses later |
| **SpecCache / ProphetKV** | ACL 2026 / OpenReview | Deep-layer / query-driven selectors beat shallow CacheBlend selectors | Desk when choosing recompute policy |
| **EncBank / CoMem** | arXiv 2610.10058 | Depth split: lower = local encode, upper = integrate | Desk only until after G1 |
| **KV Packet / CacheRepair / C2KV** | 2026 arXivs | Learned wrappers / repair nets | Out of MVP (training); Tier 3 for novelty review |

## Tier 2 (desk only for now — no Phase 1 reproduce)

| Work | Venue / ID | Type | Notes / post-G1 action |
|---|---|---|---|
| Prompt Cache | arXiv 2311.04934 | Schema modules / naive reuse reference | MLSys 2024 — baseline history only |
| APE; SEL | ICLR 2025; ACL 2025 | Attention reshaping | C5 candidates if Phase 1 ever opens |
| Cache-Craft | arXiv 2502.15734 | Chunk-cache management | Production claims; desk |
| ProphetKV | arXiv 2602.02579 | Query-driven selective recompute | Query-dependent cost — not in v0 planner set |
| RelaxKV | arXiv 2609.33503 | Joint repair allocation | Query-aware — desk |
| eOptShrinkQ / TurboQuant | arXiv 2605.02905 | Spiked SVD / KV compression | Desk only; ResolventKV still blocked |

## Tier 3 (desk only for MVP)

Block-Attention, TurboRAG, KVLink, COMB, SemPIC, CacheClip, Droidspeak, CacheSlide, ReCache, RedKnot, HeteroFold / CacheBridge / CacheLink (cross-family latent), Echo/SKA (Koopman) — see PRD §4.1 and Research kill-table.

**Explicit non-wedges (killed for our core path):** MLA-only Δ-rotation as sufficient repair; ZK-LLM proving; constant-memory Koopman attention requiring new pretrain; cross-model latent KV handoff.

## Required questions per Tier 1/2 work

1. Independently cached chunks? 2. Position/order restrictions? 3. RoPE / sink handling? 4. Full-context preserved vs approximated vs recomputed? 5. Quality/perf metric? 6. Runnable code? 7. Models / runtime pins? 8. License? 9. Superseding work? 10. Gap on our workload?

## Model RoPE desk checks (no GPU)

### Llama-3.1-8B-Instruct (`configs/models/llama31_8b_instruct.yaml`)

Fetched desk config (NousResearch mirror; re-check official after HF auth):  
`configs/models/fetched/llama31_8b_instruct.config.json`

| Field | Value |
|---|---|
| `rope_theta` | 500000.0 |
| `rope_scaling` | `llama3` type, factor 8.0, original_max 8192 |
| `max_position_embeddings` | 131072 |
| Attention | GQA 32q / 8kv, 32 layers, hidden 4096 |

**Implication:** first Case A/B rotation tests should prefer **Qwen3-8B** (unscaled) or an explicitly unscaled Llama variant; Llama-3.1 Instruct is a scaled-RoPE Phase 1 variant per PRD §7.4.

### Qwen3-8B (`configs/models/qwen3_8b.yaml`)

Fetched official HF config: `configs/models/fetched/qwen3_8b.config.json`

| Field | Value |
|---|---|
| `rope_theta` | 1000000 |
| `rope_scaling` | **null** |
| `use_sliding_window` | false |
| `max_position_embeddings` | 40960 |
| Attention | GQA 32q / 8kv, 36 layers, head_dim 128 |

**Implication:** best primary for early numerical RoPE tests; keep Llama-3.1 as primary *serving* target for CacheBlend reproductions that match the independent study.

### Desk-check commands (CPU / network only)

```bash
# Official Llama (gated):
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct config.json --local-dir /tmp/llama31-cfg
python -c "import json; print(json.load(open('/tmp/llama31-cfg/config.json'))['rope_scaling'])"
```

## License review checklist (before any GPU reproduction)

- [x] vLLM LICENSE compatible (Apache-2.0)
- [x] LMCache LICENSE compatible (Apache-2.0, v0.5.2)
- [x] EPIC repo LICENSE present (Apache-2.0)
- [ ] Model weights: Llama community license / Qwen license accepted (human)
- [ ] No redistribution of proprietary traces without partner agreement

## Reproduction runbook stubs

Detailed GPU procedure: [gpu-runbook.md](gpu-runbook.md). Pins: [runtime-pins.md](runtime-pins.md).

| Baseline | Entry | Time-box | Fallback |
|---|---|---|---|
| Smoke | `python scripts/run_baseline.py --strategy smoke` | ≤2 GPU-hours | Stop instance |
| Full prefill | `python scripts/run_baseline.py --strategy full_prefill` | 1 day | — |
| Native prefix cache | `--strategy prefix_cache` | 1 day | SGLang radix |
| CacheBlend | `--strategy cacheblend` | ≤1 week | Fail G1 if path broken |
| EPIC | `--strategy epic` | ≤1 week | Document failure; CacheBlend + methodology paper |
