# Experiment Log

## 2026-10-11 — Phase 0 harness bootstrap (CPU)

- Scaffolded research repo layout from PRD Section 19 (minimal subset).
- Implemented synthetic RAG generator + exact-prefix cache simulator + G0 metrics.
- No GPU used.
- Ran default synthetic workload (`seed=42`, 500 requests).
- **Provisional G0 PASS:** recurring non-prefix share 75.9%, median chunk 900 tokens.
- Artifacts: `docs/g0-provisional-synthetic.md`, `benchmarks/reports/g0_synthetic_rag_default.md`.
- Prior-art desk matrix + GPU runbook written. Quote GPU; rent only after smoke checklist.

## 2026-10-11 — Phase 0B desk deepening (CPU)

- Fetched Qwen3-8B official `config.json`; Llama-3.1 Instruct via NousResearch mirror (official HF gated 401).
- Finding: Llama uses `rope_scaling.rope_type=llama3` factor 8; Qwen3 has `rope_scaling: null` — prefer Qwen3 for Case A/B.
- Candidate pins: LMCache **v0.5.2** + vLLM **≥ 0.26.0**; EPIC Apache-2.0 confirmed.
- Added `synthetic_rag_longctx` workload; baseline runner registry (`scripts/run_baseline.py`).
- Docs: `docs/runtime-pins.md` updated rent-gate checklist.

## 2026-10-11 — Real-trace importer + cost model (CPU)

- Added partner_v1 / text_approx importer (`scripts/import_trace.py`, `docs/trace-schema.md`).
- Added PRD §7.5 break-even cost model (`scripts/cost_model.py`).
- Still no GPU / no local model loads.
- Next human step: obtain a real partner JSONL (hashes + token counts or token ids).

## 2026-10-11 — Path C corpus replay

- Added `scripts/build_corpus_trace.py` + sample corpus under `benchmarks/corpora/sample_docs/`.
- Documents are real local files; request mix simulated; token counts via chars/4.
- G0 from this path stays provisional (see `docs/path-c-corpus-replay.md`).

## 2026-10-11 — Path C on user corpus (`my_corpus`)

- Corpus: 11 files → 127 chunks (WhatsApp Lead Qualifier PRD/tech docs, etc.).
- Provisional G0 **PASS**: recurring non-prefix **74.6%**, median chunk **783**, prefix-cache share 45.3%.
- Report: `benchmarks/reports/g0_my_corpus.md`.
- Still provisional (simulated request mix; chars/4 tokenization; all requests under 8k).

## 2026-10-11 — Fingerprint / provenance schema

- Implemented FR-01/02/04/13 dataclasses + validation + trust boundaries (CPU-only).
- Docs: `docs/fingerprints.md`, partner ask: `docs/partner-ask.md`.

## 2026-10-11 — Cloud GPU rental decision

- Plan: rent **Runpod RTX 4090** for ≤2h smoke with **Qwen3-8B** (~$2–5 cap).
- A100 80GB deferred until smoke passes.
- Guide: `docs/cloud-gpu-rental.md`. Remote smoke script: `scripts/smoke_remote.sh`.
- Pending human: HF account/token, Runpod deploy, terminate pod after smoke.

## 2026-10-12 — Runpod agent setup (Cursor)

- Followed https://docs.runpod.io/agent-setup.md
- Skills installed under `~/.agents/skills/` and symlinked into `~/.cursor/skills/`
- MCP config written: `~/.cursor/mcp.json` + project `.cursor/mcp.json` (hosted API + docs)
- Pending user: restart Cursor / reload MCP, Sign in with Runpod (OAuth) on first tool use
- `submit_feedback` unavailable until `runpod-docs` MCP is connected in-session

## 2026-10-14 — Gemini review gaps closed (CPU)

- Accepted all 7 Gemini findings → `Docs/prd/contextweave_prd_v2.1_amendments.md`
- Response: `Docs/Reviews/Gemini_1_response.md`
- Code: G0 LRU `--cache-budget-gb` / `--require-working-set`; repair HBM roofline;
  boundary token assembly; Mode A build-mode enforcement; block-size padding
- Phase 0 GPU planning buffer raised to 350–400 hours in amendments

## Template for future entries

```
## YYYY-MM-DD — <title>
- Hypothesis / gate:
- Environment (CPU/GPU, drivers, pins):
- Command:
- Result:
- Decision:
```
