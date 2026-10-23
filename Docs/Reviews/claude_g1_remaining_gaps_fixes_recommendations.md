# ContextWeave G1: Remaining Gaps, Fixes, and Recommendations

**Status of this doc:** Critical review of the Experiment Log through 2026-10-23.
**Audience:** The AI agent / engineer continuing the G1 work.
**Bottom line:** G1 should be relabeled **INCONCLUSIVE (mechanism not shown engaged)**, not "closed negative". The measurement harness is now trustworthy. The conclusions drawn from it are not yet supported.

---

## 1. What is solid vs. what is not

### Solid (trust these)
| Finding | Evidence |
|---|---|
| Native prefix caching works | ~2.6x cold vs warm at ~6k tokens; 23.6x warm vs reorder at 12k on vLLM 0.18.0 |
| Native reorder penalty is real | After harness fix: warm ~39-251 ms vs reorder ~650-1170 ms depending on scale/pin; `harness_ok True` |
| Harness pollution bugs were found and fixed | Self-hit on repeated reorder trials; unique salts; `reset_prefix_cache`; max_tokens=1; matched `enforce_eager`; CV reporting |
| Qwen3 meta-reasoning broke the first scorer | Fixed with `/no_think`, bigger max_tokens, span extraction |

### Not solid (do not cite as findings)
| Claim in log | Why it is unsupported |
|---|---|
| "CacheBlend G1 = quality OK / latency miss" | Blend reorder (948 ms) ≈ blend cold (953 ms) ≈ native miss (928 ms). That is **no reuse**, not slow reuse. |
| "Gate D PASS" | Vacuous. If nothing was reused, matching the control is expected. Quality only means something once reuse is proven. |
| "G1 EPIC closed (fair negative)" | Different model (Mistral), different vLLM (0.7.0), n=5, ~2000 chars filler (~500 tokens). The log's own earlier runs showed no native reorder gap at that scale. Toy-scale non-test. |
| Old 1.22x MP latency | Already voided (quality fail). Keep it out of every summary. |
| Any "matched pin" claim | Pre-registered pin was the vLLM 0.32 / lmcache 0.5.x era. Trusted run used vLLM 0.18.0 / lmcache 0.4.2 (Py3.13 workaround), pip-matched, not a Docker digest. |

---

## 2. Gap list (ordered by importance)

### GAP-1 (CRITICAL): No proof that blending engaged on reorder
- **Symptom:** blend reorder ≈ blend cold ≈ native miss. Warm ABC is slower than native warm (190 vs 39 ms), which is connector overhead with no reorder benefit.
- **Missing evidence:** no LMCache retrieved/hit-token counts, no vLLM `cached_tokens` in usage, no per-request blend recompute stats for the reorder requests.
- **Why it matters:** without this you cannot distinguish "blend ran and lost" (real negative) from "blend never fired" (fixable bug). These lead to opposite project decisions.
- **Napkin check supporting "should have worked":** Qwen3-8B KV ≈ 144 KB/token (36 layers × 8 KV heads × 128 dim × 2 (K,V) × 2 bytes). 12k tokens ≈ 1.8 GB. Measured load overhead ≈ 150 ms (190 − 39). Add ~15% recompute (~140 ms). Expected blend reorder ≈ 300 ms vs ~930 ms full prefill. Observed 948 ms. A gap this large means the mechanism is not engaging.

### GAP-2 (CRITICAL): Quality gate is not conditional on reuse
- Gate D passed while reuse was absent. The pattern across runs is suspicious: when latency looked good (old 1.22x), outputs were garbage; when outputs were fine, nothing was reused. Hypothesis (untested): blend only "speeds up" when it corrupts decode.
- Gate D must be re-run only on a configuration where retrieved-token stats prove reuse happened.

### GAP-3 (HIGH): EPIC tested at a scale where no gap exists
- ~500-token prompts: prefill is dominated by fixed overhead, and LegoLink recompute overhead cannot pay off.
- The EPIC fork also differs in model and vLLM version, so it is not comparable to the CacheBlend runs.

### GAP-4 (HIGH): Pin drift and no digest-matched run
- Record exactly what ran: image/pip versions, `pip freeze`, CUDA, driver, Python. The post-remediation run is the only trusted CacheBlend data point (one pin, one scale, one model, one config).

### GAP-5 (MEDIUM): Statistical thinness
- n=10 with one scale (12k) and one workload shape. No variance across different document sets, no different chunk counts (3 docs only).
- Gate E threshold (≥15% faster) was pre-registered, which is good, but there is no effect-size interval reported.

