---
name: realtime-streaming
description: >
  Stream meeting data live during the call (track 1b, real-time
  transcription). Raise/lower hand: POST /api/v1/bots/{bot_id}/send_command
  {"command": "raise_hand"} (works without the MCP tools). Live transcripts
  arrive by HTTPS POST to live_transcription_required.webhook_url on your
  server (not a WebSocket from the bot); your server can then forward them to
  the browser (Server-Sent Events or your own WebSocket). Also raw audio, live
  video, and two-way bot control over WebSocket. Voice agent on your own stack
  (track 2, bridge server): the bot opens live_audio_required.websocket_url
  (audio in) and socket_connection_url.websocket_url (sendaudio, sendmsg,
  interrupt back); local tunnel (ngrok, cloudflared); free local
  whisper.cpp/Parakeet STT, Ollama LLM or your harness's model, Piper TTS; bot
  price only. Use for "live transcription", "live captions", "stream the
  audio", "make the bot speak", "bridge server", "websocket", or anything
  during the meeting rather than after it.
---

# Real-time streaming

This is the live path: data during the call (track 1b, real-time transcription; name the
track in your answer). For results after the call (track 1a), use `join-meeting` and
`meeting-brief`. A bot that records and also shows live captions is track 1b: the normal
recording fields plus `live_transcription_required`.

## Live captions into your app (start here for "live transcript")

Live transcripts arrive as **HTTPS POSTs to your server**, one per transcript update:
set `live_transcription_required.webhook_url` on `create_bot` and pick a streaming
provider (for example `meetstream_streaming`). To show captions in a web app, your
server forwards each update to the browser over Server-Sent Events or a WebSocket that
you host. MeetStream does not stream transcripts to the browser directly, and the API key
must never reach the browser. If you would rather run your own speech-to-text, take the
raw audio over the `live_audio_required` WebSocket instead (below).

To try it from a terminal with the `meetstream` CLI (`npx -y @meetstream/cli` if it is not
installed): `meetstream listen --json` runs a local receiver (one JSON line per event,
`127.0.0.1:3333/webhook`), and `meetstream join <url> -t meetstream_streaming
--live-transcript-webhook https://<public-url>/webhook --json --no-input` sends the bot. The
bot needs a public URL that reaches the receiver: today that is a tunnel (ngrok or
cloudflared) the user runs.

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

All of these point at **your own** server. `live_audio_required` plus `socket_connection_url`
on one bot is the bridge server for a voice agent on your own stack (below). They are never
added to a hosted voice agent bot (Agents API, MIA), which runs on MeetStream's hosted
bridge and takes only `agent_config_id`.

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

`socket_connection_url` gives you a command channel into the meeting. The bot connects to
your `wss://` endpoint, sends `{"type": "ready", "bot_id": "..."}`, then executes the JSON
commands you send (each carries `"bot_id"`):

| Command | Effect |
|---|---|
| `sendaudio` | Play audio into the call: `audiochunk` (base64 PCM16 LE), `sample_rate`, `encoding: "pcm16"`, `channels: 1`, `endianness: "little"`. Google Meet always plays it as 48 kHz |
| `sendmsg` | Post a chat message. Send both `message` and `msg` so one payload works on every platform |
| `interrupt` | `{"action": "clear_audio_queue"}`: stop playback and clear the queue. On Zoom and Teams it then holds further audio until `resume_audio` |
| `resume_audio` | `{"resume_id": "turn-42"}`: allow audio again after an `interrupt` (Zoom answers `resume_audio_ack`). Google Meet ignores it, so send it on every platform before each new reply |
| `sendimg` / `sendimg_url` | Set the bot's video frame (`img` base64, or `img_url`). Zoom and Teams; on Google Meet use the `send_image` MCP tool |

Pace `sendaudio` slightly ahead of real time (roughly 0.8x the chunk duration) so the
queue stays fed without running away. Cancel your local send loop when you issue
`interrupt`, or you will keep pushing audio the bot has been told to drop.

## Voice agent on your own stack (track 2, bridge server)

This is the way to put an agent in a meeting when the user wants their own stack: any
speech-to-text, LLM and voice, local or hosted. MeetStream charges the bot price only
($0.35 per hour, $0.25 at volume): no agent infrastructure fee and no model tokens. For a
hosted agent with no infrastructure work, use `mia-voice-agents` (track 3a, or 3c with own
keys). Running the user's own agent CLI (Claude Code, Codex) as the brain through
`meetstream setup` is track 3d, coming soon: today, call the harness's own model from this bridge.

Models for the bridge, free to run locally; check each model's license before commercial use:

- Speech-to-text: whisper.cpp or faster-whisper (Whisper models), NVIDIA Parakeet
  (parakeet-mlx on Apple silicon), Vosk, Moonshine.
- LLM: a local model through Ollama, LM Studio or llama.cpp (Llama, Qwen, Gemma,
  Mistral), or the model of the harness you already use (for example Claude behind
  Claude Code).
- Text-to-speech: Piper, Kokoro, Chatterbox, macOS `say`.

1. Run a bridge server with two WebSocket endpoints, `/bridge/audio` (meeting audio in,
   binary frames) and `/bridge` (JSON commands out). Put a random secret token in both
   paths (for example `wss://host/<token>/bridge/audio`) and reject other paths: the URLs
   are public and carry no other auth. Start from the MeetStream Bridge
   starter at https://github.com/meetstream-ai/meetstream-agent (FastAPI, OpenAI Realtime
   by default; swap in local models), or build to the bridge docs.
