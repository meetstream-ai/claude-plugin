---
type: llm
weight: 2
---
PASS if the reply uses the bridge server flow: the user runs a server with two WebSocket endpoints, the bot is created with both `live_audio_required.websocket_url` (live meeting audio in, for example `wss://host/bridge/audio`) and `socket_connection_url.websocket_url` (the control socket, for example `wss://host/bridge`, to send audio back with `sendaudio`, and chat, images or `interrupt`), and Parakeet, the local LLM and the local TTS run inside the user's bridge. It says MeetStream charges only the bot price for this ($0.35 per hour, $0.25 at volume), with no agent infrastructure fee and no model tokens. It links the bridge server docs or the meetstream-agent starter repo.
FAIL if the reply sends the user to a hosted voice agent (`agent_config_id`, `POST /api/v1/mia`, `key_source`) as the way to run their own models, adds the $0.25 per hour agent infrastructure fee to this flow, gives only one of the two sockets, says local models are not possible, or invents prices.
