# Pre-registration: Canonical chunk order (product / C1 amplification)

**Status:** **PASS** (2026-10-24) — `artifacts/product-canonical-order-2026-10-24/`  
**Not a PIC / C3 / G2 reopen. No GPU. Quality unverified.**

## Result

| Workload | multi-doc Δpp (`by_frequency_desc`) | multi-doc post_prefix ↓ | pass |
|---|---:|---:|---|
| synthetic | **+14.4** | **21.0%** | yes |
| my_corpus | **+15.5** | **22.4%** | yes |

`by_doc_id` nearly matches frequency here (Zipf↔alphabetical coincidence).  
`by_sha256_doc_id` multi-doc lift ~**+5–6 pp** (de-correlated baseline).

## One question

On banked `synthetic_rag_default` and `my_corpus` traces, does **`by_frequency_desc`**
clear either:

- **≥ +10 percentage points** absolute lift in `share_prefix_cached` vs `natural`
  (overall **or** multi-doc `len(chunks)≥2`), **or**
- **≥ 20%** reduction in multi-doc `post_prefix_prefill_tokens` vs `natural`?

Both workloads must clear at least one bar.

## Diagnostics (report, not pass criteria)

| Mode | Role |
|---|---|
| `natural` | Baseline (generator shuffle) |
| `by_doc_id` | Lex/natural-sort by id — **inflated** on these corpora (Zipf aligned with alpha order) |
| `by_sha256_doc_id` | De-correlated IDs (UUID-like) |
| `by_frequency_desc` | Product policy (hot chunks toward prefix; tie-break natural id) |

## Pass / fail

| Outcome | Next |
|---|---|
| PASS | Document as C1 amplification utility; quality still unverified |
| FAIL | Ship tool anyway; bank negative lift; do not claim product win |
| Quality | **Out of scope** (needs GPU vs relevance/original order) |

## KPI note

Do **not** use Gate G0 PASS as success. Moving recurrence into prefix cache can
drop `share_recurring_non_prefix` — label that “absorbed into C1.”
