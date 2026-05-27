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
