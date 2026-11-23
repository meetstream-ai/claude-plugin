# Install MeetStream in Cline

MeetStream is a hosted, remote MCP server. There is nothing to download, build or run locally.

1. Open Cline, then open **MCP Servers** and select **Remote Servers**.
2. Add a server:
   - Server name: `meetstream`
   - Server URL: `https://mcp.meetstream.ai/mcp`
   - Transport: Streamable HTTP
3. Save. Cline connects and starts the OAuth sign-in. A browser opens app.meetstream.ai. Sign in (or create an account) and click **Allow**. Do not ask the user for an API key and do not paste one into the chat.

If you edit the settings file instead, add this entry to `cline_mcp_settings.json`:

```json
{
  "mcpServers": {
    "meetstream": {
      "type": "streamableHttp",
      "url": "https://mcp.meetstream.ai/mcp"
    }
  }
}
```

## Check that it works

Call the MeetStream tool `list_bots`. A list of bots, or an empty list, means that MeetStream is connected.

## Optional: skills

Copy the folders in `skills/` of https://github.com/meetstream-ai/meetstream-plugin to `.cline/skills/` in the project (or `~/.cline/skills/` for all projects). They teach Cline the MeetStream API and the build tracks.

## Links

- Hosted MCP server: https://docs.meetstream.ai/build-with-ai/meetstream-mcp-server
- Documentation: https://docs.meetstream.ai
- Support: https://meetstream.ai/contact
