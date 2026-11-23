---
type: llm
weight: 2
---
PASS if the reply routes Grok to the xAI provider: a hosted voice agent config (`POST /api/v1/mia`) with `"provider": "xai"` (realtime mode without a `model` field, or pipeline mode with an xAI model such as grok-3), using the user's own xAI key saved in the dashboard (xAI is not one of the inbuilt keys), then a bot with only `agent_config_id`; or Grok as the model behind the user's own bridge server, listed before the hosted option. It must also say the Zoom bot joins through the user's Zoom app with an OBF or ZAK token.
FAIL if the reply treats Grok as a local agent (`local_agent`, track 3d), says Grok or xAI is not supported, puts `"key_source": "meetstream"` on an xAI section, sends a `model` for xAI realtime, adds bridge sockets to the hosted agent bot, or says Zoom needs no setup.
