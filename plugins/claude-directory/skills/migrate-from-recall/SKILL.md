---
name: migrate-from-recall
description: >
  Migrate an existing Recall.ai integration to MeetStream - rewrite base URLs,
  endpoints, request fields, and webhook handlers. MeetStream is essentially
  one-to-one with Recall, at a lower price.
  Use when the user says "migrate from Recall", "move off recall.ai", "switch from
  Recall to MeetStream", "port my Recall bot", "Recall alternative migration", or
  points you at a codebase that calls recall.ai. Offers an automated CLI path and a
  manual guided path. Also a short manual note for MeetingBaaS, Attendee or an
  in-house bot (the kit covers Recall only).
---

# Migrate from Recall.ai → MeetStream

MeetStream is a near drop-in replacement for Recall.ai at a lower price point. The migration is essentially **1:1**.

Pick the path that fits the user.

## Path A - Automated (recommended for a whole codebase)

The migration kit scans the project, prints every mapping as a diff, and rewrites the code. It never writes until confirmed.

```bash
# Install the migration kit once
npm install -g @meetstream/migrate

# Scan only (no changes)
meetstream-migrate scan /path/to/recall-project

# See the full diff
meetstream-migrate --dry-run /path/to/recall-project

# Migrate (asks for confirmation)
meetstream-migrate /path/to/recall-project

# Verify against the live API afterward
meetstream-migrate test --api-key YOUR_API_KEY
```

Python projects: `pip install meetstream-migrate` then `meetstream-migrate migrate <path>`. The Node CLI edits files in place regardless of language, so it works on Python projects too.

After it runs, walk the user through the **Post-migration checklist** below - the migrator flags anything that needs a human.

## Path B - Manual / guided (for a single file or a teaching walkthrough)

Apply these mappings. For full field-level detail, read `references/api-reference.md` in the **meetstream** skill (this plugin) - it is the live-verified source of truth.

**Base URL & auth**

| Recall | MeetStream |
| ------ | ---------- |
| `https://{region}.recall.ai` / `api.recall.ai` | `https://api.meetstream.ai/api/v1` |
| `Authorization: Token <key>` | `Authorization: Token <key>` (same scheme) |

**Endpoints**

| Recall | MeetStream | Note |
| ------ | ---------- | ---- |
| `POST /bot/` | `POST /bots/create_bot` | Field names differ (below) |
| `GET /bot/` | `GET /bots` | List |
| `GET /bot/{id}/` | `GET /bots/{id}/detail` (or `/status`) | |
| `DELETE /bot/{id}/` | `DELETE /bots/{id}/delete` | |
| `POST /bot/{id}/leave_call/` | `POST /bots/{id}/remove_bot` | path changes (GET also works) |
| `GET /bot/{id}/audio/` · `video/` · `screenshots/` · `speaker_timeline/` · `participants/` · `chat_messages/` | `GET /bots/{id}/get_audio` · `get_video` · `screenshots` · `get_speaker_timeline` · `get_participants` · `get_chats` | drop the `_bot_`. A large speaker timeline comes back as `{speaker_timeline_url, size_bytes, truncated}`: download the URL |
| `GET /bot/{id}/transcript/` | `GET /transcript/{transcript_id}/get_transcript` | **Uses `transcript_id`, not `bot_id`** - resolve via the create_bot response or `/bots/{id}/transcriptions` |
| `POST /bot/{id}/send_chat_message/` | `POST /bots/{id}/send_message` | body `{ "message": "..." }`; drop `to`/`pin` |
| `POST /bot/{id}/output_video/` | `POST /bots/{id}/send_image` | public `img_url` (not base64) |
| `POST /bot/{id}/pause_recording/` · `resume_recording/` | `POST /bots/{id}/pause_recording` · `resume_recording` | **1:1** - empty body |
| `POST /webhook/` (global) | `callback_url` on `create_bot` | webhooks are per-bot |

**Request fields (on create_bot)**

