---
type: llm
weight: 2
---
PASS if the reply names this as the recording bot track with real-time transcription (track 1b), and gives a `create_bot` body that records (for example `recording_config` or the post-call transcript) and sets `live_transcription_required.webhook_url` with a streaming provider (for example `meetstream_streaming`), where MeetStream POSTs transcript updates to the user's server and the server forwards them to the browser (Server-Sent Events or the user's own WebSocket). It may mention the Zoom app step (OBF or ZAK).
FAIL if the reply suggests a voice agent, says MeetStream streams captions straight to the browser, offers only a post-call transcript, or does not name the track.
