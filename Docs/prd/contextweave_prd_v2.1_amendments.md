# ContextWeave PRD amendments v2.1

**Date:** 14 October 2026  
**Status:** Binding for Phase 0–2 design until folded into a full PRD v2.1  
**Source:** Gemini review (`Docs/Reviews/Gemini_1.md`) + team acceptance  
**Supersedes:** conflicting text in `contextweave_prd_v2.md` where listed below

---

## A. Strategic (thin wedge)

**Amendment:** Phase 1 must report **intra-workload** variance separately from inter-workload variance.

- For each workload slice, compute the fraction of requests whose oracle-best config differs from the slice’s single best fixed config.
- H2 / G2 only count upside that is **predictable within a slice** (see §C). Offline “pick one config per model×task” is a pivot, not ContextWeave runtime.

---

## B. H3 → two-stage planning (fixes Gemini 2.1)

**Replace** the implication that Layer-1 key deviation is available in `/v1/cache/plan` before load.

**Stage 0 — pre-load (control plane):**  
Fingerprints (`FR-04`), cost model (§7.5 as amended), static `FR-14` calibration per `workload_slice_id`. May only select among configs whose risk is known offline, or tentatively select a reuse config subject to Stage 1 bailout.

**Stage 1 — in-flight bailout (data plane):**  
Pipeline early-layer compute with KV load. If measured Layer-1 (or agreed) deviation exceeds threshold, abort remaining cache load and fall back to full prefill from that layer, **charging wasted H2D/NVMe bandwidth** in the cost accounting.

Offline-only calibration without Stage 1 is allowed as an MVP; it must be labeled a **static slice policy**, not a per-request risk signal.

---

## C. Gate G2 oracle (fixes Gemini 2.2)

**Replace** unconstrained max quality over \(C_0\ldots C_6\).

**Oracle objective (latency under non-inferiority):**

\[
c^*(x)=\arg\min_{c\in\{C_0\ldots C_6\}}\mathrm{TTFT}(x,c)
\quad\text{s.t.}\quad
\mathrm{Quality}(x,c)\ge \mathrm{Quality}(x,C_0)-\epsilon
\]

Default \(\epsilon\): same absolute margin used at G3 (proposed 2 points) unless the owner pre-registers otherwise.

**Predictability bar at G2:** a cross-validated classifier on **pre-generation features only** (chunk lengths, positions, order, offline risk features; Layer-1 drift only if measured before commit in Stage 1 ablations) must capture **≥50%** of the oracle’s latency/quality upside vs best fixed config. Otherwise G2 fails even if the unconstrained oracle looks large.

Decoding: fixed seed / greedy or identical sampling seed across configs for paired comparisons.

---

## D. Cost model repair + paging (fixes Gemini 2.3)

**Repair time** is not \(r\cdot T_{\mathrm{prefill}}\) at peak TFLOP/s. Use roofline:

\[
T_{\mathrm{repair}}(r)\approx r\cdot T_{\mathrm{linear\_proj}}+\max\bigl(r\cdot T_{\mathrm{attn\_compute}},\, T_{\mathrm{HBM\_read}}(S_{KV})\bigr)
\]

Scattered repair reads the full preceding KV from HBM each layer.

**Block alignment:** cached chunk token lengths (after sink-prefix strip) must be multiples of the runtime KV block size (e.g. 16/64), or pad/mask tails. Record `kv_block_size` in fingerprints / `FR-03`.

**Phase 0 compute buffer:** raise planning assumption from ~200 to **350–400 GPU-hours** for Phase 0–1 debugging + multi-run baselines.

---

## E. Position storage (fixes Gemini 2.4)

**Do not** run a Phase 1 bake-off of pre-RoPE vs post-RoPE architectures.  
Store whatever LMCache / runtime exports (typically post-RoPE). Measure whether delta rotation can be **fused into H2D/copy** so it adds no extra HBM round-trip. Artifacts remain immutable via copy-on-load.

