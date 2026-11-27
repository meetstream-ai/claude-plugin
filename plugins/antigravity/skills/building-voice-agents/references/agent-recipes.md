# Voice agent recipes and other hosts

> Moved from `building-voice-agents/SKILL.md` (3.5.0) so the skill stays under 20 KB: some harnesses do not read larger files in one go.

## Coming soon: 3b (LiveKit) and 3d (your coding agent)

These tracks are not in production. Say they are coming soon. Give no setup steps and no
"do this now" steps for them, and never route a user to them as a working option. Offer
track 2 or track 3a/3c instead.

- **3b. Bring your own agent infra (LiveKit): COMING SOON.** MeetStream's Agents API will
  run with the user's own agent infrastructure. Today, put the user's own agent
  code behind a bridge server (track 2), or use 3c with their own keys.
- **3d. Your coding agent as the brain: COMING SOON.** The user's own agent CLI (Claude
  Code, Codex, Hermes, Copilot, OpenClaw and others) will be the voice agent's brain through
  `meetstream setup` and `meetstream agent serve` over the MeetStream relay (no tunnel).
  The relay is not in production yet. When you describe 3d, give this warning:

  > **Warning:** what people say and type in the meeting will reach an agent that has
  > access to your computer and your terminal. Someone in the call can try to make it run
  > commands or read files (prompt injection). The computer, the agent and the bridge must
  > stay on for the whole call, at the lowest access level.

  For "use Claude Code (or Codex) as the brain" today: track 2 with the harness's own
  model as the bridge LLM, or track 3a/3c (for example `"provider": "anthropic"` with the
  user's own Anthropic key, 3c). The `check_local_agent` MCP tool is for 3d only.

## Hosted agents on Grok (xAI) or Gemini (Google)

"Make Grok join my call" and "put Gemini in the meeting" are hosted voice agents (track 3c)
with the `xai` or `google` provider, or the model behind your own bridge server (track 2).
Grok is not a local agent. xAI and Google are not inbuilt keys: save the provider key in
the dashboard under Configure > Integrations and send no `key_source` in that section.

Realtime mode (one speech-to-speech model, lowest latency, answers every turn):

```json
{ "agent_name": "Grok in the meeting", "mode": "realtime",
  "model": { "provider": "xai", "voice": "Ara",
             "system_prompt": "You are Grok, a helpful participant. Answer briefly and out loud." } }
```

```json
{ "agent_name": "Gemini in the meeting", "mode": "realtime",
  "model": { "provider": "google", "model": "gemini-2.5-flash-native-audio-preview-12-2025",
             "voice": "Puck", "proactivity": true,
             "system_prompt": "You are a helpful participant. Answer only questions meant for you." } }
```

- xAI realtime: do not send `model`; MeetStream selects the xAI realtime model. Voices
  include `Ara` (default), `Eve`, `Leo`, `Rex`, `Sal`.
- Google realtime: `proactivity: true` lets the model skip input that is not for it.
- Wake words and `speak_only_when_asked` are pipeline-only. To have Grok answer only when
  someone says its name, use pipeline mode with xAI parts:
  `"model": {"provider": "xai", "model": "grok-3", ...}`, `"transcriber": {"provider": "xai"}`
  (or Deepgram), `"voice": {"provider": "xai", "voice_id": "ara"}`, plus
  `"agent": {"speak_only_when_asked": true}`. Google works the same way as a pipeline LLM
  (`"model": {"provider": "google", ...}`).
- Send the bot with only `agent_config_id`. On Zoom, recommend your own Zoom app
  (OBF or ZAK token) for reliable, fully supported bots (`setting-up-platforms`).

## Recipes by job

Each recipe is the job-specific part of an agent config. Start from the fastest-path config
above (pipeline, inbuilt or own keys) and add these fields. List the track choice first in
your answer: on a bridge server (track 2) your code applies the same rule (for example, reply
only when the transcript contains the agent's name); on the hosted Agents API (track 3) the
fields below do it.

Pipeline agents start with a wake word on by default (`"hey assistant"`, `"hello bot"`,
30 seconds). Set `wake_word` on purpose in every pipeline config: your own words, or
`"enabled": false` for an agent that must speak unprompted.

**Name-addressed assistant (wake word).** Silent until someone says its name.
```json
{ "mode": "pipeline",
  "agent": { "speak_only_when_asked": true, "chat_input": true },
  "wake_word": { "enabled": true, "words": ["hey nova", "ok nova", "nova"], "timeout": 30,
                 "bypass_below_participants": 1 },
  "transcriber": { "provider": "deepgram", "model": "nova-3", "boostwords": ["Nova"] } }
```
`speak_only_when_asked` lets the agent act (tools) but speak only when addressed by name;
the wake word gates listening. Use either or both. `bypass_below_participants: 1` turns the
gate off in a 1:1 call.

**Standup facilitator.** Runs the round and logs decisions; or, for "only talk when named",
use the assistant recipe above with a standup prompt.
```json
{ "model": { "system_prompt": "You run a 15-minute daily standup. Ask each person, by name, for yesterday, today and blockers. Keep each turn short. Repeat each decision back in one sentence.",
             "first_message": "Hi all, I'm the standup assistant (an AI). Who wants to start?" },
  "agent": { "speaker_aware_responses": true },
  "wake_word": { "enabled": false } }
```
`speaker_aware_responses` gives the model each speaker's name. After the call, wait for
`transcription.processed`, get the transcript, have your own model pull the decisions and
blockers, and post them with your own Slack (or Teams, email) integration. MeetStream does
not post to Slack. For a recurring standup, auto-join it from the calendar
(`scheduling-and-calendars`).

**AI interviewer.** Asks one question at a time and waits for the answer.
```json
{ "model": { "system_prompt": "You interview {{candidate_name}} for the {{role}} role. Ask one question at a time from this list: ... Wait for the full answer, ask at most one follow-up, then move on. Do not give feedback on answers.",
             "first_message": "Hi {{candidate_name}}, I'm an AI interviewer. This call is recorded and transcribed for the hiring team. Ready to start?" },
  "agent": { "enable_interruptions": true, "max_endpointing_delay": 5.0 },
  "wake_word": { "enabled": false } }
```
Per interview, send the bot with `agent_config_id`, `join_at` (or calendar auto-join),
`agent_config_params` (`{"candidate_name": "...", "role": "..."}`), and the normal recording
fields (`recording_config.transcript`, `video_required: true` if the team wants video).
After the call: `transcription.processed` → `get_transcript`, and the recording URLs
(`getting-transcripts-and-media`). A longer `max_endpointing_delay` gives candidates time to pause.

**Practice or role-play persona** (sales practice, exam practice, language partner).
Always on, so realtime mode (lowest latency) or pipeline with `"wake_word": {"enabled": false}`.
Put the persona, the scenario and the rules in `system_prompt`, and the opening line in
`first_message` (pipeline) or the prompt (realtime). For language practice, set
`transcriber.language` (pipeline) to the practice language, or `multi` for mixed speech.

**Demo or FAQ agent.** Answers product questions from your content.
```json
{ "agent": { "mcp_servers": [{ "url": "https://kb.example.com/mcp", "allowed_tools": ["search_docs"] }],
             "chat_input": true, "tools": ["screen"] },
  "model": { "provider": "openai", "model": "gpt-4o", "system_prompt": "You demo Acme. Answer from search_docs only; say when you do not know." } }
```
`agent.custom_functions` registers your own HTTPS endpoints as tools instead of an MCP
server. `tools: ["screen"]` (Google Meet only, with a model that can see images) lets the
agent present and work a live web page.

### Agents in other languages

Set `transcriber.language` to the meeting language (pipeline), write the `system_prompt`
in that language or tell the agent to answer in it, and pick a voice model that speaks it
(for example ElevenLabs `eleven_multilingual_v2`, with your own ElevenLabs key). Use `multi` or `auto` for automatic
detection or mixed-language meetings.

```json
{ "mode": "pipeline",
  "transcriber": { "provider": "deepgram", "model": "nova-3", "language": "ru" },
  "model": { "provider": "openai", "model": "gpt-4o-mini",
             "system_prompt": "Ты помощник на встрече. Отвечай только по-русски и коротко." },
  "voice": { "provider": "elevenlabs", "model": "eleven_multilingual_v2", "voice_id": "<your ElevenLabs voice id>" },
  "agent": { "speak_only_when_asked": true },
  "wake_word": { "enabled": true, "words": ["Нова", "эй Нова"] } }
```
Language support follows the provider you choose. For a decisions summary at the end of the
call, use the transcript after the call (`meetstream-cli`) or ask the agent for a recap
before it leaves.

### Anthropic Claude as the LLM

Pipeline mode only: `"model": { "provider": "anthropic", "model": "claude-haiku-5-5", ... }`
(`claude-haiku-5-5` for the fastest replies, `claude-sonnet-5-5` or `claude-opus-5-5` for
harder tasks). The Anthropic key is saved in the dashboard under model integrations
(provider `anthropic`).

- `temperature` must be 0 to 1. `reasoning_effort` is optional (`"low"` when omitted).
- `tool_choice` may only be `"auto"` or `"none"`.
- `top_p`, `frequency_penalty`, `presence_penalty` and `logit_bias` return 400
  `Anthropic models do not support: ...`.
- Claude is an LLM for MIA only, not a transcription provider and not a `create_bot` field.

## Wake-word agents

With `wake_word.enabled`, the agent stays silent until someone says a trigger phrase,
then listens for `timeout` seconds. A pipeline agent with no `wake_word` block starts with
the gate on (`"hey assistant"`, `"hello bot"`); set `"enabled": false` for an always-on
agent. Give it phrase variants people will actually say
("hey acme", "ok acme", "acme"), and keep the timeout long enough for a full question
(20-40s is usually right; 5-10s cuts people off mid-sentence).

This is the right default for agents that sit in real customer calls. An always-on
agent in a sales call is usually a bad experience.

## Hosted agent from the SDKs

Node (`npm install @meetstream/sdk`):
```ts
import { MeetStream } from '@meetstream/sdk';
const ms = new MeetStream(); // reads MEETSTREAM_API_KEY
const agent = await ms.mia.create({ agent_name: 'Meeting assistant', mode: 'pipeline', /* transcriber, model, voice as above */ });
await ms.bots.create({ meeting_link, agent_config_id: agent.agent_config_id });
```
Python (`pip install meetstream-sdk`):
```python
from meetstream import MeetStream
ms = MeetStream()  # reads MEETSTREAM_API_KEY
agent = ms.mia.create({"agent_name": "Meeting assistant", "mode": "pipeline"})  # plus transcriber, model, voice as above
ms.bots.create({"meeting_link": meeting_link, "agent_config_id": agent["agent_config_id"]})
```

Optional references: the MIA templates in "Tutorials and Sample Apps"
(https://docs.meetstream.ai/tutorials/sample-apps) and the labs repo
(https://github.com/meetstream-ai/labs).

## Latest docs

- Bridge server (track 2): https://docs.meetstream.ai/guides/websockets/bridge-server-architecture
- Voice agent pricing and keys (track 3): https://docs.meetstream.ai/guides/mia/pricing-and-keys
- Screen sharing and custom agents (3d, coming soon): https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents
- MIA API guide (every config field, realtime providers, wake word, `update_mia`): https://docs.meetstream.ai/guides/mia/mia-api-guide
- Create an agent (xAI pipeline example): https://docs.meetstream.ai/guides/mia/create-an-agent

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
