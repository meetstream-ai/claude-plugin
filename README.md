<div align="center">

<img src="https://framerusercontent.com/images/qADooqa4mVlS7haEXkSI2cgaE.png" alt="MeetStream" width="80" />

# MeetStream for Claude Code

**The fastest way to build meeting intelligence — AI notetakers, real-time sales coaches, transcription pipelines, and Google Calendar–driven recording automation.**

[![Plugin Version](https://img.shields.io/badge/plugin-v2.0.0-5C4EFF?style=for-the-badge)](https://github.com/meetstream-ai/claude-plugin)
[![Live-Tested](https://img.shields.io/badge/endpoints-live--tested-10B981?style=for-the-badge)](https://github.com/meetstream-ai/claude-plugin/commits/main)
[![MIT License](https://img.shields.io/badge/license-MIT-yellow?style=for-the-badge)](LICENSE)
[![Get API Key](https://img.shields.io/badge/get%20api%20key-app.meetstream.ai-0EA5E9?style=for-the-badge)](https://app.meetstream.ai/api-keys)

</div>

---

## 60-second quickstart

```bash
# 1. Install the plugin
claude plugin install meetstream-ai/meetstream

# 2. Set your API key (one-time)
export MEETSTREAM_API_KEY=ms_xxxxx

# 3. Verify your account is configured
claude "verify my meetstream account"

# 4. Build something
claude "build me an AI meeting notetaker that emails summaries"
```

That's it. Claude scaffolds a working FastAPI/Express app with the webhook handler, transcript fetch, LLM summary, and delivery layer wired up.

---

## What you can build

The fastest path from idea to production for every meeting-intelligence use case:

| Use case | Try in Claude | What you get |
|---|---|---|
| 🎙️ **AI Meeting Notetaker** | *"build me an AI notetaker"* | Full webhook server + transcript fetch + GPT-4 summary + email/Slack/Notion delivery |
| 🎯 **Real-Time AI Sales Coach** | *"build a real-time AI sales coach"* | Live transcription + objection detection + WebSocket push to seller's browser |
| 📊 **Conversation Intelligence Platform** | *"build a conversation intelligence tool"* | Live + post-call transcripts + speaker analytics + searchable archive |
| 📅 **Google Calendar Auto-Recording** | *"auto-record every meeting on my Google Calendar"* | OAuth setup + `/calendar/create_calendar` + auto-schedule + recurring event handling + post-meeting delivery |
| 🔁 **Scheduled / Recurring Meeting Bot** | *"join every standup automatically"* | Calendar-driven, hands-free — bot joins 1 min before each meeting, recurring events auto-reschedule |
| 🤖 **AI Meeting Assistant (MIA)** | *"build an AI agent that joins my meetings"* | MIA agent config (pipeline/realtime) + hosted bridge + voice/text interaction |
| 📞 **Customer Call Analyzer** | *"analyze every sales call for insights"* | Transcript → LLM extraction → CRM auto-update → trend dashboards |
| 🌍 **Multilingual Meeting Transcriber** | *"transcribe Hindi/Tamil/Telugu meetings"* | Sarvam provider + Indic language config + translation |
| 🎬 **Compliance Meeting Recorder** | *"record meetings with 90-day retention"* | Long-retention bot + per-participant audio + audit trail |
| 📝 **Live Captions Service** | *"build a live captions service"* | Streaming bot + caption broadcast UI + multilingual support |
| 🎓 **Interview Recorder** | *"record + diarize interview meetings"* | Per-participant audio tracks + speaker labels + structured transcript |

---

## 🚀 Copy-paste power prompts (build a full app in one shot)

Each of these is a complete, production-quality prompt. Paste any one into Claude Code and you'll get a working, end-to-end app — webhook server, MeetStream integration, AI processing, delivery layer, error handling, all wired up.

### 1️⃣ Slack-integrated AI notetaker (one prompt)

> Build me a Slack-integrated AI meeting notetaker in **Python + FastAPI**. Flow: user runs `/note <meeting-link>` in Slack → bot joins via MeetStream → meeting ends → fetch transcript via `bot_details.transcript_id` → generate a structured summary with GPT-4o (key decisions, action items with owners, open questions) → DM the user who triggered it AND post a thread reply in the original channel with the summary. Use **deepgram** as the transcription provider. Include: idempotent webhook handler (dedupe with timestamp || message fallback), Redis-backed dedup, graceful handling of `transcription.failed` (retry with a different provider via `/transcribe`), `.env` config with `.gitignore`, README with `ngrok` setup, and a `requirements.txt`. Tag every bot with the Slack user_id in `custom_attributes`. Use the recommended `automatic_leave` defaults (600/600/600/14400/300).

### 2️⃣ Real-time AI sales coach with browser dashboard (one prompt)

> Build me a real-time AI sales coaching tool in **Python + FastAPI + vanilla JS**. Flow: sales rep clicks "Start Coaching" in a web UI → enters meeting link → MeetStream bot joins with `meetstream_streaming` (no external provider key needed) + `live_transcription_required.webhook_url` → live chunks stream to FastAPI → debounced LLM (GPT-4o-mini) detects objections / buying signals / talk-time imbalance every `end_of_turn=true` → push coach cards to the rep's browser via WebSocket → render as colored cards (objection=red, signal=green, monologue=orange). Include: stateless transcript_id lookup via `bot_details.transcript_id`, XSS-safe rendering with `textContent` (not `innerHTML`), `bot.error` handling (surface as warning card), graceful WebSocket reconnect, and a "Stop Coaching" button that calls `/bots/{id}/remove_bot`. Provide a single-file `coach.html` UI plus the full backend.

### 3️⃣ Google Calendar auto-recording with summary delivery (one prompt)

> Build me a Google Calendar auto-recording system on MeetStream in **Python + FastAPI**. Flow: connect my Google Calendar via OAuth (use the helper script in the `calendar-automation` skill) → enable `/calendar/auto-schedule/enable` with a default_bot_config using deepgram → MeetStream auto-joins every upcoming meeting 1 min before start → webhook on `transcription.processed` → fetch transcript via canonical `bot_details.transcript_id` flow → generate AI summary → email me via Resend AND save to Notion via the Notion API. Include: full OAuth helper script (with `http://localhost:8080` redirect), `connect.py` (one-time call to `/calendar/create_calendar` with `google_` prefixed fields), `enable.py` (auto-schedule), `webhook.py` (FastAPI server with idempotent handler), `delivery.py` (Resend + Notion clients), and a `disable.sh` script that uses `DELETE /calendar/disconnect` for safe cleanup. Handle recurring events by setting `recurring_event: true` so each occurrence reschedules automatically.

### 4️⃣ CRM auto-enricher (HubSpot) for sales calls (one prompt)

> Build me a HubSpot CRM auto-enricher in **Node.js + Express + TypeScript**. Flow: every sales call recorded via MeetStream → on `transcription.processed` webhook → fetch transcript via canonical `bot_details.transcript_id` flow → run two LLM extractions in parallel (Claude 3.5 Sonnet): (a) extract action items with owners, (b) extract competitor mentions / pricing objections / next-step commitments → upsert a HubSpot "Meeting Activity" record with the summary + action items → if the meeting was on a known deal record (correlated via `custom_attributes.deal_id`), update the deal's `next_step` and `last_meeting_summary` properties. Include: idempotent webhook handler with dedup, retry-on-429 for HubSpot writes, structured error logging, env-based config, `.env.example`, README, and a `seed.ts` script that creates a test bot tagged with a test `deal_id` to verify the whole pipeline end-to-end.

### 5️⃣ Interview recorder with per-participant audio for HR/recruiting (one prompt)

> Build me an interview recorder for a recruiting SaaS in **Python + Django**. Flow: recruiter creates an interview record in our Django app with `candidate_email`, `interviewer_emails`, `meeting_link`, `position_id` → on save, send a MeetStream bot with `audio_separate_streams: true` (per-participant audio for clean candidate-only transcripts later) + deepgram post-call provider + `custom_attributes.interview_id={record.pk}` → on `bot.done`, fetch the per-participant audio streams via `/bots/{id}/get_audio_streams` (10-min URLs — download immediately to S3) + fetch the full transcript via canonical flow → generate a structured interview report (candidate strengths/concerns/skills mentioned/red flags) using Claude 3.5 Sonnet → save report + audio S3 URLs to a `InterviewRecording` model → email the recruiter when complete. Include: Django models, signal handlers, Celery tasks for the long-running download/processing work, and explicit handling of the 10-minute URL TTL (always re-fetch on access, never store the URLs).

### 6️⃣ Multi-tenant notetaker SaaS — each user connects their own calendar (one prompt)

> Build me a multi-tenant notetaker SaaS in **Next.js 14 (App Router) + Postgres + Prisma**. Flow: user signs up → connects their own Google Calendar via per-user OAuth (each user has their own refresh token, all stored encrypted in Postgres) → my app calls `/calendar/create_calendar` with that user's credentials → enable auto-scheduling → webhooks fire for every meeting → I fetch transcript via canonical flow → AI summary → email to that specific user via Resend. Include: full Next.js App Router setup, Prisma schema for `User`, `CalendarConnection`, `Meeting`, `Summary`, Google OAuth route handlers, encrypted secret storage helper using AWS KMS (or local sealedbox for dev), one webhook endpoint that routes by `custom_attributes.tenant_id`, idempotent processing with Postgres-backed dedup table, billing-ready Stripe Checkout integration (free tier: 10 meetings/mo, pro: $20/mo unlimited), and a clean React dashboard showing the user's last 10 summarized meetings.

### 7️⃣ Compliance meeting recorder with 90-day retention + audit log (one prompt)

> Build me a compliance-grade meeting recorder for regulated industries (healthcare/legal/finance) in **Python + FastAPI**. Flow: every recorded meeting MUST have `recording_config.retention.hours: 2160` (90 days), `audio_separate_streams: true` (for legal evidentiary separation), explicit consent flag in `custom_attributes.consent_obtained_at` (ISO timestamp + obtained_by user_id) → on `bot.inmeeting` webhook, write an audit log entry to an append-only Postgres `audit_log` table (never UPDATE, only INSERT) → on `bot.stopped`, mark the session complete → on `transcription.processed`, fetch + encrypt the transcript at rest (AES-256-GCM with KMS-managed keys) before storing → on `data_deletion` webhook, write a deletion audit entry. Include: full SQLAlchemy models, KMS encryption helpers, a `/audit/{meeting_id}` admin endpoint that returns the full timeline of bot status + processing + delete events, IP allowlist middleware for admin routes, structured JSON logging compatible with Datadog/Splunk, and a README section documenting the compliance posture for legal/security review.

### 8️⃣ AI Meeting Assistant (MIA) — voice-interactive bot that participates in the meeting (one prompt)

> Build me a voice-interactive AI assistant that joins meetings and participates conversationally. Use MeetStream's MIA (Meeting Infrastructure Agent). Flow: I run a script to create a pipeline-mode MIA agent config via `POST /api/v1/mia` (OpenAI gpt-4.1 LLM + ElevenLabs voice + Deepgram nova-3 streaming transcriber + first_message: "Hi everyone, I'm Acme AI joining to help with this meeting. Just say 'Hey Acme' to address me.") → save the returned `agent_config_id` → my Next.js dashboard has a "Send AI to Meeting" button that creates a bot with the trio of required fields (`agent_config_id` + `socket_connection_url: wss://agent-meetstream-prd-main.meetstream.ai/bridge` + `live_audio_required: wss://agent-meetstream-prd-main.meetstream.ai/bridge/audio`) → wake word `["hey acme"]` with 30s timeout → the agent responds to questions, takes notes when asked, summarizes on demand → post-meeting summary delivered via email. Include: the agent-config creation script, the bot-creation handler, a webhook server that catches `bot.error` (streaming-provider auth issue → surface to user, don't fail silently), and a settings UI to edit the agent's system prompt without redeploying.

### 9️⃣ Live captions service for accessibility (one prompt)

> Build me a real-time live captions broadcaster for accessibility (hearing-impaired users) in **Python + FastAPI + Server-Sent Events**. Flow: meeting organizer triggers `POST /captions/start` with a meeting link → MeetStream bot joins with `meetstream_streaming` + `live_transcription_required.webhook_url` → live chunks POSTed to my server → I rebroadcast via SSE to any connected client at `GET /captions/{session_id}` → clients render large, readable captions in their browser with speaker names and a scrolling history. Include: SSE handler that broadcasts to all connected clients per session, a clean accessibility-friendly HTML page (high-contrast, large font, ARIA labels), graceful disconnect handling, automatic 5-minute idle cleanup, and a `nginx.conf` snippet showing how to proxy SSE with proper buffering settings. No LLM processing — captions are passthrough only, raw transcript chunks rendered live.

### 🔟 Customer call analyzer with weekly insights dashboard (one prompt)

> Build me a customer call analyzer + insights dashboard in **Python + FastAPI + Postgres + React**. Flow: every customer call recorded via MeetStream (tagged with `custom_attributes.customer_id`, `custom_attributes.call_type` in {discovery, demo, follow-up, churn}) → on `transcription.processed` → fetch transcript → extract structured insights with Claude (sentiment, top topics, pricing objections mentioned, feature requests, competitive mentions, customer health signals like {happy, frustrated, churning}) → store in Postgres with proper indexing → React dashboard shows: per-customer call history, week-over-week sentiment trend, top 10 feature requests across all customers, churn risk leaderboard, competitor mention frequency. Include: full Postgres schema, indexes optimized for the dashboard queries, daily aggregation cron, React + Tanstack Query dashboard, role-based access (sales reps see their own customers, managers see all), and CSV export for any view.

---

> 💡 **First time?** Each of these power prompts assumes you have a MeetStream API key set. If you don't, run *"set up MeetStream"* first — it walks you through signup at https://app.meetstream.ai and key creation in 60 seconds.

---

## Why this plugin

| | Most API plugins | This plugin |
|---|---|---|
| Endpoint correctness | ❌ Common hallucinations (wrong paths, wrong fields) | ✅ Every endpoint live-tested against `api.meetstream.ai` |
| Webhook lifecycle | ❌ Generic claims ("you'll get an event") | ✅ All 12 events documented with full payloads, status codes, two-path semantics |
| Provider failure modes | ❌ Vague "configure your API key" | ✅ Live-captured error messages + exact fix for each |
| Use cases | ❌ Read the docs, write your own glue | ✅ Verb-named skills scaffold the whole app (`notetaker`, `sales-coach`, etc.) |
| Account health check | ❌ None | ✅ `verify-account` skill probes every provider before you start |
| Subagent for failures | ❌ None | ✅ `meetstream-debugger` triages bot failures without flooding main context |

---

## What's inside

```
skills/
├── meetstream/             ← Core skill: API reference, lifecycle, decision tree
├── notetaker/              ← Scaffold a complete AI meeting notetaker
├── sales-coach/            ← Scaffold a real-time AI sales coach with browser UI
├── calendar-automation/    ← Google Calendar OAuth + auto-record every meeting
├── verify-account/         ← Probe which providers are configured in your account
└── test-bot/               ← Send a test bot + watch webhooks live

agents/
└── meetstream-debugger     ← Subagent for diagnosing bot failures
```

## Live-tested correctness

Every endpoint, field name, response shape, and webhook event in this plugin has been verified by sending real bots to a real Google Meet and capturing real API responses. No hallucinations.

Specifically verified live:
- ✅ `create_bot` returns HTTP **201** Created
- ✅ `bot_details.transcript_id` is the canonical stateless fetch path (not in any webhook payload)
- ✅ Streaming providers produce **no post-call** `transcription.processed` event — lifecycle ends at `audio.processed`
- ✅ `bot.error` fires mid-meeting for streaming-provider auth issues (bot keeps recording)
- ✅ `recording_permission_denied_timeout` range is **60–300** seconds
- ✅ `in_call_recording_timeout` minimum is **600** seconds
- ✅ `POST /bots/{id}/transcribe` overwrites `bot_details.transcript_id` and fires exactly one webhook (no `bot.done` follow-up)

---

## Installation

### Claude Code (CLI)

```bash
# Add the marketplace + install
/plugin marketplace add meetstream-ai/claude-plugin
/plugin install meetstream@meetstream-ai
```

Then in any project:
```
"verify my meetstream account"
"build me an AI meeting notetaker"
"build a real-time AI sales coach"
"set up Google Calendar auto-recording for my meetings"
"connect Google Calendar to MeetStream"
```

### Cursor / Windsurf / VS Code (Claude extension)

Settings → Plugins → Add marketplace `meetstream-ai/claude-plugin` → Install **meetstream** → Reload.

### Update to the latest version

```bash
claude plugin update meetstream-ai/meetstream
```

---

## Configuration

Set once in your shell:
```bash
export MEETSTREAM_API_KEY=ms_xxxxx   # get one at https://app.meetstream.ai/api-keys
```

Optional for local webhook development:
```bash
export PUBLIC_URL=https://your-ngrok-url.ngrok-free.app
```

---

## Supported meeting platforms

| Platform | Setup | Live video | Per-participant audio |
|----------|-------|------------|----------------------|
| Google Meet | None | ✅ | ✅ |
| Microsoft Teams | None | ✅ | ❌ |
| Zoom | [Zoom app required](https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup) | ❌ | ✅ |

---

## The canonical post-call transcript flow

```
create_bot (with post-call provider + callback_url)
  ↓
bot.joining → bot.inmeeting → bot.recording
  ↓
[meeting runs]
  ↓
bot.leaving → bot.stopped → manifest.completed → audio.processed
  ↓
transcription.processed ← webhook fires when transcript is ready
  ↓
GET /bots/{bot_id}/detail → read bot_details.transcript_id
  ↓
GET /transcript/{transcript_id}/get_transcript → top-level array of segments
  ↓
bot.done ← terminal event
```

The plugin's skills walk you through every variant of this flow (live, post-call, hybrid, MIA agent, calendar auto-scheduled) with complete code.

---

## Links

- 🌐 [meetstream.ai](https://meetstream.ai) — product
- 📖 [docs.meetstream.ai](https://docs.meetstream.ai) — full API reference
- 🎛️ [app.meetstream.ai](https://app.meetstream.ai) — dashboard + API keys
- 🐙 [github.com/meetstream-ai/claude-plugin](https://github.com/meetstream-ai/claude-plugin) — this repo
- 💬 [hello@meetstream.ai](mailto:hello@meetstream.ai) — support

---

<!-- SEO keywords: meeting intelligence, AI notetaker, AI meeting assistant, AI sales coach,
     conversation intelligence, meeting transcription API, meeting bot API, real-time transcription,
     live transcription, speaker diarization, AI meeting summarizer, meeting recorder API,
     meeting summary generator, meeting bot SDK, AI conversation analytics, meeting AI platform,
     sales call analyzer, sales conversation intelligence, AI call coaching, real-time coaching,
     live meeting captions, meeting recap, meeting action items, AI meeting agent,
     Google Calendar integration, Google Calendar bot, Google Calendar meeting bot,
     calendar automation, calendar notetaker, scheduled meeting bot, recurring meeting bot,
     OAuth calendar integration, auto-record meetings, calendar API integration,
     Zoom bot API, Google Meet bot API, Microsoft Teams bot API,
     webhook, MCP server, Claude Code plugin, Anthropic plugin, MeetStream, MeetStream API -->

<div align="center">

Built by [MeetStream](https://meetstream.ai) · Made for [Claude Code](https://claude.ai/code)

</div>
