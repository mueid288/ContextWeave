# G1 Matched-Pin CacheBlend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ship Stage A CPU harness so a fresh Colab session can run the matched-pin CacheBlend quality→latency gates from the approved design.

**Architecture:** Shared scoring helpers + matched quality/TTFT benches + Colab install/smoke/blend/collect scripts; no GPU work in this plan.

**Tech Stack:** Python 3.11+, pytest, bash; GPU side uses vLLM + lmcache 0.5.3 MP blend (recorded at session start).

**Design:** `Docs/plans/2026-10-22-g1-matched-cacheblend-design.md`  
**Runbook:** `Docs/Reviews/claude_g1_cacheblend_matched_image_runbook.md`

---

### Task 1: Shared answer scoring helpers

**Files:**
- Create: `scripts/g1_scoring.py`
- Test: `tests/unit/test_g1_scoring.py`

**Step 1:** Write failing tests for `strip_think`, `extract_answer`, `score_output`, `is_garbage` (echo/`# #`/empty/no-gold).

**Step 2:** Implement helpers in `scripts/g1_scoring.py`.

**Step 3:** `pytest tests/unit/test_g1_scoring.py -q` → PASS; commit.

---

### Task 2: Matched quality bench (≥10 cases)

**Files:**
- Create: `scripts/g1_matched_quality_bench.py`
- Modify: `tests/unit/test_g1_benches.py`

**Step 1:** Cases with DOC-ids + planted facts; `--mode {native,control,blend}`; `--order {abc,bac,cba}`; JSON with contains/agree/garbage.

**Step 2:** Control/blend use `LMCacheMPConnector`; blend assumes server already up (shell wrapper). Native = no connector.

**Step 3:** CPU unit tests for case count, scoring, refuse without allow flag; commit.

---

### Task 3: Matched TTFT bench

**Files:**
- Create: `scripts/g1_matched_ttft_bench.py`

**Step 1:** Streaming TTFT when available; else wall-clock first-token proxy documented in JSON `ttft_method`.

**Step 2:** Scenarios cold_abc / warm_abc / warm_bac / warm_cba; `--backend {native_prefix,blend}`; `--runs 10` + 1 warmup; p50/p90.

**Step 3:** CPU tests for arg parsing / scenario names; commit.

---

### Task 4: Colab scripts + docs + pre-reg

**Files:**
- Create: `scripts/g1_matched_install.sh`, `g1_matched_smoke.sh`, `g1_matched_blend.sh`, `g1_collect_artifacts.sh`
- Create: `Docs/g1-matched-colab.md`
- Modify: `Docs/experiment-log.md`, `Docs/Initial/phase0-status.md`, `Docs/runtime-pins.md`

**Step 1:** Install pins `lmcache==0.5.3` + sibling vLLM; record versions to `g1_matched_env.json`.

**Step 2:** Smoke / blend wrappers (http 18080, 90s ready poll); collect tarball script.

**Step 3:** Pre-register Gate C/D/E in experiment-log; push; Stage A done.
