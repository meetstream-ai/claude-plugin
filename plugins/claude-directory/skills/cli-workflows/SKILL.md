---
name: cli-workflows
description: >
  Step-by-step workflows for the meetstream CLI (one Go binary: npm @meetstream/cli,
  PyPI meetstream-cli, Homebrew meetstream-ai/tap/meetstream). Use when the user wants to
  do MeetStream work from the terminal or wants this agent to run it: "use the meetstream
  CLI", "install meetstream", "sign in to MeetStream", "send a bot from the terminal",
  "get the transcript with the CLI", "listen for webhooks locally", "connect my calendar
  from the CLI", "set up MIA with the CLI", "meetstream setup", "meetstream doctor",
  "signed-in bot accounts", "Zoom OBF or ZAK with the CLI", or any `meetstream <command>`.
---

# meetstream CLI workflows

The `meetstream` CLI (version 1.x, repo meetstream-ai/cli) is one binary for macOS, Linux and
Windows. It replaced the earlier Node and Python command-line tools. Every workflow below works the
same from a terminal and from this agent. Full command reference and JSON shapes:
`skills/meetstream/references/meetstream-cli.md` (a copy of the CLI's SKILL.md; `meetstream skill`
prints the same text).

## Rules for this agent
- Always pass `--json --no-input`. Parse stdout; human messages go to stderr.
- Exit codes: `0` ok, `1` runtime or API error, `2` usage error or not signed in, `3` not ready
  or not available on this server, `4` transcript failed, `130` interrupted. With `--json`,
  errors are `{"error": {"message", "hint", "exit_code"}}`: follow the `hint`.
