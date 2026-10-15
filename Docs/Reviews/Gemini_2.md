The Phase 0 codebase is well-structured, fast to run on CPU, and enforces the local-safety policy (`src/contextweave/safety.py`) cleanly. You also translated the v2.1 architectural fixes—working-set LRU simulation, HBM roofline repair modeling, boundary-aware tokenization, Mode A canonical provenance, and extended FR-01/FR-02 fingerprints—into dedicated Python modules.

However, a line-by-line audit of the code and generated reports in `benchmarks/reports/` reveals **seven critical bugs and wiring disconnects** where the implementation either contradicts the math, silently rigs a gate, or leaves the new v2.1 modules disconnected from the actual execution path.

---

## 1. Critical Bugs in `trace_analysis` & `workloads`

### 1.1 The "79.0% > 74.6%" Upper-Bound Paradox & Missing Prefix Tokens (`metrics.py`, `working_set.py`)

Look at your generated report `benchmarks/reports/g0_my_corpus_ws.md`:

* **Unconstrained recurring non-prefix share:** `74.6%` (`251,495 / 337,207`)


* **Constrained LRU hit share @ 128 GB:** `79.0%` (`251,495 / 318,533`)



The report footer states: *"Unconstrained recurrence is an upper bound; working-set hits are the decision metric"*. Yet your constrained LRU hit share (`79.0%`) is **higher** than your unconstrained upper bound (`74.6%`) for the exact same `251,495` hit tokens!

**Why this happens (two bugs in `metrics.py` and `working_set.py`):**

1. **Denominator mismatch:** `DemandMetrics.share_recurring_non_prefix` divides `recurring_non_prefix_tokens` by `post_prefix_prefill_tokens` (`337,207`, which includes `18,162` query tokens). Meanwhile, `WorkingSetMetrics.hit_share_of_post_prefix_chunks` divides `hit_tokens` by `post_prefix_chunk_tokens` (`318,533`, which excludes query tokens). If G0 requires 30% of **post-prefix prefill token volume** to be served by working-set hits, `WorkingSetMetrics` must divide by `post_prefix_prefill_tokens` (`251,495 / 337,207 = 74.6%`), not chunk-only tokens.


2. **Vanishing cold-prefix tokens (`337,207 != 251,495 + 67,038 + 18,162`):**
In `g0_my_corpus_ws.md`, `251,495 + 67,038 + 18,162 = 336,695`, which is **512 tokens short** of `post_prefix_prefill_tokens` (`337,207`). In `g0_synthetic_rag_default.json`, `459,410 + 105,328 + 39,808 = 604,546`, which is **768 tokens short** of `605,314`.


* **Root cause:** In `analyze_trace` (`src/contextweave/trace_analysis/metrics.py`), on the very first request for each system-prefix template (`2 * 256 = 512` tokens in `my_corpus`; `3 * 256 = 768` tokens in `synthetic_rag_default`), `cache.lookup(token_ids)` returns `prefix_hit_tokens = 0`. Those cold system-prefix tokens are added to `post_prefix_prefill_tokens`, but line 159 sets `cursor = len(prefix_ids)`, skipping over `max(0, prefix_len - prefix_hit_tokens)` uncovered system-prefix tokens so they are never counted in any bucket.





### 1.2 Silent Gate-Rigging in Path C (`src/contextweave/workloads/corpus_trace.py`)

In `chunk_document` (`corpus_trace.py`), look at what happens when a real document is shorter than `chunk_chars_min` (`2,048` chars $\approx 512$ tokens):

```python
if len(body) < chunk_chars_min:
    # Pad short standalone docs so G0 chunk-length gate is meaningful.
    pad_unit = (
        f"\n\n[contextweave-pad] Additional reference material for {doc_stem}, "
        f"section {idx}. " + ("Details follow. " * 40)
    )
    while len(body) < chunk_chars_min:
        body += pad_unit
    body = body[:chunk_chars_max]

```

