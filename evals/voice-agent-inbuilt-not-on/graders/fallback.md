---
type: llm
weight: 2
---
PASS if the reply says that MeetStream's inbuilt keys are not turned on for the user's account yet (not a bug in their request), and goes on with the user's own provider keys: add the provider key in the dashboard integrations (or the section's `api_key`), drop `"key_source": "meetstream"` (or set it to `"user"`), and save the agent again. It tells the user not to retry the same request in a loop.
FAIL if the reply tells the user to retry the same request, wait and poll, or contact support as the only step; says voice agents cannot work; or explains internal causes such as regions, catalogs or account flags.
