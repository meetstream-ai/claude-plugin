# Hermes in Meetings

Hermes in Meetings is a [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin from [MeetStream](https://meetstream.ai).
With this plugin, Hermes can join your Zoom, Google Meet, and Microsoft Teams calls as a visible bot.
The bot records and transcribes the call.
During the call, you can ask Hermes to post a message through the bot.
After the call, Hermes uses the transcript to write notes, action items, and follow-up messages.

You must supply only one item: a MeetStream API key.
You set the other options in the MeetStream dashboard.

MeetStream has three build tracks. Use them in this order:

1. **Recording bot.** A bot joins the call, records it, and transcribes it. 1a gives the transcript, the participants and the chat after the call. 1b gives live data during the call.
   This plugin uses this track.
2. **Bridge server (your own stack, local).** Use this track first when you want an agent that talks in the call.
   Your server runs your own speech-to-text, LLM and text-to-speech.
   Refer to [Voice answers in the call](#voice-answers-in-the-call).
3. **Agents API infra (hosted by MeetStream).** MeetStream hosts the voice agent (API name MIA).
   3a uses MeetStream's own, default keys. 3c uses your own keys.
   3b (bring your own agent infra, LiveKit) and 3d (local agent: your own agent CLI, for example Hermes, as the brain) are coming soon. They are not available yet.

## What you get

| Item | Name | What it does |
|---|---|---|
| Tool | `meetstream_join` | Sends the bot to a meeting link, now or at a set time. |
| Tool | `meetstream_recover_brief` | Retrieves a saved brief and delivery status from the original private chat. |
| Tool | `meetstream_status` | Shows the status of one bot, or a list of the recent Hermes bots. |
| Tool | `meetstream_chat` | Sends a message to the meeting chat. |
| Tool | `meetstream_transcript` | Gives the transcript and the meeting chat. |
| Tool | `meetstream_leave` | Makes the bot leave the call. MeetStream keeps the data. |
| Tool | `meetstream_find_meetings` | Finds recent calls by title, date or calendar occurrence. |
| Tool | `meetstream_calendar` | Lists upcoming events and previews one chosen occurrence. |
| Tool | `meetstream_schedule_event` | Requests approval, then schedules one previewed occurrence. |
| Gateway platform | `meetstream` | Delivers decision briefs and shows Google Meet status GIFs. Routes live replies when meeting chat is available. |
| Skill | `meetstream:hermes-in-meetings` | Tells Hermes how to attend a call and how to do the follow-up work. |

## Requirements

- Hermes Agent 0.23.0 or a later version.
- A MeetStream account. Get an API key at <https://app.meetstream.ai/api-key>.
- Posting a message in the call requires the bot to be admitted. The saved chat is available after processing.

## Install the plugin

1. Install the plugin:

   ```bash
   hermes plugins install meetstream --enable
   ```

2. When Hermes asks for `MEETSTREAM_API_KEY`, paste your MeetStream API key.
   The key starts with `ms_`.
   Hermes keeps the key in the `.env` file of your profile.
3. Start a new Hermes session.

The Hermes plugin catalog can pin an earlier version of this plugin than the one on `main` (the catalog entry names the version). To install the latest `main`, use the repository address:

```bash
hermes plugins install meetstream-ai/hermes-meetstream --enable
```

In the Hermes desktop app, you can also set the key in **Settings → Plugins → Hermes in Meetings**.

## Send Hermes to a call

Tell Hermes what to do in plain words. Examples:

- "Join https://meet.google.com/abc-defg-hij and take notes."
- "Join my Zoom call at 3 PM today: https://zoom.us/j/123456789."
- "Summarize the call and give me the action items with owners."

A successful join request returns a bot ID while MeetStream connects. Ask Hermes for the status if you
need to confirm that it got in. Repeating a join for a room with an active bot created by this version
returns that bot. Reusing the room after the bot leaves can start a new bot.

When the bot joins, it sends an introduction to the meeting chat.
The introduction tells the people in the call that the bot records the call.
If the host uses a waiting room, the host must admit the bot.
The bot leaves when all the other people leave the call.

## Get a decision brief after the call

In a private Hermes Desktop chat, say “Join this call and send me a decision brief when the bot leaves.”
Automatic briefs require MeetStream, Deepgram, or AssemblyAI transcription. Hermes checks the active
bot's transcription before queueing a brief on a reused bot. A successful join tells you whether
the brief was queued in that conversation. Ask for the bot status
if you want to check admission, recording or transcript processing. The brief lists decisions,
actions and open questions with speaker names and timestamps relative to the transcript. Missing
owners and deadlines are called out explicitly.

Keep the MeetStream gateway enabled in the same Hermes profile. The queued job resumes on gateway
restart, including after the host removes the bot, and writes one result to the originating chat.
Open the original chat to read the brief once it is ready. Other chats and the meeting chat do not
receive it. MeetStream may need a few minutes to process the transcript.

### Get the brief on Telegram or WhatsApp

Automatic phone delivery requires a Hermes build with the private delivery SDK.

Connect a native [Telegram](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/telegram)
or [WhatsApp](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/whatsapp) gateway
adapter in the same Hermes profile. Use a private DM from an authorized account. Text your bot:
“Join this call and send me the decisions and action items when it ends: https://meet.google.com/abc-defg-hij.”

Hermes saves the brief to the original conversation and sends a phone notification there. It checks
that the original sender is still authorized before sending. If the messaging connection is offline,
delivery waits for it. After a Telegram rate-limit refusal, the worker waits for Telegram's retry
window and tries again. It saves Telegram's message ID on success. If Telegram may have accepted
the message before the connection dropped, the worker marks delivery as unconfirmed. Ask Hermes
in the original chat to recover the saved brief if it is missing. Long briefs in a Telegram
DM without a topic arrive as a single text attachment. Telegram topics and WhatsApp get a
shorter notification and can recover the full brief from Hermes history.

This setup needs the Hermes gateway and your native messaging connection, plus the MeetStream API
key. The brief worker checks only queued bots. While a bot is in the meeting it checks about once a
minute, then about every 15 seconds while waiting for the transcript. If the Mac is asleep or the
gateway is offline, the checks resume when it is available.

For faster wake-ups with an existing HTTPS reverse proxy, install Hermes with messaging support
(`aiohttp`) and set `platforms.meetstream.extra.brief_webhook_port` to an unused local port. Proxy
only `POST /meetstream/briefs` to that loopback port. Register the HTTPS URL as a
[MeetStream workspace webhook](https://docs.meetstream.ai/guides/webhooks/workspace-webhooks)
in the workspace that owns the Hermes profile's `MEETSTREAM_API_KEY` and subscribe to
`transcription.processed` and `bot.done`. Put the endpoint signing secret in
`MEETSTREAM_BRIEF_WEBHOOK_SECRET` in that Hermes profile and restart the gateway. The listener rejects
missing or malformed signatures before reading the body, limits the body size and read time,
then verifies the raw bytes. It deduplicates events per bot and wakes the worker only for a
brief already in the queue. The worker reads bot and transcript state from MeetStream's API.
Polling still handles restarts and missed webhooks.

## Google Meet status GIFs

Ask Hermes to show its status in the call, or enable **Google Meet status GIFs** in the plugin settings
for future joins. Hermes shows the supplied **Thinking** GIF at the start of a live meeting chat
turn, the combined activity GIF during longer turns, and **Working** while sending a reply. The
GIFs expire shortly after the activity ends. The bot announces recording in the meeting chat.
Admission, recording and post-call processing remain available through `meetstream_status`.
The bundled files are resized and re-encoded for the video command and retain their embedded
Nous Research artwork credits and MIT notices. Inline uploads showed the first frame in our
Google Meet test. For animated playback, serve the three files from a public HTTPS directory
and set `status_gif_base_url`. Hermes appends each asset's filename to that directory and uses
MeetStream's [URL-based GIF playback](https://docs.meetstream.ai/guides/features/chat-and-visuals).

## Find a previous meeting by name

In a private Hermes chat or Telegram DM, ask “What did we decide in Tuesday’s launch sync?” Hermes looks for
recent calls and synced calendar occurrences by title or date. If several calls match, pick one
by its title and start time. Hermes then fetches only that call’s transcript. Search reads metadata
on demand and keeps no transcript index.

Connect Google Calendar or Outlook in the MeetStream dashboard to search by calendar title.
When creating a bot by link, you can supply a title for future searches. Older bots without a title
can be found by date or by a unique calendar match on the same room link and nearby actual start
time. If a legacy calendar bot has audio but no transcript, request transcription in MeetStream
before asking Hermes for its notes.

## Schedule one named calendar event

From a private Hermes chat or an authorized Telegram DM, ask “Send Hermes to tomorrow’s design review.” If more than one event matches, pick the occurrence
you want. Hermes previews its title, start time and time zone, and what you’ll receive. Approve the
preview with the Hermes approval prompt to schedule the bot. It checks the event again before booking.

This uses MeetStream’s [one-off scheduled join](https://docs.meetstream.ai/guides/features/scheduling-bots)
so the existing transcription and decision-brief flow applies. It uses the event’s current time and
link. If the calendar event is moved, cancelled, or gets a new link after booking, update or cancel
the scheduled bot in MeetStream. This flow skips declined occurrences and leaves calendar auto-join
settings alone.

## Meeting chat

From your private Hermes chat, ask Hermes to post a message using `meetstream_chat`. After the
call, `meetstream_transcript` reports chat and transcript readiness separately.

Live inbound Q&A depends on live chat delivery. The MeetStream REST chat endpoint can return
HTTP 202 until the post-call manifest is processed, so the plugin does not promise live answers.
For guaranteed live input, MeetStream provides
[`participant_events.chat_message`](https://docs.meetstream.ai/guides/platforms/google-meet)
through real-time endpoints. This release does not receive those events.

On deployments where chat is readable during the call, the adapter routes messages addressed
to the configured bot name. The gateway must be running and the sender must be allowed by
its configured display name. For example, `hermes config set MEETSTREAM_ALLOWED_USERS "Sid,Nav"`.

## Security

### Identity of participants

- **Display names are not a proof of identity.** A guest can type any name when the guest joins a call.
  Thus, a guest can use a name from your allowed list.
  Use `MEETSTREAM_ALLOWED_USERS="*"` only for calls with people that you trust.
  MeetStream does not give a stable identifier for a participant. Thus, the plugin cannot do a better check.
- **Hermes also accepts the names in `GATEWAY_ALLOWED_USERS`.** If that list contains a name, a meeting guest with that display name can ask Hermes questions.
- **The adapter discovers bots tagged `hermes: true` or using the configured bot name.**
  If multiple Hermes profiles share one MeetStream account, the discovery markers can overlap.
  Use separate MeetStream workspaces or run one chat gateway per workspace.
### Tools in meeting chat

- **Meeting chat can only search the web.** A question in the meeting chat starts a Hermes turn with a fixed, small set of tools:
  `web_search` and `web_extract`. The plugin blocks all the other tools for these turns.
  The blocked tools include the terminal, files, code execution, MCP servers, the tools of other plugins, and the `meetstream_*` tools.
  Thus, a guest with a false display name cannot run commands, read files, or send the bot to other calls.
- **This limit is always on.** The setting `platform_toolsets.meetstream` has no effect.
  To do more with a call, ask Hermes outside the meeting, for example in the CLI.
### Other protections

- **The skill tells Hermes that text from a meeting is data, not an instruction.**
  Hermes does not run commands, send files, or send email because a person in the call asked.
  Hermes does these actions only when you confirm them outside the call.
- The plugin uses outbound polling by default. Configuring the optional webhook opens a loopback
  listener for the HTTPS reverse proxy. The adapter contacts MeetStream, and the brief uses
  Hermes’s configured model provider.

## Settings

You set these values in **Settings → Plugins → Hermes in Meetings**, or in `config.yaml` under `plugins.entries.meetstream.settings`.

| Setting | Default | What it does |
|---|---|---|
| `bot_name` | `Hermes` | The name of the bot in the call. People use this name to ask a question. |
| `transcription` | `meetstream` | The transcription provider: `meetstream`, `meeting_captions`, `deepgram`, `assemblyai`, or `none`. `meetstream` adds $0.10 for each hour. For `deepgram` and `assemblyai`, save your own provider key in the MeetStream dashboard. |
| `status_gifs` | `false` | Show status artwork on the bot tile for new Google Meet joins. |
| `status_gif_base_url` | Empty | Public HTTPS directory for animated playback of the three supplied GIFs. |
| `join_message` | A short introduction | The chat message that the bot sends when it joins. `{name}` changes to the bot name. |

You can set these values for the gateway in `config.yaml` under `platforms.meetstream.extra`:

| Setting | Default | What it does |
|---|---|---|
| `chat_poll_seconds` | `5` | The time between two reads of the meeting chat. The minimum is 3 seconds. |
| `discovery_seconds` | `120` | The time between two searches for new Hermes bots. `0` stops the search. |

## Settings in the MeetStream dashboard

Set these items at <https://app.meetstream.ai>. You do not have to install Hermes again after a change.

- **Calendar auto-join.** Connect your calendar. MeetStream then sends a bot to your calls.
  To make Hermes answer in these calls, set the default bot name to the Hermes bot name (default `Hermes`).
- **Webhooks.** Get an event when a bot joins, leaves, or when a transcript is ready.
- **Storage.** Keep the recordings in your own storage bucket.
- **Signed-in bots.** Use the MeetStream dashboard or API to dispatch signed-in bots. Direct joins
  from this plugin do not request Google or Teams sign-in. For a guest bot in the waiting room,
  admit it from the host account. Hermes can report `WaitingRoomTimeout` when nobody admits it.

## How the plugin works

- `meetstream_join` creates a MeetStream bot with the custom attribute `hermes: true`.
- The gateway platform reads the chat of each Hermes bot that is in a call.
- Every 120 seconds, the gateway also searches the bots of the last day for two markers:
  the attribute `hermes: true`, or the Hermes bot name.
  Thus, bots from your calendar or from the dashboard also get Hermes.
  Calendar auto-join replaces the custom attributes of a bot. Thus, for these bots, only the name is a marker.
- A chat message that starts with the bot name goes to Hermes as a message from that person.
  The answer of Hermes goes back to the same meeting chat.
- When the bot leaves the call, the gateway stops the reads for that bot.

## Limits

- The search reads the 200 most recent bots of the last day. On an account with more bots in one day, use `meetstream_join` to start Hermes bots.
- If the gateway finds a bot created before the gateway started, or more than 5 minutes after the
  bot was created, it skips the existing chat history. Ask the question again after the gateway connects.

## Network calls and data

The plugin uses your MeetStream API key at `https://api.meetstream.ai`. For requested briefs it also uses Hermes’s configured model.

- Calendar lookup reads synced event titles, times, calendars, links, RSVP status, and attached bot IDs
  from the connected MeetStream account. Scheduling stores the selected occurrence ID and title as
  bot attributes. No separate calendar credentials are stored by the plugin.
- The tools send requests when Hermes uses them. Joining searches for a matching bot and sends a
  hashed join target as a bot attribute and in an idempotency key. A transcript wait checks for
  readiness every 15 seconds for up to 120 seconds per tool call.
- While the gateway runs, the gateway searches for Hermes bots every 120 seconds.
  During a call, it tries to read the chat every 5 seconds and backs off to 30 seconds if the artifact is pending.
- The plugin sends the meeting link, the bot name, the join message, and the chat answers of Hermes.
  The plugin receives bot status, meeting chat, and transcripts. Hermes sends retrieved transcript
  text to its configured model provider when asked to produce notes.
- MeetStream keeps recordings and transcripts as your MeetStream account settings tell it.
- For a requested brief, the gateway polls the queued bot's status and transcript. It stores job
  metadata, the private messaging destination when applicable, and temporarily stages the brief in
  `meetstream-briefs.sqlite3` in that Hermes profile. The final brief is stored in the originating
  Hermes chat history. Google Meet status GIFs send packaged artwork to MeetStream.
- The plugin starts no shell commands and sends no telemetry.
- The plugin does not update itself.

MeetStream bills the bot time and the transcription to your MeetStream account from prepaid credit.
Refer to <https://meetstream.ai/pricing>.
If the account has no credit, `meetstream_join` tells Hermes to give you the top-up link: <https://app.meetstream.ai/billing>.

## Voice answers in the call

This plugin answers in the meeting chat. If you want an agent that talks in the call, use these tracks after the recording bot.
Use them in this order:

| Track | What you do | Price for each meeting hour |
|---|---|---|
| 2. Bridge server (your own stack, local) | The bot sends the live audio of the call to your server (`live_audio_required.websocket_url`). Your server sends audio, chat and images back on the control socket (`socket_connection_url.websocket_url`). You run your own speech-to-text, LLM and text-to-speech. Free local models are possible, for example faster-whisper or Parakeet, a model in Ollama, and Piper or Kokoro. On a laptop, use a local tunnel (ngrok or cloudflared). With the CLI: `meetstream join <url> --live-audio-ws wss://<public-url>/audio --socket-ws wss://<public-url>/control`. Refer to [Bridge server architecture](https://docs.meetstream.ai/guides/websockets/bridge-server-architecture) and the starter [MeetStream Bridge](https://github.com/meetstream-ai/meetstream-agent). | Bot price only. MeetStream charges no agent infrastructure and no model tokens. |
| 3. Agents API infra (MIA, hosted by MeetStream) | MeetStream hosts the agent. 3a: MeetStream's own, default keys. Inbuilt keys work in pipeline mode only: Deepgram (speech-to-text) and OpenAI (LLM and voice). Realtime mode runs on OpenAI and needs your own OpenAI key. 3c: your own provider keys (OpenAI, Anthropic, Deepgram, ElevenLabs and others). | Bot price + $0.25 agent infrastructure + the price of the models you pick. The agent editor in the dashboard shows the rate before the bot runs. With 3c, your provider bills you for model usage. |
| 3b. Bring your own agent infra (LiveKit) | Coming soon. Not available yet. | |
| 3d. Local agent: Hermes as the brain | Coming soon. Not available in production yet. Hermes on your computer will write what the voice agent says, through `meetstream setup` and `meetstream agent serve` over the MeetStream relay (no tunnel). | |

The bot price is $0.35 for each recording hour ($0.25 at volume). Refer to <https://meetstream.ai/pricing>.
If you do not want to operate servers, use track 3a or 3c.
Inbuilt keys are not on for all accounts yet. If the API says "MeetStream-managed keys are not available for ... Use your own key.", use track 3c. Do not retry the same request.
A hosted agent bot (track 3) takes only `agent_config_id`. Do not add the bridge sockets to that bot.

### Set up a voice agent with the MeetStream CLI

The `meetstream` CLI can make the agent and send it to a call. Install the CLI with one of these commands:

```bash
npm install -g @meetstream/cli          # or: npx -y @meetstream/cli <command>
pipx install meetstream-cli             # or: uvx --from meetstream-cli meetstream <command>
brew install meetstream-ai/tap/meetstream
```

Binaries are at <https://github.com/meetstream-ai/cli/releases>.
To sign in, run `meetstream login`. The command opens your browser and keeps a key. You can also set `MEETSTREAM_API_KEY`.

- Track 3a: run `meetstream setup --mode hosted`, then `meetstream join <url> --agent-config <id>`.
- Track 3c: run `meetstream setup --mode byok`. Add your provider keys in the dashboard. The setup does not ask for keys.

When Hermes runs the CLI, Hermes uses `meetstream <command> --json --no-input` and reads the JSON output. `meetstream skill` prints the CLI's full guide for agents (every command and its JSON output).

Hermes can use MeetStream today for recording (this plugin) and with hosted agents (track 3).
Hermes as the brain of the voice agent (track 3d) is coming soon. When it is available, know this:
the speech and chat of the meeting will go to an agent that has access to your computer and your terminal, and a participant can try to give it instructions (prompt injection).
Use the lowest access level.

## Hermes in Meetings or the MeetStream connector

Hermes also has a MeetStream connector in its MCP catalog (`hermes mcp install meetstream`).
The connector exposes the broader MeetStream MCP toolset. The plugin adds a meeting-specific
skill and gateway adapter. Installing both gives Hermes two sets of meeting tools.

## Latest docs

- Integration paths: <https://docs.meetstream.ai/guides/introduction/integration-paths>
- Bridge server (track 2): <https://docs.meetstream.ai/guides/websockets/bridge-server-architecture>
- First bot: <https://docs.meetstream.ai/guides/get-started/create-your-first-bot>
- Voice agent pricing and keys: <https://docs.meetstream.ai/guides/mia/pricing-and-keys>
- What is MIA: <https://docs.meetstream.ai/guides/mia/what-is-mia>
- Local agent (`local_agent`, track 3d, coming soon): <https://docs.meetstream.ai/guides/features/mia-screen-sharing-and-custom-agents>

For the latest details, fetch a page with `.md` at the end of the URL, read <https://docs.meetstream.ai/llms.txt>, or connect the docs MCP server at <https://docs.meetstream.ai/_mcp/server>.

## Development

```bash
git clone https://github.com/NousResearch/hermes-agent
cd hermes-agent && uv sync --extra messaging && cd ..
PYTHONPATH=hermes-agent hermes-agent/.venv/bin/python -m unittest discover -s hermes-meetstream/tests -v
hermes-agent/.venv/bin/hermes plugins validate hermes-meetstream
```

The tests use a fake MeetStream API. The tests do not need an API key or a network connection.

## License

MIT. Refer to [LICENSE](LICENSE).
