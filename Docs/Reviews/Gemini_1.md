**ContextWeave PRD v2.0** is an unusually disciplined, intellectually honest engineering document. Splitting the document into an actionable **Part I (Research Charter)** and a gated **Part II (Deferred Product Requirements)**, demoting RoPE rebasing from a "core invention" to a routine $O(N)$ sub-problem, integrating the **HijackKV** threat model, and establishing falsifiable gates (**G0–G5**) eliminates almost all of the "vaporware" risk common to AI systems proposals.

However, beneath the clean structure, there are **seven technical, architectural, and methodological blind spots** that could invalidate the Phase 1/2 experiments or break the Phase 3 runtime architecture if not corrected before execution begins.

---

## 1. Strategic Verdict: The "Thin Wedge" Dilemma

By correctly abandoning the claim of inventing a new repair algorithm (Section 0.4, Section 4.2), ContextWeave stakes its entire existence on **H2 and H3**: that a per-request planner choosing among existing training-free methods ($C_0 \dots C_6$) beats the best single fixed configuration after accounting for selector overhead.

* **The Strategic Tension:** If the optimal choice among $C_0 \dots C_6$ depends mainly on *model family and task type* (e.g., "use PSR with $r=0.15$ for multi-doc QA on Llama-3.1-8B"), operators only need a one-time offline benchmark script, not a runtime per-request control plane.


* **The Narrow Path to Viability:** For ContextWeave to justify existing at runtime, the optimal strategy must vary *per request within the same workload* based on dynamic properties (chunk count, chunk length, storage tier locality, or in-flight Layer-1 attention drift). Your Phase 1 design must isolate **intra-workload variance** from **inter-workload variance**.



---

## 2. Seven Critical Technical & Methodological Flaws

### 2.1 The Control-Plane / Data-Plane Paradox in H3 (Section 3.2, 7.6, 14.2)

* **The Contradiction:** Section 3.2 (H3) proposes using a "cheap runtime risk signal (for example first-layer key deviation, which CacheBlend already computes, or per-chunk offline calibration)" to gate unsafe reuse. Yet in Section 14.2 (Request Flow) and Section 15 (`/v1/cache/plan`), the Planner selects the strategy in the control plane *before* loading tensors and *before* invoking the inference runtime.


* **Why It Breaks:** You cannot compute Layer-1 key deviation in the control plane. Computing Layer-1 deviation requires loading Layer-0/1 KV caches into GPU HBM and executing the Layer-0/1 forward pass over the composed sequence. Conversely, if the planner relies strictly on offline calibration records (`FR-14`) so it can run pre-load in the control plane, it is blind to request-specific cross-chunk interactions and collapses into a static lookup table per workload slice.


* **Required Fix:** Split planning into a **two-stage execution model**:
1. **Stage 0 (Pre-Load Control Plane):** Filter strategies using fingerprints (`FR-04`), the bandwidth/latency cost model (Section 7.5), and static workload-slice calibration (`FR-14`).


2. **Stage 1 (In-Flight Layer-1 Bailout):** Pipeline Layer-0/1 execution with Layer-2+ KV loading; if measured Layer-1 KV drift exceeds the threshold, abort the cache load mid-flight and fall back to $C_0$ (full prefill) from Layer 1 onward, explicitly modeling the wasted PCIe/NVMe bandwidth in your cost equation.



### 2.2 Max-of-$N$ Selection Bias in the Oracle Study (Section 5, Gate G2 & Section 8.2)

* **The Flaw:** Section 8.2 defines the Phase 1 Oracle Study by running $C_0 \dots C_6$ on every request and picking "the best achievable choice per request using ground-truth quality". Gate G2 passes if this oracle beats the best fixed configuration by at least **+3 quality points** at equal p95 TTFT.


* **Why It Breaks:** Because approximate KV methods ($C_2 \dots C_6$) perturb logits, evaluating 6 configurations per query and taking the post-hoc maximum F1/EM score introduces severe **max-of-$N$ selection bias**. On queries where $C_0$ (full prefill) is near a decision boundary, one of $C_2 \dots C_6$ will randomly flip an output token and score higher by chance. An unconstrained post-hoc oracle will artificially clear the +3 point G2 bar—and even appear to beat full prefill ($C_0$)—purely by cherry-picking stochastic decoding variance across 6 runs.
* **Required Fix:**
1. **Cap Oracle Quality at $C_0$:** Define the oracle objective as **latency minimization subject to non-inferiority against $C_0$**:

$$c^*(x) = \arg\min_{c \in \{C_0 \dots C_6\}} \text{TTFT}(x, c) \quad \text{s.t.} \quad \text{Quality}(x, c) \ge \text{Quality}(x, C_0) - \epsilon$$


2. **Require Feature Predictability at G2:** Require that a simple cross-validated classifier trained on *pre-generation features* (chunk lengths, positions, Layer-1 KV drift) captures at least 50% of the oracle's latency/quality upside before passing G2.



