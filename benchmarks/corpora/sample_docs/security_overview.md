# Security Overview

## Encryption
Data in transit uses TLS 1.2+. Data at rest uses AES-256. Customer-managed keys are available on Enterprise. Secrets never appear in application logs by default.

## Isolation
Workspaces are logically isolated. Cross-tenant cache reuse is forbidden. Build-context fingerprints must include model revision, tokenizer, and any prefix tokens used during KV construction.

## Access control
RBAC roles include Viewer, Developer, Admin, and Billing. SSO and SCIM are supported for Enterprise. API keys inherit the creator's permission ceiling unless constrained.

## Auditing
Admin actions emit immutable audit events. Customers can export audits via API. Security reviews for new inference features require threat-model sign-off when caches are shared.

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