* **Why this is dangerous:** Gate G0 explicitly tests whether a corpus has a median chunk length $\ge 512$ tokens because short chunks cannot amortize KV load latency. By silently stuffing `"Details follow. " * 40` into every short document until it reaches `2,048` characters (`512` tokens), **Path C makes it mathematically impossible for a corpus of short documents to fail the G0 median chunk-length gate**.


* **Fix:** Remove automatic text padding from `chunk_document` (or gate it behind an explicit `--pad-short-docs-for-demo` CLI flag that forces `provisional=True` and prints a warning). If a user's real docs average 250 tokens, Gate G0 *must* report `median_chunk_length = 250` and fail as designed.



### 1.3 `boundaries.py` Is Disconnected from the Trace Generators & Analyzer

You created `src/contextweave/tokenization/boundaries.py` with `assemble_prompt_token_ids` (which inserts `boundary_token_ids = (198, 198)` between prefix, chunks, and query, and pads chunks to `kv_block_size = 16`).
However:

1. `assemble_prompt_token_ids` is never called anywhere outside tests.


* `synthetic.py` still does `token_ids = prefix_ids + [t for chunk in chunks for t in chunk] + query_ids` and generates unaligned chunk lengths (e.g., `[1016, 698, 1007]` in `synthetic_rag_default/trace.jsonl`).


* `import_trace.py` still does `token_ids = prefix_token_ids + [t for c in chunk_token_ids for t in c] + query_token_ids`.


* `corpus_trace.py` defines `CorpusTraceConfig.chunking_config()`, which is dead code and never called.




2. **If `assemble_prompt_token_ids` *were* called, `analyze_trace` would break:**
In `metrics.py`, `analyze_trace` advances `cursor` purely by `len(chunk)` without accounting for `len(boundary_token_ids)` between chunks. If `token_ids` includes boundary tokens, `cursor` drifts out of alignment with `prefix_hit_tokens` and leaves `(num_chunks + 1) * len(boundary_token_ids)` tokens unaccounted for on every request.



### 1.4 Intra-Request Duplicate Chunks & Weak Hashing (`synthetic.py`, `corpus_trace.py`, `metrics.py`)

* **Duplicate chunks in one request:** In `synthetic.py` and `corpus_trace.py`, the document-sampling loop tries `while cand in chosen and attempts < 8:`. Because `popularity_alpha = 1.1` and `recent` heavily weight `doc-0000`, `attempts < 8` can still pick the same document twice inside a single synthesis request, recording a bogus `reuse_distance = 0` (`idx - prev == 0`) in `metrics.py` and violating your own RAG guideline (*"Avoid stuffing the same document twice in one request"*).


* **Weak key hashing in `metrics.py`:** `_chunk_key` uses `f"len={len(token_ids)}:h={hash(tuple(token_ids))}"`. Do not use Python's built-in `hash()` for content identity; use `hash_token_ids(token_ids)` (SHA-256) from `contextweave.fingerprints.schema`.



---

## 2. Flaws in Cost Model, Fingerprints & Provenance

### 2.1 Broken Roofline Math in `src/contextweave/costmodel/breakeven.py`

Look at `repair_time_roofline_s` in `breakeven.py`:

```python
t_prefill = prefill_time_s(n_tokens, model)
eff = max(model.repair_tflop_efficiency, 1e-6)
attn_share = 0.40
t_linear = repair_fraction * (1.0 - attn_share) * t_prefill / eff
t_attn = repair_fraction * attn_share * t_prefill / eff
t_hbm = hbm_read_time_s(n_tokens, model)
return t_linear + max(t_attn, t_hbm)

```

Three physical modeling errors occur here:

1. Hardcoding `attn_share = 0.40` contradicts `prefill_flops` right above it:
Linear FLOPs ($2PN$) scale with $N$, while causal attention FLOPs ($2LN^2d_{\text{model}}$) scale with $N^2$. For your 8B model, attention is **14.1%** of total prefill FLOPs at $N = 10,000$, **34.9%** at $N = 32,000$, and **62.1%** at $N = 100,000$. You already have the exact terms—don't hardcode `0.40`.


