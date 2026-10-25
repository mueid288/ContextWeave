# Field order A/B — Layer 1 (2026-10-25)

Trace: `artifacts/cw-field-g0-2026-10-25-field/trace.jsonl` (N=27, all multi-doc).

| Mode | share_prefix_cached | Δ vs natural | post_prefix ↓% |
|------|--------------------:|-------------:|---------------:|
| natural | 30.9% | — | — |
| by_frequency_desc | **36.6%** | **+5.64 pp** | **+8.2%** |
| by_doc_id | 30.9% | 0 | 0 |
| by_sha256_doc_id | 27.9% | −3.04 pp | −4.4% |

- **Plan desk bar (≥ +2 pp):** **PASS**
- **Pre-reg bar (≥ +10 pp or ≥20% post_prefix cut):** **FAIL** (`pass_heuristic=False` in analyzer)
- Recurrence drop 42.0% → 36.8% under frequency = absorbed into C1 (expected)

**Claim:** On this field trace, frequency order lifts simulated prefix-cache share by **+5.6 pp** and cuts post-prefix tokens **8.2%** vs natural. Live TTFT not measured (Layer 2).
