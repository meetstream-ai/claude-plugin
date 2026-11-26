---
name: meetstream-cli
description: >
  Run MeetStream from this agent or a terminal (the meetstream CLI 1.0, or the
  MCP tools): join-meeting, meeting-brief, verify-account, test-bot and
  cli-workflows. Raise hand: POST /api/v1/bots/{bot_id}/send_command
  {"command": "raise_hand"}. Use when the user says "join this meeting", "send a
  bot to <meeting url>", "record this call", "make the bot leave", "summarize
  that meeting", "action items from the call", "verify my account", "which
  providers do I have", "send a test bot", "watch bot events live", "install
  meetstream", "meetstream login", "listen for webhooks locally", or any
  `meetstream <command>`. Low credits: https://app.meetstream.ai/billing
  (top_up_link tool when connected); never retry in a loop. Tools not
  connected: give the one connect step (Codex: codex mcp login meetstream;
  Claude Code: /mcp; Cursor: Settings → MCP), then the CLI or POST
  /api/v1/bots/create_bot with meeting_link; a one-off meeting link needs no
  calendar integration; never say MeetStream can't record.
---

# Run MeetStream from this agent: MCP tools and the meetstream CLI

Operator skill: do the work now for the user (send a bot, follow it, brief the meeting, check
the account, run a test bot). Use the MeetStream MCP tools when they are connected; otherwise run
the `meetstream` CLI (released version 1.0.1, repo meetstream-ai/cli). Do not write API client
code unless the user asks for a script; app builds go to the need skills (`sending-bots`,
`handling-webhooks` and the others in the `meetstream` router). Full command reference and JSON
shapes: `skills/meetstream/references/meetstream-cli.md` (`meetstream skill` prints the same text).
Commands marked pre-release in `skills/meetstream/references/generated/cli-map.md` (`init`, `api`,
`mock`, `trigger`, `env`, `transcriptions`, `ai install`) come in the next CLI release: mention them
only as coming, never as a command to run today.