2. Dividing `t_linear` by `repair_tflop_efficiency = 0.25` inflates repair time to 60% of full prefill:
In `benchmarks/reports/cost_model_8b.json`, at $N = 100,000$, full prefill is `9.38 s`, and 15% roofline repair is **`5.63 s`** (`0.15 / 0.25 * 9.38 s`)! Why? Because you divided **both** linear projections and attention by `0.25`. When recomputing $rN$ tokens (at $N=32\text{k}, r=0.15 \implies 4,800$ tokens), linear projections (`QKV`, `O`, `MLP`) are dense batched GEMMs of shape $[4800, 4096] \times [4096, D]$ that run at near-100% of `effective_tflops` (bounded only by reading the $2P \approx 16\text{ GB}$ of model weights from HBM). Only the **scattered/ragged attention kernel** suffers from `repair_tflop_efficiency`!


3. **Missing model-weight HBM reads during repair:**
A repair pass over $L$ layers must read all model weights ($S_W = P \cdot b \approx 16\text{ GB}$) plus the full KV cache ($S_{KV}$) from HBM.

**Correct Roofline Equation for `breakeven.py`:**

```python
def repair_time_roofline_s(
    n_tokens: int,
    model: ModelCostParams,
    *,
    repair_fraction: float,
) -> float:
    if repair_fraction <= 0:
        return 0.0
    n = float(n_tokens)
    r_n = repair_fraction * n
    eff = max(model.repair_tflop_efficiency, 1e-6)

    # 1. Dense linear GEMMs over r*N tokens vs HBM model-weight read
    linear_flops = 2.0 * model.params * r_n
    t_linear_compute = linear_flops / (model.effective_tflops * 1e12)
    weight_bytes = model.params * model.bytes_per_scalar
    t_weight_hbm = weight_bytes / (model.hbm_bandwidth_gb_s * 1e9)
    t_linear = max(t_linear_compute, t_weight_hbm)

    # 2. Ragged attention of r*N queries attending to N keys/values vs HBM KV read
    # Average causal attention context for uniformly scattered repair tokens is ~N/2
    attn_flops = 2.0 * model.num_layers * r_n * n * model.d_model
    t_attn_compute = attn_flops / (eff * model.effective_tflops * 1e12)
    t_kv_hbm = hbm_read_time_s(n_tokens, model)

    return t_linear + max(t_attn_compute, t_kv_hbm)

```

### 2.2 Trust & Provenance Bypass (`src/contextweave/provenance/trust.py`)

Look at `assert_reuse_allowed` in `src/contextweave/provenance/trust.py`:

```python
def assert_reuse_allowed(
    artifact_ns: TrustNamespace,
    request_ns: TrustNamespace,
    *,
    artifact_from_untrusted_content: bool,
    build_mode: ArtifactBuildMode = ArtifactBuildMode.CANONICAL_ISOLATED,
) -> None:
    assert_canonical_build_mode(build_mode)
    if artifact_ns.name != request_ns.name or artifact_ns.kind != request_ns.kind:
        ...

```

1. **Untrusted same-namespace bypass:** If `artifact_ns == request_ns` (e.g., both are `TrustNamespace("pool", TrustNamespaceKind.UNTRUSTED)`), the `if` condition is `False` and `assert_reuse_allowed` **succeeds**, even when `artifact_from_untrusted_content=True` or `artifact_ns.kind == TrustNamespaceKind.UNTRUSTED`! Per PRD Section 9 and `FR-13`, untrusted content must never be admitted or reused as shared KV artifacts.


2. **Lifecycle & canonical flags on `ProvenanceRecord` are ignored:** `ProvenanceRecord` tracks `built_in_canonical_context: bool` and `lifecycle: ArtifactLifecycle` (including `QUARANTINED`, `REQUESTED`, `EXPIRED`), but `assert_reuse_allowed` never checks them.



