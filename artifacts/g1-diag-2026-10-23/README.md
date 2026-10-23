# G1-DIAG artifacts — 2026-10-23

Session `cw-g1-diag-2` (Colab A100). In-process CacheBlend + blend hooks
(`g1_blend_hooks.py`). Collected **before** stop.

| File | Role |
|---|---|
| `g1_matched_artifacts_20261023T100338Z.tar.gz` | Session tarball |
| `g1_diag_pip_freeze.txt` | Exact pin freeze |
| `g1_matched_env.json` | Matched install pins |
| `g1_matched_control.json` | Gate C |
| `g1_matched_blend_abc.json` / `g1_matched_blend_bac.json` | Gate D |
| `g1_ttft_native_12k_chunks.json` / `g1_ttft_blend_12k_chunks.json` | Stage E / Gate R |
| `g1_diag_summary.json` | Early paste reconstruction (pre-tarball) |

**Gate R:** `ENGAGEMENT_FAIL` got=7705 need≥8063 (≈66.9% &lt; 70%) — engagement
**proven** vs DIAG #1 got=0; formal bar miss. warm_bac≈warm_abc; warm_cba slow.
Gate E skipped. Narrative: `Docs/experiment-log.md`.
