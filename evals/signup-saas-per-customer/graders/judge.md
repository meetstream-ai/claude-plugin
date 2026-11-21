---
type: llm
weight: 2
---
PASS if the reply gives a per-customer (multi-tenant) setup using MeetStream features: tag every bot with the customer or tenant id in `custom_attributes` and route webhook events on it (per-bot `callback_url` or workspace webhooks), connect each end user's calendar as its own calendar connection if they want auto-join, optionally a storage destination per customer with `storage_id`, AND it covers scale: the bot-creation limit for prepaid accounts (429 with Retry-After) and scheduling with `join_at` 10 or more minutes ahead, AND it notes that Zoom calls need the user's Zoom app (OBF or ZAK) for meetings outside their own Zoom account.
FAIL if the reply suggests a voice agent, says Zoom needs no setup, invents endpoints or fields not in the MeetStream docs, or writes a full multi-file app.
