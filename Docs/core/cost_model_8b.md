# Cost model — PRD §7.5 (planning estimates)

**CPU-only. Not a measurement.** Overlap (pipelined load/recompute) would improve reuse further.

- Model: `dense-8b-gqa` P=8.00e+09, L=32, d_model=4096, H_kv=8, d_h=128
- KV dtype bytes/scalar: 2.0 → **128 KiB/token**
- Assumed effective compute: 450.0 TFLOP/s
- Assumed HBM bandwidth: 2000 GB/s (repair roofline)
- KV block size (alignment): 16
- Repair fraction r=15% — **roofline** used for break-even (naive r×T_prefill shown for contrast)
- Storage: 1e6 cached tokens ≈ **131.1 GB**

| Context N | KV size | Est. full prefill | PCIe_5.0 | PCIe_4.0 | 100GbE | NVMe_Gen4 | 25GbE | Break-even GB/s (0% / 15% repair) |
|---|---|---|---|---|---|---|---|---|
| 10,000 | 1.31 GB | 0.41 s | 0.03 s | 0.05 s | 0.12 s | 0.22 s | 0.47 s | 3.2 / 4.0 |
| 32,000 | 4.19 GB | 1.73 s | 0.08 s | 0.17 s | 0.38 s | 0.70 s | 1.50 s | 2.4 / 3.5 |
| 100,000 | 13.11 GB | 9.38 s | 0.26 s | 0.52 s | 1.19 s | 2.18 s | 4.68 s | 1.4 / 2.4 |

## Repair time: naive vs HBM roofline (v2.1)

| N | Naive r×T_prefill | HBM read S_KV | Roofline T_repair |
|---|---|---|---|
| 10,000 | 0.062 s | 0.0007 s | 0.088 s |
| 32,000 | 0.260 s | 0.0021 s | 0.529 s |
| 100,000 | 1.407 s | 0.0066 s | 4.029 s |

## Serialized win matrix (load + **roofline** repair < prefill)

- N=10,000: wins on PCIe_5.0, PCIe_4.0, 100GbE, NVMe_Gen4; loses on 25GbE
- N=32,000: wins on PCIe_5.0, PCIe_4.0, 100GbE, NVMe_Gen4; loses on 25GbE
- N=100,000: wins on PCIe_5.0, PCIe_4.0, 100GbE, NVMe_Gen4, 25GbE; loses on none

## Implications (PRD + v2.1)

- Host memory / fast PCIe often clear the load bar; **scattered repair** may still be HBM-bound and erase naive TFLOP savings.
- Short contexts over slow links (e.g. 25 GbE at 10k) can lose if load is serialized.
- Chunk lengths should be multiples of `kv_block_size` (pad/mask tails).
- Corpus storage, not just per-request TTFT, drives cost.
- Tables above remain **planning estimates**, not H4 validation.

## Measured A100 anchors (G1 — not H4)

Source: `artifacts/g1-diag-2026-10-23/` + earlier G1 steps. Colab A100, Qwen3-8B,
vLLM 0.18 / lmcache 0.4.2 (blend in-process). **Quality-constrained KPI still fails**
for CacheBlend even where latency looks soft-positive.

| Scenario | p50 TTFT | Notes |
|---|---|---|
| Native prefix warm ABC @~12k | **~41 ms** | Exact prefix hit |
| Native reorder @~12k | **~924 ms** | Prefix miss on reorder |
| Blend warm ABC @~12k | **~619 ms** | Same-order LMCache hit (not as fast as native prefix) |
| Blend warm BAC @~12k | **~622 ms** | Non-prefix engage (~7705 cached tok) |
| Blend warm CBA @~12k | **~1065 ms** | ≈miss (cached ~19); slower than cold |
| Blend cold ABC @~12k | **~930 ms** | |
| Blend reorder (bac+cba median) vs native reorder | **~1.10×** | Below 1.15× Gate E; Gate D bac agree 0.67 |
| Full vs prefix @6k (earlier G1 step 1) | **~2.57×** | Prefix gap is real |

**Planner implication:** do not treat §7.5 “reuse wins on PCIe” as permission to pick
C4. Use measured quality + ≥15% bar (`contextweave.planner.v0`). H4 (cost-model
±20% vs measured) remains **untested** — needs a dedicated Phase 2 comparison.
