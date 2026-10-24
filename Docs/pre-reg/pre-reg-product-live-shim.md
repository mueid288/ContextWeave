# Pre-registration: Live canonical-order shim (CPU) + quality bar (GPU later)

**Status:** Part A **PASS** · Part B **PASS** (2026-10-24, Colab A100)  
**Depends on:** product canonical-order PASS  
**Not a PIC reopen.**

## Part A result

`FrequencyPrior` + `apply_chat_documents` + `cw-serve-order` (--reorder-json /
stdlib proxy). Unit tests in `tests/unit/test_live_order.py`. No GPU.

## Part B result

`artifacts/product-order-quality-2026-10-24/` — frequency **1.0**, natural **1.0**,
`pass_heuristic: true` (freq ≥ 0.80 and ≥ 0.90 × relevance). Shim may default to
`by_frequency_desc`.

## Part A — Live shim (CPU, this lane)

### One question

Can a local OpenAI-compatible shim reorder `cw_documents` with a **rolling
frequency prior** (cold-start → `by_doc_id`), rewrite the user message, and
optionally forward to an upstream `/v1/chat/completions` URL — with unit tests
and a dry-run reorder path that needs no GPU?

### Pass

- `FrequencyPrior` observe/snapshot works; cold_start_n uses `by_doc_id`
- `apply_chat_documents` reorders and injects docs into messages
- `cw-serve-order --dry-run` (or `/v1/cw/reorder`) returns ordered docs + rewritten messages
- cpu_gate green; no torch/vllm on laptop

## Part B — Quality bar (GPU, 90 min cap) — READY

### One question

On a GPU OpenAI server, needle suite (city/year/code): does **frequency** order
keep `contains_rate ≥ 0.80` **and** `≥ 0.90 × relevance` contains_rate?

Harness: `scripts/product/eval_order_quality.py` (HTTP only; laptop may call remote).

| Outcome | Next |
|---|---|
| PASS | Default shim to frequency order |
| FAIL | Keep shim; default relevance/`natural`; document caveat |
| Block / OOM | One retry smaller model; else close quality unverified |

### Fixed

| Item | Value |
|---|---|
| Session | `cw-order-quality` |
| Time cap | **90 min** wall |
| Server | vLLM OpenAI (`--model mistralai/Mistral-7B-Instruct-v0.2` or Qwen3-8B) |
| Modes | relevance (oracle order) · natural (answer-last) · frequency (warm prior) |
| Pass | freq ≥ 0.80 and ≥ 0.90 × relevance |
| Out | `artifacts/product-order-quality-YYYY-MM-DD/` |

### Procedure (Colab)

Full copy-paste: **`Docs/product/colab-order-quality.md`**

```bash
colab new -s cw-order-quality --gpu A100
# then cells in Docs/product/colab-order-quality.md
# bank artifacts/product-order-quality-YYYY-MM-DD/ before:
colab stop -s cw-order-quality
```

CPU dry-build (no GPU): `python scripts/product/eval_order_quality.py --base-url x --dry-build`
