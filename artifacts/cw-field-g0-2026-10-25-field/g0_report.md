# Phase 0A Demand Analysis (Gate G0)

- Trace: `/home/harborsoft/Mueid/ContextWeave/artifacts/cw-field-g0-2026-10-25-field/trace.jsonl`
- Requests: 27
- Provisional: **True**
- Gate G0: **PASS**
- Rationale: G0 PASS: unconstrained recurring non-prefix=42.0% (≥30%); median chunk=528 (≥512); LRU hit share=42.0% @ 128 GB (≥30% required). Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 54,714 |
| Served by native prefix cache | 16,928 (30.9%) |
| Post-prefix prefill tokens | 37,786 |
| Cold / uncovered system-prefix tokens | 384 |
| Recurring non-prefix tokens (unconstrained) | 15,856 (42.0% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 21,376 |
| Query tokens (post-prefix) | 170 |
| Post-prefix bucket sum (must match) | 37,786 |
| Median chunk length (tokens) | 528 |
| Synthesis request fraction | 92.6% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=1, p90=2, mean=1.8 |

- Prefix-cache token budget: 183,105 (evictions=0)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 37,786 |
| Post-prefix chunk tokens (diagnostic) | 37,232 |
| Hit tokens under budget | 15,856 (42.0% of post-prefix) |
| Hit share of chunks only | 42.6% |
| Miss tokens | 21,376 |
| Evictions | 0 |
| Peak resident | 2.80 GB |

### Context length buckets

- <8k: 27
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `d_89be893b3426_docx::chunk-000`: 7
- `d_6238b4548de7_docx::chunk-000`: 6
- `d_e14215197615_md::chunk-000`: 6
- `d_e14215197615_md::chunk-001`: 6
- `d_4cf10e58a42c_md::chunk-002`: 5
- `d_64efe24d4eeb_pdf::chunk-001`: 4
- `d_71c81970948d_docx::chunk-000`: 4
- `2023f-mulbscs-223_B_6_docx::chunk-000`: 3
- `2023f-mulbscs-223_B_6_docx::chunk-001`: 3
- `Engagement-Metrics-Architecture-v3_docx_md::chunk-000`: 3

## Interpretation

G0 thresholds (PRD v2 + v2.1): unconstrained recurring non-prefix ≥ 30% of post-prefix tokens; median chunk ≥ 512; and by default, LRU hit share under the declared GB budget also ≥ 30% (same post-prefix denominator).

Unconstrained recurrence is an upper bound; working-set hits are the decision metric for achievable cache value. Replace Path C / synthetic traces with a serving log before treating G0 as final.
