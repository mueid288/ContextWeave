# Response to Gemini PRD review (`Gemini_1.md`)

**Date:** 14 October 2026  
**Disposition:** Accept all seven technical points; encode as binding **PRD v2.1 amendments** and repo changes below.

## Summary

| # | Issue | Disposition | Where fixed |
|---|---|---|---|
| 1 | Thin wedge / intra-workload variance | Accept | Amendments §A |
| 2.1 | H3 control/data-plane paradox | Accept | Amendments §B (two-stage planner) |
| 2.2 | Oracle max-of-N bias | Accept | Amendments §C (non-inferiority + predictability) |
| 2.3 | Repair FLOPs / page align | Accept | Amendments §D; `costmodel/breakeven.py`; block pad |
| 2.4 | Pre vs post-RoPE bake-off | Accept — drop bake-off | Amendments §E |
| 2.5 | HijackKV Mode A vs B | Accept Mode A only | Amendments §F; `provenance/trust.py` |
| 2.6 | G0 ignores working set | Accept | Amendments §G; `--cache-budget-gb` |
| 2.7 | Tokenizer non-homomorphism | Accept | Amendments §H; `tokenization/boundaries.py` |
| Extra | GPU-hours 350–400; paired bootstrap; plan API fields; Llama scaling note | Accept | Amendments §D,I,J,K |

Canonical amendment text: [`Docs/prd/contextweave_prd_v2.1_amendments.md`](../prd/contextweave_prd_v2.1_amendments.md).

## Strategic note (thin wedge)

We agree: if the best config is stable per model×task, ContextWeave collapses to an offline recipe. Phase 1 must quantify **intra-slice** request-level variance and G2 predictability ≥50% before building a runtime control plane.

## Not done in this pass (needs GPU / Phase 1+)

- Implementing Stage-1 in-flight bailout in a real runtime  
- Running the corrected G2 oracle on GPU  
- Measuring true repair HBM behavior  

CPU harness + normative PRD text are updated so those experiments are not mis-designed.
