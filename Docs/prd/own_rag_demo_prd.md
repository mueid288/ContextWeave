# PRD: Own-corpus RAG demo with ContextWeave C1 shim

**Status:** DRAFT for implementation (handoff to new agent)  
**Date:** 2026-10-24  
**Owner:** ContextWeave product track (post v0 closeout)  
**Depends on (already shipped — do not rebuild):**

- Product v0 closeout: `Docs/status/closeout-product-v0.md`
- Live shim: `Docs/product/live-shim.md`, `cw-serve-order`, `contextweave.product.*`
- Evidence: sim lift, quality PASS, live TTFT **1.79×** (`artifacts/product-order-ttft-2026-10-24/`)
- Research Phase 0/1: **ARCHIVED** — do **not** reopen PIC / EPIC / CacheBlend / H3 / ResolventKV

---

## 1. Problem

ContextWeave’s product v0 (canonical document order → native prefix-cache / C1)
is proven on synthetic needles and a controlled TTFT harness, but there is **no
partner traffic**. Without a system that issues real multi-doc questions over a
corpus, the shim cannot be exercised as an integration.

This PRD specifies a **small, owner-operated RAG demo** that:

1. Indexes a local document corpus the owner already controls  
2. Retrieves top‑k chunks per question  
3. Sends them through **`cw-serve-order`** (frequency-stable order) into a vLLM
   OpenAI server with **prefix caching enabled**  
4. Measures whether warm latency improves vs shuffled retrieval order on
   **that** corpus  

This is not a multi-tenant SaaS. It is a **demo + measurement loop** so the
product has “real enough” prompts without a partner.

---

## 2. Goals

### Primary (must)

- **G1.** End-to-end path: `question → retrieve k chunks → cw_documents → shim → vLLM → answer`
- **G2.** A/B warm latency on the demo corpus: **frequency order vs shuffled order**,
  same questions, vLLM `--enable-prefix-caching`, report p50 and speedup
- **G3.** Laptop-safe CPU pieces (index, retrieve, client, eval orchestration);
  model load **only** on GPU host with `CONTEXTWEAVE_ALLOW_MODEL_LOAD=1`
- **G4.** One Colab/runbook the owner can paste; bank artifacts under
  `artifacts/own-rag-demo-YYYY-MM-DD/`

### Secondary (should)

- Simple CLI: `cw-rag-demo ask "…"` and `cw-rag-demo bench`
- Reuse existing corpus paths (`benchmarks/corpora/sample_docs` and/or Path C
  `my_corpus` if present on disk)
- Document how to swap corpus directory

### Non-goals (must not)

- Partner onboarding, auth, billing, multi-tenant priors  
- Reopening non-prefix PIC (C3/C4), EPIC, CacheBlend, ResolventKV  
- Training / fine-tuning  
- Replacing vLLM; building a new inference engine  
- Claiming production readiness beyond “demo on owner corpus”  
- Downloading models on the laptop  

---

## 3. Users & success

| User | Success looks like |
|---|---|
| Owner (solo) | Can run ask + bench on Colab against own docs in ≤90 min GPU |
| New agent | Implements from this PRD without reading the full research archive |
| Future reader | Artifacts + README prove the demo ran and whether C1 lift held on this corpus |

**Acceptance bar (pre-register before GPU):**

| Metric | Pass |
|---|---|
| Functional | ≥5 demo questions return non-empty answers containing an expected gold substring (owner-defined list) |
| Latency | Warm p50 speedup `shuffled / frequency ≥ 1.15` on the demo bench (same protocol spirit as `eval_order_ttft.py`) **or** explicit FAIL banked with numbers |
| Hygiene | No torch/vllm in laptop venv; cpu_gate still green |

If latency FAIL: still ship the demo; document “no live C1 lift on this corpus/retriever”; do not reopen PIC.

---

## 4. Architecture

