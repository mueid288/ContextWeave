# Pre-registration: EPIC @ ≥6k/12k (optional GPU)

**Status:** PARKED — do not run until the owner explicitly starts a session.  
**Date written:** 2026-10-23  
**Not a G1 reopen.** CacheBlend G1 stays **CLOSED**. Partner trace not required.

## One question

On Colab A100, with the **EPIC fast path** (vLLM 0.7.0 wheel + overlay) and
`Mistral-7B-Instruct-v0.2`, at **≥6k token** chunked context (prefer **12k** if
it fits), does LegoLink-8 deliver **≥15% lower p50 TTFT** than same-stack full
prefill **and** preserve gold answers (contains rate ≥0.9)?

## Fixed (do not change mid-session)

| Item | Value |
|---|---|
| Session name | `cw-epic-12k` |
| Time cap | **90 min** wall, then stop |
| Install | `scripts/g1_epic_install_fast.sh` only (no full nvcc unless Path A probe fails once) |
| Model | `mistralai/Mistral-7B-Instruct-v0.2` (demo fork; not Qwen3) |
| Scale | Target prefix/context **≥6000** tokens; try **12000** if OOM-free |
| Runs | n≥5 after one warmup; report p50/p90 |
| Baseline | Full prefill on **same** EPIC-overlay stack (not native vLLM 0.18) |
| Quality | Gold contains ≥0.9 on the bench’s cases; garbage ≤0.05 |
| Out of scope | CacheBlend, ResolventKV, pin sweeps, model swaps |

## Pass / fail (pre-registered)

| Outcome | Meaning | Next |
|---|---|---|
| Speed ≥15% **and** quality OK | EPIC provisional positive at this scale | Log; optional planner v0 calibration row for C3; still no Phase 1 auto-start |
| Engages but speed &lt;15% or quality fail | Real negative / soft miss at scale | Log; keep C3 out of planner; stop EPIC lane |
| Cannot reach ≥6k (OOM / fork limits) | Scale BLOCK | Document max working size; do not cite toy ~500 tok as close |
| Install/runtime block | Harness BLOCK | One Path B/C attempt **or** close EPIC as unreproducible on Colab |

## Procedure (when approved)

```bash
colab new -s cw-epic-12k --gpu A100
cd /content && git clone --depth 1 https://github.com/mueid288/ContextWeave.git
cd ContextWeave && git pull

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_EPIC_REINSTALL=1
export SMOKE_MODEL=mistralai/Mistral-7B-Instruct-v0.2
bash scripts/g1_epic_install_fast.sh
source /content/epic-venv/bin/activate

# Extend bench args if needed for ≥6k/12k (document exact command in log).
python scripts/g1_epic_bench.py --json | tee g1_epic_12k.json

# collect JSON + pip freeze, download, THEN:
colab stop -s cw-epic-12k
```

If `g1_epic_bench.py` lacks a scale flag, **stop and patch offline first** — do not
improvise a new protocol on the GPU clock.

## Collect

- `g1_epic_12k.json` (or whatever `--out` writes)
- `pip freeze` from the epic venv
- Exact CLI + `max_model_len` / filler size used
- Bank under `artifacts/g1-epic-12k-YYYY-MM-DD/` **before** `colab stop`

## Non-goals

- Do not reopen CacheBlend G1.
- Do not treat a fail here as “Phase 0 demand failed.”
- Do not open ResolventKV from an EPIC miss.
