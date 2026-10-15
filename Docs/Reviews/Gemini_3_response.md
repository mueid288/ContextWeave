# Response to Gemini review 3

**Date:** 14 October 2026  
**Status:** Accepted — spec traps closed in v2.1.1; code aligned

| Finding | Disposition |
|---|---|
| §1.1 Boundary shim breaks 16-token alignment | **Fixed.** Boundary-then-pad in `canonicalize_segment_tokens`. |
| §1.2 Dynamic/YaRN allowed in validate | **Fixed.** Allowlist `{"default", "llama3"}` only. |
| §1.3 `allowed_noncanonical` backdoor | **Removed** from schema + validate. |
| §1.4 Example fingerprint PRE_ROPE | **Fixed.** Default `POST_ROPE`. |
| §1.5 Working-set opt-in | **Fixed.** `require_working_set=True` default; CLI BooleanOptionalAction. |
| §1.6 Roofline ≠ §D | **Fixed.** Same formula as Gemini_2 §2.1. |
| Trap 1 (§C ε per-request) | **v2.1.1** ε_req vs ε_slice + UpsideCaptured definition. |
| Trap 2 (§B bailout formula) | **v2.1.1** + `max_tolerable_bailout_rate()`. |
| Trap 3 (infinite prefix cache) | **Fixed.** LRU token budget default 24 GB HBM. |