```text
┌─────────────┐     top-k chunks      ┌──────────────────┐
│  Corpus     │ ───────────────────►  │  rag_demo client │
│  (md/txt)   │   {document_id,       │  (CPU)           │
│  + index    │    content}[]         └────────┬─────────┘
└─────────────┘                                │
                                               │ POST /v1/chat/completions
                                               │ + cw_documents
                                               │ + cw_chunk_order
                                               ▼
                                      ┌──────────────────┐
                                      │  cw-serve-order  │
                                      │  FrequencyPrior  │
                                      └────────┬─────────┘
                                               │ stripped OpenAI body
                                               ▼
                                      ┌──────────────────┐
                                      │  vLLM OpenAI     │
                                      │  + prefix cache  │
                                      └──────────────────┘
```

**Reuse existing code — do not duplicate:**

| Need | Use |
|---|---|
| Reorder + inject docs | `contextweave.product.live_order.apply_chat_documents` |
| Rolling frequency | `contextweave.product.frequency.FrequencyPrior` |
| HTTP shim | `cw-serve-order` / `contextweave.product.proxy` |
| TTFT A/B pattern | Mirror `scripts/product/eval_order_ttft.py` |
| Safety | `contextweave.safety.assert_model_load_allowed` only if anything loads weights (prefer HTTP-only client) |

---

## 5. Functional requirements

### FR-01 Corpus ingest (CPU)

- Input: directory of `.md` / `.txt` (default: `benchmarks/corpora/sample_docs`;
  optional override `--corpus` for owner `my_corpus` if available)
- Chunking: fixed char or token-approx windows (e.g. ~800–1200 chars, 100 overlap);
  `document_id` = `{stem}::chunk-{idx:03d}` (natural-sortable, matches existing CW style)
- Persist index under `artifacts/own-rag-demo/index/` (JSONL or sqlite — pick one, keep simple)
- No embeddings **required** for v0 of this demo: **lexical retriever** (BM25 or TF‑IDF /
  whoosh / rank_bm25) is enough so laptop stays light  
  - Optional later: embedding retriever behind a flag; not blocking

### FR-02 Retrieve (CPU)

- `retrieve(question, k=3) -> list[{document_id, content}]`
- Deterministic given seed / frozen index
- CLI prints retrieved ids for debugging

### FR-03 Ask path (CPU client → GPU server)

- Build OpenAI chat body:
  - `messages`: user question (and optional short system)
  - `cw_documents`: retrieved chunks
  - `cw_chunk_order`: `by_frequency_desc` (default) or `natural` / shuffle for A/B
- POST to shim base URL (default `http://127.0.0.1:8080`) which forwards to vLLM
- Print answer + `cw_meta` if returned

### FR-04 Bench path (measurement)

- Fixed question set (N≥8) written in repo under e.g.
  `configs/product/own_rag_demo_questions.yaml` with optional `gold` substrings
- For each mode `shuffled` | `frequency`:
  - 1 warmup discard
  - ≥8 warm trials (reuse questions in a loop or repeat suite)
  - Record wall ms, contains vs gold if present
- Report JSON: p50/mean per mode, speedup, pass_heuristic (≥1.15), artifact path
- **Shuffled mode:** permute retrieved chunk order per trial (not the corpus)
- **Frequency mode:** go through shim with `by_frequency_desc` and warm prior
  (observe retrieval ids across the suite, or pre-warm from index popularity)

### FR-05 Runbooks

- `Docs/product/colab-own-rag-demo.md`: Colab A100 ≤90 min — install vLLM with
  `--enable-prefix-caching`, start `cw-serve-order` with `CW_UPSTREAM_URL`, run
  `cw-rag-demo bench`, bank artifacts, stop session
- Laptop: index + dry retrieve without GPU

### FR-06 Tests (CPU)

- Unit: chunker ids, retrieve returns k, ask client builds correct `cw_documents`
- Unit: bench dry-build (no HTTP) constructs two mode payloads
- Optional: mock upstream + shim (extend existing `tests/unit/test_proxy_forward.py` pattern)
- `scripts/ci/cpu_gate.sh` must stay green; no new required GPU deps in default extra

