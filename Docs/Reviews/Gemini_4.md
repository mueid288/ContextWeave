Pivoting the immediate deliverable to a **CPU-only prefix-cache amplification utility** (while keeping the non-prefix PIC research archived and explicitly disclaiming unverified answer-quality impacts) is a pragmatic engineering move. You avoid fragile runtime forks and focus on maximizing native `C1` (RadixAttention / PagedAttention prefix cache) hits.

However, inspecting this plan against your existing generators (`synthetic.py` and `corpus_trace.py`) and analyzer (`metrics.py`) reveals **five methodological and algorithmic traps**—including a major benchmark coincidence in your codebase that will artificially inflate `by_doc_id` results.

---

## 1. Five Critical Flaws in the Plan

### 1.1 The "Alphabetical == Zipf Rank 0" Benchmark Coincidence (`synthetic.py` & `corpus_trace.py`)

Your plan proposes sorting chunks lexicographically `by_doc_id` and measuring prefix-hit lift on `synthetic_rag_default` and `my_corpus`.
Look at how both traces were generated in your repo:

1. **`synthetic.py`:** `_build_corpus()` creates `doc-0000`, `doc-0001`, …, `doc-0079` in ascending order, and `generate_trace()` assigns Zipf popularity weights $w_i \propto (i+1)^{-\alpha}$ in that exact list order. Thus, **`doc-0000` is simultaneously the most popular document (182/500 requests) and lexicographically first** (`doc-0001` is 2nd at 118 requests, `doc-0002` is 3rd at 60 requests).


2. **`corpus_trace.py` (`my_corpus`):** `discover_documents()` sorts file paths alphabetically (`sorted(corpus_dir.glob(pattern))`), and `generate_partner_requests()` assigns Zipf weights in that exact index order. Thus, **`01_PRD_WhatsApp_Lead_Qualifier::chunk-000` is simultaneously the hottest chunk (114/300 requests) and lexicographically first** (followed by `chunk-001` at 55, `chunk-002` at 42, `chunk-003` at 40)!



* **Why this invalidates the benchmark:** On both `synthetic_rag_default` and `my_corpus`, sorting alphabetically by `document_id` **secretly acts as an oracle popularity-descending sort** because Zipf rank $0, 1, 2, \dots$ is monotonically aligned with ASCII order!


* **What happens in production:** In real corpora, document IDs are UUIDs, hashes, or arbitrary filenames where the hottest document is just as likely to be `"z_refund_policy"` as `"01_prd"`. If a request retrieves `{doc_rare_A, doc_hot_Z}` and another retrieves `{doc_hot_Z, doc_rare_B}`, sorting alphabetically produces `[doc_rare_A, doc_hot_Z]` and `[doc_hot_Z, doc_rare_B]`—yielding **zero** shared document prefix!
* **Required Fix:**
1. **Add Frequency-Aware Canonicalization (`by_popularity_desc` / `by_access_count`):** In addition to `by_doc_id`, implement a frequency-aware orderer (using a rolling frequency table or corpus popularity prior, tie-broken by `document_id`) that places the hottest chunks closest to the system prefix.
2. **De-correlate IDs in the Benchmark:** In your A/B evaluation, also test `by_sha256_doc_id` (sorting by `sha256(document_id)`), which simulates real-world UUIDs where alphabetical order is uncorrelated with popularity. Comparing `natural` vs. `by_sha256_doc_id` vs. `by_popularity_desc` will show the true difference between **exact-subset canonicalization** (ID sort) and **prefix-tree compression** (popularity sort).



### 1.2 The Gate G0 "Metric Inversion" Trap (`metrics.py`)

Your plan proposes running `analyze_trace` in an A/B comparison and reporting `share_prefix_cached`, post-prefix recurring share (`share_recurring_non_prefix`), and working-set hit share (`working_set_hit_share`).

* **Why `evaluate_g0` will invert:** In `metrics.py`, `share_recurring_non_prefix` is defined as:

$$\text{share\_recurring\_non\_prefix} = \frac{\text{recurring\_non\_prefix\_tokens}}{\text{post\_prefix\_prefill\_tokens}}$$



where $\text{post\_prefix\_prefill\_tokens} = \text{total\_prefill\_tokens} - \text{prefix\_cached\_tokens}$.


* When canonical ordering succeeds, it converts $\Delta$ tokens from **recurring non-prefix** into **prefix-cached** (`C1`). Both the numerator and denominator of `share_recurring_non_prefix` shrink by $\Delta$:



$$\frac{R - \Delta}{P - \Delta} < \frac{R}{P} \quad (\text{whenever } R < P)$$


* If canonical ordering is highly effective, `share_recurring_non_prefix` and `working_set_hit_share` will drop **below 30%**, causing `evaluate_g0()` to flip from **`G0 PASS` to `G0 FAIL**`!


* **Required Fix:** Remember that Gate G0 was designed to ask *"Is there enough uncached non-prefix recurrence left over to justify PIC research?"*. For a `C1`-only product slice, shifting tokens *out* of post-prefix recurrence and *into* `prefix_cached_tokens` is the goal. Your `--compare-chunk-order` report should highlight:


