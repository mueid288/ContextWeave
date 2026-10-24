# Pre-registration: Own-corpus RAG demo (C1 via cw-serve-order)

**Status:** READY (written before first GPU bench)  
**Date:** 2026-10-24  
**Depends on:** Product v0 closeout · live shim · `cw-serve-order`  
**Not a PIC / EPIC / CacheBlend / H3 / ResolventKV reopen.**

## One question

On Colab A100, vLLM + `--enable-prefix-caching`, owner demo corpus (or
`benchmarks/corpora/sample_docs` until Own-corpus has documents) + lexical
top‑k, does frequency-stable order via `cw-serve-order` achieve warm p50
speedup **≥1.15** vs shuffled chunk order on the fixed question suite?

## Pass / fail / block

| Outcome | Next |
|---|---|
| PASS | Demo README claims live C1 on this corpus; stop |
| FAIL | Bank numbers; demo still usable for ask; **no PIC reopen** |
| Block | One OOM/config retry; else close unreproducible |

## Fixed protocol

| Item | Value |
|---|---|
| Session | `cw-own-rag-demo` |
| Cap | **90 min** |
| Model | `mistralai/Mistral-7B-Instruct-v0.2` |
| Server | vLLM OpenAI + `--enable-prefix-caching` |
| Shim | `cw-serve-order` with `CW_UPSTREAM_URL` → vLLM |
| Corpus | Own-corpus if non-empty `.md`/`.txt`; else `benchmarks/corpora/sample_docs` |
| Harness | `cw-rag-demo bench` |
| Questions | `configs/product/own_rag_demo_questions.yaml` (N≥8) |
| Warm | 1 discard + ≥8 warm trials per mode |
| Pass bar | `speedup_shuffled_over_frequency ≥ 1.15` **or** explicit FAIL banked |
| Functional | ≥5 answers contain owner-defined gold substring |

## Result (fill after GPU)

| Mode | warm p50 | gold_ok rate |
|---|---:|---:|
| shuffled | _TBD_ | _TBD_ |
| frequency | _TBD_ | _TBD_ |

- Speedup: _TBD_  
- `pass_heuristic`: _TBD_  
- Artifacts: `artifacts/own-rag-demo-YYYY-MM-DD/`  

## Procedure

See `Docs/product/colab-own-rag-demo.md`.
