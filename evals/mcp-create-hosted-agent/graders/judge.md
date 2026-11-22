---
type: llm
weight: 2
---
The tool calls (list_agents before create_agent, system_prompt, voice_id, pipeline mode, no bot) are graded separately. Judge only the final reply.
PASS if the reply says the voice agent was created from here and gives its `agent_config_id`, says it runs on MeetStream's inbuilt keys (or that the user's own provider keys must be saved in the dashboard), and says the next step is sending a bot to a meeting with the `agent_config_id`. Doubts about what a read-back tool returned are fine.
FAIL if the reply says it cannot create the agent from here, gives only a REST call or dashboard steps instead of creating it, asks the user to paste a provider API key or a pairing token into the chat, says it sent a bot, puts `socket_connection_url` or `live_audio_required` on the agent bot, or states a per-hour price for a specific model.
