# Pre-registration: H3 GPU confirm (fresh prompts)

**Status:** READY — start `cw-h3-confirm` when owner runs GPU.  
**Date written:** 2026-10-23  
**Depends on:** H3 replay PASS (`artifacts/h3-order-risk-2026-10-23/`)  
**Not a G2 redo.** Phase 2 not opened.

## One question

On Colab A100 EPIC Path A + Mistral-7B-Instruct-v0.2, with **new gold facts and
filler** (not the Phase1 oracle prompt text), does the H3 rule
“refuse C3 if order ∈ {ACB, BAC} else C3” still achieve **precision ≥0.9** on
C3 fails and policy **contains ≥0.95** with **mean TTFT ≥20%** below always-C0?

## Fixed

| Item | Value |
|---|---|
| Session | `cw-h3-confirm` |
| Time cap | **90 min** |
| Install | Path A only |
| Model | `mistralai/Mistral-7B-Instruct-v0.2` |
| N | ≥12 requests (all 6 orders × rotating questions) |
| Scale | `--target-context-tokens 12000` (drop to 6000 if wall-clock risk) |
| Runs | n≥2 timed after warmup |
| Golds | **alt set** (Lisbon / 2021 / BETA-4242) + `--filler-seed 99` |
| Analysis | `eval_h3_order_risk.py` on new JSONL |

## Pass / fail

| Outcome | Next |
|---|---|
| PASS | Keep H3 gate; still no Phase 2 |
| FAIL (rule breaks on new text) | Revert C3 to refused; archive H3 as suite-specific |
| Install/OOM | One 6k retry or close unreproducible |

## Procedure

```bash
colab new -s cw-h3-confirm --gpu A100
cd /content && git clone --depth 1 https://github.com/mueid288/ContextWeave.git
cd ContextWeave && git pull

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1
bash scripts/g1/epic/g1_epic_install_fast.sh
source /content/epic-venv/bin/activate

python scripts/phase1/collect_h3_confirm.py \
  --n-requests 12 --runs 2 \
  --target-context-tokens 12000 --max-model-len 16384 \
  --filler-seed 99 \
  --out h3_confirm_trials.jsonl --json

python scripts/phase1/eval_h3_order_risk.py \
  --input h3_confirm_trials.jsonl \
  --out h3_confirm_report.json --json

# bank under artifacts/h3-confirm-YYYY-MM-DD/ then:
colab stop -s cw-h3-confirm
```
