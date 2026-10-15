# GPU Acquisition and Phase 0B Runbook

**Start here for rental steps:** [cloud-gpu-rental.md](cloud-gpu-rental.md)

**Rule:** Laptop never loads models ([local-safety.md](local-safety.md)).  
Rent only when ready to run the smoke the same day.

## Quote criteria

| Item | Smoke (recommended first) | Full Phase 0B matrix |
|---|---|---|
| GPU | 1× RTX 4090 24GB (or A6000 48GB) | 1× A100 80GB (or H100) |
| Mode | On-demand / community | On-demand; no monthly reserve until G1 looks good |
| Software | CUDA 12.x + vLLM ≥0.26 + LMCache 0.5.2 | Same pins after smoke |
| First model | Qwen3-8B | Llama-3.1-8B-Instruct + Qwen3 |

## Quote snapshot (fill live prices at checkout)

| Provider | SKU | $/GPU-hour (indicative) | Notes |
|---|---|---|---|
| RunPod Community | RTX 4090 24GB | ~0.34 | **Preferred smoke** |
| RunPod Secure | RTX 4090 24GB | ~0.69–0.74 | More stable |
| RunPod Community | A100 80GB | ~1.19–1.39 | Matrix after smoke |
| Lambda | A100 80GB | ~1.29 | Alternative |
| Vast.ai | RTX 4090 | ~0.25–0.50 | Cheap; verify host reliability |

Your checkout prices:

| Provider | SKU | $/GPU-hour | Date | Notes |
|---|---|---|---|---|
| | | | | |
| | | | | |

Budget / decision owner: fill PRD §0.5 when known.

## Rent gate (checklist)

- [x] Provisional G0 exists (synthetic + Path C `my_corpus` PASS)
- [x] Demand interesting enough to fund a **$2–5 smoke**
- [x] Candidate pins in `docs/runtime-pins.md`
- [ ] HF account + Qwen3 (and/or Llama) license accepted
- [ ] HF token ready
- [ ] Repo available to clone on the pod (or zip upload)
- [ ] Hard spend cap set (recommend **$5** for first session)
- [x] Smoke entrypoints: `docs/cloud-gpu-rental.md`, `scripts/smoke_remote.sh`

## First paid job: smoke (≤2 GPU-hours)

1. Deploy RunPod 4090 — see [cloud-gpu-rental.md](cloud-gpu-rental.md).
2. `export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1`
3. Install vLLM + LMCache; `huggingface-cli login`
4. `bash scripts/smoke_remote.sh` (or the inline Python in the rental doc)
5. Record `nvidia-smi`, package versions in `docs/experiment-log.md`
6. **Stop the pod**
7. Only if smoke passed: schedule A100 session for Tier-1 baselines

## Full Tier-1 matrix (after smoke)

| Order | Baseline | Success artifact |
|---|---|---|
| 1 | Full prefill | p50/p95 TTFT + quality |
| 2 | Native prefix caching | Shared-prefix prompts |
| 3 | LMCache + CacheBlend | Non-prefix hits verified (not just prefix) |
| 4 | EPIC | Or documented failure in ≤1 week |

## Stop conditions

- Smoke cannot load an 8B model after one session → fix offline, don’t keep burning hours.
- CacheBlend non-prefix hits stay zero on pinned stack → document; don’t expand matrix yet.
- Spend exceeds your cap → terminate immediately.

## Local reminder

```bash
# On your Mac — must print blocked_local
python scripts/run_baseline.py --strategy smoke --json
```
