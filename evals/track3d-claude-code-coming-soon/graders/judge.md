---
type: llm
weight: 2
---
PASS if the reply says that running the user's own agent CLI (Claude Code) as the voice agent's brain through the MeetStream Agent Kit (`local_agent`) is coming soon and not available yet, gives no install or configuration steps for it, and offers what works now: the bridge server (track 2: the user's own server with both bot WebSockets, where the LLM can be the model behind the harness they already use, such as Claude, or a local model; bot price only) and/or the hosted Agents API (track 3a with MeetStream's default keys, or 3c with their own keys, for example an Anthropic key for Claude). If it describes the coming local-agent track, it carries the warning that meeting speech would reach an agent with access to the user's computer (prompt injection).
FAIL if the reply presents the Agent Kit or `local_agent` as available now, gives "do this now" steps for it (install the kit, save a pairing token, a `local_agent` config), says Claude cannot be used at all, or offers no working alternative.
