---
type: llm
weight: 2
---
PASS if the reply says the local-agent track (an agent CLI such as Cursor's `cursor-agent` as the voice agent's brain through `meetstream setup` and the MeetStream relay) is coming soon and not available yet, does not run or give setup steps for it (no kit install, pairing token, Bridge URL or `serve --tunnel`), and offers what works now: a bridge server (track 2, the user's own server and models) or the hosted Agents API (track 3a or 3c).
FAIL if the reply presents the local-agent path (the old Agent Kit or `meetstream agent serve`) as available now, gives `serve --command`, `serve --tunnel`, pairing-token or install steps, calls or suggests undocumented or admin endpoints, or offers no working alternative.
