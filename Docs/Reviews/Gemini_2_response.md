# Response to Gemini review 2

**Date:** 14 October 2026  
**Status:** Accepted — wiring bugs fixed in code + v2.1.1 clarifications

| Finding | Disposition |
|---|---|
| §1.1 Denominator mismatch (79% > 74.6%) | **Fixed.** Working-set decision share uses `post_prefix_prefill_tokens`. |
| §1.1 Cold prefix tokens vanishing | **Fixed.** `uncovered_prefix_tokens` counted; report asserts bucket sum. |
| §1.2 Silent short-doc padding | **Fixed.** Off by default; `--pad-short-docs-for-demo` only. |
| §1.3 `boundaries.py` disconnected | **Fixed.** Wired into synthetic / import / corpus; analyzer honors `segments_canonical`. |
| §1.4 Duplicate chunks + weak `hash()` | **Fixed.** Exhaustive dedupe; SHA-256 via `hash_token_ids`. |
| §2.1 Roofline math | **Fixed.** Linear at peak TFLOP/s; attention only /eff; weight HBM. |
| §2.2 Untrusted same-NS + lifecycle | **Fixed.** `assert_reuse_allowed` blocks UNTRUSTED and non-AVAILABLE. |
| §2.3 RoPE / unpinned / PRE_ROPE / `or 1` | **Fixed.** Allowlist `{default,llama3}`; block unpinned; POST_ROPE; raise on missing YAML fields. |
| §3 CLI import without working-set | **Fixed.** Shared flags on `import_trace` / `build_corpus_trace`. |
| §3 Stale reports | **Regenerated** under `benchmarks/reports/`. |