**Install the meetstream CLI** (see https://docs.meetstream.ai/build-with-ai/meetstream-cli). Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat). Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`.

This is the post-call path (record now, transcript and brief after) plus chat and
raise hand during the call. Do not offer a voice agent unless the user asks for one.
If the user wants live transcription or live streams, use `streaming-live-data`.

**If the MeetStream tools are missing or not signed in** (no `meetstream` tools, or a tool
answers 401 or "not signed in"): give the user the one step to connect, and in the same
reply keep helping. Do not stop at "sign in first".
- Claude Code: `/mcp` → `meetstream` → sign in. Cursor: Settings → MCP → **Connect** next
  to `meetstream`. Codex: `codex mcp login meetstream` (full steps:
  https://github.com/meetstream-ai/meetstream-plugin/blob/main/INSTALL_FOR_AGENTS.md).
- Then go on: give the plan, the `create_bot` fields you will send once the tools work,
  or run the CLI (next section), or give the REST call (`curl` with
  `Authorization: Token YOUR_API_KEY`).
- The one step is the MeetStream MCP sign-in, nothing else. A one-off meeting link needs
  no calendar integration (calendars are only for auto-joining every meeting).
- Never tell the user MeetStream cannot record the meeting: it can, through the tools
  once connected, or now through the CLI (`meetstream join <url>`) or REST
  `POST /api/v1/bots/create_bot` with `meeting_link`.

## Join a meeting: the short path

1. **`create_bot`** with `meeting_link` and a `bot_name`.
2. **`get_bot_status`** to follow it (`Joining` -> `InWaitingRoom` -> `InMeeting` -> `MediaProcessing` -> `Done`; full list below). Stop at `Done` or another final status, never loop forever.
3. When the meeting ends, **`get_transcript`** with the `bot_id`.

That is the whole flow. Everything below is detail you need when it is not that simple.

## Join a meeting without the MCP: the CLI

The same flow from the terminal (track 1a):

```bash
meetstream bots list --json --no-input                                  # reuse a bot already in this meeting
meetstream join "<meeting-url>" -n "Acme Notetaker" -t meetstream --json --no-input   # prints the bot_id
meetstream bots status <bot-id> --json --no-input                       # --watch polls every 5 seconds
meetstream transcript <bot-id> --wait --json --no-input                 # exit 3 = not ready, 4 = transcript failed
meetstream recordings <bot-id> --json --no-input                        # audio and video links
```

In the meeting: `meetstream bots say <bot-id> "<message>"`, `meetstream bots hand <bot-id> up`
(or `down`), `meetstream bots remove <bot-id>` (the bot leaves). `meetstream bots delete
<bot-id> --yes` erases the data: only after the user confirms. `join` takes the
`create_bot` options as flags (`--video`, `--video-layout`, `--join-at`, `--callback`,
`--waiting-room-timeout`, `--zoom-obf-url`, `--zoom-zak-url`, `--storage-id`,
`--idempotency-key`); `meetstream join --help` lists them.

**Tell the user before the first bot:**
- **Someone must admit it.** The bot asks to join like a guest. The host (on Google Meet,
  the host or a co-host) admits it from the waiting room or lobby. It waits
  `automatic_leave.waiting_room_timeout` seconds (default 600 on Zoom and Google Meet,
  1200 on Teams), then ends as `NotAllowed`; `Denied` means a person declined it.
- **Zoom:** recommend setting up the user's own Zoom app first, for reliable, fully supported Zoom bots (OBF or ZAK, below).
- **Platforms:** Zoom, Google Meet, Microsoft Teams, and WhatsApp calls (Beta: enabled per
  workspace, pair a number under Integrations > WhatsApp, `deepgram` post-call
  transcription only, no chat or per-participant files; `setting-up-platforms`). Links from
  other services (Webex, Slack huddles and others) return 400; say they are not supported.

## Creating the bot

Ask for the meeting link if the user has not given one. Sensible defaults:

- `bot_name` - something recognisable to the humans in the call, e.g. "Acme Notetaker".
  Never leave this blank; a bot with no name looks like an intruder.
- `record_video` - default off. Turn it on only if the user explicitly asks for video,
  since it takes longer to process and transcripts, summaries and speaker timelines all
  work without it. On REST the field is `video_required`, which defaults to `false`;
  send `"video_required": false` explicitly anyway so the intent is visible.
- `video_layout` - only when video is on. Send `"speaker_view"` unless the user asks for
  grid or gallery view; the REST API defaults to `"grid_view"`. `"speaker_view"` and
  `"grid_view"` work on every platform. Google Meet and Teams also accept
  `"speaker_view_default"` / `"grid_view_default"` (the bot records the platform's own
  layout in the call as one finished file); Zoom returns 400 for them. It is ignored when
  video is off, and WhatsApp accepts only `"grid_view"`.
- `separate_video_streams` - leave unset. Per-participant video is opt-in only; set it
  only when the user explicitly asks for it. Per-participant audio is unaffected.
- Transcription provider - `meetstream` works on every account with no extra keys, so
  use it unless the user says they added their own Deepgram, AssemblyAI or Sarvam key in
  the MeetStream dashboard (then `deepgram` with model `nova-3` is a good English choice).
  A provider whose key is missing fails after the call with no transcript. See
  `getting-transcripts-and-media` for other languages and diarization.
- `bot_image_url` (REST) - a public `https://` PNG, JPEG, GIF or WebP URL. `http://` and
  `data:` URIs return 400.
- Zoom: recommend that the user sets up and configures their own Zoom app (Meeting SDK
  credentials under Integrations > Zoom) for reliable, full, officially supported Zoom bots.
  With it, the bot joins as that app with an OBF token (on behalf of a user in the meeting)
  or a ZAK token (a signed-in bot), the way Zoom asks Meeting SDK apps to join since 2 March
  2026; send `zoom.obf_url` or `zoom.zak_url` on REST for meetings outside the app's account:
  https://docs.meetstream.ai/guides/app-integrations/zoom-marketplace-app-setup and
  https://docs.meetstream.ai/guides/app-integrations/zoom-authenticated-bots
  (`setting-up-platforms`). Without the user's own app, a limited fallback joins as a named
  guest in the US execution region only: no OBF or ZAK, no per-participant camera video.
- `storage_id` (REST) - one of the workspace's storage destinations from the dashboard
  (1-80 letters, numbers, `_` or `-`). Omit it for the default destination.

Before creating a bot, call **`list_bots`**: if a bot is already joining or in that
meeting, reuse its `bot_id` instead of sending a second one.

If `create_bot` fails:

| Error | What to do |
|---|---|
| `Low credits please recharge` (403) | Call the `top_up_link` tool and give the user its link (`https://app.meetstream.ai/billing`). Do not retry `create_bot` until they say they added credits. |
| 401 / not signed in | Sign in to the `meetstream` MCP server again (Cursor: Settings → MCP → Connect; Claude Code: `/mcp` → Authenticate; Codex: `codex mcp login meetstream`), then retry once. |
| 400 with a field message | Fix that one field and retry once. |
| 429 `rate_limit_exceeded` | Prepaid accounts may create 5 bots per minute and 50 per hour. Wait the `Retry-After` seconds, then retry once. |

`get_balance` can answer that the balance is not available here and give the billing
link. That is normal, not an error to debug: give the user `https://app.meetstream.ai/billing`
(or the `top_up_link` result) and go on.

If the user wants the bot to arrive at a future time, pass `join_at` as an ISO 8601
timestamp rather than sleeping and creating it later.

## Following the bot

Statuses (`get_bot_status`, REST `GET /bots/{bot_id}/status`):

- In progress: `Scheduled` · `Joining` · `InWaitingRoom` · `InMeeting` (Zoom may show
  `RecordingPermissionAllowed`) · `Leaving` · `MediaProcessing`.
- Ended in the meeting: `Stopped` · `Kicked`, then `MediaProcessing` → `Done`.
- Never got in (final): `NotAllowed` · `Denied` · `Failed` / `FAILED` · `Error` / `ERROR`.
- Other final: `Done` (post-call processing finished; fetch the transcript now) ·
  `MediaExpired` · `Cancelled`.

A polling app must stop on any final status, not wait for `Stopped`: between two polls a
bot can go `InMeeting` → `MediaProcessing` → `Done` and you never see `Stopped`. Poll every
5-10 seconds with a time cap, or use the webhooks (`bot.stopped`, `transcription.processed`,
`bot.done`). Never loop forever. `Recording` appears in the timeline and webhooks, not as
the stored status.

**Listing bots** (duplicate checks, dashboards): never page through the whole history.
Filter: `GET /api/v1/bots?status=InMeeting&platform=GMeet&from=2026-11-21&limit=50`
(`status`, `platform` = `GMeet` / `Zoom` / `Teams`, `from` / `to` dates, `custom_attr[key]`).
`limit` is at most 50 (above it the API returns 400); follow `nextCursor` by sending it
back as `cursor` while `hasNextPage` is true. For one bot per meeting, prefer a
`deduplication_key` on `create_bot`.

These mean the bot never got in, and you should say so plainly rather than polling
forever:

| Status | What actually happened | What to tell the user |
|---|---|---|
| `NotAllowed` | Sat in the waiting room until `waiting_room_timeout` ran out (on Zoom and Teams, also a meeting nobody started) | Nobody admitted the bot. Ask the host to watch for it by name and admit it, raise `automatic_leave.waiting_room_timeout` (Zoom up to 1200, Google Meet 600, Teams 1800), let guests in, or use a signed-in bot (`setting-up-platforms`). Then send a new bot. |
| `Denied` | A host actively rejected it (on Zoom, also Zoom refusing the bot's account) | The host declined. Ask them to admit it next time; on Zoom check the meeting allows guests or join with `zoom.zak_url`. Nothing to retry automatically. |
| `Error` / `Failed` | The join failed or the session crashed | Check `ErrorReason` in `get_bot_detail`: `MeetingRestricted` (organization or invitees only) and `SignInRequired` (no anonymous guests) need a signed-in bot; `InvalidMeetingLink` needs the full join link. Otherwise create a fresh bot. |

Poll with a sensible interval (5-10s) and a cap. Do not busy-loop.

## While it is in the meeting

Commands (chat, image, raise hand, `send_command`, `update_mia`) need the bot to be
`InMeeting` first. Before admission they return 409 or 503 (`no command endpoint`). Wait for
the `bot.inmeeting` webhook or the `InMeeting` status, then send; retry a 503 two or three
times with a few seconds' pause, never in a tight loop.

- **`send_chat_message`** - post into the meeting chat, e.g. to announce the bot is
  recording. Good manners and often a legal requirement.
- **`send_image`** - show an image or GIF as the bot's video frame. The URL must be
  publicly reachable and resolve to a public address; MeetStream fetches it server side,
  so local paths, private hosts and `data:` URIs will not work.
- **Raise / lower hand** - with the MCP connected, call the `raise_hand` / `lower_hand`
  tool. From a terminal: `meetstream bots hand <bot_id> up --json --no-input`. With no MCP
  (or in app code), the bot can do it now with REST. Give the user (or run, when
  your MeetStream API key is set) this call, with the connect step only as a side note:
  ```bash
  curl -X POST "https://api.meetstream.ai/api/v1/bots/<bot_id>/send_command" \
    -H "Authorization: Token YOUR_API_KEY" -H "Content-Type: application/json" \
    -d '{"command": "raise_hand"}'
  ```
  It is `POST /api/v1/bots/{bot_id}/send_command`
  with `{"command": "raise_hand"}` or `{"command": "lower_hand"}` (Google Meet, Zoom,
  Teams). The bot must be `InMeeting` or `Recording`, otherwise 409. Response:
  `{"status": "accepted", "bot_id": "...", "command": "raise_hand", "hand_raised": true}`,
  where `hand_raised` is the state read back from the meeting, not an echo. Repeats are
  no-ops. Allow up to 10 seconds. Bots outside the US region return 501. Guide:
  https://docs.meetstream.ai/guides/features/raise-lower-hand
- **`take_screenshot`** - capture the meeting (Google Meet and Teams; not Zoom bots that
  join through your own Zoom app), then `get_media_urls` with `kind: "screenshots"`.
- **`get_participants`** / **`get_chats`** - read who is present and what has been said in chat.

## Ending it

- **`remove_bot`** makes the bot leave now. Recorded data is kept. REST:
  `POST /api/v1/bots/{bot_id}/remove_bot` (GET also works). Every app that sends a bot
  calls it on shutdown or Ctrl-C, so the bot does not stay in the meeting.
- **`delete_bot_data`** permanently erases the recording and transcript. This is
  irreversible - always confirm with the user before calling it, and never call it
  speculatively.

## Getting the recording afterwards

Use **`get_transcript`** with the `bot_id`; it resolves the transcript for you.
For media files use **`get_media_urls`** (audio, video, per-participant streams,
screenshots).

If a transcript is not ready yet the tool will say so. Wait and retry a few times
rather than reporting failure. One exception: if the bot used a **streaming-only**
transcription provider, there is no post-call transcript at all and waiting will
never help - the transcript was delivered live during the meeting.

## Do not

- Do not invent endpoints or fields. The MCP tools are the API surface.
- Do not call `delete_bot_data` without explicit confirmation.
- Do not create a second bot for the same meeting because the first is slow to join;
  check its status first.

## Brief a finished meeting (was meeting-brief)

1. `get_transcript` with `wait: true` (CLI: `meetstream transcript <bot-id> --wait --json --no-input`;
   exit 3 = not ready, 4 = the run failed). Everything in the brief comes from it.
2. `get_speaker_timeline` (CLI: `meetstream bots timeline <bot-id>`) for talk time,
   `get_participants` (CLI: `meetstream bots get <bot-id> --part participants`) for attendees.
3. Read segments as participant-keyed: speaker `participant.name`, text `words[].text` joined with
   spaces (some providers give `speaker` / `transcript`; read both). Never summarize a meeting you
   have not read: MeetStream has no built-in summary (`get_bot_summary` only says so).

Brief contents, talk-time math, saving the brief, choosing a provider and re-running a transcription:
[`references/meeting-brief.md`](references/meeting-brief.md).

## Verify the account (was verify-account)

Read-only, no bots: `meetstream auth status`, `meetstream balance` (exit 3 = use
https://app.meetstream.ai/billing), `meetstream mia list`, `meetstream calendar list`, each with
`--json --no-input`. `meetstream` and `meetstream_streaming` transcription need no provider key;
Deepgram, AssemblyAI, Sarvam and Interfaze need the user's key in the dashboard. Report and the REST
equivalents: [`references/verify-account.md`](references/verify-account.md).

## Send a test bot (was test-bot)

Ask for a meeting link, a provider (`meetstream_streaming` by default) and a webhook URL, then
`meetstream join <url> -n "Test Bot - delete me" -t meetstream_streaming -c <webhook> --retention-hours 24 --attr test_run=true --json --no-input`,
stream the events, report timing per stage, and offer `meetstream bots remove` and
`meetstream bots delete --yes` (only after the user confirms). Full steps and the report format:
[`references/test-bot.md`](references/test-bot.md).

## CLI workflows (was cli-workflows)

### Rules for this agent
- Always pass `--json --no-input`. Parse stdout; human messages go to stderr.
- Exit codes: `0` ok, `1` runtime or API error, `2` usage error or not signed in, `3` not ready
  or not available on this server, `4` transcript failed, `130` interrupted. With `--json`,
  errors are `{"error": {"message", "hint", "exit_code"}}`: follow the `hint`.
- Never ask for the API key in chat. Never print it. On exit 2 "not signed in", run
  `meetstream login --json` (it opens the user's browser) or ask the user to set
  your MeetStream API key.
- No CLI on the machine: the meetstream CLI (to install it, see https://docs.meetstream.ai/build-with-ai/meetstream-cli).
- Prices come from the API (`setup --dry-run`, `balance`); never quote prices from memory.

### W1 · Install, sign in, check
```bash
npm install -g @meetstream/cli          # or: meetstream <command>
pipx install meetstream-cli             # or: meetstream <command>
brew install meetstream-ai/tap/meetstream
meetstream login --json                 # browser sign-in; stores a named key (0600). --no-browser prints the link
meetstream doctor --json                # key, API URL, config, agent CLIs; exit 1 if a check fails
meetstream auth status --json           # key in use (masked), valid or not
```
CI: `printf %s "YOUR_API_KEY" | meetstream login --with-key` or just set your MeetStream API key.
After `login` in a terminal, the CLI offers to connect a calendar (`--no-calendar` skips).

### W2 · Recording bot, transcript after the call (track 1a)
```bash
meetstream join https://meet.google.com/abc-defg-hij -n "Notetaker" -t meetstream --json
meetstream bots status <bot-id> --watch --json      # successive status values
meetstream transcript <bot-id> --wait --json        # exit 3 while pending, 4 if it failed
meetstream recordings <bot-id> --json               # audio and video links
meetstream bots get <bot-id> --part participants --json   # also: detail, chats, screenshots, streams, audio-streams
```
- `-t meetstream` = MeetStream transcription (adds a per-hour charge; tell the user). Other
  providers need the user's own key saved in the dashboard.
- Audio only unless the user asked for video (`--video`, `--video-layout speaker_view|grid_view`).
- Other `join` options: `--join-at <iso8601>` (schedule), `-c <url>` (lifecycle webhook),
  `--max-recording-seconds`, `--waiting-room-timeout`, `--everyone-left-timeout`,
  `--retention-hours`, `--storage-id` (customer S3), `--separate-audio`, `--separate-video`,
  `--attr key=value`, `--idempotency-key`.
- Re-run transcription on a finished meeting: `meetstream transcribe <bot-id> -p <provider>`
  (no default provider on the server; `meetstream` needs no key). Listing runs as a command
  (`meetstream transcriptions`) comes in the next CLI release; today use the MCP
  `list_transcriptions` tool or `GET /api/v1/bots/{bot_id}/transcriptions`.
- Speaker timeline: `meetstream bots timeline <bot-id> [--download]`.
- End or clean up: `meetstream bots remove <bot-id>`; permanent delete
  `meetstream bots delete <bot-id> --yes` (confirm with the user first).

### W3 · Live transcript and webhooks on a laptop (track 1b)
```bash
meetstream listen -p 3333 --json        # loopback receiver: one JSON line per event
# expose it with a tunnel (ngrok, cloudflared), then:
meetstream join <url> -t meetstream_streaming -c https://<public-url>/webhook --live-transcript-webhook https://<public-url>/webhook --json
```
`-t meetstream_streaming` is MeetStream live transcription (no provider key). Deepgram, AssemblyAI, Sarvam and other `*_streaming` providers need the user's key in the dashboard.
`listen --forward <url>` also relays events elsewhere. `meetstream bots tail` (events over the
relay, no tunnel) is planned: today it exits 2 with a hint.

### W4 · Talk in the meeting from the terminal
```bash
meetstream bots say <bot-id> "Recording has started"
meetstream bots show-image <bot-id> https://example.com/slide.png -d 10
meetstream bots hand <bot-id> up        # or down
```

### W5 · Bridge server: your own STT, LLM and TTS (track 2)
```bash
meetstream join <url> --live-audio-ws wss://<public-url>/audio --socket-ws wss://<public-url>/control --json
```
Audio comes in on `--live-audio-ws`; your server sends audio, chat and images back on
`--socket-ws` (`--live-video-ws` for video frames). Free local models work (faster-whisper or
Parakeet, Ollama, Piper or Kokoro). A laptop needs a tunnel for these URLs. Never add the bridge
sockets to a MIA bot (`--agent-config`).

### W6 · Zoom
Recommend setting up the customer's own Zoom app in MeetStream first (reliable, fully supported
Zoom). For meetings outside that app's Zoom account, pass a token URL:
```bash
meetstream join https://zoom.us/j/123 --zoom-obf-url https://<your-service>/obf --json   # or --zoom-zak-url
```
`--zoom-use-own-app` / `--no-zoom-use-own-app` override the account default (the no-app join is a
limited US-only fallback with no OBF or ZAK).

### W7 · Signed-in bots (Google Workspace, Microsoft Teams)
```bash
meetstream logins teams add-domain contoso.com
printf %s "$PASSWORD" | meetstream logins teams add --domain contoso.com --email bot@contoso.com --password-stdin
meetstream logins google add --domain acme.com --email bot@acme.com --key key.pem --cert cert.pem
meetstream join <url> --teams-login-domain contoso.com     # or --google-login-domain / --sign-in-email
```
Passwords only from stdin, an environment variable or a hidden prompt; never in argv or chat.

### W8 · Calendar auto-join
```bash
meetstream calendar connect --provider google --no-input --open --json   # one-click sign-in, where the server offers it
meetstream calendar auto-join on -n "Notetaker"                          # --video to record video
meetstream calendar events --json
meetstream calendar schedule <event-id> | unschedule <event-id> | reschedule <bot-id> <iso8601> | cancel <bot-id>
```
One-click connect is coming soon in production: there it exits 3 with a hint. Use your own
Google OAuth app today:
`meetstream calendar connect --own-app --client-id <id> --client-secret <secret> --refresh-token <token>`.
Join rule: `--join-rule accepted` (default: meetings the account hosts or accepted) or `all`.

### W9 · MIA voice agent hosted by MeetStream (tracks 3a and 3c)
```bash
meetstream setup --mode hosted --name "Product FAQ" --dry-run --json   # shows the request and the price per hour
meetstream setup --mode hosted --name "Product FAQ" --json --no-input  # MeetStream keys (pipeline: Deepgram + OpenAI)
meetstream setup --mode byok --name "Support" --json --no-input        # your provider keys, saved in the dashboard
meetstream join <url> --agent-config <agent_config_id> --json
```
- `--ears`, `--brain`, `--voice` take `provider:model` (defaults come from the server catalog).
- Realtime mode needs the user's own OpenAI key. Setup never asks for keys: they go in the dashboard.
- Agent configs as code: `meetstream mia apply -f mia.json [--dry-run]`;
  manage with `meetstream mia list | get | create | update | delete`.
- MIA bots take only `--agent-config` (with optional `--agent-param key=value`); no bridge sockets.

### W10 · Your coding agent as MIA's brain (track 3d) · coming soon
Not available in production yet (the MeetStream relay is not live there; `setup` exits 3).
Do not present it as available. When it ships, the flow is:
```bash
meetstream agent login                  # this computer's relay sign-in (browser)
meetstream setup --agent claude --access readonly   # or codex, hermes, copilot, muse, openclaw, agy
meetstream agent serve                  # outbound only; nothing listens on the laptop
meetstream agent context show|edit      # what the agent reads in meetings (MEETING.md)
meetstream agent bench --compare        # tokens and cost per meeting hour, per model
meetstream doctor --agent claude        # installed, signed in, warm session, relay, context
```
Meeting speech reaches an agent with access to this computer (prompt injection): keep the
lowest access level (`readonly`).

### W11 · Tools for agents and editors
```bash
meetstream mcp add claude|codex|cursor|vscode [--write]   # hosted MCP (OAuth) setup; --write merges the config
meetstream skill                                          # the agent guide (SKILL.md)
meetstream docs                                           # the README in the terminal
meetstream balance --json                                 # prepaid balance; exit 3 if not available
```

### Choosing a workflow
| User wants | Workflow |
|---|---|
| Notes or a transcript after the call | W2 |
| Live captions, webhooks on a laptop | W3 |
| Their own voice stack | W5 |
| A hosted voice agent | W9 |
| Their coding agent in the meeting | W10 (coming soon) |
| Every meeting on a calendar | W8 |
| Zoom outside their own account | W6 |
| Bots that sign in to Workspace or Teams | W7 |

## Latest docs

- CLI guide: https://docs.meetstream.ai/build-with-ai/meetstream-cli
- Create your first bot: https://docs.meetstream.ai/guides/get-started/create-your-first-bot
- Raise and lower hand: https://docs.meetstream.ai/guides/features/raise-lower-hand
- Local webhook server (tunnels): https://docs.meetstream.ai/guides/webhooks/local-webhook-server
- CLI source and README: https://github.com/meetstream-ai/cli

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