### GAP-6 (MEDIUM): Project impact of a real negative was never written down
- The runbook asked for this to be decided before the run. It was not. Decide it now (see section 6) so a negative result does not get rationalized after the fact.

### GAP-7 (LOW): Log hygiene
- "Closed" was written, then reopened, multiple times. Entries are out of chronological order in places. Voided results sit next to valid ones.
- Add a status field per entry: `VALID | VOIDED | CONFOUNDED | INCONCLUSIVE`.

---

## 3. Fixes (concrete)

### FIX-1: Add engagement instrumentation (do this first, CPU-testable parts offline)
For every reorder request, record:
1. vLLM `usage.prompt_tokens_details.cached_tokens` (or equivalent from the response/metrics endpoint).
2. LMCache retrieved/hit token counts per request (server logs or metrics endpoint; confirm the exact metric names in the pinned lmcache version before the session, and write them in the log).
3. Blend-specific: number of chunks matched, tokens recomputed vs reused, if exposed.
4. Fail-fast assertion: if blend reorder `retrieved_tokens < 50%` of non-prefix tokens, mark the run `ENGAGEMENT_FAIL` and **skip Gate D/E interpretation** (still save data).

### FIX-2: Chunk and boundary alignment audit (probable root cause candidates)
Check each of these on the reorder prompts; log pass/fail:
- Chunk boundaries align to LMCache chunk size (256 tokens) **after tokenization**, not just in characters. Token-count each doc chunk and pad/trim to exact multiples.
- Separator token sequence is identical in seeding and reorder prompts (` # # ` join must tokenize identically in context; verify by tokenizing the full prompt and comparing per-chunk token ids).
- Per-chunk hash inputs are identical regardless of position. Verify that the hash of chunk B at position 1 equals the hash of chunk B at position 0 (no leading context included in the hash).
- BOS/leading-token handling: first chunk differs from others by BOS; make sure reorder doesn't put a non-first chunk where a BOS-prefixed chunk is expected.
- Blend config: recompute ratio, which layer(s) are used for selecting tokens to recompute, and whether blending is actually enabled in the server **and** the connector (both sides).
- Model is eligible: confirm the pinned LMCache blend path supports Qwen3 (RoPE re-application for position shift). If it only supports llama-family, that explains "no reuse" and suggests testing with a supported model.

### FIX-3: Control that proves reuse (new gate, "Gate R")
Add a gate before D/E:
- **Gate R (reuse proven):** on reorder requests, retrieved tokens ≥ 70% of the chunk tokens AND TTFT drops below native reorder p50 by any margin. If R fails, report `NO_REUSE` and stop the quality/latency claims.
- Then Gate D (quality vs control with reuse active), then Gate E (≥15% faster than native reorder).

### FIX-4: Reframe EPIC test
- Do not call EPIC closed. Mark as `INCONCLUSIVE (toy scale)`.
- If rerun: same Mistral/Llama-family model, filler sized to ≥6k tokens (≥12k preferred), n≥10, native reorder baseline measured **on the same vLLM 0.7.0 stack**, and recompute ratio swept at most over 2 values (e.g. 8 and 16) with the pre-registered primary value declared first.
- Only run EPIC if CacheBlend diagnostic (below) still leaves the question open, to avoid sprawl.

### FIX-5: Reproducibility artifacts
- Save in the repo for every GPU session: `pip freeze`, `nvidia-smi`, full server logs, exact commands, raw per-trial TTFT arrays (not just p50), and the per-request engagement stats from FIX-1.
- Commit JSON + log to `artifacts/<date>-<name>/` and reference it from the log entry.

### FIX-6: Log schema
Add to the template:
```
- Status: VALID | VOIDED | CONFOUNDED | INCONCLUSIVE
- Engagement evidence: retrieved/cached tokens on reorder (numbers)
- Supersedes: <entry title or none>
```
Add a one-line "Current verdict" block at the top of the log, updated whenever a verdict changes.

---

## 4. Next GPU session: single diagnostic (recommended)

**Name:** G1-DIAG: Does blend engage on reorder?
**Time cap:** 60 minutes. **One question only.**

1. Use the same pinned stack as the last trusted run (vLLM 0.18.0 / lmcache 0.4.2) to avoid new variables. Record the freeze.
2. Smoke (Gate B).
3. Control (Gate C) quickly, same as before.
4. Blend on, 12k, chunk_sep format, **with FIX-1 instrumentation and FIX-2 alignment verified offline first**.
5. Run 10 reorder trials (salted so no self-hits). For each: TTFT, `cached_tokens`, LMCache retrieved tokens.
6. Report the table and apply Gate R.

