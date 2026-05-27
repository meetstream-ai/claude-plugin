# Changelog

All notable changes to the MeetStream Claude Code plugin.

## [2.2.0] — 2026-05-27

### Added
- **`skills/getting-started/`** — first-time onboarding skill that walks brand-new users through signup at https://app.meetstream.ai, API key creation, environment variable setup, and validation ping. Every use-case skill now auto-invokes this if `MEETSTREAM_API_KEY` is missing — no more "scaffolded app that crashes on first run."
- **Power Prompts Gallery** — 10 elaborate copy-paste prompts in `README.md` that scaffold complete production apps in one shot (API-triggered notetaker with email delivery, real-time sales coach, Google Calendar auto-recording, CRM auto-enricher, interview recorder, multi-tenant SaaS, compliance recorder, AI Meeting Assistant via MIA, live captions broadcaster, customer call analyzer dashboard).
- **Step 0 auth check** on all 5 use-case skills (notetaker, sales-coach, calendar-automation, verify-account, test-bot) — explicit hand-off pattern to `getting-started` skill.
- **Power-prompt summary section** in `skills/meetstream/SKILL.md` so Claude recognizes one-shot product spec patterns and pre-picks sensible defaults instead of asking 4 clarifying questions.

### Changed
- All Slack references removed from skills and README — Slack delivery is the user's own integration, not a MeetStream native feature. Power prompt #1 replaced with "API-triggered AI notetaker with email delivery (Resend)."
- Delivery-option lists in `notetaker`, `sales-coach`, and `calendar-automation` skills reframed: MeetStream provides the transcript; delivery channel (email/webhook/DB) is the user's own choice.
- Plugin version → `2.2.0`.
- Marketplace.json keywords synced to match plugin.json (35 keywords).
- Core `meetstream` skill description strengthened with 10+ explicit trigger phrases for better Claude auto-activation.

## [2.1.0] — 2026-05-27

### Added
- **`skills/calendar-automation/`** — Google Calendar OAuth + auto-record scaffold. Walks user through Google Cloud OAuth setup, `/calendar/create_calendar` connect, hands-free auto-scheduling, per-event manual scheduling with recurring options, and safe `DELETE /calendar/disconnect` cleanup.
- 6 calendar SEO keywords (`google-calendar-integration`, `google-calendar-bot`, `calendar-automation`, `calendar-notetaker`, `scheduled-meeting-bot`, `recurring-meeting-bot`).

### Fixed
- `DELETE /calendar/disconnect` documented as the single correct path across all files (was previously "try POST then fall back to DELETE"). Docs guide + cURL examples are authoritative; OpenAPI spec's POST is a quirk.
- All 15 calendar endpoints re-verified accurate against fresh `docs.meetstream.ai`.

### Removed
- `skills/migrate-from-recall/` deleted entirely.
- All competitor mentions across skills, README, and SEO keyword blocks.

## [2.0.0] — 2026-05-27

### Added
- **5 verb-named use-case skills** that scaffold complete apps:
  - `skills/notetaker/` — full AI meeting notetaker with webhook handler, transcript fetch, LLM summary, email delivery
  - `skills/sales-coach/` — real-time AI sales coach with WebSocket browser UI (XSS-safe DOM rendering)
  - `skills/verify-account/` — probes every transcription provider in user's account
  - `skills/test-bot/` — send a single test bot + watch every webhook event live
- **`agents/meetstream-debugger.md`** — focused subagent for bot failure diagnosis, read-only tools, returns root cause in under 30 lines.
- **Plugin manifest v2.0** with 19 use-case-focused SEO keywords for marketplace discoverability.
- **README overhaul** with 60-second quickstart, use case showcase, live-tested correctness callouts.

## [1.5.0] — 2026-05-26

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
- `status_code` not always 200 — failure events use 500.
- `recording_permission_denied_timeout` range 60–300 seconds (live-tested API constraint).
- `in_call_recording_timeout` minimum 600 seconds (live-tested API constraint).
- Many other corrections from live API testing against `api.meetstream.ai`.

## [1.0.0] — Initial release

- Core `meetstream` skill with API reference, code patterns (Python + Node.js), webhook event documentation.
- Marketplace listing on `meetstream-ai/claude-plugin`.
