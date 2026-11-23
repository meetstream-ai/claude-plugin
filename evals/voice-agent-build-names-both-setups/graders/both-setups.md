---
type: llm
weight: 2
---
PASS if the reply names both ways to run the agent, own stack first: (1) a bridge server the user runs (the bot sends live audio to it and takes audio, chat and interrupts back over a control socket; any speech-to-text, LLM and voice models, including local ones; the bot price only), and (2) the hosted Agents API (MIA), with MeetStream's inbuilt keys and the user's own provider keys as its key choices. Asking one question "your own stack (bridge) or hosted by MeetStream?" with both options described also passes. Mentioning the user's own coding agent through `meetstream setup` (3d) is optional, but if mentioned it must be called coming soon.
FAIL if the reply offers only the hosted agent or only the bridge, lists the hosted agent before the bridge, or starts with wake words or mode questions before the setup choice. MeetStream's own hosted audio bridge ("MeetStream hosts the bridge, you host nothing") is not the bridge server and does not count.
