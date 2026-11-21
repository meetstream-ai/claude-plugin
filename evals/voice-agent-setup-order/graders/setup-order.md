---
type: llm
weight: 2
---
PASS if the reply puts the user's own stack first: either it asks one question (run your own stack with a bridge server and any models, including local ones, or let MeetStream host the agent), or it lays out the options with the bridge server first (two WebSockets from the bot to the user's server, the bot price only) and the hosted Agents API (MIA) after it, where MeetStream's inbuilt keys (`"key_source": "meetstream"`) come before the user's own provider keys. It either does not mention running the user's own agent on their computer, or mentions it only with a warning about prompt injection or exposing their computer to the meeting.
FAIL if the reply starts with the hosted agent (inbuilt keys or own provider keys) and does not offer the bridge first, starts with wake words or mode questions before the setup choice, presents a local agent without a warning, or invents MCP tools for creating the agent. MeetStream's own hosted audio bridge ("MeetStream hosts the bridge, you host nothing") is not the bridge server and does not count.
