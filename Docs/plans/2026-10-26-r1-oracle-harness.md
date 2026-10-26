# R1 — Oracle harness (control-plane falsification)

**Parent:** [2026-10-26-revolutionary-product-thesis.md](2026-10-26-revolutionary-product-thesis.md)  
**Status:** Ready to run on **rented GPU** (laptop: CPU analysis only — [local-safety.md](../runbooks/local-safety.md))  
**Differs from failed G2 (2026-10-23):** that study used **EPIC LegoLink** on needle-style reorder; C3 quality collapsed → best fixed = C0, oracle upside 0. R1 uses **LMCache CacheBlend** + **Zipfian multi-hop RAG** + **feasible C1 order+prefix**.

---

## 1. Question

On one pinned model + runtime, does **per-request oracle** choice among:

| Code | Strategy |
|---|---|
| **C0** | Full prefill (prefix cache reset / no reuse) |
| **C1** | Frequency-stable document order + native prefix cache |
| **C3** | LMCache CacheBlend at fixed recompute ratio (default **15%**) |

beat the **best single fixed** arm on the Gate R1 bar?

---

## 2. Gate R1 (ratified — do not edit after seeing data)

| Pass if | Fail if |
|---|---|
| Oracle ≥ **+10%** lower p95 TTFT vs best fixed at quality within **−2 pp** of C0 **or** equal TTFT (±3%) with **+2 pp** quality vs best fixed | Upside below bar after counting analysis overhead |
| ≥1 workload slice where fixed **C3** quality fails the −2 pp margin but **C0** or **C1** passes (proves a gate is needed) | All arms equivalent → no planner value |

**On fail:** stay C1 kit; do not build R2 control plane.  
**On pass:** open R2 (fingerprints + plan API).

---

## 3. Fixed pins (edit only before first timed trial)

| Item | Value |
|---|---|
| Model | `Qwen/Qwen2.5-7B-Instruct` (fallback: `Mistral-7B-Instruct-v0.3`) |
| Runtime | vLLM ≥0.6 with **prefix caching on** + LMCache CacheBlend |
| N requests | ≥40 (Zipfian doc popularity; ≥50% multi-doc synthesis) |
| Context | ~8k–12k prompt tokens typical |
| Quality | Exact / contains vs gold for multi-hop; also report answer-preservation vs C0 greedy short decode |
| Latency | Warm p50/p95 TTFT; ≥3 timed runs after warmup; reset or salt cold vs warm protocol documented |
| Analysis | CPU: `cw-r1-oracle` / `contextweave.oracle.upside` |

**Do not** use EPIC LegoLink as C3 for this gate (prior negative result).

---

## 4. Procedure (GPU host)

```bash
# On rented GPU only — never on laptop
export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
git clone … && cd ContextWeave && pip install -e ".[dev]"
# Install vLLM + LMCache per their docs (not in laptop extras)

# 1) Generate Zipfian multi-hop workload (or import Hotpot/2Wiki slice)
cw-generate-workload --config configs/workloads/r1_zipfian_rag.yaml   # when added

# 2) Collect trials (script TBD — restore/adapt from archive phase1 collectors)
python scripts/r1/collect_oracle_lmcache.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --n-requests 40 \
  --blend-recompute-ratio 0.15 \
  --out artifacts/r1-oracle-WIP/oracle_trials.jsonl \
  --report artifacts/r1-oracle-WIP/oracle_report.json

# 3) CPU analysis (safe on laptop once trials are banked)
cw-r1-oracle --input artifacts/r1-oracle-WIP/oracle_trials.jsonl \
  --report artifacts/r1-oracle-WIP/oracle_upside.json
```

Bank `pip freeze`, trials, report under `artifacts/r1-oracle-YYYY-MM-DD/` **before** tearing down the GPU.

---

## 5. CPU deliverables on `main` (this batch)

| Item | Purpose |
|---|---|
| `src/contextweave/oracle/` | Oracle vs best-fixed upside (no model load) |
| `cw-r1-oracle` CLI | Analyze banked trials against Gate R1 |
| Unit tests | Synthetic trials: pass/fail frontier math |
| This runbook | GPU collect still TODO until `scripts/r1/collect_*` lands |

---

## 6. Explicit non-claims until banked

- No control-plane product claim  
- No “CacheBlend works” claim from old G1 harness  
- No re-use of `artifacts/phase1-oracle-2026-10-23/` as R1 evidence (wrong C3 stack)
