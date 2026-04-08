# MeetStream Claude Plugin

Build complete meeting bot integrations without writing boilerplate. Get your MeetStream API key, install this plugin, and tell Claude what you're building — it handles the rest.

## What you can build

- Record Zoom, Google Meet, or Teams meetings via a single API call
- Real-time transcription with speaker attribution
- Live audio/video streaming over WebSocket to your own models
- Interactive bots that send messages or audio into meetings
- Calendar-automated bots that join every meeting on a schedule
- Full note-taking agents — transcript + AI summary, delivered post-call

## Setup

1. **Get your API key** — [app.meetstream.ai](https://app.meetstream.ai)
2. **Install this plugin** in your AI coding tool (see below)
3. **Tell Claude what you're building** — it will generate complete, runnable code

## Example prompts

```
"Build a Python webhook server that records my Zoom calls and emails me a transcript when it's done."

"Create a real-time transcription pipeline that streams speaker-attributed text to my WebSocket server."

"Write a Next.js API route that joins a meeting, waits for it to end, and generates an AI summary with action items."

"Set up calendar automation so a MeetStream bot joins every Google Meet on my calendar."
```

## Supported platforms

- Google Meet
- Microsoft Teams
- Zoom (requires Zoom app setup — [docs.meetstream.ai/guides/zoom](https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup))

---

## Installation

### Claude Code (CLI)

```bash
/plugin marketplace add meetstream-ai/claude-plugin
/plugin install meetstream@meetstream-ai
/reload-plugins
```

### Cursor

1. Open **Settings** → **Claude** → **Plugins**
2. Click **Add Marketplace** and enter: `meetstream-ai/claude-plugin`
3. Find **MeetStream** in the plugin list and click **Install**
4. Reload the window (`Cmd+Shift+P` → **Reload Window**)

### VS Code (with Claude extension)

1. Open the **Claude** panel in the sidebar
2. Click the **⚙ Settings** icon → **Plugins**
3. Click **Add from GitHub** and enter: `meetstream-ai/claude-plugin`
4. Click **Install** on the MeetStream plugin
5. Reload VS Code

### Windsurf

1. Open **Windsurf Settings** (`Cmd+,`) → **AI** → **Plugins**
2. Click **Add Plugin Repository**: `meetstream-ai/claude-plugin`
3. Install **meetstream** from the list
4. Restart Windsurf

### Manual install (any environment)

If your tool supports Claude plugins via config file, add this to your plugin config:

```json
{
  "marketplace": "https://github.com/meetstream-ai/claude-plugin",
  "plugin": "meetstream"
}
```

Or clone directly and point your tool at the local path:

```bash
git clone https://github.com/meetstream-ai/claude-plugin.git ~/.claude-plugins/meetstream
```

---

## What's included

```
.claude-plugin/plugin.json          # Plugin manifest
.claude-plugin/marketplace.json     # Marketplace registry
skills/meetstream/
├── SKILL.md                        # Core skill — patterns, lifecycle, platform notes
└── references/
    ├── api-reference.md            # Full endpoint map with params and return types
    ├── code-patterns-python.md     # Complete Python implementations
    └── code-patterns-node.md       # Complete Node.js / TypeScript implementations
```

Claude also queries the [MeetStream MCP server](https://docs.meetstream.ai/_mcp/server) directly for up-to-date parameter schemas and edge cases.

---

## Links

- Docs: [docs.meetstream.ai](https://docs.meetstream.ai)
- Dashboard: [app.meetstream.ai](https://app.meetstream.ai)
- Website: [meetstream.ai](https://meetstream.ai)
