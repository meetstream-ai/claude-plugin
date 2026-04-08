<div align="center">

<img src="https://framerusercontent.com/images/qADooqa4mVlS7haEXkSI2cgaE.png" alt="MeetStream Logo" width="80" />

# MeetStream × Claude

**The fastest way to build meeting intelligence.**  
Drop in your API key. Tell Claude what you're building. Ship in minutes.

[![Install Plugin](https://img.shields.io/badge/Claude%20Code-Install%20Plugin-5C4EFF?style=for-the-badge&logo=anthropic&logoColor=white)](https://claude.ai)
[![MeetStream Docs](https://img.shields.io/badge/Docs-docs.meetstream.ai-0EA5E9?style=for-the-badge)](https://docs.meetstream.ai)
[![Get API Key](https://img.shields.io/badge/Get%20API%20Key-app.meetstream.ai-10B981?style=for-the-badge)](https://app.meetstream.ai/api-keys)

</div>

---

> **MeetStream** is a meeting bot API that lets developers programmatically join, record, transcribe, and stream Zoom, Google Meet, and Microsoft Teams meetings. This Claude plugin gives Claude full knowledge of the MeetStream API so it can generate complete, production-ready integrations — note-takers, AI coaching tools, CRM auto-updaters, calendar bots, and more.

---

## ✨ What you can build

| | Use Case |
|--|---------|
| 🎙️ | **AI meeting notetaker** — bot joins, records, emails summary to attendees |
| 📝 | **Real-time transcription** with per-speaker attribution |
| 🔊 | **Live audio/video streaming** over WebSocket to your own models |
| 🤖 | **Interactive meeting bots** that send messages or play audio |
| 📅 | **Calendar-automated bots** that join every meeting on a schedule |
| 🧠 | **Sales coaching tools** — live objection detection, talk-time tracking |
| 📊 | **CRM auto-update pipelines** — extract action items, sync to HubSpot/Salesforce |
| 🗓️ | **Post-call follow-up agents** — transcript → summary → email in one pipeline |

---

## 🚀 Quick Start

**1.** Get your API key → [app.meetstream.ai/api-keys](https://app.meetstream.ai/api-keys)

**2.** Install the plugin (see your tool below)

**3.** Tell Claude what you're building:

```
"Build a Python webhook server that records my Zoom calls and emails me a transcript when it's done."

"Create a real-time transcription pipeline that streams speaker-attributed text to my WebSocket server."

"Write a Next.js API route that joins a meeting, waits for it to end, and generates an AI summary with action items."

"Set up calendar automation so a MeetStream bot joins every Google Meet on my calendar."

"Build a sales coaching bot that detects competitor mentions and objections in real time."
```

---

## 📦 Installation

### Claude Code (CLI)

```bash
/plugin marketplace add meetstream-ai/claude-plugin
/plugin install meetstream@meetstream-ai
/reload-plugins
```

### Cursor

1. Open **Settings** → **Claude** → **Plugins**
2. Click **Add Marketplace** → enter `meetstream-ai/claude-plugin`
3. Find **MeetStream** in the plugin list → click **Install**
4. `Cmd+Shift+P` → **Reload Window**

### VS Code (Claude extension)

1. Open the **Claude** panel → click **⚙ Settings** → **Plugins**
2. Click **Add from GitHub** → enter `meetstream-ai/claude-plugin`
3. Click **Install** → reload VS Code

### Windsurf

1. Open **Settings** (`Cmd+,`) → **AI** → **Plugins**
2. Click **Add Plugin Repository** → enter `meetstream-ai/claude-plugin`
3. Install **meetstream** → restart Windsurf

### Manual / Config-based

```bash
git clone https://github.com/meetstream-ai/claude-plugin.git ~/.claude-plugins/meetstream
```

---

## 🌐 Supported Platforms

| Platform | Setup |
|----------|-------|
| ✅ Google Meet | Works immediately — no setup |
| ✅ Microsoft Teams | Works immediately — no setup |
| ⚙️ Zoom | Requires a Zoom Marketplace app → [setup guide](https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup) |

---

## 🏗️ How It Works

```
Your code  →  POST /bots/create_bot  →  Bot joins meeting
                                              ↓
                                    Meeting ends
                                              ↓
                              Webhook fires: transcription.processed
                                              ↓
                              GET /bots/{id}/get_bot_transcript
                                              ↓
                              Claude generates summary / action items
                                              ↓
                              Deliver to email / Slack / Notion / CRM
```

MeetStream handles the hard parts: platform compatibility, bot admission, audio capture, speaker diarization, and post-processing. You write business logic.

---

## 💡 Example Integrations

**Note-taker with email delivery (Node.js)**
```typescript
// Bot joins → meeting ends → Claude summarizes → email sent
await createBot({ meetingLink, callbackUrl: '/webhook' })
// On transcription.processed webhook:
const transcript = await getTranscript(botId)
const summary = await claude.summarize(transcript)
await sendEmail(attendees, summary)
```

**Live sales coaching (Python)**
```python
# Transcript chunks stream to your WebSocket in real time
async def on_chunk(chunk):
    if "competitor" in chunk["transcript"].lower():
        alert_sales_rep(f"Competitor mention: {chunk['transcript']}")
```

**Calendar automation (one-time setup)**
```bash
# Connect Google Calendar → bots auto-join every meeting
POST /calendar/create-calendar
{ "refresh_token": "...", "client_id": "...", "client_secret": "..." }
```

---

## 🗂️ What's Included

```
.claude-plugin/
├── plugin.json             ← Plugin manifest
└── marketplace.json        ← Marketplace registry

skills/meetstream/
├── SKILL.md                ← Core skill: patterns, lifecycle, platform notes
└── references/
    ├── api-reference.md          ← Full endpoint map with params + return types
    ├── code-patterns-python.md   ← Complete Python implementations
    └── code-patterns-node.md     ← Complete Node.js / TypeScript implementations
```

Claude also queries the [MeetStream MCP server](https://docs.meetstream.ai/_mcp/server) directly for live parameter schemas and edge cases.

---

## 🔗 Links

- 🌐 Website: [meetstream.ai](https://meetstream.ai)
- 📖 Docs: [docs.meetstream.ai](https://docs.meetstream.ai)
- 🎛️ Dashboard: [app.meetstream.ai](https://app.meetstream.ai)
- 🐙 GitHub: [github.com/meetstream-ai/claude-plugin](https://github.com/meetstream-ai/claude-plugin)
- 💬 Support: [hello@meetstream.ai](mailto:hello@meetstream.ai)

---

<!-- GitHub SEO keywords -->
<!-- meeting bot API, AI notetaker, meeting transcription, Zoom bot, Google Meet bot, Teams bot, 
     Claude plugin, meeting intelligence, real-time transcription, meeting recording API,
     meeting SDK, developer tools, speech-to-text, speaker diarization, calendar automation,
     webhook, note-taking agent, sales coaching, CRM integration, AI meeting assistant -->

<div align="center">

Built with ❤️ by [MeetStream.ai](https://meetstream.ai) &nbsp;·&nbsp; Powered by <img src="https://upload.wikimedia.org/wikipedia/commons/7/78/Anthropic_logo.svg" alt="Anthropic" width="14" style="vertical-align:middle"/> [Claude](https://claude.ai)

</div>
