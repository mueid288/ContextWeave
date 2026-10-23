# Phase 0A G0 — Corpus Replay (Path C, provisional)

- Trace: `benchmarks/workloads/corpus_replay_default/trace.jsonl`
- Requests: 300
- Provisional: **True**
- Gate G0: **PASS**
- Rationale: G0 PASS: unconstrained recurring non-prefix=85.9% (≥30%); median chunk=720 (≥512); LRU hit share=85.9% @ 128 GB (≥30% required). Marked provisional.

## Section 2.2 metrics

| Metric | Value |
|---|---|
| Total prefill tokens | 526,321 |
| Served by native prefix cache | 337,824 (64.2%) |
| Post-prefix prefill tokens | 188,497 |
| Cold / uncovered system-prefix tokens | 544 |
| Recurring non-prefix tokens (unconstrained) | 161,936 (85.9% of post-prefix) |
| First-seen chunk tokens (post-prefix) | 7,328 |
| Query tokens (post-prefix) | 18,689 |
| Post-prefix bucket sum (must match) | 188,497 |
| Median chunk length (tokens) | 720 |
| Synthesis request fraction | 47.7% |
| Requests ≥8k / ≥32k / ≥100k | 0.0% / 0.0% / 0.0% |
| Reuse distance (requests) | median=2, p90=10, mean=4.7 |

- Prefix-cache token budget: 183,105 (evictions=202)

### Working-set constrained hits (v2.1 amendment G)

| Metric | Value |
|---|---|
| Cache budget | 128.0 GB (LRU) |
| Bytes / token (KV) | 131,072 |
| Post-prefix prefill tokens (decision denom) | 188,497 |
| Post-prefix chunk tokens (diagnostic) | 169,264 |
| Hit tokens under budget | 161,936 (85.9% of post-prefix) |
| Hit share of chunks only | 95.7% |
| Miss tokens | 7,328 |
| Evictions | 0 |
| Peak resident | 0.96 GB |

### Context length buckets

- <8k: 300
- 8k-32k: 0
- 32k-100k: 0
- >=100k: 0

### Top-10 document popularity

- `api_authentication::chunk-000`: 138
- `api_authentication::chunk-001`: 88
- `data_retention::chunk-000`: 52
- `model_routing::chunk-001`: 44
- `incident_runbook::chunk-000`: 42
- `data_retention::chunk-001`: 41
- `model_routing::chunk-000`: 33
- `refund_policy::chunk-000`: 28
- `refund_policy::chunk-001`: 25
- `incident_runbook::chunk-001`: 23

## Interpretation

G0 thresholds (proposed defaults from PRD): recurring non-prefix share ≥ 30% of post-prefix-cache prefill tokens, and median chunk length ≥ 512.

This synthetic result bounds whether GPU baseline work is worth funding. Replace with a real serving trace before treating G0 as final.

## Path C note

Documents are real local files; the request stream is simulated. `token_count` uses chars/chars_per_token, not a model tokenizer. Replace with a serving-log export before treating G0 as final.
