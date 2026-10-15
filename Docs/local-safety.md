# Local safety policy — no models on the laptop

**Hard rule:** do not download weights, install `torch`/`vllm`/`lmcache`/`transformers`, or run inference on the laptop.

Phase 0A work (synthetic traces, G0 analysis, docs) is CPU-only and stays that way.

## What is allowed locally

- `pip install -e ".[dev]"` (pyyaml, pytest only)
- `python scripts/generate_workload.py`
- `python scripts/analyze_trace.py`
- `python scripts/import_trace.py` / `build_corpus_trace.py` / `cost_model.py`
- Editing docs / configs / tests

## What is forbidden locally

- Installing GPU extras (`torch`, `vllm`, `lmcache`, `transformers`, CUDA toolkits for this project)
- `huggingface-cli download` of model **weights** (config.json desk fetches are fine)
- Running `scripts/run_baseline.py` with model load enabled
- Any `from_pretrained` / vLLM engine start

## Enforcement

1. Default dependencies in `pyproject.toml` do **not** include ML stacks.
2. `contextweave.safety.assert_model_load_allowed()` gates every baseline `setup()`.
3. Model load is allowed only when:

```bash
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
```

Set that **only** on a rented GPU host after reading `Docs/gpu-runbook.md`. Never export it in your laptop shell profile.

## If something asks to install torch

Decline. Continue with CPU scripts, or move the job to a cloud GPU when you are ready to rent.
