# ContextWeave Phase 0/1: Post-Archive Critical Review and Recommendations

**Based on:** Experiment Log through 2026-10-24 (tag `v0.1.0-phase01-archive`)
**Audience:** The engineer / AI agent holding the repo.
**Purpose:** Say which verdicts are solid, which labels overstate the evidence, what is still unresolved, and what (if anything) to do next.

---

## 0. TL;DR

- The process is good: pre-registrations, voided results flagged, negative results banked, harness bugs found and fixed. That discipline is the most valuable thing the project produced.
- "C1 else C0" as the archive verdict is fair. But **several PASS/FAIL labels overstate the evidence**: H4 FAIL (the test was misspecified), FP gates PASS (self-authored conformance tests, not security evidence), and the CacheBlend closure (rests on a heavily shimmed stack).
- **Biggest unresolved question:** your EPIC and CacheBlend quality numbers (C3 mean_q 0.70 and 0.50; CacheBlend 0.67) look far worse than published accuracy claims for these methods, on simple single-fact lookups. That gap is unexplained and may be a harness/prompt artifact. Do not publish "PIC loses quality" without scoping it or resolving it.
- **Recommendation:** stop opening lanes. Do the free offline fixes (section 4, R1-R3), optionally one capped fidelity session (R4), then write a short, scoped negative-results report (R5).

---

## 1. State at a glance

| Item | Log verdict | Evidence strength (my read) |
|---|---|---|
| G0 (non-prefix share ~75%) | Provisional PASS | **Weak.** Synthetic + own-corpus replay, simulated request mix, chars/4 tokens, no real partner trace. The motivating premise was never validated on real traffic. |
| Native prefix cache works; reorder gap is real | PASS | **Strong.** Harness fixed (self-hits, resets, salts), n=10, several scales/pins, 4-24x gaps. |
| CacheBlend (lmcache 0.4.2 / vLLM 0.18, in-process) | Closed negative: quality 0.67 when engaged, ~1.10x mean TTFT | **Medium-weak.** See 2.6. |
| EPIC @12k latency | PASS, 3.84x (city); 1.98-3.86x multi-fact | **Medium.** Real speedup, but one fork/model, synthetic needle tasks. |
| EPIC quality (Phase 1 G2) | FAIL: C3 q=0.70 vs C0 1.0 (N=20) | **Medium.** Direction consistent across suites; N small; discrepancy with literature unexplained (2.2). |
| H3 order / slice / keydev predictors | In-sample PASS, GPU confirms FAIL | **Medium.** Shows instability; N=12-20 can't support a predictor either way. |
| H4 cost model | FAIL (rel err ~0.60) | **Misleading.** See 2.4. |
| FP provenance / poison (8/8) / fault (7/7) | PASS | **Conformance only.** See 2.5. |
| Planner "C1 else C0" | Shipped | Equals default vLLM behavior (2.7). |

---

## 2. Issues (ordered roughly by importance)

### 2.1 The EPIC quality "PASS" was order-blind (process lesson)
- The multi-fact quality lane passed (contains 1.0/1.0), which helped justify the Phase 1 GO. Then the oracle run, which actually permuted chunk order, gave C3 q=0.70.
- A quality gate for non-prefix reuse that does not permute chunk order doesn't test the thing non-prefix reuse is for.
- **Fix (process):** any PIC quality gate must cover **all chunk permutations and at least 2 filler seeds**. Add this to the log template (section 6).

