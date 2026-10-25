# Trace schema (Gate G0)

CPU-only. No model weights. Traces are JSONL (one request per line).

## Canonical format (analyzer input)

What `analyze_trace.py` consumes. Synthetic generator and the importer both emit this.

| Field | Type | Required | Notes |
|---|---|---|---|
| `request_id` | string | yes | Stable id |
| `query_type` | `"lookup"` \| `"synthesis"` | yes | Synthesis = multi-doc reasoning |
| `prefix_token_ids` | int[] | yes | System / instruction prefix (may be empty) |
| `chunk_token_ids` | int[][] | yes | Document chunks in prompt order |
| `chunk_lengths` | int[] | yes | `len` of each chunk |
| `document_ids` | string[] | yes | Parallel to chunks |
| `query_token_ids` | int[] | yes | User question / task tokens |
| `token_ids` | int[] | yes | Full prompt = prefix + concat(chunks) + query |
| `context_length` | int | optional | Equals `len(token_ids)` if present |

Recurrence is detected by **exact `chunk_token_ids` match** (or by stable ids derived from `content_hash` after import).

## Partner / real-trace export (importer input)

Looser schema for serving logs. Convert with:

```bash
python scripts/workloads/import_trace.py \
  --input path/to/partner.jsonl \
  --format auto \
  --out benchmarks/workloads/partner_imported/trace.jsonl
```

### Format `canonical`

Already canonical — validated and copied (or lightly filled).

### Format `partner_v1` (recommended for design partners)

```json
{
  "request_id": "2026-10-11T12:00:00Z#42",
  "query_type": "synthesis",
  "prefix_token_count": 256,
  "prefix_content_hash": "sha256:system-prompt...",
  "chunks": [
    {
      "document_id": "policy-v3",
      "content_hash": "sha256:abc...",
      "token_count": 2048
    },
    {
      "document_id": "faq-12",
      "token_ids": [10, 11, 12]
    }
  ],
  "query_token_count": 12,
  "segments_canonical": false,
  "timestamp": "2026-10-11T12:00:00Z"
}
```

Hash/count exporters (e.g. **cw-field**) may omit real `token_ids` and send counts + hashes instead. Prefer `prefix_token_ids` / `query_token_ids` when the serving stack logged them.

Rules:

- Prefer real `token_ids` when the serving stack logged them.
- If only `content_hash` + `token_count` exist, the importer synthesizes a **stable** token sequence from the hash so recurrence still works. Mark meta `token_ids_synthetic: true`.
- **`prefix_content_hash` (or `prefix_id`)** is required for honest prefix-cache metrics when using `prefix_token_count`. Salting synthetic prefixes on `request_id` alone makes every ask look like a cold prefix.
- Set **`segments_canonical: true`** only when segment lengths already include §H boundary-then-pad. cw-field emits `false` (char/4 approx). Default on import is `false`.
- `query_type`: `synthesis` only when ≥2 distinct documents; else `lookup`.
- Do **not** put raw prompt text in shared repos without partner approval. Prefer hashes + counts.

### Format `text_approx` (last resort)

```json
{
  "request_id": "r1",
  "query_type": "lookup",
  "prefix_text": "You are a helpful assistant.",
  "chunks": [
    {"document_id": "d1", "text": "...long document..."}
  ],
  "query_text": "What is the refund policy?"
}
```

Tokenization ≈ `max(1, ceil(len(text) / chars_per_token))` with a stable hash-derived id stream.  
**G0 from this format is approximate** — report as provisional.

## Path C (no partner yet)

Build a provisional `partner_v1` file from a folder of `.md`/`.txt` docs:

```bash
python scripts/workloads/build_corpus_trace.py --corpus-dir benchmarks/corpora/sample_docs --analyze
```

Details: [path-c-corpus-replay.md](path-c-corpus-replay.md).

## Privacy

- Default: no prompt text in analyzer logs.
- Strip or hash PII before committing traces.
- Partner traces stay under `benchmarks/workloads/` (gitignored) unless explicitly approved.