### 2.3 Validation Loopholes in `fingerprints/validate.py` & `cli/fingerprint_example.py`

1. **Unvalidated Dynamic/YaRN RoPE allowed (`validate.py` line 48):**
`if fp.rope.rope_type not in {"default", "llama3", "linear", "dynamic", "yarn"}:`.
Under `"dynamic"` (Dynamic NTK) and `"yarn"`, the RoPE frequency vector $\theta_i$ and temperature scale change dynamically as a function of total prompt length. Rotating a chunk built at 1k tokens into a 64k prompt via $R(\Delta\theta_i)$ is **mathematically invalid** because $\theta_i$ itself changed. Only `{"default", "llama3"}` preserve static position-independent $\theta_i$ and should pass validation in Phase 0/1.


2. **Placeholder revisions pass validation (`schema.py` / `fingerprint_example.py`):**
`fingerprint_example.py` sets `revision="desk-unpinned"` and `validate_artifact_fingerprint` returns `"ok": true, "status": "validated"`. Add `"desk-unpinned"`, `"unpinned"`, `"latest"`, and `"main"` to the blocked string set in `_require()` (or reject them in `validate_artifact_fingerprint` unless `allow_unpinned=True` is explicitly passed for desk examples).


3. **Silent `or 1` fallbacks in `fingerprint_example.py`:**
Lines 52–55 use `num_layers=int(raw.get("num_hidden_layers") or 0) or 1`. If a model YAML omits `num_hidden_layers`, it silently fingerprints as a 1-layer model instead of raising `UnknownFieldError` as required by `FR-01`. Also, line 92 sets `PositionStorageMode.PRE_ROPE` instead of `POST_ROPE`.



---

## 3. CLI & Repository Hygiene Issues

1. **`cli/import_trace.py --analyze` ignores working-set constraints:**
In `src/contextweave/cli/import_trace.py` (line 72), running `--analyze` calls `analyze_trace(args.out)` with `working_set_cfg=None` and `evaluate_g0(metrics, provisional=provisional)` with `require_working_set=False`. When you import a real partner trace, it won't run the v2.1 LRU working-set check! Wire `--cache-budget-gb`, `--bytes-per-token`, and `--require-working-set` into `import_trace.py` and `build_corpus_trace.py` just like `analyze_trace.py`.


2. **Stale reports in `benchmarks/reports/` contradict current code:**
* `benchmarks/reports/cost_model_8b.md` was generated before your v2.1 roofline update (`3.2 / 3.7` break-even, missing the roofline table), whereas `cost_model_8b.json` has the updated output (`3.2 / 7.9`).


* `benchmarks/reports/example_fingerprint_qwen3.json` and `example_fingerprint_llama31.json` are missing the new `boundary_token_ids`, `kv_block_size`, `padded_to_block`, and `assembly_rule` fields that `schema.py` now defines.




3. **Ignored artifacts packaged in the workspace:**
Your `.gitignore` properly excludes `__pycache__/`, `*.egg-info/`, `benchmarks/workloads/*/`, and `benchmarks/reports/*`, yet all of them (including `benchmarks/workloads/synthetic_rag_default/trace.jsonl`, which truncated the end of your archive upload!) are sitting on disk in the snapshot.



---

## 4. Drop-In Code Fixes

### Fix 1: `src/contextweave/trace_analysis/metrics.py` & `working_set.py`

Fixes the denominator mismatch (`79.0% > 74.6%`), accounts for cold prefix tokens (`uncovered_prefix_tokens`), and replaces Python's `hash()` with SHA-256 (`hash_token_ids`):

