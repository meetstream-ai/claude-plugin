# MeetStream Claude Plugin

Enables Claude to build complete meeting bot integrations using the MeetStream API.

## What it does

Once installed, Claude can generate complete, production-ready code for:
- Recording Zoom / Google Meet / Teams meetings via bot
- Real-time transcription with speaker attribution
- Live audio/video streaming over WebSocket
- Interactive bots that send messages or audio in meetings
- Calendar-automated bot scheduling
- Full note-taking agents (transcript + AI summary)

The developer provides their MeetStream API key. Claude handles everything else.

## Setup

1. Get a MeetStream API key: https://app.meetstream.ai/api-keys
2. Install this plugin in Claude
3. Tell Claude what you're building — it will generate complete implementations

## Supported Platforms

- Google Meet (no setup required)
- Microsoft Teams (no setup required)
- Zoom (requires Zoom app setup — see https://docs.meetstream.ai/guides/zoom/zoom-marketplace-app-setup)

## Plugin Structure

```
plugin.json                          # Claude plugin manifest
skills/meetstream/
├── SKILL.md                         # Core skill — patterns, lifecycle, platform notes
└── references/
    ├── api-reference.md             # Full endpoint map with params and return types
    ├── code-patterns-python.md      # Complete Python implementations
    └── code-patterns-node.md        # Complete Node.js / TypeScript implementations
```

## MCP Server

This plugin also registers the MeetStream documentation MCP server:
```
https://docs.meetstream.ai/_mcp/server
```

Claude queries it directly for detailed parameter schemas and edge cases.

## Publishing to Claude Marketplace

1. Ensure `plugin.json` has correct `name`, `display_name`, `description`, and `version`
2. Submit at https://claude.ai/plugins/submit (when marketplace launches)
3. Or install locally in Claude Desktop via Settings > Extensions > Install from directory
