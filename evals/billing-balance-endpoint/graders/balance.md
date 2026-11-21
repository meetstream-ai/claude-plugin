---
type: llm
weight: 1
---
PASS if the reply gives `GET https://api.meetstream.ai/api/v1/billing/balance` with `Authorization: Token <key>` as the read-only balance call, AND says that if it answers "not available" (or 404) on the account, that is expected and the balance is on the billing page https://app.meetstream.ai/billing (where credits are added).
FAIL if it invents another route, invents a balance number or response fields as fact, or tells the user to retry or debug a "not available" answer.
