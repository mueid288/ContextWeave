Reviewing `contextweave_prd_v2.1_amendments.md` and `Gemini_1_response.md` alongside the full codebase in `Context Weave.zip` shows that your **normative specification in `v2.1` is tight**, but there are **six places where the Python code directly violates the new `v2.1` rules**, plus **three subtle mathematical traps inside `contextweave_prd_v2.1_amendments.md` itself** that need to be tightened before Phase 1.

---

## Part 1: Spec-to-Code Contradictions (`v2.1` Amendments vs. Repo Code)

### 1.1 The Boundary Delimiter Destroys 16-Token Block Alignment (§D & §H vs. `boundaries.py`)

* **What `v2.1` (§D & §H) mandates:** Cached chunk token lengths must be multiples of `kv_block_size` (e.g., 16) so paged KV blocks align, and prompts must be assembled by concatenating token IDs with `boundary_token_ids` (default `(198, 198)`, length 2) between prefix, chunks, and query.


* **What `src/contextweave/tokenization/boundaries.py` actually does:**
In `assemble_prompt_token_ids()`:


```python
for i, chunk in enumerate(chunk_token_ids):
    if i > 0 or (prefix_token_ids and chunk):
        if i == 0 and prefix_token_ids:
            out.extend(cfg.boundary_token_ids)
        elif i > 0:
            out.extend(cfg.boundary_token_ids)
    body = list(chunk)
    if cfg.pad_to_block:
        body = pad_token_ids_to_block(body, cfg.kv_block_size)
    out.extend(body)

```


* **Why this breaks PagedAttention block alignment:**
Suppose `prefix_token_ids` is 256 tokens (aligned to $16 \times 16$) and each chunk `body` is padded to 512 tokens ($32 \times 16$). Because `assemble_prompt_token_ids` inserts **2 boundary tokens** `(198, 198)` *between* the 16-aligned chunks:


* `prefix` occupies indices `[0 .. 255]`
* `boundary_0` occupies `[256, 257]`
* `Chunk 0` starts at index **`258`** ($258 \equiv 2 \pmod{16}$) and ends at `769`!
* `boundary_1` occupies `[770, 771]`
* `Chunk 1` starts at index **`772`** ($772 \equiv 4 \pmod{16}$)!
Every single chunk in the prompt is shifted off the physical 16-token page grid by $+2(i+1) \pmod{16}$ tokens. A paged runtime (vLLM / SGLang / LMCache) cannot map pre-built KV pages into a page table when the chunk starts at offset 2 or 4 inside a physical page!


* **The Fix:** The canonical boundary delimiter (`\n\n`) **must be appended to the chunk (and prefix) *before* padding/aligning to `kv_block_size = 16**`, not inserted as an unaligned 2-token shim between already-aligned blocks:
```python
def canonicalize_chunk_tokens(
    chunk_token_ids: list[int],
    cfg: ChunkingConfig,
) -> list[int]:
    """Append canonical trailing boundary tokens, then pad to kv_block_size."""
    tokens = list(chunk_token_ids) + list(cfg.boundary_token_ids)
    if cfg.pad_to_block:
        tokens = pad_token_ids_to_block(tokens, cfg.kv_block_size)
    return tokens

```


When each prefix and chunk includes its trailing delimiter *inside* its 16-token-aligned block, `Chunk 0` starts at `256` ($0 \pmod{16}$), `Chunk 1` starts at `768` ($0 \pmod{16}$), and physical KV pages concatenate with zero shift.

### 1.2 Dynamic NTK and YaRN Are Excluded in §I, but Allowed in `validate.py`

* **What `v2.1` (§I) mandates:** *"Dynamic NTK / YaRN remain excluded until separately validated."*

* **What `src/contextweave/fingerprints/validate.py` (line 48) does:**
```python
if fp.rope.rope_type not in {"default", "llama3", "linear", "dynamic", "yarn"}:

```


It explicitly validates `"dynamic"`, `"yarn"`, and `"linear"` as `ValidationStatus.VALIDATED`!


