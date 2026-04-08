<div align="center">

<img src="https://meetstream.ai/favicon.png" alt="MeetStream Logo" width="80" />

# MeetStream × Claude

**The fastest way to build meeting intelligence.**  
Drop in your API key. Tell Claude what you're building. Ship in minutes.

[![Install Plugin](https://img.shields.io/badge/Claude%20Code-Install%20Plugin-5C4EFF?style=for-the-badge&logo=anthropic&logoColor=white)](https://claude.ai)
[![MeetStream Docs](https://img.shields.io/badge/Docs-docs.meetstream.ai-0EA5E9?style=for-the-badge)](https://docs.meetstream.ai)
[![Get API Key](https://img.shields.io/badge/Get%20API%20Key-app.meetstream.ai-10B981?style=for-the-badge)](https://app.meetstream.ai/api-keys)

</div>

---

## ✨ What you can build

| | Use Case |
|--|---------|
| 🎙️ | Record Zoom, Google Meet, or Teams meetings via a single API call |
| 📝 | Real-time transcription with speaker attribution |
| 🔊 | Live audio/video streaming over WebSocket to your own models |
| 🤖 | Interactive bots that send messages or audio into meetings |
| 📅 | Calendar-automated bots that join every meeting on a schedule |
| 📬 | Full note-taking agents — transcript + AI summary, delivered post-call |

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

Or add to your plugin config:
```json
{
  "marketplace": "https://github.com/meetstream-ai/claude-plugin",
  "plugin": "meetstream"
}
```

---

## 🌐 Supported Platforms

| Platform | Setup |
|----------|-------|
| ✅ Google Meet | Works immediately |
| ✅ Microsoft Teams | Works immediately |
| ⚙️ Zoom | Requires a Zoom app → [setup guide](https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup) |

---

## 🗂️ What's Included

```
.claude-plugin/
├── plugin.json             ← Plugin manifest
└── marketplace.json        ← Marketplace registry

skills/meetstream/
├── SKILL.md                ← Core skill: patterns, lifecycle, platform notes
└── references/
    ├── api-reference.md    ← Full endpoint map
    ├── code-patterns-python.md   ← Complete Python implementations
    └── code-patterns-node.md     ← Complete Node.js / TypeScript implementations
```

Claude also queries the [MeetStream MCP server](https://docs.meetstream.ai/_mcp/server) for live parameter schemas and edge cases.

---

## 🔗 Links

- 🌐 Website: [meetstream.ai](https://meetstream.ai)
- 📖 Docs: [docs.meetstream.ai](https://docs.meetstream.ai)
- 🎛️ Dashboard: [app.meetstream.ai](https://app.meetstream.ai)
- 🐙 GitHub: [github.com/meetstream-ai/claude-plugin](https://github.com/meetstream-ai/claude-plugin)

---

<div align="center">

Built with ❤️ by [MeetStream.ai](https://meetstream.ai) &nbsp;·&nbsp; Powered by <img src="https://anthropic.com/favicon.ico" alt="Anthropic" width="14" style="vertical-align:middle"/> [Claude](https://claude.ai)

</div>