2. Expose it on a public `wss://` host. On a laptop, use a local tunnel (ngrok or
   cloudflared, for example `ngrok http 8000` or `cloudflared tunnel --url
   http://localhost:8000`); `localhost` is not reachable from the bot. Do not start a tunnel or a
   long-running server in a build unless the user asked: give the commands and let the
   user run them (Codex, for example, stops background processes at the end of each turn).
3. Send a bot with both sockets on the same host. From a terminal, with the `meetstream` CLI:
   ```bash
   meetstream join "https://meet.google.com/abc-defg-hij" -n "Assistant" \
     --live-audio-ws wss://your-bridge.example/bridge/audio \
     --socket-ws wss://your-bridge.example/bridge --json --no-input
   ```
   In app code, the API or SDK:
   ```bash
   curl -X POST https://api.meetstream.ai/api/v1/bots/create_bot \
     -H "Authorization: Token $MEETSTREAM_API_KEY" -H "Content-Type: application/json" \
     -d '{"meeting_link": "https://meet.google.com/abc-defg-hij", "bot_name": "Assistant",
          "live_audio_required": {"websocket_url": "wss://your-bridge.example/bridge/audio"},
          "socket_connection_url": {"websocket_url": "wss://your-bridge.example/bridge"}}'
   ```
   ```ts
   await ms.bots.create({ meeting_link, bot_name: 'Assistant',            // @meetstream/sdk
     live_audio_required: { websocket_url: 'wss://your-bridge.example/bridge/audio' },
     socket_connection_url: { websocket_url: 'wss://your-bridge.example/bridge' } });
   ```
   ```python
   ms.bots.create({"meeting_link": meeting_link, "bot_name": "Assistant",  # meetstream-sdk
       "live_audio_required": {"websocket_url": "wss://your-bridge.example/bridge/audio"},
       "socket_connection_url": {"websocket_url": "wss://your-bridge.example/bridge"}})
   ```
4. Both sockets open with a `{"type": "ready", "bot_id": "..."}` handshake; keep one AI
   session per `bot_id`, created when the first socket connects and closed when both have
   disconnected.
5. Audio in: decode each frame by its type byte (`0x01` or `0x04`, on every platform,
   including Google Meet; table and decoder below), downmix and resample to your model's
   rate (for example 16 kHz). Echo guard: ignore input while your bridge is sending audio
   and for a short tail after it (Google Meet tags audio `NoSpeaker`, so filtering by the
   bot's name does not work).
6. Reply: before the first chunk of each reply send `resume_audio`, then stream
   `sendaudio` at 48 kHz; post text with `sendmsg`. When a person talks over the agent,
   send `interrupt` and stop your send loop (barge-in).

7. Shutdown: on Ctrl-C or exit, call `POST /api/v1/bots/{bot_id}/remove_bot` so the bot
   leaves the meeting.

### Audio frame format

Read byte 0 first; every platform can send either audio type (live Google Meet bots send
one `0x01` frame and then `0x04` frames):

| Type | Header | Speaker fields start at |
|---|---|---|
| `0x01` | `[type:1]`, PCM16 LE, 48 kHz mono | offset 1 |
| `0x04` | `[type:1][sample_rate:4, uint32 LE][channels:1]` | offset 6 |

Then `sid_length` (uint16 LE), `speaker_id`, `sname_length` (uint16 LE), `speaker_name`,
then raw PCM16 LE samples (no container). Skip any other type. Duration =
`len(pcm) / 2 / channels / sample_rate`.

```python
import struct
def decode(data: bytes):
    if data[0] == 0x01:
        rate, ch, off = 48000, 1, 1
    elif data[0] == 0x04:
        rate, ch, off = struct.unpack_from("<I", data, 1)[0], data[5], 6
    else:
        return None                      # unknown type: skip
    n = struct.unpack_from("<H", data, off)[0]; sid = data[off+2:off+2+n].decode(); off += 2 + n
    n = struct.unpack_from("<H", data, off)[0]; name = data[off+2:off+2+n].decode(); off += 2 + n
    return sid, name, rate, ch, data[off:]   # downmix if ch > 1, resample for your STT
```

`speaker_name` is `"NoSpeaker"` when MeetStream cannot attribute the audio (Google Meet
mixed audio often is), so you cannot drop the bot's own voice by name.

Do not add `agent_config_id` to a bridge bot: a bridge bot and a hosted agent bot are
separate bots.

## Simpler alternatives

Before building a WebSocket server, check whether the REST path is enough:

- Just posting a message? Use the **`send_chat_message`** MCP tool.
- Raising the bot's hand? Use the **`raise_hand`** / **`lower_hand`** MCP tool. With no
  MCP (or in app code), the REST call works now (header `Authorization: Token <API key>`):
  `POST /api/v1/bots/{bot_id}/send_command` with `{"command": "raise_hand"}` /
  `{"command": "lower_hand"}` (bot must be in the meeting, else 409; see `join-meeting`).
- Just showing an image? Use the **`send_image`** MCP tool (public URL, not base64).
- Only if the user asks for a bot that talks or answers: on their own stack, the bridge server above (bot price only); with no infrastructure work, the hosted voice agent (`mia-voice-agents`, track 3a or 3c, `agent_config_id`).

Reach for WebSockets when you need raw media or custom real-time logic, not for
one-off actions.

## Latest docs

- Live transcription: https://docs.meetstream.ai/guides/transcription-recordings/live-transcription
- Real-time audio WebSocket: https://docs.meetstream.ai/guides/websockets/real-time-audio-streaming
- Meeting control WebSocket: https://docs.meetstream.ai/guides/websockets/meeting-control-patterns
- Bridge server for a voice agent on your own stack (track 2): https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
- Bot camera streaming: https://docs.meetstream.ai/guides/websockets/bot-camera-streaming

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