---

## F. HijackKV → Mode A only (fixes Gemini 2.5)

**Normative:** ContextWeave **never harvests** non-prefix KV slices from mid-prompt live user requests.

All non-prefix artifacts are built in **isolated canonical prefills**:  
`[canonical_sink_or_link_prefix + chunk_tokens]` under operator-controlled build context.

- HijackKV build-context poisoning is impossible by construction for non-prefix artifacts.
- `FR-13` sampled rebuild audit is reduced to **integrity / bit-rot / nondeterminism checks**, not poisoning detection.
- Opportunistic in-flight harvest remains out of scope (explicit non-goal).

---

## G. Gate G0 working-set (fixes Gemini 2.6)

**Additional G0 pass condition (with the existing share + median chunk rules):**

> At least 30% of post-prefix-cache prefill token volume is served by **chunk-cache hits** when simulating an LRU (or LFU) artifact cache capped at a declared host budget (defaults: **128 GB DRAM** and optionally **1 TB NVMe**), using the §7.5 bytes/token model. Median reusable unit length remains ≥ 512 tokens (or packed super-chunks meeting that length).

Unbounded recurrence alone is insufficient. Reports must show both:

1. Unconstrained recurrence share (upper bound)  
2. Budget-constrained hit share (G0 decision metric)

---

## H. Tokenizer boundaries (fixes Gemini 2.7)

**FR-02 / §8.6:** All strategies (\(C_0\) and \(C_2\ldots C_6\)) must use the same token-ID sequence.

- Tokenize **chunk-by-chunk** with a **canonical boundary delimiter** (default: `\n\n` as tokenizer-specific token id sequence, recorded in chunking config).
- Append boundary tokens to each segment **before** padding to `kv_block_size` (page alignment).
- Assemble prompts by **concatenating token IDs**, never by concatenating raw text then re-tokenizing the whole string.
- Record `boundary_token_ids` and `chunking_config_id` in content identity.

---

## I. Model selection (§6.1)

- Prefer **Qwen2.5 / Qwen3-8B** or **Mistral-7B-Instruct-v0.3** for first unscaled-RoPE Cases A/B.
- **Llama-3.1-8B-Instruct** uses `llama3` piecewise frequency scaling; still position-linear in \(m\) after \(\theta_i\) are fixed — standard \(\Delta\) rotation holds; Dynamic NTK / YaRN remain excluded until separately validated.
- Primary smoke model may be Qwen family when Llama HF gating blocks progress.

---

## J. API sketch (§15)

`/v1/cache/plan` request **must** include:

- `query_token_count` (or `query_token_ids` length)
- `workload_slice_id` (ties to `FR-14` calibration)

Optional later: `stage1_bailout_policy`.

---

## K. Gate G3 statistics

Use a **paired bootstrap** (or paired permutation test) over identical queries for \((\mathrm{planner}-\mathrm{full\ prefill})\) quality. Do not rely on unpaired CIs alone.

---

## Implementation pointers (repo)

| Amendment | Code / doc |
|---|---|
| G0 working-set | `analyze_trace.py --cache-budget-gb` (default on) |
| Repair roofline | `costmodel/breakeven.py` (`repair_time_roofline_s`, `max_tolerable_bailout_rate`) |
| Boundaries + block size | `tokenization/boundaries.py` (boundary **then** pad), generators |
| Mode A | `provenance/trust.py`, `Docs/fingerprints.md` |
| Gemini disposition | `Docs/Reviews/Gemini_1_response.md`, `Gemini_2_response.md`, `Gemini_3_response.md` |

---

# ContextWeave PRD amendments v2.1.1

**Date:** 14 October 2026  
**Status:** Binding clarifications on top of v2.1  
**Source:** Gemini reviews 2 & 3 (`Docs/Reviews/Gemini_2.md`, `Gemini_3.md`)

---

## Trap C — G2 oracle ε: per-request vs slice-aggregate