1. **`share_prefix_cached` delta** (`prefix_cached_tokens / total_prefill_tokens`) — the primary product KPI.


2. **`post_prefix_prefill_tokens` reduction (%)** — the direct compute/prefill savings from canonicalization.


3. Explicitly label any drop in post-prefix non-prefix recurrence as **"Recurrence absorbed into native prefix cache (C1)"** rather than a G0 failure.



### 1.3 Pre-Registration Bar (`lift > 0`) Is a Tautology Against `rng.shuffle()`

In `synthetic.py` (line 149) and `corpus_trace.py` (line 262), the generators explicitly call `rng.shuffle()` on every request's chosen documents.

* Against uniform random permutations ($1/k!$ probability of matching order on a $k$-doc set), *any* deterministic ordering function is guaranteed to produce `lift > 0` as long as a single pair of documents repeats in the trace.
* **Required Fix:** Make the pre-registration in `Docs/pre-reg/pre-reg-product-canonical-order.md` falsifiable and non-trivial:
1. Require a meaningful effect size (e.g., **$\ge +10\text{ percentage points}$ absolute lift** in `share_prefix_cached`, or **$\ge 20\%$ reduction** in `post_prefix_prefill_tokens` on multi-doc synthesis requests).
2. Include a **de-correlated ID baseline** (`by_sha256_doc_id`) alongside `by_doc_id` and `by_frequency_desc` so the lift isn't an artifact of `doc-0000` being Zipf rank 0.





### 1.4 ASCII Sort Scrambles Intra-Document Reading Order (`chunk-10` < `chunk-2`)

While your own generator zero-pads chunk IDs (`chunk-000`, `chunk-001`), real partner traces (`partner_v1`) often name chunks `docA::chunk-2` and `docA::chunk-10` or `sec_2` and `sec_10`.

* A naive Python `str` sort places `docA::chunk-10` **before** `docA::chunk-2`, scrambling contiguous sections of the same document and hurting LLM comprehension even when both chunks belong to the same file.
* **Required Fix:** Use a **natural sort key** (`natsort`) in `canonicalize_chunks_by_doc_id`:
```python
import re

def _natural_doc_key(doc_id: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", doc_id)]

```


This keeps contiguous chunks of the same document in true numerical reading order (`chunk-2` before `chunk-10`) with zero external dependencies.

### 1.5 Contradiction with Your Own Bundled Corpus (`rag_best_practices.md`)

In `benchmarks/corpora/sample_docs/rag_best_practices.md` (which is bundled in the repo and used for Path C!), the prompt assembly section currently states:

> *"Place system instructions first, then documents in relevance order unless the task requires chronological order."*
> 
> 

* Be sure to note this tension in `Docs/product/canonical-order.md`: standard RAG pipelines sort by retriever relevance score, which maximizes relevance position bias but destroys prefix caching across queries with different phrasings; canonical ordering trades retriever-score order for prefix-cache reuse.

---

## 2. Implementation Details to Tighten in Step 1 & Step 2

### 2.1 Lockstep Permutation & `segments_canonical` Preservation

When implementing `canonicalize_chunks_by_doc_id(row) -> dict[str, Any]`, make sure it handles both `segments_canonical=True` (from your `v2.1.1` boundary-then-pad pipeline) and legacy rows cleanly:

* Permute `document_ids`, `chunk_token_ids`, and `chunk_lengths` in lockstep using stable `enumerate` indices so duplicate `document_ids` (if present in a partner trace) preserve their relative order.
* If `row.get("segments_canonical")` is `True`, each chunk in `chunk_token_ids` and `prefix_token_ids` already contains its trailing boundary tokens and 16-token block padding, so `token_ids = prefix_token_ids + [t for c in sorted_chunks for t in c] + query_token_ids` preserves exact 16-token page alignment and the `metrics.py` bucket-sum assertion.


* Assert `len(new_row["token_ids"]) == len(row["token_ids"])` inside `canonicalize_chunks_by_doc_id` so reordering is strictly length-invariant.

### 2.2 Separate Single-Doc (`lookup`) from Multi-Doc (`synthesis`) in the A/B Delta

In `synthetic_rag_default` (56% `lookup`) and `my_corpus` (49% `lookup`), roughly half of all requests contain only **1 chunk** (`n_docs == 1`), where chunk reordering is a no-op on the request itself (though it still benefits from multi-doc requests populating shared first-chunk trie paths). In your `--compare-chunk-order` output table, report both **Overall `share_prefix_cached**` and **Multi-Doc (`len(chunks) >= 2`) `share_prefix_cached**` so the impact on multi-document prompts is visible.

---

Would you like me to write the drop-in `chunk_order.py` module (supporting `natural`, `by_doc_id` with natural sorting, `by_sha256_doc_id`, and `by_frequency_desc`) and the `--compare-chunk-order` table formatter for `analyze_trace.py`?

Draft the complete `src/contextweave/trace_analysis/chunk_order.py` module with unit tests

Draft the `Docs/pre-reg/pre-reg-product-canonical-order.md` specification with the de-correlated ID and frequency baselines

Write the `--compare-chunk-order` CLI extension for `analyze_trace.py`