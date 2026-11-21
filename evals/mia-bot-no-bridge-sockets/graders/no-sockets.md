---
type: llm
weight: 2
---
PASS if the create_bot body has `meeting_link` and `agent_config_id: "cfg_123"` and no `socket_connection_url` or `live_audio_required`; the reply says not to add the bridge URLs to this bot, because MeetStream hosts this agent and the extra sockets are a usual cause of a silent agent; and it says the bridge server is a separate way to run an agent, used on a separate bot (with both `live_audio_required.websocket_url` and `socket_connection_url.websocket_url`, and no `agent_config_id`).
FAIL if the body or the advice adds `socket_connection_url` or `live_audio_required` to the hosted agent bot, says to combine both on one bot, or does not say that the bridge is a separate bot.
