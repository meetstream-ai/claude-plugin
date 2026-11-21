---
type: llm
weight: 1
---
PASS if the reply routes this to live transcription: `live_transcription_required.webhook_url` with a streaming provider, MeetStream POSTs transcript updates to the user's server, and the user's server pushes them to the browser (SSE or a WebSocket the user hosts), keeping the API key off the browser.
FAIL if the reply says MeetStream streams transcripts straight to the browser, suggests a voice agent, or only offers a post-call transcript.