### 2.3 Unrealistic Repair FLOPs & Missing Page-Alignment Costs (Section 7.5)

* **The Flaw:** The worked example in Section 7.5 estimates $T_{\text{repair}}$ at a $15\%$ recompute ratio as simply $0.15 \times T_{\text{prefill}}$ at an effective **450 TFLOP/s**. It also models $T_{\text{assemble}}$ as a simple additive term.


* **Why It Breaks:**
1. **Scattered Repair is Memory-Bound, Not Compute-Bound:** Recomputing 15% of tokens scattered across chunks (as in CacheBlend / $C_4$) still requires reading **100% of the preceding KV cache** from GPU HBM at every attention layer. You do not get 450 TFLOP/s on sparse query tokens attending to a 100k-token KV cache; attention becomes heavily HBM-bandwidth-bound, and non-contiguous token gathering breaks standard FlashAttention tile packing unless custom ragged kernels are used.


2. **PagedAttention Block Fragmentation:** vLLM and SGLang allocate KV caches in fixed physical page blocks (e.g., 16 or 64 tokens). If `artifact-a` is 1,005 tokens and `artifact-b` is 810 tokens, concatenating them either leaves unaddressed mid-block gaps (requiring custom block-mask support in the attention kernel) or forces a physical memory compaction copy across all subsequent tokens so they align to page boundaries.




* **Required Fix:**
* Enforce in `FR-02`/`FR-03` that cached chunk lengths (after stripping sink prefixes) must be exact multiples of the runtime's KV block size, or explicitly pad/mask block tails.
* Replace the $0.15 \times T_{\text{prefill}}$ compute assumption in Section 7.5 with a roofline estimate that accounts for full-context HBM KV reads during the repair pass:

$$T_{\text{repair}}(r) \approx r \cdot T_{\text{linear\_proj}} + \max\left(r \cdot T_{\text{attn\_compute}},\, T_{\text{HBM\_read}}(S_{KV})\right)$$





### 2.4 Pre-RoPE vs. Post-RoPE Storage Misconception (Section 7.3)

* **The Flaw:** Section 7.3 proposes comparing (1) storing post-RoPE keys and rotating by $\Delta\theta_i$ at assembly vs. (2) storing pre-RoPE keys and applying RoPE at runtime so stored artifacts remain immutable.


* **Why It Breaks:** Both approaches have the exact same $O(N \cdot L \cdot H_{kv} \cdot d_h)$ compute and memory-bandwidth footprint at runtime, and **neither requires mutating stored artifacts in place** if rotation occurs during the Host-to-Device (H2D) copy or inside a copy-on-load buffer. More importantly, during chunk build, Layers $1 \dots L$ still require RoPE to be applied at Layer $l-1$ to compute valid self-attention hidden states. Storing pre-RoPE keys requires patching the model forward pass to tap $k^{\text{pre}}$ *before* the RoPE op while still feeding $k^{\text{post}}$ into self-attention.


* **Required Fix:** Don't waste Phase 1 engineering cycles benchmarking pre-RoPE vs. post-RoPE storage as separate architectures. Store standard post-RoPE keys (or whatever format LMCache natively exports), and test whether the delta-rotation kernel can be **fused into the H2D transfer/copy stream** so it adds zero extra HBM round-trips.



### 2.5 Ambiguity in Artifact Creation vs. HijackKV Threat Model (Section 9 & FR-13)