| Recall | MeetStream |
| ------ | ---------- |
| `meeting_url` | `meeting_link` |
| `recording_mode` (`speaker_view`/`gallery_view`/`audio_only`) | `video_required` (boolean) + `recording_config.video_layout` (`speaker_view`/`grid_view`). `audio_only` maps to `video_required: false`. Recall's `gallery_view` maps to `grid_view`. Default every migrated bot to `video_required: false`, and send `video_layout: "speaker_view"` when video is on: the MeetStream API default is `grid_view`. |
| `metadata` | `custom_attributes` (string values) |
| `transcription_options` | `recording_config.transcript` (object shape differs - review) |
| `real_time_transcription.destination_url` | `live_transcription_required.webhook_url` (requires a streaming provider) |
| `noone_joined_timeout` | `automatic_leave.voice_inactivity_timeout` |
| `assembly_ai` | `assemblyai` |

**Webhooks**: every delivery carries the event name under **`event`**, and most also carry **`bot_event`** with the specific name. Map Recall's string events to MeetStream's:

- `bot.in_call_recording` → `bot.recording`, `bot.in_waiting_room` → `bot.in_waiting_room`, etc.
- Recall's separate end reasons arrive as one **`event: "bot.stopped"`** whose **`bot_event`** says why: `bot.stopped` (clean exit), `bot.kicked` (removed by a participant), `bot.notallowed` (lobby timeout), `bot.denied` (host refused), `bot.failed` (crash). Lobby timeouts, denials and failures carry `status_code: 500`; clean exits and kicks `200`. Branch on `bot_event`, since a kick and a clean exit both report `bot_status: "Stopped"`.
- Streaming-only providers produce no `transcription.processed`, but `bot.done` still fires on every path.

For the complete event catalog and payloads, use the `webhook_events_guide` reference (via the MeetStream MCP server) or `references/api-reference.md`.

## Coming from MeetingBaaS, Attendee or an in-house bot

The migration kit reads Recall.ai code only. For MeetingBaaS, Attendee or your own bot,
port by hand with the same four mappings as Path B:

1. Your create-bot call → `POST https://api.meetstream.ai/api/v1/bots/create_bot` with
   `Authorization: Token YOUR_API_KEY`, `meeting_link`, `bot_name`, `callback_url`
   (or workspace webhooks) and your ids in `custom_attributes`.
2. Your status handling → the `bot.*` webhook events: branch on `bot_event` (`bot.stopped`,
   `bot.notallowed`, `bot.denied`, `bot.kicked`, `bot.failed`).
3. Your transcript fetch → `transcription.processed`, then `get_transcript` by
   `transcript_id` (segments use `transcript`, not `text`). Pick the provider in
   `recording_config.transcript.provider` (`meetstream` needs no key).
4. Media → `get_audio`, `get_video`, `get_audio_streams` (`recordings-and-media`).

Zoom bots join through your Zoom app with OBF or ZAK (`platform-setup`). For data location
or residency questions, contact support (https://docs.meetstream.ai/guides/help/support);
do not promise a region.

## Post-migration checklist

1. Swap `RECALL_API_KEY` → your MeetStream API key in env and secrets.
2. Confirm auth header is `Authorization: Token <key>`.
3. Point webhooks at your handler via `callback_url` on `create_bot`.
4. Fetch transcripts by **`transcript_id`** (from the create response or `/bots/{id}/transcriptions`), not `bot_id`.
5. Convert `recording_mode` values to the `video_required` boolean.
6. Update webhook handlers: `event` key, collapse end-reasons into `bot.stopped` + `bot_status`, check `status_code` (200 success / 500 failure).
7. Run `meetstream-migrate test --api-key ...` (optionally `--meeting-url <url>`) to confirm the live API responds.
8. Review anything the migrator flagged (only the full live-video-output case is unsupported today).

## What to tell the client

MeetStream matches Recall on the core bot lifecycle, recording, per-participant streams, real-time audio/transcript, chat + image output, calendar (Google + Outlook), scheduling, signed-in bots, retention, and **pause/resume recording**. Same auth scheme, near-identical endpoints, lower price.

## Latest docs

- Migrate from Recall.ai: https://docs.meetstream.ai/migration/migrate-from-recall
- Create Bot payload reference: https://docs.meetstream.ai/api-reference/create-bot-payload-reference
- Webhooks and events: https://docs.meetstream.ai/guides/webhooks/webhooks-and-events

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
