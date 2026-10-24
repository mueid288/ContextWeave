# Pre-registration: EPIC multi-fact quality @ 12k

**Status:** **PASS (order-blind)** — banked `artifacts/g1-epic-quality-2026-10-23/`.  
**Superseded for non-prefix quality:** Phase 1 oracle (`pre-reg-phase1-oracle.md`) — C3 mean_q **0.70** under chunk-order permutation.  
**Date written:** 2026-10-23 · **Closed:** 2026-10-23  
**Depends on:** EPIC@12k latency PASS (`artifacts/g1-epic-12k-2026-10-23/`)  
**Not a CacheBlend reopen. Not Phase 1.**

### Result

| Case | Speedup | Contains |
|---|---|---|
| city | 3.86× | full+kvlink |
| year | 2.19× | full+kvlink |
| code | 1.98× | full+kvlink |

`contains_rate_*` = 1.0; all cases `latency_ok`; `pass_heuristic: true`.  
**Caveat:** fixed chunk order (does not permute); not a PIC quality gate for reorder.

## One question

On Colab A100, EPIC fast path + `Mistral-7B-Instruct-v0.2`, at **~12k** tokens,
does LegoLink-8 keep **≥0.9 gold-contains** on **both** full and kvlink arms across
**three** facts in the same doc set (city / year / secret code), **and** still clear
**≥15% TTFT** on **every** case?

## Fixed

| Item | Value |
|---|---|
| Session | `cw-epic-quality` |
| Time cap | **90 min** wall |
| Install | Path A only (`g1_epic_install_fast.sh`) |
| Model | `mistralai/Mistral-7B-Instruct-v0.2` |
| Scale | `--target-context-tokens 12000 --max-model-len 16384` |
| Suite | `--suite quality` (city, year, code) |
| Runs | n≥5 after one warmup **per case** |
| Pass | `contains_rate_{full,kvlink} ≥ 0.9` **and** every case `latency_ok` |
| Out of scope | CacheBlend, ResolventKV, model swaps, Phase 1 |

## Pass / fail

| Outcome | Next |
|---|---|
| PASS | Keep C3; optionally note multi-fact in planner notes; still no Phase 1 auto |
| Quality miss | Soften/remove C3 preference or refuse C3 until better evidence |
| Latency miss on a case | Document; do not claim uniform ≥15% |
| Install/OOM block | One retry at 6k or close as unreproducible |

## Procedure

```bash
colab new -s cw-epic-quality --gpu A100
cd /content && git clone --depth 1 https://github.com/mueid288/ContextWeave.git
cd ContextWeave && git pull

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1
bash scripts/g1/epic/g1_epic_install_fast.sh
source /content/epic-venv/bin/activate

python scripts/g1/epic/g1_epic_bench.py \
  --model mistralai/Mistral-7B-Instruct-v0.2 \
  --max-model-len 16384 \
  --target-context-tokens 12000 \
  --suite quality \
  --runs 5 \
  --json \
  --out g1_epic_quality_12k.json

# bank under artifacts/g1-epic-quality-YYYY-MM-DD/ then:
colab stop -s cw-epic-quality
```

## Collect

- `g1_epic_quality_12k.json`
- `pip freeze` from epic-venv
- Exact CLI
