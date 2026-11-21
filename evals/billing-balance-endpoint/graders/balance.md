---
type: llm
weight: 1
---
PASS if the reply gives `GET https://api.meetstream.ai/api/v1/billing/balance` with `Authorization: Token <key>`, says it is read only, and points to https://app.meetstream.ai/billing to add credits.
FAIL if it invents another route, says there is no way to read the balance with the API key, or invents a balance number.
