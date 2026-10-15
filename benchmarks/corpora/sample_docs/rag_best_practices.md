# RAG Best Practices (Internal)

## Chunking
Prefer 500–1,000 token chunks with 10–15% overlap for narrative docs. Keep tables and code fences intact when possible. Record chunk boundaries and content hashes in the index metadata for cache reuse experiments.

## Retrieval
Use hybrid lexical + embedding retrieval. Cap top-k at 8 for latency-sensitive apps. Deduplicate near-identical chunks before prompt assembly. Log document ids and token counts per request for demand analysis.

## Prompt assembly
Place system instructions first, then documents in relevance order unless the task requires chronological order. Keep the user question last. Avoid stuffing the same document twice in one request.

## Evaluation
Track groundedness, citation accuracy, and refusal quality. Report aggregate and adjusted metrics when the baseline model fails a large share of questions. Never treat cache hit rate as a success metric alone.

## Operations
Invalidate embeddings and KV artifacts when source documents change. Namespace caches by trust boundary. Prefer canonical build contexts for any reusable KV store.

## Additional reference notes
Paragraph 1: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 2: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 3: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 4: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 5: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 6: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 7: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 8: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 9: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 10: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.

Paragraph 11: operational guidance for implementers integrating Acme APIs, including retries, idempotency keys, pagination cursors, and workspace quotas. Teams should document assumptions, monitor error budgets, and keep runbooks current. When assembling long contexts, prefer stable document identifiers and explicit versions. This filler ensures sample chunks meet minimum length for demand analysis experiments.
