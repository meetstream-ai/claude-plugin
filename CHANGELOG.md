# Changelog

All notable changes to the MeetStream Claude Code plugin.

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
