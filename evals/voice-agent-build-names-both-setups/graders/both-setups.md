---
type: llm
weight: 2
---
PASS if the reply names both setups: MeetStream's inbuilt keys (also called MeetStream-managed keys) (`"key_source": "meetstream"`, no provider keys of the user's own) as the default, AND the user's own provider keys as the alternative. Mentioning the user's own agent through the Agent Kit is optional, but if mentioned it must carry a prompt-injection warning.
FAIL if the reply offers only one of the two key setups, or starts with wake words or mode questions before the setup choice.
