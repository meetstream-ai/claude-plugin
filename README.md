<div align="center">

<img src="https://framerusercontent.com/images/qADooqa4mVlS7haEXkSI2cgaE.png" alt="MeetStream" width="80" />

# MeetStream for Claude Code

**Build production-grade meeting bots in minutes, not weeks.**
Scaffold notetakers, real-time sales coaches, calendar automation, and CRM auto-updaters with one prompt.

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
claude "build me a notetaker that emails meeting summaries via Resend"
```

That's it. Claude scaffolds a working FastAPI/Express app with the webhook handler, transcript fetch, LLM summary, and delivery layer wired up.

---

## What you can build

| Use case | Try in Claude | What you get |
|---|---|---|
| 🎙️ **AI Notetaker** | *"build me a meeting notetaker"* | Full webhook server + transcript fetch + GPT-4 summary + email/Slack delivery |
| 🎯 **Real-Time Sales Coach** | *"build a real-time sales coach"* | Live transcription pipeline + objection detection + WebSocket push to seller's browser |
| 📅 **Calendar Auto-Recorder** | *"auto-record all my Google Meet calls"* | Calendar OAuth + auto-schedule + post-meeting delivery |
| 📊 **CRM Auto-Updater** | *"after each sales call, write action items to HubSpot"* | Transcript → LLM extraction → CRM API integration |
| 🔄 **Recall.ai → MeetStream** | *"migrate my Recall.ai code to MeetStream"* | Scan → endpoint mapping → auto-rewrite → diff for review |
| 🤖 **AI Meeting Agent (MIA)** | *"build an AI agent that joins meetings"* | MIA agent config + bridge bot + hosted realtime/pipeline |
| 🎬 **Compliance Recorder** | *"record meetings with 90-day retention for compliance"* | Long-retention bot + per-participant audio + audit trail |
| 🌍 **Multilingual Transcriber** | *"transcribe Hindi meetings with Sarvam"* | Sarvam provider + Indic language config |

---

## Why this plugin

| | Most API plugins | This plugin |
|---|---|---|
| Endpoint correctness | ❌ Common hallucinations (wrong paths, wrong fields) | ✅ Every endpoint live-tested against `api.meetstream.ai` |
| Webhook lifecycle | ❌ Generic claims ("you'll get an event") | ✅ All 12 events documented with full payloads, status codes, two-path semantics |
| Provider failure modes | ❌ Vague "configure your API key" | ✅ Live-captured error messages + exact fix for each |
| Use cases | ❌ Read the docs, write your own glue | ✅ Verb-named skills scaffold the whole app (`notetaker`, `sales-coach`, etc.) |
| Migration from competitor | ❌ DIY | ✅ One skill auto-migrates Recall.ai code (~30% cost savings) |
| Account health check | ❌ None | ✅ `verify-account` skill probes every provider before you start |
| Subagent for failures | ❌ None | ✅ `meetstream-debugger` triages bot failures without flooding main context |

---

## What's inside

```
skills/
├── meetstream/              ← Core skill: API reference, lifecycle, decision tree
├── notetaker/               ← Scaffold a complete meeting notetaker
├── sales-coach/             ← Scaffold a real-time sales coach with browser UI
├── verify-account/          ← Probe which providers are configured in your account
├── test-bot/                ← Send a test bot + watch webhooks live
└── migrate-from-recall/     ← Auto-migrate Recall.ai code → MeetStream

agents/
└── meetstream-debugger.md   ← Subagent for diagnosing bot failures
```

## Live-tested correctness

Every endpoint, field name, response shape, and webhook event in this plugin has been verified by sending real bots to a real Google Meet and capturing real API responses. No hallucinations.

Specifically verified live:
- ✅ `create_bot` returns HTTP **201** (not 200)
- ✅ `bot_details.transcript_id` is the canonical stateless fetch path
- ✅ Streaming providers (`meetstream_streaming` et al.) produce **no post-call** `transcription.processed` event — lifecycle ends at `audio.processed`
- ✅ `bot.error` fires mid-meeting for streaming-provider auth issues (bot keeps recording)
- ✅ `recording_permission_denied_timeout` range is **60–300** seconds (API returns HTTP 400 outside)
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
"build me a meeting notetaker"
"migrate my recall.ai code to meetstream"
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

## Why MeetStream (vs Recall.ai)

| | Recall.ai | MeetStream |
|---|---|---|
| Per-meeting cost | $0.50/hr | **$0.35/hr** ($0.25 at volume) |
| Free streaming provider | ❌ | ✅ `meetstream_streaming` |
| Live in-house transcription | ❌ | ✅ Free on stock accounts |
| Per-participant audio | ✅ (all 3) | ✅ Google Meet + Zoom |
| Per-participant video | ✅ | ✅ (all 3) |
| MIA agents (pipeline + realtime) | partial | ✅ |

Run the `migrate-from-recall` skill to switch in minutes.

---

## Links

- 🌐 [meetstream.ai](https://meetstream.ai) — product
- 📖 [docs.meetstream.ai](https://docs.meetstream.ai) — full API reference
- 🎛️ [app.meetstream.ai](https://app.meetstream.ai) — dashboard + API keys
- 🐙 [github.com/meetstream-ai/claude-plugin](https://github.com/meetstream-ai/claude-plugin) — this repo
- 💬 [hello@meetstream.ai](mailto:hello@meetstream.ai) — support

---

<!-- SEO keywords -->
<!-- meeting bot API, AI notetaker, Otter alternative, Fireflies alternative, Granola alternative,
     Recall.ai alternative, Recall.ai migration, meeting transcription, real-time transcription,
     Zoom bot, Google Meet bot, Microsoft Teams bot, meeting intelligence, speaker diarization,
     live captions, sales coaching, AI sales coach, calendar automation, webhook, MCP server,
     Claude Code plugin, Claude plugin, Anthropic plugin, MIA agent, meeting AI -->

<div align="center">

Built by [MeetStream](https://meetstream.ai) · Made for [Claude Code](https://claude.ai/code)

</div>