* **The Flaw:** Section 9 and `FR-13` highlight **HijackKV** (where an attacker-controlled build prefix poisons a cached chunk's KV state) and propose two mitigations: (1) building artifacts only in an operator-controlled canonical context, and (2) running a background "sampled audit [that] rebuilds artifacts in the canonical context and compares KV and behavior".


* **Why It Breaks:** These two mitigations belong to mutually exclusive system designs:
* **Mode A (Explicit / Isolated Canonical Build):** When a chunk is missed or registered via `POST /v1/cache/artifacts`, the server runs a clean prefill of `[canonical_sink_prefix + chunk_tokens]` in isolation. Here, **HijackKV is impossible by construction** because user-supplied preceding context is never present during artifact creation. A sampled rebuild audit (`FR-13`) will only ever test deterministic GPU math or bit-rot, not poisoning.


* **Mode B (Opportunistic In-Flight Harvesting):** Extracting the KV slice of `Document B` from a live user request `[User_Prompt_A + Document_B + Query]` to reuse in later requests. Here, HijackKV is a critical vulnerability—but `FR-01`/`FR-04` already state that any non-canonical `build_context_hash` is rejected, which would reject 100% of opportunistically harvested non-prefix chunks!




* **Required Fix:** Explicitly state in Section 7 and `FR-13` that ContextWeave **never harvests non-prefix KV chunks from mid-prompt live requests**; all non-prefix artifacts are built in isolated canonical passes. That eliminates HijackKV build-context poisoning by construction and lets you drop the complex background rebuild auditor from `FR-13` (retaining only a lightweight checksum verification).



### 2.6 Gate G0 (Demand) Ignores Working-Set Size and Cache Eviction (Section 2.2 & 5)

* **The Flaw:** Gate G0 passes if $\ge 30\%$ of post-prefix-cache prefill token volume is recurring non-prefix content with median chunk length $\ge 512$ tokens.


* **Why It Breaks:** Unbounded trace recurrence does not equal achievable cache hits. As Section 7.5 calculates, **1M tokens of KV cache for an 8B model consumes ~131 GB**. If 35% of a workload's tokens recur across a 30-day trace, but the active corpus spans 20M tokens (2.6 TB of KV state), a single node with 128 GB of host RAM or 1 TB of NVMe will suffer continuous cache thrashing and near-zero hit rates. Additionally, many production RAG pipelines use 256- to 400-token chunks; a rigid 512-token median floor could fail G0 on valid workloads where packing 2–3 co-retrieved chunks into a super-chunk would easily clear the bar.


* **Required Fix:** Redefine Gate G0 around **working-set-constrained recurrence**:
> *At least 30% of post-prefix-cache prefill token volume is served by cache hits when simulating an LRU cache capped at the target host memory/NVMe budget (e.g., 128 GB DRAM / 1 TB NVMe), with median reusable unit length $\ge 512$ tokens.*



### 2.7 Tokenizer Non-Homomorphism at Chunk Boundaries (`FR-02`)

* **The Flaw:** `FR-02` warns against assuming identical text produces identical token IDs across tokenizer versions, and tracks `token_ids_hash`.


* **Why It Breaks:** Even within a single pinned tokenizer version, BPE/tiktoken/SentencePiece tokenizers are **not boundary-homomorphic**: $\text{tokenize}(A + B) \neq \text{tokenize}(A) + \text{tokenize}(B)$. Leading spaces, newlines, and subword merges across chunk boundaries cause the first token of Chunk $B$ to tokenize differently when tokenized in isolation (or after a Link0 sink prefix) versus when concatenated after Chunk $A$ in a full prompt ($C_0$). This creates silent 1-token alignment shifts during Case C/D comparisons and runtime fallback (`FR-08`).


* **Required Fix:** Specify in `FR-02` and Section 8.6 that prompts must be tokenized **chunk-by-chunk with canonical boundary delimiters** (e.g., enforced `\n\n` boundary tokens) and concatenated at the token-ID level for both $C_0$ (full prefill) and $C_2 \dots C_6$, ensuring strict token-ID parity across all strategies.

---

## 3. Targeted Edits Before Approving Phase 0

| Section | Current State | Recommended Revision |
| --- | --- | --- |
| **Section 0.5 (Budget & Compute)** | Estimates ~200 GPU-hours on one 80 GB GPU for Phase 0.

 | Increase buffer to **350–400 GPU-hours**. Running 5+ trials across 4 baselines (Full, Prefix, CacheBlend, EPIC) on long-context workloads (32k–100k) with sweeps over recompute ratios $r$ will quickly exhaust 200 hours once environment debugging is included.

 |
| **Section 5 (Gate G3 Statistical Bar)** | Requires lower bound of 95% CI of $(\text{planner} - \text{full prefill}) \ge -2.0$ points absolute.

 | Specify a **paired bootstrap test** over identical queries (since query difficulty variance is huge, unpaired CIs will require thousands of queries to achieve a $\pm 2$ point CI width). |
| **Section 6.1 (Model Selection)** | Suggests Llama-3.1-8B-Instruct, Qwen3-8B, Mistral-7B-Instruct-v0.3; notes preferring unscaled RoPE first.

 | Note that **Llama-3.1-8B-Instruct uses `llama3` piecewise frequency-scaled RoPE by default** (`rope_scaling` is enabled in its base `config.json` for 128k context). If you want unscaled RoPE first, use **Mistral-7B-Instruct-v0.3** or **Qwen2.5/Qwen3-8B** (within native unscaled length) as Primary Model 1, and treat Llama-3.1's piecewise scaling properly from Day 1. Note: standard RoPE delta rotation $R(\Delta\theta_i)$ *still holds* for Llama-3.1's `llama3` scaling because the frequency scaling modifies the static $\theta_i$ vector, not position linearity—unlike Dynamic NTK or YaRN temperature scaling. State this distinction explicitly in Section 7.1/7.4! |
| **Section 15 (API Sketch)** | `/v1/cache/plan` takes `content_hash` and `token_count` per chunk, but no query tokens or task slice identifier.

 | Add `query_token_count` and `workload_slice_id` to the `/v1/cache/plan` request payload; without `query_token_count`, the cost model in Section 7.5 cannot compute $T_{\text{query}}$ or $T_{\text{baseline}}(\text{context} + \text{query})$.

 |