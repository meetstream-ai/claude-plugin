---
type: llm
weight: 1
---
PASS if the reply explains creating the agent config with POST /api/v1/mia (or in the dashboard), recommends MeetStream's inbuilt keys (also called MeetStream-managed keys) (`"key_source": "meetstream"`) as the default setup, and attaches it by passing only `agent_config_id` on create_bot.
FAIL if it tells the user to also pass `socket_connection_url` or `live_audio_required` for the agent (those belong to the separate bridge server flow), or invents MCP tools for agent configs.