---

## 6. Non-functional requirements

| ID | Requirement |
|---|---|
| NFR-01 | Default deps remain laptop-safe (no torch/vllm in base `pyproject` install) |
| NFR-02 | GPU work only via HTTP to remote OpenAI-compatible server |
| NFR-03 | Session time cap documented (90 min); OOM fallback: smaller `max-model-len`, smaller k, shorter chunks |
| NFR-04 | Honest labeling: demo corpus ≠ partner production traffic |
| NFR-05 | Do not break existing product CLIs (`cw-serve-order`, `cw-analyze-trace`, …) |

---

## 7. Suggested layout (implementer may adjust)

```text
src/contextweave/product/rag_demo/
  __init__.py
  chunk.py          # ingest + document_id scheme
  index.py          # build/load lexical index
  retrieve.py       # top-k
  client.py         # ask() HTTP
  bench.py          # A/B latency
src/contextweave/cli/rag_demo.py   # cw-rag-demo
configs/product/own_rag_demo_questions.yaml
Docs/product/colab-own-rag-demo.md
Docs/pre-reg/pre-reg-own-rag-demo.md   # one-question GPU pre-reg before Colab
tests/unit/test_rag_demo_*.py
artifacts/own-rag-demo-YYYY-MM-DD/     # banked after GPU
```

Entry point in `pyproject.toml`:

```toml
cw-rag-demo = "contextweave.cli.rag_demo:main"
```

---

## 8. Pre-registration (write before first GPU bench)

File: `Docs/pre-reg/pre-reg-own-rag-demo.md`

**One question:** On Colab A100, vLLM + prefix caching, owner demo corpus + lexical
top‑k, does frequency-stable order via `cw-serve-order` achieve warm p50 speedup
≥1.15 vs shuffled chunk order on the fixed question suite?

| Outcome | Next |
|---|---|
| PASS | Demo README claims live C1 on this corpus; stop |
| FAIL | Bank numbers; demo still usable for ask; no PIC reopen |
| Block | One OOM/config retry; else close unreproducible |

---

## 9. Implementation order (for the new agent)

1. Read this PRD + `Docs/status/closeout-product-v0.md` + `Docs/product/live-shim.md`  
2. Write `pre-reg-own-rag-demo.md` (status READY)  
3. CPU: chunk → index → retrieve → unit tests  
4. CPU: `cw-rag-demo ask` against dry-run shim (`cw-serve-order` without upstream)  
5. CPU: bench dry-build + HTTP client  
6. Colab runbook; owner runs GPU; agent banks artifacts + updates pre-reg PASS/FAIL  
7. Update `Docs/status/pause.md` / experiment-log with one entry — **then stop**

Do **not** start GPU until steps 1–5 pass `cpu_gate`.

---

## 10. Out-of-scope reminders for the agent

- No “fix EPIC quality” or “reopen G2”  
- No partner schema work unless needed for optional import later  
- No new planner C3 path  
- Prefer extending `product/` over inventing a second shim  

---

## 11. Definition of done

- [ ] `cw-rag-demo` ask + bench exist; cpu_gate green  
- [ ] Pre-reg written before GPU  
- [ ] Colab runbook executed; artifacts banked  
- [ ] Pre-reg marked PASS or FAIL with numbers  
- [ ] Short note in `Docs/status/experiment-log.md`  
- [ ] No open “next lane” unless owner provides a new goal  

---

## 12. References

- `Docs/status/closeout-product-v0.md`  
- `Docs/product/live-shim.md`  
- `Docs/product/canonical-order.md`  
- `Docs/product/colab-order-ttft.md` (Colab + prefix-caching pattern to copy)  
- `scripts/product/eval_order_ttft.py`  
- `benchmarks/corpora/sample_docs/`  
- Laptop policy: `Docs/runbooks/local-safety.md`  
