# G1 matched-pin CacheBlend on Colab

**Goal:** Fair quality-gated CacheBlend on a **pip-matched** pin.  
**Current verdict:** `CLOSED` — engaged @12k but no quality-preserving ≥15% TTFT win
(see experiment-log 2026-10-23 closeout; artifacts `artifacts/g1-diag-2026-10-23/`).

Do **not** reopen matched Colab for G1 unless a new pre-registered question is written.
Blend path that engaged: in-process `LMCacheConnectorV1` + `g1_blend_hooks.py`
(Qwen3-8B, vLLM 0.18 / lmcache 0.4.2).

Offline first:
```bash
python scripts/g1/common/g1_blend_alignment_audit.py --json
pytest tests/unit/test_g1_engagement_and_alignment.py -q
```

Full agent law: [`Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`](Reviews/claude_g1_cacheblend_matched_image_runbook.md)

## Session policy (default)

**Reuse the same Colab session** whenever possible. Creating a new VM forces a full
`pip`/model reinstall. Only call `colab new` when the user asks, the old session is
gone/`not found`, or the requirement forces a different stack (e.g. EPIC fork).

```bash
colab sessions                    # see what is alive
colab console -s cw-matched       # reconnect (name may differ)
cd /content/ContextWeave && git pull
# skip g1_matched_install.sh if vllm/lmcache already match g1_matched_env.json
```

Stop only when idle for a long break or switching to an incompatible pin:
`colab stop -s <session>`.

## Fresh session (only if needed; ≤90 min GPU)

```bash
cd /content && git clone https://github.com/mueid288/ContextWeave.git
cd ContextWeave

export CONTEXTWEAVE_ALLOW_MODEL_LOAD=1
export CONTEXTWEAVE_ALLOW_MATCHED_REINSTALL=1
export SMOKE_MODEL=Qwen/Qwen3-8B
export PYTHONHASHSEED=0

chmod +x scripts/g1_matched_*.sh scripts/g1/matched/g1_collect_artifacts.sh
bash scripts/g1/matched/g1_matched_install.sh          # writes g1_matched_env.json
bash scripts/g1/matched/g1_matched_smoke.sh            # Gate B
bash scripts/g1/matched/g1_matched_blend.sh            # Gate C then D
# If Gate D PASS — Stage E uses **chunk+separator** prompts (not markdown concat):
bash scripts/g1/matched/g1_matched_ttft_chunk_e.sh
# Writes g1_ttft_native_12k_chunks.json + g1_ttft_blend_12k_chunks.json
# Gate E: blend warm_reorder ≤ 0.85 × native warm_reorder; polluted must be False

bash scripts/g1/matched/g1_collect_artifacts.sh
# download the tarball, then:
colab stop -s <session>
```

## Stage E / D prompt format (post antigravity Round-2)

- Quality + TTFT use **fixed token chunks** joined by `" # # "`, with
  `LMCACHE_ENABLE_BLENDING` / `LMCACHE_BLEND_SPECIAL_STR` on the **client** for blend.
- Chunk lengths are multiples of **256**. TTFT defaults to `--max-tokens 1` and the
  same `--enforce-eager` on both native and blend arms.
- Quality: each case does `reset → seed ABC → measure order+question` (no shared-body
  prefix hits across cases). Includes multi-hop cases.
- Install: `scripts/g1/matched/g1_matched_install.sh` picks a pair by Python version:
  - Py 3.10–3.12 → `vllm==0.6.6.post1` + `lmcache==0.5.3` (legacy “0.5.3 era”)
  - Py ≥3.13 (current Colab) → `vllm==0.18.0` + `lmcache==0.4.2` (LMCache matrix green)
  Override with `VLLM_PIN` / `LMCACHE_PIN`. Do **not** force 0.6.6 on Py3.13 (no wheel).
- Pre-remediation artifacts under `artifacts/g1-matched-2026-10-22/` are **confounded** —
  re-run Gates C–E after `git pull` on a fresh matched install before citing results.

## Gates

| Gate | Pass |
|---|---|
| B smoke | coherent `smoke-ok`-like output |
| C control | `contains_rate ≥ 0.9`, `garbage_rate ≤ 0.05` |
| **R reuse** | reorder `cached/retrieved ≥ 0.7 × chunk_token_total` (fail closed if metric missing) |
| D blend | **only if R passes**; C bars + `agree_with_control_rate ≥ 0.9` on reorder |
| E latency | **only if R passes**; blend warm-reorder ≤ 0.85 × native warm-reorder |

**Never cite D/E if Gate R is `ENGAGEMENT_FAIL` / `ENGAGEMENT_UNKNOWN`.**
