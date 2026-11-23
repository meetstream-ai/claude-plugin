# CLAUDE.md

Claude Code does not read `AGENTS.md` natively, so this file imports it. Everything in it applies here.

@AGENTS.md

## Claude Code specifics

Install the MeetStream MCP server so you are working against current API truth rather than this repo's files:

```sh
claude mcp add --transport http meetstream https://mcp.meetstream.ai/mcp
# then /mcp -> Authenticate, sign in at app.meetstream.ai and click Allow
```

Separately, the [MeetStream Claude plugin](https://github.com/meetstream-ai/meetstream-plugin) adds skills for the build tracks: the recording bot (notetakers, live coaching, calendar automation), the bridge server on your own stack, and the hosted Agents API (voice agents; LiveKit and local agents are coming soon). It also declares this MCP server, so installing the plugin is enough:

```sh
/plugin marketplace add meetstream-ai/meetstream-plugin
```

Confirm it is live with `/mcp`, then ask for `list_bots` - a clean response means sign-in and transport are both good.

## Keep these two files in sync

`CLAUDE.md` imports `AGENTS.md` rather than duplicating it, so edit **`AGENTS.md`** and the change lands in both. Only Claude-Code-specific instructions belong in this file.
