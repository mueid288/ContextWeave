# Path C — Corpus-backed replay (provisional G0)

Use this when you have **documents** but no serving-log export and no GPU budget.

## What it does

1. Reads `.md` / `.txt` from a folder  
2. Chunks them (target ~800 tokens via `chars/4`)  
3. Emits `partner_v1.jsonl` with `document_id`, `content_hash`, `token_count`  
4. Optionally imports + runs Gate G0 (**always provisional**)

## Quick start

```bash
source .venv/bin/activate

# Bundled sample docs
python scripts/build_corpus_trace.py --analyze \
  --report benchmarks/reports/g0_corpus_replay.md

# Your own docs
python scripts/build_corpus_trace.py \
  --corpus-dir /path/to/your/docs \
  --config configs/workloads/corpus_replay_default.yaml \
  --out-dir benchmarks/workloads/my_corpus \
  --analyze \
  --report benchmarks/reports/g0_my_corpus.md
```

## Honesty rules

| Claim | OK? |
|---|---|
| Real document text used | Yes |
| Real production traffic mix | **No** — simulated Zipf + reuse |
| Real model tokenizer | **No** — `chars_per_token` estimate |
| Final G0 for PRD gate | **No** — provisional until a serving trace |

## Next upgrade

Replace Path C with a partner `partner_v1` export from a live RAG stack ([trace-schema.md](trace-schema.md)).
