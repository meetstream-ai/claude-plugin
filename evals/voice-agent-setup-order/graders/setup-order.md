---
type: llm
weight: 2
---
PASS if the reply recommends MeetStream-managed keys first (`"key_source": "meetstream"` in the agent config, no provider keys of the user's own, billed by MeetStream), offers the user's own provider keys as the alternative, and either does not mention running the user's own agent on their computer or mentions it only with a warning about prompt injection or exposing their computer to the meeting.
FAIL if the reply starts with the user's own provider keys, wake words or mode questions before the setup choice, presents a local agent without a warning, or invents MCP tools for creating the agent.