```python
# In src/contextweave/trace_analysis/working_set.py:
@dataclass
class WorkingSetMetrics:
    budget_gb: float
    bytes_per_token: float
    policy: str
    post_prefix_prefill_tokens: int = 0  # total post-prefix tokens (same denominator as G0)
    post_prefix_chunk_tokens: int = 0
    hit_tokens: int = 0
    miss_tokens: int = 0
    admit_tokens: int = 0
    evictions: int = 0
    unique_chunks_touched: int = 0
    peak_bytes: float = 0.0
    final_bytes: float = 0.0

    @property
    def hit_share_of_post_prefix(self) -> float:
        """Share of total post-prefix prefill tokens served by the budget-constrained cache."""
        if self.post_prefix_prefill_tokens == 0:
            return 0.0
        return self.hit_tokens / self.post_prefix_prefill_tokens

    @property
    def hit_share_of_post_prefix_chunks(self) -> float:
        """Diagnostic: hit share over chunk tokens only (excluding query/cold-prefix tokens)."""
        if self.post_prefix_chunk_tokens == 0:
            return 0.0
        return self.hit_tokens / self.post_prefix_chunk_tokens

```

And in `src/contextweave/trace_analysis/metrics.py`:

```python
from contextweave.fingerprints.schema import hash_token_ids

def _chunk_key(token_ids: list[int]) -> str:
    if not token_ids:
        return "empty"
    return f"len={len(token_ids)}:{hash_token_ids(token_ids)}"

```

Inside `analyze_trace` (`metrics.py`), track `uncovered_prefix_tokens = max(0, prefix_len - prefix_hit_tokens)` so `uncovered_prefix_tokens + recurring_non_prefix_tokens + unique_first_seen_chunk_tokens + query_tokens == post_prefix_prefill_tokens` holds identically on every trace, and pass `post_prefix_prefill_tokens=metrics.post_prefix_prefill_tokens` into `simulate_working_set`, using `metrics.working_set.hit_share_of_post_prefix` in `evaluate_g0`.

### Fix 2: `src/contextweave/provenance/trust.py`

Closes the same-namespace untrusted bypass and enforces lifecycle/canonical checks:

```python
def assert_reuse_allowed(
    artifact_ns: TrustNamespace,
    request_ns: TrustNamespace,
    *,
    artifact_from_untrusted_content: bool,
    build_mode: ArtifactBuildMode = ArtifactBuildMode.CANONICAL_ISOLATED,
    record: ProvenanceRecord | None = None,
) -> None:
    assert_canonical_build_mode(build_mode)

    if artifact_from_untrusted_content or artifact_ns.kind == TrustNamespaceKind.UNTRUSTED:
        raise CrossTrustReuseError(
            "Refuse reuse of KV artifact built from untrusted content or in an untrusted namespace."
        )

    if record is not None:
        if not record.built_in_canonical_context:
            raise CrossTrustReuseError(
                f"Artifact {record.artifact_id} was not built in a canonical context."
            )
        if record.lifecycle != ArtifactLifecycle.AVAILABLE:
            raise CrossTrustReuseError(
                f"Artifact {record.artifact_id} is not available for reuse (lifecycle={record.lifecycle.value})."
            )

    if artifact_ns.name != request_ns.name or artifact_ns.kind != request_ns.kind:
        raise CrossTrustReuseError(
            f"Refuse cross-namespace reuse: artifact={artifact_ns.to_dict()} "
            f"request={request_ns.to_dict()}"
        )

```

### Fix 3: Deduplicated Sampling in `synthetic.py` & `corpus_trace.py`

To prevent a request from ever containing duplicate chunks and producing `reuse_distance == 0`:

```python
# In synthetic.py and corpus_trace.py:
n_docs = min(n_docs, len(ids))  # or len(doc_ids)
while cand in chosen:
    # Fallback to uniform choice over remaining unselected docs after 8 weighted tries
    if attempts >= 8:
        remaining = [d for d in ids if d not in chosen]
        cand = rng.choice(remaining)
        break
    cand = rng.choices(ids, weights=weights, k=1)[0]
    attempts += 1

```