# cw-field Gate G0 — collected field traffic (2026-10-24 → 10-25)

**Status:** Emitter contract fixed; first clean **PASS** banked (provisional, N=3). Larger multi-user runs showed demand recurrence **before** chunk fix but could not PASS the median-chunk bar.

## Runs (banked under `artifacts/`)

| Artifact | N | Users | Recurrence | Median chunk | Gate |
|---|---:|---:|---:|---:|---|
| `cw-field-g0-2026-10-24-auto` | 3 | 1 | 11% | 250 | FAIL |
| `cw-field-g0-2026-10-24` | 30 | 5 | **31.2%** | 250 | FAIL (chunk only) |
| `cw-field-g0-2026-10-25` | 82 | 10 | **45.2%** | 250 | FAIL (chunk only) |
| `cw-field-g0-2026-10-25-chunkfix` | 17 | 3 | **53.2%** | 250 | FAIL (`build_index` still 1000) |
| `cw-field-g0-2026-10-25-chunk2048` | 3 | 1 | **65.3%** | **512** | **PASS** (provisional) |

## What the data shows

1. **Real multi-user reuse exists.** At N=82 / 10 users (pre-fix emitter), unconstrained + working-set hit share cleared 30% with reuse distance median 1. Top docs (assignments, CV/PDF material) recur across asks.
2. **G0 was blocked by emitter, not demand.** `retrieve.build_index` hardcoded `chunk_chars=1000` → `token_count≈250`. Fixed in cw-field `4ca4d7a`.
3. **Post-fix PASS is narrow.** `chunk2048`: all chunks 512, prefix=83, recurrence 65.3%, but **1 user / 3 asks** after a trace wipe — not yet multi-user field evidence.
4. **Synthetic tokens.** All rows `meta.token_ids_synthetic: true`. Keep provisional; do not flip `--final`.

## Claim language (allowed / not)

- **Allowed:** “Live cw-field traffic exhibits ≥30% recurring non-prefix share at multi-user N≈80 under small chunks; after fixing chunk size to ≥512 tokens, a provisional G0 PASS was obtained on a clean post-fix sample.”
- **Not allowed yet:** “Final partner-trace G0 PASS from production multi-user demand.”

## Next bank

Re-accumulate multi-user traffic **without** wiping traces (post-`4ca4d7a`), then:

```bash
cw-field-g0 --tag YYYY-MM-DD-field --min-traces 30 --min-users 5
```

Target: PASS with N≥30 and ≥5 users, still provisional until real tokenizer IDs.