**Clarify §C:** default G3 ε of **2 points** is a **slice-aggregate** floor, not a per-request allowance.

- \(\epsilon_{\mathrm{req}}=0\) for binary metrics (EM, Pass@1, structured validity).
- \(\epsilon_{\mathrm{req}}=0.05\) (relative) for continuous token-level F1 unless pre-registered.
- \(\epsilon_{\mathrm{slice}}=2.0\) points on \(\mathbb{E}_x[\mathrm{Quality}]\).

**G2 predictability bar (matched slice quality):** let \(c_{\mathrm{fixed}}^*\) be the fastest fixed config within \(\epsilon_{\mathrm{slice}}\) of \(C_0\), and \(\hat{c}(x)\) a cross-validated pre-generation classifier calibrated to the same slice floor. Then:

\[
\mathrm{UpsideCaptured}=\frac{\mathrm{TTFT}_{p95}(c_{\mathrm{fixed}}^*)-\mathrm{TTFT}_{p95}(\hat{c})}{\mathrm{TTFT}_{p95}(c_{\mathrm{fixed}}^*)-\mathrm{TTFT}_{p95}(c^*)}\ge 0.50
\]

---

## Trap B — Stage-1 bailout penalty

**Add to §B / §D:** aborting after Stage 1 still pays partial load + check time:

\[
T_{\mathrm{expected}}(p_{\mathrm{bail}})=(1-p_{\mathrm{bail}})\,T_{\mathrm{reuse}}+p_{\mathrm{bail}}\bigl(T_{\mathrm{stage1\_check}}+\alpha_{\mathrm{load}}T_{\mathrm{load}}+T_{\mathrm{prefill}}\bigr)
\]

Maximum tolerable bailout rate:

\[
p_{\mathrm{bail}}^{\max}=\frac{T_{\mathrm{prefill}}-T_{\mathrm{reuse}}}{T_{\mathrm{prefill}}-T_{\mathrm{reuse}}+T_{\mathrm{stage1\_check}}+\alpha_{\mathrm{load}}T_{\mathrm{load}}}
\]

Default planning \(\alpha_{\mathrm{load}}\in[0.10,0.20]\). Implemented as `max_tolerable_bailout_rate()` in `breakeven.py`.

---

## Trap G — Finite prefix-cache budget

**Clarify §G:** native prefix caching is **not** infinite HBM. G0 analysis must simulate prefix cache under a declared GPU leftover budget (default **24 GB** HBM) with LRU eviction, alongside the chunk working-set budget (default **128 GB** host).

CLI: `--prefix-cache-budget-gb` (0 = unbounded, research-only).

---

## Boundary-then-pad (§H clarification)

Canonical segments **append** `boundary_token_ids` **then** pad to `kv_block_size` so each cached chunk starts on a page boundary when concatenated. Do **not** insert an unaligned 2-token shim between already-padded blocks.

---

## Mode A / RoPE hardenings

- Remove any `allowed_noncanonical` reuse bypass; non-canonical builds always fail validation.
- Phase 0/1 `rope_type` allowlist: `{"default", "llama3"}` only.
- Example / runtime position storage default: **post-RoPE** (§E).

---

## Research ingest — causal-closure quality bar (2026-10-20)

From desk review of SAFE-KV / ATTUNER / Irminsul (`Docs/Research/`). Binding for **G1 reporting**, not a new product module:

1. **Answer preservation:** every non-prefix reuse baseline reports answer agreement (or equivalent task metric) **vs full prefill** on a multi-hop / doc-dependent slice — TTFT alone is insufficient.
2. **Sink carve-out:** system / first-chunk preamble stays on exact prefix cache; chunk reuse applies only to movable non-prefix docs (aligns with Mode A + FR-02).
3. **ResolventKV:** deferred spectral causal-closure candidate — open only if G1 shows a residual gap after CacheBlend/EPIC. See `Docs/Research/ResolventKV-adoption.md`.
