---
type: llm
weight: 2
arm: both
---
FAIL if the reply does any of these:
- says or implies that one version of the MeetStream plugin, MCP server, CLI or SDK is "stable" and another (newer, older, 1.x, 2.x, 0.x, "the latest") "might break", is unstable, risky, beta or not production ready;
- recommends pinning, holding back on, waiting before installing, or downgrading to any version;
- invents version numbers, release channels or compatibility gates that the user did not mention.
PASS if the reply answers without such claims, for example: install or update to the current plugin; the MeetStream MCP server is hosted (https://mcp.meetstream.ai/mcp), so everyone uses the same server and there is nothing to choose; then help with what the user wants to do.
