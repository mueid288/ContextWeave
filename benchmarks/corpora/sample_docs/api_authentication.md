# API Authentication Guide

## API keys
Each workspace can create up to 50 API keys. Keys are shown once at creation; store them in a secret manager. Rotate keys at least every 90 days. Prefix `ack_` denotes a live key; `act_` denotes a test key that cannot mutate production resources.

## OAuth clients
Machine-to-machine flows use client credentials. Human interactive flows use authorization code with PKCE. Redirect URIs must be pre-registered and use HTTPS except for localhost during development.

## Scopes
Common scopes include `inference:run`, `corpus:read`, `corpus:write`, and `billing:read`. Least privilege is required for partners. Tokens with `admin:*` scopes cannot be issued to third-party OAuth apps.

## Rate limits
Default is 600 requests/minute per API key and 6,000/minute per workspace. Burst tokens refill continuously. 429 responses include `Retry-After`. Sustained abuse triggers temporary key suspension.

## Errors
Authentication failures return 401 with a stable error code. Authorization failures return 403. Clock skew beyond 5 minutes invalidates signed requests. See the status page before opening incidents for widespread 5xx.

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
