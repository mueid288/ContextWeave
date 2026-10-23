# Design-partner ask (short)

**Subject:** Anonymized RAG request trace for KV-cache research (no prompts, no GPU ask)

Hi —

I'm researching whether recurring documents in RAG prompts create enough *non-prefix* reuse to matter after normal prefix caching (project: ContextWeave).

Could you share an anonymized JSONL export from a few hundred–thousand requests? Need only:

- `request_id`
- system-prefix token count (or token ids)
- per retrieved chunk: stable `document_id`, `content_hash` (sha256 of normalized text), `token_count`
- `query_type`: `lookup` (1 doc) or `synthesis` (2+ docs)
- optional query token count

**Please do not send** raw prompts, answers, user PII, or API keys.

Schema + tiny example: `docs/trace-schema.md` and `benchmarks/trace_analysis/examples/partner_v1_sample.jsonl`.

Happy to sign an NDA and keep the file offline. One export is enough for our Phase 0 demand gate.

Thanks  
[Your name]