### 2.2 Results diverge from published claims; harness suspicion not ruled out
- EPIC (LegoLink-8) recomputes only a few tokens per chunk. Failing 30-50% of simple single-fact lookups is a much larger loss than I'd expect from a method published as quality-preserving. I can't verify the papers' exact numbers from here, so check them; treat the discrepancy as a flag, not a conclusion.
- Candidate harness/implementation causes to rule out:
  - Python-overlay on a prebuilt vLLM 0.7.0 wheel (not the authors' full build).
  - Prompt layout: where the question sits, chunk separators, BOS handling, Mistral chat template, how the answer is extracted.
  - Chunk boundary alignment and position handling after reorder.
- CacheBlend has the same flavor: in-process path needed 4 compat patches (attention import shim, flashinfer sparse shim, `ConstantList` lookup patch, `get_input_embeddings` alias), and engagement was asymmetric: BAC cached 7705 of 11520 tokens, CBA cached 19. That asymmetry is unexplained (suspect hash/position/first-chunk handling).
- **Why it matters:** if the cause is the harness, "PIC loses quality" is a harness result, not an algorithm result.

### 2.3 The H3 chain looks like fitting noise
- Order rule: in-sample precision 1.0, GPU confirm 0.5; the failing cells inverted between suites.
- Slice calibration: LOO 1.0 in-sample, GPU 0.33 on a new filler seed with the *same golds*. Cells flipped both ways (ABC/city 1→0, CAB/CBA code 0→1).
- Keydev: isolated-seam scores were order-tied and untrainable.
- Reading: per-request C3 correctness is driven by something other than order or fact type (filler content, seed, token alignment). With N=12-20, any in-sample 1.0 is expected overfitting, and LOO within the same filler is not an independent test.
- **Takeaway:** "no input-side predictor transferred" is the finding. Stop building predictors.

### 2.4 The H4 test was misspecified
- The default 450 TFLOP/s exceeds A100 dense bf16 peak (about 312 TFLOP/s), so a large error was guaranteed before any data was collected.
- Measured effective throughput (~182 TFLOP/s) is about 58% of 312, a normal prefill utilization.
- The calibrated seed-100 error (~2.9%) is encouraging but calibrated on the same hardware and workload family, so it's not independent confirmation.
- **Fix (CPU, ~10 min):** new pre-reg with peak = 312 and an MFU prior range fixed before looking (e.g. 40-65%). Report whether measured values land in range. Mark the old entry `misspecified, superseded`.

### 2.5 The FP gates are conformance tests, not security evidence
- The poison suite (8/8) and fault suite (7/7) were written by the same author as the code, for attack classes the author thought of. They show the refusal logic behaves as implemented.
- The planner refuses C3 by default, so these gates currently protect a disabled path.
- **Fix:** relabel as "implementation conformance (self-authored)". If you want to claim more, get an independent red-team of the provenance schema (another reviewer or model) before saying "validated".

### 2.6 CacheBlend closure caveats
- Quality 0.67 on a small suite (the log doesn't state N; record it). Recompute ratio was never swept (skipped by decision). Stack depends on shims (2.2).
- The closure text already says "this config". Keep that scope everywhere. Don't generalize to "CacheBlend doesn't work".

### 2.7 The planner adds little
- "C1 if prefix else C0" is what vLLM already does. The planner's real content is the refusal logic for hypothetical C3/C4. Say so plainly in any summary.

### 2.8 Evidence hygiene
- DIAG #1 artifacts were lost (reconstructed from chat paste). Don't cite that run as primary evidence.
- On 2026-10-23 the pause was lifted roughly six times, each lane individually justified (EPIC@12k, EPIC quality, Phase 1 oracle, H3 confirm, slice-cal, keydev). Together that is the treadmill the log itself warns about.
- N is 12-20 almost everywhere and often missing from entries.

---

## 3. What you can and cannot claim

### Can claim (with setup stated)
- On A100-40GB, Qwen3-8B, vLLM 0.18 + lmcache 0.4.2 in-process blend at ~12k tokens (chunk_sep): reorder reuse engaged partially (BAC 7705/11520 tokens, CBA ~0), mean TTFT about 1.10x vs native miss, quality 0.67 on the needle suite.
- On Mistral-7B with the EPIC LegoLink-8 Python overlay on vLLM 0.7.0 at ~12k tokens: TTFT 2-3.9x vs full prefill; C3 mean quality 0.70 (N=20) and 0.50 (N=12) on synthetic needle tasks under reorder.
- Neither order nor (order, fact-type) predictors transferred across filler seeds in these suites.
- Harness lessons: self-hit pollution of reorder trials, scorer pitfalls with Qwen3 thinking output, version ABI mismatches between lmcache and vLLM, lost artifacts when sessions stop early.

### Cannot claim
- That CacheBlend or EPIC fail in general, or that the quality loss is inherent to the methods (vs. this harness).
- That the cost model fails (H4 was misspecified).
- That the provenance gate is secure.
- That non-prefix reuse has no value on real RAG traffic (G0 was never validated on real traces).
- That the planner improves on default behavior.

---

## 4. Recommendations

### R1 (free, now): fix the labels
- Update the log: H4 → `misspecified, superseded`; FP suites → `implementation conformance (self-authored)`; EPIC quality lane → add "order-blind; superseded by Phase 1 oracle"; CacheBlend closure → add scope note and shim list; add N to each entry.
- Add a **Final verdict** paragraph at the top using the scoped claims in section 3.

### R2 (free, CPU): redo H4 correctly
- New pre-reg with A100 peak 312 TFLOP/s and a fixed MFU prior range. Re-evaluate on banked data. Report in/out of range. No GPU needed.

### R3 (free): template and standards
- Add to every future entry: N cases, seeds, chunk orders covered, shims/patches applied, artifacts collected (yes/no).

### R4 (optional, one GPU session, 90-minute cap): EPIC fidelity check
Only do this if you want the discrepancy in 2.2 resolved. One question: **is the quality loss the algorithm or my harness?**
1. Run the EPIC authors' demo/eval example exactly as shipped (their model, their prompt layout, their data) on your overlay stack. Record accuracy.
2. Run your needle suite using the authors' prompt layout (question placement, separators, template).
3. Compare against your existing harness result.

Pre-registered outcomes (decide now, treat as terminal):
| Outcome | Meaning | Next |
|---|---|---|
| Authors' example is accurate, your suite with their layout is accurate, yours is not | Your prompt/harness is the problem | Fix harness, re-run G2 once, then close either way |
| Authors' example is accurate, your suite with their layout still fails | Task or implementation difference; real quality gap on your workload | Report as workload-specific negative; close |
| Authors' example also degrades | Overlay implementation or stack is not faithful | Report as unreproducible on this stack; close |

Do not open CacheBlend, new models, predictors, or ResolventKV in this session.

### R5: write a short, scoped negative-results report (2-4 pages)
Contents: setup and stacks; results table (latency, quality, N, seeds, orders); the harness pitfalls list; what is unresolved (2.2); explicit "cannot claim" list. The harness-pitfalls section is probably the most reusable part for other people.

### R6: stopping rule
No new lane unless all three hold:
1. A pre-registered question whose answer changes a decision.
2. Quality gates permute chunk order and use at least 2 seeds; engagement is measured (retrieved/cached tokens).
3. A hard cap: at most one more GPU session in total unless R4 uncovers a harness bug.

### R7 (optional, CPU, no failed assumptions): canonical chunk ordering
If the goal is product value, not research: a way to get "non-prefix" requests to behave like prefix requests without any PIC quality risk is to canonicalize retrieved-chunk order (e.g. stable sort by document id) so shared chunks form shared prefixes.
- Use your existing G0 simulator to measure how much the prefix hit rate rises on the synthetic and own-corpus workloads. This is CPU-only.
- Caveat: reordering can change answer quality through position bias in the model, so any gain needs a quality check against original order (C0) before it counts. Verify, don't assume.

---

## 5. Decision checkpoint (fill in before doing anything else)

What is this project for?
- [ ] A research writeup (then R1, R2, R5, and optionally R4)
- [ ] A product / planner people would use (then R7 first; the current planner has no edge over default)
- [ ] A learning exercise (it has already paid off; archive, write R5, move on)

Opportunity cost note: each additional lane costs GPU time plus attention, and the last 15 or so sessions produced one clear structural result (non-prefix reuse is risky and hard to predict) plus harness knowledge. A stop is cheaper than another lane unless R4 or R7 answers a specific question.

---

## 6. Template additions

```
## YYYY-MM-DD: <title>
- Status: VALID | VOIDED | CONFOUNDED | INCONCLUSIVE | MISSPECIFIED
- Hypothesis / gate:
- Environment (CPU/GPU, drivers, pins, shims/patches applied):
- N cases / seeds / chunk orders covered:
- Engagement evidence: retrieved/cached tokens on reorder (or none)
- Command:
- Result:
- Artifacts collected before stop: yes/no (path)
- Decision:
- Supersedes: <entry or none>
```