* **Also in `configs/models/llama31_8b_instruct.yaml`:** The YAML note still says *"rope_scaling.rope_type=llama3 with factor 8 means Case B (constant position shift) may not hold"*, contradicting `v2.1` §I which notes that `llama3` scaling is position-linear in $m$ after $\theta_i$ are fixed.


* **The Fix:** Restrict `validate.py` line 48 to `{"default", "llama3"}`, and update the note in `configs/models/llama31_8b_instruct.yaml`.



### 1.3 Mode A Is Normative in §F, but `schema.py` & `validate.py` Keep a Non-Canonical Backdoor

* **What `v2.1` (§F) mandates:** *"Normative: ContextWeave never harvests non-prefix KV slices from mid-prompt live user requests. All non-prefix artifacts are built in isolated canonical prefills."*

* **What `schema.py` and `validate.py` do:**
`BuildContextFingerprint` in `src/contextweave/fingerprints/schema.py` still defines `allowed_noncanonical: bool = False` and `policy_allows_reuse()` returns `self.canonical or self.allowed_noncanonical`. And `validate.py` (lines 83–90) skips the `build_context_hash_mismatch` check whenever `request.build_context.allowed_noncanonical` is `True`!


* **The Fix:** Remove `allowed_noncanonical` from `BuildContextFingerprint` (or hard-fail `validate_artifact_fingerprint` whenever `not fp.build_context.canonical`) so the schema enforces Amendment §F without a bypass flag.



### 1.4 Pre-RoPE Bake-Off Is Dropped in §E, but `fingerprint_example.py` Defaults to `PRE_ROPE`

* **What `v2.1` (§E) mandates:** *"Do not run a Phase 1 bake-off of pre-RoPE vs post-RoPE architectures. Store whatever LMCache / runtime exports (typically post-RoPE)."*

* **What `src/contextweave/cli/fingerprint_example.py` (line 92) does:**
It hardcodes `position_storage_mode=PositionStorageMode.PRE_ROPE`, which also pollutes `benchmarks/reports/example_fingerprint_qwen3.json` and `example_fingerprint_llama31.json` with `"pre_rope_keys"`. Change this default to `PositionStorageMode.POST_ROPE`.



### 1.5 Working-Set Gate Is Mandatory in §G, but Opt-In Across the CLI & Missing in 4 Reports

* **What `v2.1` (§G) mandates:** *"Unbounded recurrence alone is insufficient. Reports must show both: 1. Unconstrained recurrence share (upper bound) 2. Budget-constrained hit share (G0 decision metric)."*

* **What the CLI and reports do:**
1. `evaluate_g0()` in `metrics.py` defaults to `require_working_set: bool = False`.


2. `cli/analyze_trace.py` makes `--require-working-set` an opt-in flag (`action="store_true"`).


3. `cli/import_trace.py` doesn't instantiate `WorkingSetConfig` at all when `--analyze` is passed.


4. As a result, `g0_synthetic_rag_default.md`, `g0_synthetic_rag_longctx.md`, `g0_corpus_replay.md`, and `g0_imported_sample.md` in `benchmarks/reports/` **do not contain the Working-Set table at all**!




* **The Fix:** Default `require_working_set=True` in `evaluate_g0()`, default `working_set_cfg=WorkingSetConfig.from_gb(128.0)` in `analyze_trace()` and `import_trace.py`, and regenerate all reports in `benchmarks/reports/`.



### 1.6 `breakeven.py` Contradicts the §D Roofline Formula

* **What `v2.1` (§D) states:**

$$T_{\mathrm{repair}}(r) \approx r \cdot T_{\mathrm{linear\_proj}} + \max\bigl(r \cdot T_{\mathrm{attn\_compute}},\, T_{\mathrm{HBM\_read}}(S_{KV})\bigr)$$



* **What `src/contextweave/costmodel/breakeven.py` does:**
As detailed in my code audit, `repair_time_roofline_s()` divides **both** `t_linear` and `t_attn` by `repair_tflop_efficiency = 0.25` and hardcodes `attn_share = 0.40` across all context lengths $N$. Dividing dense linear projections by `0.25` makes 15% repair take **60% of full prefill time** (`5.63 s` vs `9.38 s` at 100k tokens in `cost_model_8b.json`). Apply the exact separated linear + attention roofline formula from my previous review so `breakeven.py` matches §D.



