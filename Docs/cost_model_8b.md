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
- Confirm with measurement when a GPU is available; do not treat these as G1 results.
