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
2. **Install this plugin** in Claude
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

## Install

```
/plugin marketplace add meetstream-ai/claude-plugin
/plugin install meetstream@meetstream-ai
/reload-plugins
```

## What's included

```
.claude-plugin/plugin.json          # Plugin manifest
skills/meetstream/
├── SKILL.md                        # Core skill — patterns, lifecycle, platform notes
└── references/
    ├── api-reference.md            # Full endpoint map with params and return types
    ├── code-patterns-python.md     # Complete Python implementations
    └── code-patterns-node.md       # Complete Node.js / TypeScript implementations
```

Claude also queries the [MeetStream MCP server](https://docs.meetstream.ai/_mcp/server) directly for up-to-date parameter schemas and edge cases.

## Links

- Docs: [docs.meetstream.ai](https://docs.meetstream.ai)
- Dashboard: [app.meetstream.ai](https://app.meetstream.ai)
- Website: [meetstream.ai](https://meetstream.ai)