**Outcomes and decisions (pre-registered):**
| Outcome | Meaning | Next step |
|---|---|---|
| Retrieved ≈ 0 on reorder | Config/alignment/harness bug, **not** an algorithm result | Fix per FIX-2 / client blender hooks (`register_model` #4131, MP vs in-worker), re-run diagnostic once. Qwen3 adapter is present on lmcache 0.4.2 — do not switch models for “support” |
| Retrieved high, TTFT still ≈ native miss | Reuse happens but overhead eats the gain (or recompute ratio too high) | Log as a real negative at this scale; run one sweep of recompute ratio, then close |
| Retrieved high, TTFT better, quality fails | Matches the earlier "speed only when corrupting" hypothesis | Real quality negative for this config; evaluate recompute ratio tradeoff curve |
| Retrieved high, TTFT ≥15% better, quality OK | Gate R/D/E pass | G1 CacheBlend provisional PASS; scale n, doc sets, longer contexts |

**Do not:** open EPIC, change models, sweep multiple parameters, or touch ResolventKV in this session.

---

## 5. Recommendations

1. **Relabel now (free, offline):** update the log's verdict to `INCONCLUSIVE: engagement unproven`. Mark pre-remediation Gate D/E and the EPIC "closed" entry accordingly.
2. **Do FIX-1 and FIX-2 before renting any GPU.** Most of the alignment audit (tokenization, chunk multiples, hash invariance) can run on CPU with just the tokenizer.
3. **One question per GPU session.** The sprawl (multiple pins, models, methods) is what produced the voided results. G1-DIAG answers one thing.
4. **Qwen3 support confirmed for G1-DIAG (2026-10-23).** lmcache `v0.4.2` includes `LMCQwen3Model` (PR [#1633](https://github.com/LMCache/LMCache/pull/1633) / issue [#1121](https://github.com/LMCache/LMCache/issues/1121)). Keep `Qwen/Qwen3-8B`; if Gate R fails, debug harness engagement, not model eligibility.
5. **Report intervals, not just p50.** Report p50/p90, min/max, CV. With n=10 an effect needs to be large to claim.
6. **Do not open ResolventKV kernels** until a non-prefix path shows a verified, quality-preserving win, as the log already says.
7. **Budget awareness:** Phase 0 GPU planning buffer is 350-400 hours. A single 60-minute diagnostic is cheap relative to that; the cost of another ambiguous run is the real risk, so insist on engagement proof first.

---

## 6. Decide now: what a real negative means for the project

Filled **2026-10-23 before G1-DIAG** (do not edit after the diagnostic runs):

- If CacheBlend and EPIC both show verified-engaged reuse with no latency win at ≥12k on A100:
  - [x] Pivot to: fingerprint/provenance + cost-model / planner desk work; optional later
    longer-context or different-hardware PIC probe **outside** G1 closeout
  - [x] Continue to ResolventKV only if: a non-prefix path shows **verified engagement +
    quality-preserving ≥15% TTFT win** at ≥12k (or documented equivalent scale)
  - [x] Stop/report negative result: **yes** for “PIC wins TTFT on A100 @12k on these pins”
- If quality fails when reuse is engaged:
  - [x] Treat as: **real quality negative** for that config; at most one pre-registered
    recompute-ratio tradeoff curve; do **not** open ResolventKV to “fix” quality

---

## 7. Checklist (copy into the next log entry)

- [x] Log verdict relabeled to INCONCLUSIVE; status fields added
- [x] Engagement instrumentation implemented and tested on CPU where possible
- [x] Token-level chunk alignment + hash invariance verified offline (FakeTok; re-run with `--model` on GPU host)
- [x] Blend support for the chosen model confirmed from source/docs (link recorded) —
  lmcache `v0.4.2` `LMCQwen3Model` via PR [#1633](https://github.com/LMCache/LMCache/pull/1633);
  see experiment-log 2026-10-23 Qwen3 entry
- [ ] Exact pin recorded (`pip freeze`) before launch — confirm `g1_diag_pip_freeze.txt` in artifacts
- [x] Gate R added and pre-registered outcomes written
- [x] Section 6 decision filled in
- [ ] GPU session capped at 60 min, instance terminated, artifacts committed
- [x] G1-DIAG #1: Gate R `ENGAGEMENT_FAIL` got=0 (2026-10-23)
- [x] Harness fix: in-process `LMCacheConnectorV1` + `register_model` (`g1_blend_hooks.py`)
- [ ] G1-DIAG #2 re-run (Gate R); collect tarball before stop
