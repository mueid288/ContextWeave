# EPIC @ 12k — 2026-10-23

**Pre-reg:** `Docs/pre-reg/pre-reg-epic-12k.md`  
**Session:** `cw-epic-12k` (Colab A100)  
**Verdict:** **PASS** (`pass_heuristic: true`)

| Metric | Value |
|---|---|
| Model | `mistralai/Mistral-7B-Instruct-v0.2` |
| `prompt_tokens` | 12001 |
| Full prefill p50 / p90 | 1021 / 1022 ms |
| LegoLink-8 p50 / p90 | 266 / 266 ms |
| Speedup (p50) | **3.84×** (≥15% bar) |
| Quality | gold `Karachi` in both outputs |

## Files

- `g1_epic_12k.json` — bench payload
- `pip_freeze.txt` — epic-venv freeze (145 lines)

## CLI

```bash
python scripts/g1/epic/g1_epic_bench.py \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --max-model-len 16384 \
  --target-context-tokens 12000 \
  --runs 5 --json --out g1_epic_12k.json
```

Install: Path A `scripts/g1/epic/g1_epic_install_fast.sh` (vLLM 0.7.0 wheel + EPIC overlay).
Scale flags were uploaded mid-session (not yet on `origin/main` at run time).
