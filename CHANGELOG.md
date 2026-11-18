# Changelog

All notable changes to the MeetStream Claude Code plugin.

## [2.7.0] - 2026-11-18

Brings the plugin up to MeetStream API v1.9.0, adds intake routing, and stops agents from giving version-stability advice. Replaces the open 2.5.1 and API v1.7.0-v1.9.0 changes, re-applied on top of 2.6.0.

### Fixed
- **No version-stability advice.** Skills described per-version gates ("MCP server 0.3.2+", "CLI 0.4.0+"), an "old Node server frozen at 0.3.0", a migrator build that "lags", "as of v2.2" and "used to / now" history. Agents turned these into unprompted claims that one version is stable and another might break. Skills now describe current behaviour only: everyone uses the hosted MCP at `https://mcp.meetstream.ai/mcp`. The README badge showed 2.2.0; it now matches the manifests, and CI checks the badge and the top CHANGELOG entry.
- `INSTALL_FOR_AGENTS.md` no longer offers "answer questions in the meeting chat": no skill in this plugin does that.
- `migrate-from-recall` no longer claims built-in AI summaries (the API has none) or a roadmap item.

### Changed
- **Zoom needs no setup.** A Zoom bot needs only the MeetStream sign-in or API key and the meeting link. Your own Zoom app is optional (ZAK / OBF joins, per-participant camera video, live bot camera video). `zoom.use_own_app` (`true` / `false` / omitted) picks the join; there is no fallback when Zoom refuses the user's own app.
- **`video_required` defaults to `false`** and `audio_required` is a real `create_bot` field (default `true`). Send `video_required` explicitly anyway. Both `false` with nothing else to do returns 400.
- **`get_speaker_timeline`** can return `{bot_id, speaker_timeline_url, size_bytes, truncated}` for large timelines.
- **`recording_permission_denied_timeout`** range is 60 to 600 seconds, default 600.
- **`bot_image_url`** must be an https:// PNG, JPEG, GIF or WebP URL on a public host; other values return 400.
- Zoom `meeting_captions` works only on bots that join without the user's own Zoom app. Voice agents on those bots can show images, video and an avatar.

### Added
- **Intake routing** in `meetstream` and `getting-started`, matched in `join-meeting`, `meeting-brief`, `mia-voice-agents`, `realtime-streaming`, `AGENTS.md` and `INSTALL_FOR_AGENTS.md`: MeetStream is meeting-bot and recording infrastructure first; when intent is unclear the agent asks "after the meeting or live?"; voice agents only when the user asks for one ("voice agent", "agent in the meeting", a bot that talks or answers, or "MIA"). Voice agent setups in order: MeetStream-managed keys (`key_source: "meetstream"`), the user's own provider keys, then the user's own agent (for example a Claude Code subscription) through the MeetStream Agent Kit, with a prompt-injection warning.
- **When the MeetStream tools are missing or not signed in**, skills give the one step to connect (Claude Code, Cursor, Codex) and still help with the plan or the REST call.
- Live captions: `realtime-streaming` starts with how live transcripts reach a web app (HTTPS POST to your server, then SSE or your own WebSocket to the browser). Raise hand is offered as the REST `send_command` call even though there is no MCP tool. Low credits name the `top_up_link` tool and the billing page; a balance that is not available is normal. A "which version?" question gets "install or update the current plugin; the MCP server is hosted, nothing to pin".
- **Raise / lower hand** through the REST `POST /api/v1/bots/{bot_id}/send_command` (`raise_hand` / `lower_hand`, `hand_raised` in the response, 409 before the bot is in the meeting).
- **Participant hand events** `participant_events.raise_hand` / `participant_events.lower_hand` (Google Meet, Zoom), opt-in through `recording_config.realtime_endpoints`.
- `bot_camera_stream`, `storage_id`, `video_layout` values `speaker_view_default` / `grid_view_default` (Google Meet, Teams), Smallest AI transcription (`smallest`, `smallest_streaming`), Anthropic Claude as a voice-agent LLM (not a transcription provider), `update_mia` with `wait_for_ack`, failure reasons `MeetingRestricted`, `SignInRequired`, `InvalidMeetingLink`.
- "Errors, Rate Limits and Validation": `{"message": ...}` error bodies, the prepaid 429 (5 per minute, 50 per hour) with `Retry-After`, the `create_bot` 400s and the public-address rule. `join-meeting` handles the 429.

## [2.6.0] - 2026-11-17

### Fixed
- **The marketplace now installs the current plugin.** It pinned commit `89b1d4a` (2.2.3, 2026-08-06), so installs from this repo missed every later release. The plugin source is now `./`.

