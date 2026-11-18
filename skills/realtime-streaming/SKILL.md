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

This is the live path: data during the call. For results after the call, use
`join-meeting` and `meeting-brief`.

## Live captions into your app (start here for "live transcript")

Live transcripts arrive as **HTTPS POSTs to your server**, one per transcript update:
set `live_transcription_required.webhook_url` on `create_bot` and pick a streaming
provider (for example `meetstream_streaming`). To show captions in a web app, your
server forwards each update to the browser over Server-Sent Events or a WebSocket that
you host. MeetStream does not stream transcripts to the browser directly, and the API key
must never reach the browser. If you would rather run your own speech-to-text, take the
raw audio over the `live_audio_required` WebSocket instead (below).

Four separate channels, often confused with each other. Pick by what the user
actually needs.

| Need | Field on `create_bot` | Transport |
|---|---|---|
| Transcript text as it is spoken | `live_transcription_required.webhook_url` | HTTPS POST to you |
| Raw audio bytes | `live_audio_required.websocket_url` | WebSocket, binary PCM |
| Live video frames | `live_video_required.websocket_url` | WebSocket, fMP4 |
| Send things into the meeting | `socket_connection_url.websocket_url` | WebSocket, JSON commands |
| Live video/audio INTO the bot camera and mic | `bot_camera_stream.websocket_url` | WebSocket signaling + WebRTC |
| Participant join/leave and raise/lower hand | `recording_config.realtime_endpoints` | HTTPS POST, per event |

All of these point at **your own** server. They are not used for voice agents (MIA), which run
on MeetStream's hosted bridge and need only `agent_config_id`.

## Live transcription

`live_transcription_required.webhook_url` **requires a streaming provider** in the
transcription config (`deepgram_streaming`, `assemblyai_streaming`,
`jigsawstack_streaming`, `meetstream_streaming`, `smallest_streaming`, or
`meeting_captions`). Without one the API returns HTTP 400 telling you exactly that.

`smallest_streaming` (Smallest AI) takes `model` `pulse` (default) or `pulse-2` (English
only) and `language` (default `en`), and needs a Smallest AI key saved in the dashboard
under voice integrations. `meeting_captions` works on Google Meet and Teams, and on Zoom
only for bots that join without the user's own Zoom app.

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

## Bot camera stream (WebRTC into the meeting)

`bot_camera_stream: { "websocket_url": "wss://..." }` on the REST `create_bot` makes the
bot connect **out** to your signaling socket and publish your WebRTC video (and optional
audio) through its camera and microphone.

- Google Meet (`ws://` or `wss://`), Teams and Zoom (`wss://` only; `ws://` returns 400).
  Other platforms return 400.
- Zoom: cannot be combined with `agent_config_id` (400), and not available on bots that
  join without the user's own Zoom app.
- The signaling host must resolve to a public address; private ICE candidates are dropped.
- Protocol (offer/answer, ICE, status messages):
  https://docs.meetstream.ai/guides/websockets/bot-camera-streaming

## Participant hand events

Add `participant_events.raise_hand` / `participant_events.lower_hand` to
`recording_config.realtime_endpoints[].events` (Google Meet, Zoom). They reach only the
endpoints that list them, never `callback_url` or workspace webhooks. Same nested shape as
`participant_events.join`; `data.data.action` is `raise_hand` / `lower_hand`. Transitions
only; the bot's own hand is never reported.

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
- Raising the bot's hand? There is no MCP tool, but the REST call works:
  `POST /api/v1/bots/{bot_id}/send_command` with `{"command": "raise_hand"}` /
  `{"command": "lower_hand"}` (bot must be in the meeting, else 409; see `join-meeting`).
- Just showing an image? Use the **`send_image`** MCP tool (public URL, not base64).
- Only if the user asks for a bot that talks or answers: use a voice agent (`mia-voice-agents`, `agent_config_id`) and host nothing.

Reach for WebSockets when you need raw media or custom real-time logic, not for
one-off actions.

## Reference

- [Live transcription](https://docs.meetstream.ai/guides/transcription-recordings/live-transcription)
- [Real-time audio streaming](https://docs.meetstream.ai/guides/websockets/real-time-audio-streaming)
- [Meeting control patterns](https://docs.meetstream.ai/guides/websockets/meeting-control-patterns)
- [Bridge server architecture](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture)
- [Bot camera streaming](https://docs.meetstream.ai/guides/websockets/bot-camera-streaming)
- [Streaming providers](https://docs.meetstream.ai/guides/transcription-recordings/providers/transcription-providers)
- [Chat and visuals](https://docs.meetstream.ai/guides/features/chat-and-visuals)