---

## Part 2: Three Subtle Traps Inside `contextweave_prd_v2.1_amendments.md`

Even after fixing the Python code above, `contextweave_prd_v2.1_amendments.md` has three specification traps in **§C, §B, and §G** that will cause trouble when you run Phase 0A/1 experiments.

### Trap 1: Per-Request $\epsilon$ vs. Dataset-Aggregate $\epsilon$ in the G2 Oracle (§C)

Look at the oracle definition in **§C**:


$$c^*(x)=\arg\min_{c\in\{C_0\ldots C_6\}}\mathrm{TTFT}(x,c) \quad\text{s.t.}\quad \mathrm{Quality}(x,c)\ge \mathrm{Quality}(x,C_0)-\epsilon$$

> *"Default $\epsilon$: same absolute margin used at G3 (proposed 2 points) unless the owner pre-registers otherwise."*
> 

**Why this breaks on per-request metrics:**

* At Gate G3, a **2-point margin** ($\epsilon = 0.02$ on a $[0, 1]$ scale) is an **aggregate dataset expectation**: $\mathbb{E}_x[\mathrm{Quality}(x, \pi(x))] \ge \mathbb{E}_x[\mathrm{Quality}(x, C_0)] - 0.02$.


* On a **single request $x$**, Exact Match (EM), Code Pass@1, and Structured-Output Validity are **binary** ($\{0, 100\}$ points). Even token-level F1 on a 4-word answer jumps in discrete steps of $25$ points ($0, 25, 50, 75, 100$).


* Therefore, setting $\epsilon = 2\text{ points}$ at the *individual request level* forces $\mathrm{Quality}(x, c) = \mathrm{Quality}(x, C_0)$ (zero degradation allowed on any single query), whereas the best fixed configuration $c_{\text{fixed}}^*$ at G3 is allowed to lose 100 points on 2% of queries (averaging $-2.0$ points across the slice)!
* Furthermore, §C says the cross-validated classifier must *"capture $\ge 50\%$ of the oracle's latency/quality upside vs best fixed config"*, without defining how a 2D (latency, quality) tuple is scalarized into a single percentage.



**How to tighten §C in `contextweave_prd_v2.1_amendments.md`:**

1. Distinguish **per-request oracle tolerance** ($\epsilon_{\text{req}} = 0$ for binary metrics; $\epsilon_{\text{req}} = 0.05$ for continuous F1) from the **slice-aggregate quality floor** ($\epsilon_{\text{slice}} = 2.0\text{ points}$).
2. Define the **G2 Predictability Bar** explicitly at matched slice quality:
Let $c_{\text{fixed}}^*$ be the fastest single fixed config whose slice-average quality is within $\epsilon_{\text{slice}}$ of $C_0$, and let $\hat{c}(x)$ be the cross-validated pre-generation classifier calibrated to the same slice-average quality floor ($\mathbb{E}[\mathrm{Quality}(x, \hat{c}(x))] \ge \mathbb{E}[\mathrm{Quality}(x, C_0)] - \epsilon_{\text{slice}}$). Then G2 requires:

$$\text{Upside Captured} = \frac{\mathrm{TTFT}_{p95}(c_{\text{fixed}}^*) - \mathrm{TTFT}_{p95}(\hat{c})}{\mathrm{TTFT}_{p95}(c_{\text{fixed}}^*) - \mathrm{TTFT}_{p95}(c^*)} \ge 0.50$$



### Trap 2: Missing Stage-1 Bailout Penalty Formula in §B & §D

In **§B**, you state:

> *"If measured Layer-1 (or agreed) deviation exceeds threshold, abort remaining cache load and fall back to full prefill from that layer, **charging wasted H2D/NVMe bandwidth** in the cost accounting."*
> 

