---
type: llm
weight: 2
---
PASS if the reply builds the live path on the Bot API: create_bot with `live_transcription_required.webhook_url` and a streaming transcription provider (for example `meetstream_streaming` or `deepgram_streaming`), the user's server receives the transcript events by HTTPS POST and forwards them to the overlay (for example by WebSocket or SSE), and the tips come from the user's own logic or model.
FAIL if the reply uses a voice agent or MIA, makes the bot speak, or writes a full multi-file app.
