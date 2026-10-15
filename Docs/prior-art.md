# Prior Art Matrix (Phase 0B desk work)

Status: desk review updated 2026-10-11. Reported claims are authors' numbers, not reproductions.  
Verification policy: see PRD Appendix C.  
Runtime pins: [runtime-pins.md](runtime-pins.md).

**Tier 1 = must reproduce or adopt. Tier 2 = reproduce if code exists / time allows. Tier 3 = desk only.**

## Tier 1

| Work | Venue / ID | Type | Training | Code / license notes | Runtime pins (to confirm) | Gap after our workload |
|---|---|---|---|---|---|---|
| vLLM / PagedAttention | arXiv 2309.06180 | Native prefix caching | None | https://github.com/vllm-project/vllm — Apache-2.0 | **≥ 0.26.0** with LMCache 0.5.2 | Baseline only |
| SGLang / RadixAttention | arXiv 2312.07104 | Prefix reuse | None | https://github.com/sgl-project/sglang — Apache-2.0 | Optional alternate host | Baseline only |
| LMCache | arXiv 2510.09665 | KV-cache layer; CacheBlend host | None | https://github.com/LMCache/LMCache — **Apache-2.0** | **v0.5.2** (+ explicit `kv_connector_module_path`) | Integration host |
| CacheBlend | arXiv 2405.16444, EuroSys 2025 | Selective recompute by KV deviation | None | Via LMCache; verify non-prefix hits (issue #3238 risk) | Same as LMCache | Quality gap on our model |
| EPIC (LegoLink) | arXiv 2410.15332 | PIC + sink mitigation | None | https://github.com/DerekHJH/epic — **Apache-2.0** | Often older vLLM; 1-week time-box | Fallback = LMCache CacheBlend |
| Independent CLC comparison | arXiv 2603.20218 | Eval + PSR combo | None (PSR) | Methodology reference | N/A | Evaluation protocol |
| HijackKV | arXiv 2607.19957 | Build-context poisoning | n/a | Threat model for Phase 2 tests | N/A | Fingerprint / canonical build |

## Tier 2

| Work | Venue / ID | Type | Notes |
|---|---|---|---|
| Prompt Cache | arXiv 2311.04934 | Schema modules / naive reuse reference | MLSys 2024 |
| APE; SEL | ICLR 2025; ACL 2025 | Attention reshaping | arXiv IDs to confirm in 0B |
| Cache-Craft | arXiv 2502.15734 | Chunk-cache management | Production workload claims |
| ProphetKV | arXiv 2602.02579 | Query-driven selective recompute | Query-dependent cost |
| RelaxKV | arXiv 2609.33503 | Joint repair allocation | Query-aware |

## Tier 3 (desk only for MVP)

Block-Attention, TurboRAG, KVLink, KV Packet (first learned revisit), COMB, C²KV, ATTUNER, SemPIC, CacheClip, Droidspeak, CacheSlide, ReCache, RedKnot — see PRD §4.1.

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