Right now, neither §D nor `breakeven.py` includes the equation for that wasted bandwidth. Because PCIe/NVMe asynchronous DMA streams ahead of Layer-1 compute, aborting after Layer 1 still transfers a fraction $\alpha_{\text{load}} \in [1/L, 1]$ of $S_{KV}$ (typically $10\%\text{–}20\%$ of total KV bytes before the DMA queue drains) plus incurs $T_{\text{stage1\_check}}$ before restarting full prefill.

Add this explicit break-even condition to **§B / §D** and `breakeven.py`:


$$T_{\text{expected}}(p_{\text{bail}}) = (1 - p_{\text{bail}})\,T_{\text{reuse}} + p_{\text{bail}}\bigl(T_{\text{stage1\_check}} + \alpha_{\text{load}} T_{\text{load}} + T_{\text{prefill}}\bigr) < T_{\text{prefill}}$$


which yields the **maximum tolerable Stage-1 bailout rate**:


$$p_{\text{bail}}^{\max} = \frac{T_{\text{prefill}} - T_{\text{reuse}}}{T_{\text{prefill}} - T_{\text{reuse}} + T_{\text{stage1\_check}} + \alpha_{\text{load}} T_{\text{load}}}$$


If a workload slice triggers Stage-1 bailouts more frequently than $p_{\text{bail}}^{\max}$, Stage 0 must route the slice directly to $C_0$.

### Trap 3: Infinite-Memory Prefix Cache vs. Finite-Memory Chunk Cache in §G

In `src/contextweave/trace_analysis/prefix_cache.py`, `PrefixCacheSimulator` inserts every full prompt into an **unbounded in-memory trie** (`_roots`) that never evicts anything.

* In a synthetic 300-request trace, this barely matters.


* In a real production partner trace (e.g., 50,000 requests over 24 hours), an unbounded trie assumes the baseline vLLM server has **infinite GPU HBM** to hold every historical prompt prefix forever. In reality, vLLM's prefix cache lives in leftover GPU HBM (often 16–32 GB) and evicts old prefixes rapidly, whereas ContextWeave's chunk cache lives in larger host DRAM/NVMe (128 GB–1 TB).


* **Why this matters for Gate G0:** An unbounded `PrefixCacheSimulator` over-credits native prefix caching on long traces and **artificially depresses** `post_prefix_prefill_tokens`. Cap `PrefixCacheSimulator` with an LRU token budget (defaulting to e.g. `--prefix-cache-budget-gb 24.0` of GPU HBM) so native prefix caching and chunk caching are simulated under realistic memory hierarchy constraints.

---

## Summary Checklist to Close Out Phase 0 Code

1. **`src/contextweave/tokenization/boundaries.py`:** Append `boundary_token_ids` to each prefix/chunk *before* padding to `kv_block_size = 16`, and wire `assemble_prompt_token_ids` into `synthetic.py`, `import_trace.py`, `corpus_trace.py`, and `metrics.py`.


2. **`src/contextweave/trace_analysis/metrics.py` & `working_set.py`:** Fix the denominator in `WorkingSetMetrics` (`post_prefix_prefill_tokens`), count cold prefix tokens (`uncovered_prefix_tokens`), default `require_working_set=True`, and use `hash_token_ids`.


3. **`src/contextweave/workloads/corpus_trace.py`:** Remove silent `"Details follow. " * 40` padding of short documents so Gate G0 chunk-length evaluation is honest.


4. **`src/contextweave/costmodel/breakeven.py`:** Fix `repair_time_roofline_s` so dense linear projections aren't divided by `repair_tflop_efficiency = 0.25`, compute exact `attn_flops` instead of `0.40`, and add `max_tolerable_bailout_rate()` for §B.


5. **`src/contextweave/fingerprints/` & `provenance/`:** Restrict `rope_type` to `{"default", "llama3"}`, remove `allowed_noncanonical`, change `fingerprint_example.py` to `POST_ROPE`, and block `TrustNamespaceKind.UNTRUSTED` even on same-namespace lookups.


6. **Regenerate `benchmarks/reports/*`:** Run the updated CLI scripts so all committed markdown and JSON reports reflect the `v2.1` working-set and roofline outputs.