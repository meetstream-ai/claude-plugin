---
type: llm
weight: 2
---
PASS if the reply says that bringing their own agent infrastructure (a LiveKit agent) to MeetStream's Agents API is coming soon and not available yet, gives no setup steps or config fields for it, and offers what works now: the bridge server (track 2: the bot opens `live_audio_required.websocket_url` and `socket_connection_url.websocket_url` to the user's server, so their own agent code can sit behind it; bot price only) and/or the hosted Agents API with their own provider keys (track 3c, or 3a with MeetStream's default keys).
FAIL if the reply presents LiveKit as supported today, invents LiveKit config fields, endpoints or steps, says it will never be possible, or offers no working alternative.