- Never ask for the API key in chat. Never print it. On exit 2 "not signed in", run
  `meetstream login --json` (it opens the user's browser) or ask the user to set
  your MeetStream API key.
- No CLI on the machine: the meetstream CLI (to install it, see https://docs.meetstream.ai/build-with-ai/meetstream-cli).
- Prices come from the API (`setup --dry-run`, `balance`); never quote prices from memory.

## W1 · Install, sign in, check
```bash
npm install -g @meetstream/cli          # or: meetstream <command>
pipx install meetstream-cli             # or: meetstream <command>
brew install meetstream-ai/tap/meetstream
meetstream login --json                 # browser sign-in; stores a named key (0600). --no-browser prints the link
meetstream doctor --json                # key, API URL, config, agent CLIs; exit 1 if a check fails
meetstream auth status --json           # key in use (masked), valid or not
```
CI: `printf %s "YOUR_API_KEY" | meetstream login --with-key` or just set your MeetStream API key.
After `login` in a terminal, the CLI offers to connect a calendar (`--no-calendar` skips).

## W2 · Recording bot, transcript after the call (track 1a)
```bash
meetstream join https://meet.google.com/abc-defg-hij -n "Notetaker" -t meetstream --json
meetstream bots status <bot-id> --watch --json      # successive status values
meetstream transcript <bot-id> --wait --json        # exit 3 while pending, 4 if it failed
meetstream recordings <bot-id> --json               # audio and video links
meetstream bots get <bot-id> --part participants --json   # also: detail, chats, screenshots, streams, audio-streams
```
- `-t meetstream` = MeetStream transcription (adds a per-hour charge; tell the user). Other
  providers need the user's own key saved in the dashboard.
- Audio only unless the user asked for video (`--video`, `--video-layout speaker_view|grid_view`).
- Other `join` options: `--join-at <iso8601>` (schedule), `-c <url>` (lifecycle webhook),
  `--max-recording-seconds`, `--waiting-room-timeout`, `--everyone-left-timeout`,
  `--retention-hours`, `--storage-id` (customer S3), `--separate-audio`, `--separate-video`,
  `--attr key=value`, `--idempotency-key`.
- Re-run transcription on a finished meeting: `meetstream transcribe <bot-id> -p <provider>`;
  list runs with `meetstream transcriptions <bot-id>`.
- Speaker timeline: `meetstream bots timeline <bot-id> [--download]`.
- End or clean up: `meetstream bots remove <bot-id>`; permanent delete
  `meetstream bots delete <bot-id> --yes` (confirm with the user first).

## W3 · Live transcript and webhooks on a laptop (track 1b)
```bash
meetstream listen -p 3333 --json        # loopback receiver: one JSON line per event
# expose it with a tunnel (ngrok, cloudflared), then:
meetstream join <url> -t meetstream_streaming -c https://<public-url>/webhook --live-transcript-webhook https://<public-url>/webhook --json
```
`-t meetstream_streaming` is MeetStream live transcription (no provider key). Deepgram, AssemblyAI, Sarvam and other `*_streaming` providers need the user's key in the dashboard.
`listen --forward <url>` also relays events elsewhere. `meetstream bots tail` (events over the
relay, no tunnel) is planned: today it exits 2 with a hint.

## W4 · Talk in the meeting from the terminal
```bash
meetstream bots say <bot-id> "Recording has started"
meetstream bots show-image <bot-id> https://example.com/slide.png -d 10
meetstream bots hand <bot-id> up        # or down
```

## W5 · Bridge server: your own STT, LLM and TTS (track 2)
```bash
meetstream join <url> --live-audio-ws wss://<public-url>/audio --socket-ws wss://<public-url>/control --json
```
Audio comes in on `--live-audio-ws`; your server sends audio, chat and images back on
`--socket-ws` (`--live-video-ws` for video frames). Free local models work (faster-whisper or
Parakeet, Ollama, Piper or Kokoro). A laptop needs a tunnel for these URLs. Never add the bridge
sockets to a MIA bot (`--agent-config`).

## W6 · Zoom
Zoom always needs setup: bots join through the customer's own Zoom app, set up in MeetStream
first. For meetings outside that app's Zoom account, pass a token URL:
```bash
meetstream join https://zoom.us/j/123 --zoom-obf-url https://<your-service>/obf --json   # or --zoom-zak-url
```
`--zoom-use-own-app` / `--no-zoom-use-own-app` override the account default.

## W7 · Signed-in bots (Google Workspace, Microsoft Teams)
```bash
meetstream logins teams add-domain contoso.com
printf %s "$PASSWORD" | meetstream logins teams add --domain contoso.com --email bot@contoso.com --password-stdin
meetstream logins google add --domain acme.com --email bot@acme.com --key key.pem --cert cert.pem
meetstream join <url> --teams-login-domain contoso.com     # or --google-login-domain / --sign-in-email
```
Passwords only from stdin, an environment variable or a hidden prompt; never in argv or chat.

## W8 · Calendar auto-join
```bash
meetstream calendar connect --provider google --no-input --open --json   # one-click sign-in, where the server offers it
meetstream calendar auto-join on -n "Notetaker"                          # --video to record video
meetstream calendar events --json
meetstream calendar schedule <event-id> | unschedule <event-id> | reschedule <bot-id> <iso8601> | cancel <bot-id>
```
One-click connect is coming soon in production: there it exits 3 with a hint. Use your own
Google OAuth app today:
`meetstream calendar connect --own-app --client-id <id> --client-secret <secret> --refresh-token <token>`.
Join rule: `--join-rule accepted` (default: meetings the account hosts or accepted) or `all`.

## W9 · MIA voice agent hosted by MeetStream (tracks 3a and 3c)
```bash
meetstream setup --mode hosted --name "Product FAQ" --dry-run --json   # shows the request and the price per hour
meetstream setup --mode hosted --name "Product FAQ" --json --no-input  # MeetStream keys (pipeline: Deepgram + OpenAI)
meetstream setup --mode byok --name "Support" --json --no-input        # your provider keys, saved in the dashboard
meetstream join <url> --agent-config <agent_config_id> --json
```
- `--ears`, `--brain`, `--voice` take `provider:model` (defaults come from the server catalog).
- Realtime mode needs the user's own OpenAI key. Setup never asks for keys: they go in the dashboard.
- Agent configs as code: `meetstream mia apply -f mia.json [--dry-run]`;
  manage with `meetstream mia list | get | create | update | delete`.
- MIA bots take only `--agent-config` (with optional `--agent-param key=value`); no bridge sockets.

## W10 · Your coding agent as MIA's brain (track 3d) · coming soon
Not available in production yet (the MeetStream relay is not live there; `setup` exits 3).
Do not present it as available. When it ships, the flow is:
```bash
meetstream agent login                  # this computer's relay sign-in (browser)
meetstream setup --agent claude --access readonly   # or codex, hermes, copilot, muse, openclaw, agy
meetstream agent serve                  # outbound only; nothing listens on the laptop
meetstream agent context show|edit      # what the agent reads in meetings (MEETING.md)
meetstream agent bench --compare        # tokens and cost per meeting hour, per model
meetstream doctor --agent claude        # installed, signed in, warm session, relay, context
```
Meeting speech reaches an agent with access to this computer (prompt injection): keep the
lowest access level (`readonly`).

## W11 · Tools for agents and editors
```bash
meetstream mcp add claude|codex|cursor|vscode [--write]   # hosted MCP (OAuth) setup; --write merges the config
meetstream skill                                          # the agent guide (SKILL.md)
meetstream docs                                           # the README in the terminal
meetstream balance --json                                 # prepaid balance; exit 3 if not available
```

## Choosing a workflow
| User wants | Workflow |
|---|---|
| Notes or a transcript after the call | W2 |
| Live captions, webhooks on a laptop | W3 |
| Their own voice stack | W5 |
| A hosted voice agent | W9 |
| Their coding agent in the meeting | W10 (coming soon) |
| Every meeting on a calendar | W8 |
| Zoom outside their own account | W6 |
| Bots that sign in to Workspace or Teams | W7 |

## Latest docs
- CLI guide: https://docs.meetstream.ai/build-with-ai/meetstream-cli
- Create your first bot: https://docs.meetstream.ai/guides/get-started/create-your-first-bot
- Local webhook server (tunnels): https://docs.meetstream.ai/guides/webhooks/local-webhook-server
- CLI source and README: https://github.com/meetstream-ai/cli ; command reference and JSON shapes: `skills/meetstream/references/meetstream-cli.md` (or `meetstream skill`)

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
