# What’s missing — prioritized gaps

**Audience:** maintainers.  
**Baseline:** [READINESS.md](../product/READINESS.md) · [CLAIMS.md](../product/CLAIMS.md) · [ship-v0.2-c1-kit.md](ship-v0.2-c1-kit.md)

## Verdict

The **C1 eval kit is ready for lab outbound**. It is **not** final G0, **not**
live field-TTFT proven, and **not** on PyPI. Default next: outbound with the
kit. Open Layer 2 / PyPI / final G0 only on explicit ask.

## Explicit Missing (gated)

| ID | Gap | Done looks like | Blocker | Effort |
|----|-----|-----------------|---------|--------|
| M1 | Final tokenizer G0 | Real `token_ids` in partner traces; `provisional_g0=false`; G0 PASS; `summary.ok=true` without `--allow-provisional-ok` | cw-field uses chars/4 + `token_ids_synthetic`; DeepSeek returns text only | Large |
| M2 | Field Layer 2 live TTFT | Banked warm p50 frequency/natural ≥ **1.2×** on live field asks | Needs prefix-caching engine (not DeepSeek); ship non-goal | Med–Large |
| M3 | PyPI publish | `pip install contextweave==0.2.0` | Explicit non-goal this tag | Small–Med |

See CLAIMS **Cannot claim** for the same items in integrator language.

### Provisional vs final G0

Gate thresholds (`evaluate_g0`): unconstrained recurring ≥30% of post-prefix,
median chunk ≥512 tokens, LRU working-set hit ≥30% @ 128 GB. **Provisional** =
synthetic / approx tokens (`synthetic_token_rows` or `text_approx_rows`). Banked
field evidence (`artifacts/cw-field-g0-2026-10-25-field/`): N=27, gate PASS,
`ok: false` / `provisional_not_bankable`. `cw-analyze-trace --final` refuses when
`import_meta.provisional_g0=true`.

### Layer 1 vs Layer 2

| Layer | What | Bar | Status |
|-------|------|-----|--------|
| 1 | CPU `--compare-chunk-order` on imported field traces | Desk ≥**+2 pp** `share_prefix_cached`; analyzer pre-reg ≥**+10 pp** or ≥**20%** multi-doc cut | Desk banked (~+5.6 pp); pre-reg not met |
| 2 | GPU live A/B TTFT on field asks | Warm p50 ≥**1.2×** | Skipped (M2) |

## Soft / honesty gaps

| Gap | Status | Notes |
|-----|--------|-------|
| Own-RAG warm ≥1.15× | **Not met** | FAIL banked — [artifacts/own-rag-demo-2026-10-24/](../../artifacts/own-rag-demo-2026-10-24/); harness/`cw-rag-demo` removed from `main` |
| Field A/B analyzer pre-reg | Desk only | +5.64 pp / +8.2% cut; keep soft desk claim |
| Kit dogfood Layer 1 | **Banked (scoped)** | [product-kit-dogfood-2026-10-26](../../artifacts/product-kit-dogfood-2026-10-26/) — +17 pp is **sim** on frequency-arm trace (N=15, provisional, G0 FAIL); not live cross-arm TTFT |
| Process-local `FrequencyPrior` | Known limit | Restarts reset cold start; use `COLD_START_N=0` or filter `order_mode_effective` |

## Capability tracks (ask before starting)

- **M1** — wire real tokenizer or serving-log token IDs into cw-field / import; re-run field G0 non-provisional.
- **M2** — stand up prefix-caching stack; timed natural vs frequency; bank `product-field-order-ttft-*`.
- **M3** — release `0.2.0` with trusted publishing.

## Control plane track (approved 2026-10-26)

Thesis: [../plans/2026-10-26-revolutionary-product-thesis.md](../plans/2026-10-26-revolutionary-product-thesis.md).  
Archive reopen policy: [ARCHIVE.md](ARCHIVE.md).

| ID | Gap | Done looks like | Status |
|----|-----|-----------------|--------|
| R0 | Thesis + docs | Plan approved; north star; CLAIMS future section | **Done** |
| R1 | Oracle upside on LMCache C3 + C1 + C0 | Banked `artifacts/r1-oracle-*` with `r1_pass` | **Blocked** — C0/C1 smoke banked (`artifacts/r1-oracle-2026-10-26/`); C3 serve fatals on lmcache 0.5.6 + vllm 0.32 (`IndexError` dim 4); no `r1_pass` |
| R2 | Fingerprints + plan API | Library + fault suite; 0 silent invalid reuse | Blocked on R1 |
| R3 | Engine provider + field plan UI | Partner-usable quality_margin | Blocked on R2 |

C1 tracks M1–M3 remain optional and orthogonal.
