---
type: llm
weight: 2
---
Truth: per-bot `callback_url` deliveries are not signed. Deliveries to workspace webhook endpoints configured in the MeetStream dashboard (with a signing secret) carry `X-MeetStream-Signature: sha256=<hex>`, an HMAC-SHA256 of the raw request body with that secret, plus `X-MeetStream-Timestamp`.
PASS if the reply (code or text) says callback_url requests carry no signature to verify (so it does not reject unsigned callback_url requests), explains that signed delivery needs a workspace webhook endpoint with a secret, and describes the X-MeetStream-Signature HMAC-SHA256 check on the raw body.
FAIL if the reply says or implies callback_url deliveries are signed, or invents another header or algorithm.
