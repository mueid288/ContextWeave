# Pre-registration: Live canonical-order shim (CPU) + quality bar (GPU later)

**Status:** Part A **PASS** (desk) · Part B **PARKED** (GPU quality)  
**Depends on:** product canonical-order PASS  
**Not a PIC reopen.**

## Part A result

`FrequencyPrior` + `apply_chat_documents` + `cw-serve-order` (--reorder-json /
stdlib proxy). Unit tests in `tests/unit/test_live_order.py`. No GPU.


## Part A — Live shim (CPU, this lane)

### One question

Can a local OpenAI-compatible shim reorder `cw_documents` with a **rolling
frequency prior** (cold-start → `by_doc_id`), rewrite the user message, and
optionally forward to an upstream `/v1/chat/completions` URL — with unit tests
and a dry-run reorder path that needs no GPU?

### Pass

- `FrequencyPrior` observe/snapshot works; cold_start_n uses `by_doc_id`
- `apply_chat_documents` reorders and injects docs into messages
- `cw-serve-order --dry-run` (or `/v1/cw/reorder`) returns ordered docs + rewritten messages
- cpu_gate green; no torch/vllm on laptop

## Part B — Quality bar (GPU, separate session, 90 min cap)

### One question

On A100 (or available GPU), needle/multi-doc suite: does `by_frequency_desc`
keep contains/agree within **≥0.90 of relevance-order C0** at the same scale?

| Outcome | Next |
|---|---|
| PASS | Default shim to frequency order |
| FAIL | Keep shim; default `natural` / relevance; document caveat |
| Block | Close quality as unverified; shim stays opt-in |

**Part B is PARKED** until Part A ships and owner starts a GPU session.