### Added
- **Hosted MCP server in the plugin** (`.mcp.json`): installing the plugin adds `https://mcp.meetstream.ai/mcp` (HTTP, OAuth). Sign in once with `/mcp` → Authenticate; no API key to copy.
- **Use-it skills, the same as the Cursor plugin** (one skill set for every agent): `join-meeting` (send a bot to the user's own meeting; keyless `meetstream` transcription by default, audio-only, reuses an existing bot, low-credit handling), `meeting-brief` (post-call brief that is saved and remembered for later questions). **Merged from the Cursor plugin** so every agent has the same skills: `recordings-and-media`, `mia-voice-agents`, `realtime-streaming`, `webhooks`, `platform-setup`, `troubleshooting`; `calendar-automation` now covers both using the MCP tools from an agent (Google and Outlook) and the Google Calendar app scaffold. Cursor's `build-notetaker` is covered by `meetstream` and `notetaker`. A `.cursor-plugin` manifest ships in this repo. CI validates manifests and skills on every PR. Live answers in the meeting chat are in the Hermes plugin (`hermes-meetstream`); other agents get them with the live path later.
- **Other agents**: Codex and Copilot CLI install this plugin from the same Claude manifests (Codex checked: skills and MCP server load); `setup --host codex|muse|openclaw|copilot|claude` for agents without a plugin installer; `INSTALL_FOR_AGENTS.md`, which an agent can follow end to end (ends with a real `list_bots` call). Hermes and Cursor point to their existing MeetStream plugins.

## [2.5.0] - 2026-09-22

### Changed
- **Recording defaults policy applied across the plugin: video off by default, speaker view when video is on, per-participant video only on request.** New "Recording Defaults" section in the core skill states all three rules in one place, and the decision tree, the `create_bot` field list and the Common Mistakes list now carry them.
- Decision tree Step 1: Q1.4 asks whether the user actually asked for video and defaults to `"video_required": false`; new Q1.4a picks the layout; Q1.6 makes per-participant video an explicit opt-in.
- `agents/meetstream-debugger.md`: three new error-catalog rows for unexpected video, grid-view output, and unexpected per-participant webcam files.
- Inline notes on the `notetaker`, `sales-coach`, `calendar-automation` and `verify-account` examples confirming they are audio only.

### Added
- **`recording_config.video_layout` documented** in the core skill and `references/api-reference.md`: values are exactly `speaker_view` and `grid_view`, `grid_view` is the API default when `video_required: true`, the field is ignored when video is off, Google Meet / Teams / Zoom accept both values, and WhatsApp accepts only `grid_view`.
- Common Mistakes 27 (video on without a layout) and 28 (setting `video_separate_streams` unasked).
- The live-video examples in the core skill and both code-pattern reference files now send `video_layout: "speaker_view"`.

### Fixed
- `skills/migrate-from-recall/SKILL.md`: the Recall `recording_mode` row mapped only to `video_required`, losing the layout. It now maps to `video_required` plus `recording_config.video_layout` (`gallery_view` to `grid_view`, `audio_only` to `video_required: false`).

## [2.4.0] - 2026-09-18

### Added
- **Microsoft Teams Signed-In Bots** section in the core skill: dedicated M365 tenant setup (security defaults off, SSPR None), `/teams-login-domains` + `/teams-logins` registration, the `create_bot` `teams` block (`login_required`, `teams_login_domain`, `sign_in_email`, `strict_email`), one concurrent bot per account, name/avatar from the Microsoft account, and the 400/403/404/409/429 error table.
- Decision tree step Q2.4 for Teams sign-in, and a signed-in row in the Platform Notes table.
- `references/api-reference.md`: all Teams login endpoints with bodies and responses, and the `teams` / `google_meet` create_bot fields.
- Pointers to the CLI (`meetstream logins`, `bot create --teams-login-domain / --google-login-domain`, 0.4.0+) and MCP `create_bot` params (0.3.2+).

### Fixed
- Google Signed-In Bots: added `sign_in_email` / `strict_email`; domain body uses `sso_workspace_domain`; logins take `sso_private_key_pem` / `sso_cert_pem`; updates are PATCH (not PUT) with `domain` in the body, deletes need `?domain=`, and there is no `GET /google-logins/{login_id}`.
- Removed the em dashes left in the plugin description.

## [2.3.0] - 2026-09-18

### Fixed
- **Webhook model rewritten against 4,139 captured deliveries (Jun 2026).** Terminals are two-layer: every ending arrives once as `event: "bot.stopped"` and `bot_event` gives the reason (`bot.stopped`, `bot.kicked`, `bot.notallowed`, `bot.denied`, `bot.failed`). Lobby timeouts, denials and failures carry `status_code: 500`. Every event carries a `timestamp`. `bot.done` fires on every path, streaming-only bots included. Added `bot.in_waiting_room`, `bot.scheduled`, `bot.uploading`, `bot.transcriptionready` and the `*.skipped` events.
- Example webhook handlers branch on `bot_event` instead of `bot_status` (a kick and a clean exit both report `Stopped`); the status poller compares case-insensitively (`FAILED` / `ERROR` / `Failed`).
- Zoom authenticated joins use `zoom.zak_url` / `zoom.obf_url`. Removed `use_zoom_obf` and the old OAuth callback URL, which the API now rejects.
- Default retention is 30 days (720h), not 24h.
- `word_is_final` does appear on most live-transcript words; documented as optional.

### Changed
- Removed per-hour provider price estimates from the notetaker skill.
- Removed remaining em dashes.

## [2.2.0] - 2026-05-27

### Added
- **`skills/getting-started/`** - first-time onboarding skill that walks brand-new users through signup at https://app.meetstream.ai, API key creation, environment variable setup, and validation ping. Every use-case skill now auto-invokes this if `MEETSTREAM_API_KEY` is missing - no more "scaffolded app that crashes on first run."
- **Power Prompts Gallery** - 10 elaborate copy-paste prompts in `README.md` that scaffold complete production apps in one shot (API-triggered notetaker with email delivery, real-time sales coach, Google Calendar auto-recording, CRM auto-enricher, interview recorder, multi-tenant SaaS, compliance recorder, AI Meeting Assistant via MIA, live captions broadcaster, customer call analyzer dashboard).
- **Step 0 auth check** on all 5 use-case skills (notetaker, sales-coach, calendar-automation, verify-account, test-bot) - explicit hand-off pattern to `getting-started` skill.
- **Power-prompt summary section** in `skills/meetstream/SKILL.md` so Claude recognizes one-shot product spec patterns and pre-picks sensible defaults instead of asking 4 clarifying questions.

### Changed
- All Slack references removed from skills and README - Slack delivery is the user's own integration, not a MeetStream native feature. Power prompt #1 replaced with "API-triggered AI notetaker with email delivery (Resend)."
- Delivery-option lists in `notetaker`, `sales-coach`, and `calendar-automation` skills reframed: MeetStream provides the transcript; delivery channel (email/webhook/DB) is the user's own choice.
- Plugin version → `2.2.0`.
- Marketplace.json keywords synced to match plugin.json (35 keywords).
- Core `meetstream` skill description strengthened with 10+ explicit trigger phrases for better Claude auto-activation.

## [2.1.0] - 2026-05-27

### Added
- **`skills/calendar-automation/`** - Google Calendar OAuth + auto-record scaffold. Walks user through Google Cloud OAuth setup, `/calendar/create_calendar` connect, hands-free auto-scheduling, per-event manual scheduling with recurring options, and safe `DELETE /calendar/disconnect` cleanup.
- 6 calendar SEO keywords (`google-calendar-integration`, `google-calendar-bot`, `calendar-automation`, `calendar-notetaker`, `scheduled-meeting-bot`, `recurring-meeting-bot`).

### Fixed
- `DELETE /calendar/disconnect` documented as the single correct path across all files (was previously "try POST then fall back to DELETE"). Docs guide + cURL examples are authoritative; OpenAPI spec's POST is a quirk.
- All 15 calendar endpoints re-verified accurate against fresh `docs.meetstream.ai`.

### Removed
- `skills/migrate-from-recall/` deleted entirely.
- All competitor mentions across skills, README, and SEO keyword blocks.

## [2.0.0] - 2026-05-27

### Added
- **5 verb-named use-case skills** that scaffold complete apps:
  - `skills/notetaker/` - full AI meeting notetaker with webhook handler, transcript fetch, LLM summary, email delivery
  - `skills/sales-coach/` - real-time AI sales coach with WebSocket browser UI (XSS-safe DOM rendering)
  - `skills/verify-account/` - probes every transcription provider in user's account
  - `skills/test-bot/` - send a single test bot + watch every webhook event live
- **`agents/meetstream-debugger.md`** - focused subagent for bot failure diagnosis, read-only tools, returns root cause in under 30 lines.
- **Plugin manifest v2.0** with 19 use-case-focused SEO keywords for marketplace discoverability.
- **README overhaul** with 60-second quickstart, use case showcase, live-tested correctness callouts.

## [1.5.0] - 2026-05-26

### Added
- Live-API-tested `bot_details.transcript_id` as canonical stateless transcript fetch path.
- Two-path lifecycle documentation (Path A: post-call providers → `bot.done` terminal; Path B: streaming providers → `audio.processed` terminal).
- New events documented: `bot.recording`, `bot.leaving`, `bot.done`, `manifest.completed`, `transcription.failed`, `bot.error`.
- `POST /bots/{id}/transcribe` re-transcribe path as backup/fallback.
- Bot Configuration Decision Tree (walks the user through every `create_bot` field).
- Live audio binary frame format + live video fMP4 WebSocket protocol.
- Full MIA (Meeting Infrastructure Agents) surface.
- All 5 WebSocket control commands (`sendaudio`, `sendmsg`, `sendchat`, `interrupt`, `sendimg`/`sendimg_url`).

### Fixed
- Removed every hallucinated endpoint, field name, and response shape claim.
- `create_bot` returns HTTP 201 (not 200).
- `status_code` not always 200 - failure events use 500.
- `recording_permission_denied_timeout` range 60–300 seconds (live-tested API constraint).
- `in_call_recording_timeout` minimum 600 seconds (live-tested API constraint).
- Many other corrections from live API testing against `api.meetstream.ai`.

## [1.0.0] - Initial release

- Core `meetstream` skill with API reference, code patterns (Python + Node.js), webhook event documentation.
- Marketplace listing on `meetstream-ai/claude-plugin`.
