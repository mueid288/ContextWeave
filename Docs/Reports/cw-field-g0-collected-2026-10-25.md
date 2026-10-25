# cw-field Gate G0 — collected field traffic (2026-10-24 → 10-25)

**Headline bank:** `artifacts/cw-field-g0-2026-10-25-field` — **Gate G0 PASS** (provisional).  
N=27 asks · 5 users · recurrence 42.0% · median chunk 528 · WS hit 42.0%.  
Synthetic partner_v1 tokens → not final.

## Run ladder

| Artifact | N | Users | Recurrence | Median chunk | Gate |
|---|---:|---:|---:|---:|---|
| `…-10-24-auto` | 3 | 1 | 11% | 250 | FAIL |
| `…-10-24` | 30 | 5 | 31.2% | 250 | FAIL (chunk only) |
| `…-10-25` | 82 | 10 | 45.2% | 250 | FAIL (chunk only) |
| `…-10-25-chunkfix` | 17 | 3 | 53.2% | 250 | FAIL (`build_index` still 1000) |
| `…-10-25-chunk2048` | 3 | 1 | 65.3% | 512 | PASS (smoke, 1 user) |
| **`…-10-25-field`** | **27** | **5** | **42.0%** | **528** | **PASS provisional** |

## What we learned

1. Multi-user reuse showed up before the chunk fix (31–45% at N=30–82).
2. G0 was blocked by `retrieve.build_index(chunk_chars=1000)` — fixed in cw-field `4ca4d7a`.
3. Post-fix multi-user sample clears all three bars (recurrence, median chunk, working-set).

## Claim language

- **Allowed:** Provisional partner-field G0 PASS on live cw-field traffic (N=27, 5 users, synthetic token IDs).
- **Not allowed:** Final / production-tokenizer G0.

## Keep

Prefer `cw-field-g0-2026-10-25-field` as the cited bank. Older FAIL / smoke runs are ladder history only.

## Product follow-up (closed)

Field order A/B Layer 1: `artifacts/product-field-order-ab-2026-10-25/` — frequency
**+5.64 pp** prefix share vs natural (desk PASS, pre-reg FAIL). **Layer 2 skipped;**
cw-field keeps frequency default. See `Docs/product/field-order-ab.md` and
`Docs/status/closeout-product-v0.md`.
