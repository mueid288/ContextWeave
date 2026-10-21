# Runtime pins (Phase 0B candidate)

Date: 2026-10-11  
Status: **partially validated** — smoke + prefix TTFT OK on Colab; CacheBlend **blocked** on vLLM 0.32.0 + lmcache 0.5.6 (2026-10-21).

## Recommended stack for first smoke

| Component | Pin | License | Notes |
|---|---|---|---|
| Python | 3.11 or 3.12 | — | Match LMCache wheel ABI |
| CUDA | 12.4+ (match vLLM wheel) | — | Record exact driver via `nvidia-smi` |
| vLLM | **≥ 0.26.0** (try latest stable ≤ 0.28 unless recipe says otherwise) | Apache-2.0 | External connector load supported for ≥ 0.20.0 |
| LMCache | **v0.5.2** (or newer stable that documents CacheBlend + HMA) | Apache-2.0 | Release notes: required for vLLM ≥ 0.26.0; CacheBlend under hybrid KV manager |
| Smoke model (first) | `Qwen/Qwen3-8B` | Qwen license | Prefer for first cloud smoke (usually ungated) |
| Primary serving model | `meta-llama/Llama-3.1-8B-Instruct` | Llama community license | HF gated — accept before Llama runs |
| Secondary | `Qwen/Qwen3-8B` | Qwen license | Also used for unscaled-RoPE Case A/B later |
| EPIC | https://github.com/DerekHJH/epic | **Apache-2.0** | Confirmed via GitHub license API; often older vLLM — 1-week time-box |

## Connector config (must set explicitly)

For vLLM ≥ 0.20.0, do **not** rely on the bundled connector. Set:

```json
{
  "kv_connector": "LMCacheMPConnector",
  "kv_connector_module_path": "lmcache.integration.vllm.lmcache_mp_connector",
  "kv_role": "kv_both"
}
```

Source: [LMCache compatibility docs](https://docs.lmcache.ai/getting_started/compatibility.html).

## Known risk: CacheBlend non-prefix matching

Issue [#3238](https://github.com/LMCache/LMCache/issues/3238) reported CacheBlend non-prefix reuse broken with older vLLM V1 connector paths (scheduler only did prefix match). Smoke test **must** verify non-prefix document reuse, not only shared-prefix hits. Prefer LMCache ≥ 0.5.2 + documented CacheBlend/HMA path; abort matrix if non-prefix hits stay zero.

### Observed block (2026-10-21)

| Stack | Result |
|---|---|
| Colab A100-40GB, vLLM **0.32.0**, lmcache **0.5.6**, Qwen3-8B, in-process blend | Engine starts (after #4131 register_model patch); first generate dies in layerwise `batched_from_gpu` with `IndexError` dim 4 |

**Do not** treat this pair as a CacheBlend baseline host. Prefer `lmcache/vllm-openai` image or re-pin to a pair LMCache documents for blending.

## Install sketch (GPU box)

```bash
python -m venv .venv-gpu && source .venv-gpu/bin/activate
pip install -U pip
# Pin exact versions after checking https://docs.lmcache.ai/getting_started/installation.html
pip install "vllm==<PIN>" "lmcache==0.5.2"
huggingface-cli login   # for Llama-3.1
```

Record the final tuple in `docs/experiment-log.md`: vLLM, LMCache, torch, CUDA, GPU SKU.

## License checklist update

- [x] vLLM — Apache-2.0
- [x] LMCache — Apache-2.0 (verified from `v0.5.2` LICENSE)
- [x] EPIC — Apache-2.0
- [ ] Llama-3.1 weights — accept on HF (human action)
- [ ] Qwen3 weights — accept/confirm card terms (human action)
