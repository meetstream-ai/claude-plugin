---
name: realtime-streaming
description: >
  Stream meeting data live while the call is happening - live transcription,
  raw audio, live video, and two-way bot control over WebSocket. Use when the
  user says "live transcription", "real-time captions", "stream the audio",
  "live video from the bot", "make the bot speak", "interrupt the bot",
  "websocket", "sendaudio", or wants anything during the meeting rather than
  after it.
---

# Real-time streaming

Four separate channels, often confused with each other. Pick by what the user
actually needs.

| Need | Field on `create_bot` | Transport |
|---|---|---|
| Transcript text as it is spoken | `live_transcription_required.webhook_url` | HTTPS POST to you |
| Raw audio bytes | `live_audio_required.websocket_url` | WebSocket, binary PCM |
| Live video frames | `live_video_required.websocket_url` | WebSocket, fMP4 |
| Send things into the meeting | `socket_connection_url.websocket_url` | WebSocket, JSON commands |

All of these point at **your own** server. They are not used for MIA agents, which run
on MeetStream's hosted bridge and need only `agent_config_id`.

## Live transcription

`live_transcription_required.webhook_url` **requires a streaming provider** in the
transcription config (`deepgram_streaming`, `assemblyai_streaming`,
`jigsawstack_streaming`, `meetstream_streaming`, or `meeting_captions`). Without one
the API returns HTTP 400 telling you exactly that.

The critical trade-off: **streaming-only providers produce no post-call transcript.**
`transcription.processed` never fires for these bots (though `bot.done` still does), and a
post-call transcript fetch returns HTTP 202 indefinitely. Treat the live stream as the record.

If the user wants both live captions *and* a clean transcript afterwards, run a
streaming provider for the live feed and then call `transcribe_audio` (MCP tool) after
the meeting to produce a post-call transcript from the stored audio.

Note this is an **HTTPS webhook**, not a WebSocket, despite being "real time".

## Live audio

`live_audio_required` opens a WebSocket from the bot to your server carrying PCM audio
frames with speaker metadata. You host the server; it must be `wss://` and publicly
reachable.

## Live video

`live_video_required` streams fMP4 over a WebSocket. Implement the keepalive contract:
answer every ping message immediately with the matching pong, echoing the sequence
number, **before** doing any other work on that message. Slow pong handling drops the
stream. Raise your WebSocket max payload - keyframes are large.

## Two-way control

`socket_connection_url` gives you a command channel into the meeting. Send JSON:

| Command | Effect |
|---|---|
| `sendaudio` | Play audio into the call - base64 PCM16 LE chunks |
| `sendmsg` | Post a message |
| `sendchat` | Chat with role tagging and streaming support |
| `interrupt` | `{"action": "clear_audio_queue"}` - stop bot audio. Google Meet only; Zoom/Teams accept it but do not clear |
| `sendimg` / `sendimg_url` | Set the bot's video frame to an image |

Pace `sendaudio` slightly ahead of real time (roughly 0.8x the chunk duration) so the
queue stays fed without running away. Cancel your local send loop when you issue
`interrupt`, or you will keep pushing audio the bot has been told to drop.

## Simpler alternatives

Before building a WebSocket server, check whether the REST path is enough:

- Just posting a message? Use the **`send_chat_message`** MCP tool.
- Just showing an image? Use the **`send_image`** MCP tool (public URL, not base64).
- Want a talking agent? Use **MIA** (`agent_config_id`) and host nothing.

Reach for WebSockets when you need raw media or custom real-time logic, not for
one-off actions.

## Reference

- [Live transcription](https://docs.meetstream.ai/guides/transcription-recordings/live-transcription)
- [Real-time audio streaming](https://docs.meetstream.ai/guides/websockets/real-time-audio-streaming)
- [Meeting control patterns](https://docs.meetstream.ai/guides/websockets/meeting-control-patterns)
- [Bridge server architecture](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture)
- [Streaming providers](https://docs.meetstream.ai/guides/transcription-recordings/providers/transcription-providers)
- [Chat and visuals](https://docs.meetstream.ai/guides/features/chat-and-visuals)
