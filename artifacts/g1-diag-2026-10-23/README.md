# G1-DIAG artifacts — 2026-10-23

Session `cw-g1-diag` (Colab A100). **Full JSON tarball was not collected before
`colab stop`** — VM disk is gone. Numbers below are reconstructed from the
operator paste in chat (same session). Treat as **summary-only**, not a full
reproducible freeze.

| File | Role |
|---|---|
| `g1_diag_summary.json` | Reconstructed Gate B/D/R/E summary from paste |

**Missing (unrecoverable):** `g1_ttft_*_12k_chunks.json`, `g1_matched_*.json`,
`g1_diag_pip_freeze.txt`, lmcache server logs, per-trial engagement arrays.

- Gate B PASS; Gate D PASS (agree=1.0); Gate R **ENGAGEMENT_FAIL** got=0 need≥8063
- Gate E SKIPPED (correct)
- blend warm_abc p50 **188** ms; reorder/cold ≈ **947–955** ms
- Narrative: `Docs/experiment-log.md` (2026-10-23 G1-DIAG entry)
