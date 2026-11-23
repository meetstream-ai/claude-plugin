---
name: verify-account
description: >
  Verify a MeetStream account's configuration before building. Checks API key
  validity, prepaid balance (shown on https://app.meetstream.ai/billing; the
  read-only GET /api/v1/billing/balance may answer not available, then use the
  billing page), which transcription providers can be used
  (meetstream and meetstream_streaming need no key; deepgram / assemblyai /
  sarvam / jigsawstack need the user's key in dashboard Integrations), voice
  agent configs, calendar connection and webhook URL reachability. Use when the
  user says "verify my MeetStream account", "check setup", "which providers do
  I have", "test API key", "diagnose meetstream", or before any other build
  skill runs.
allowed-tools: Bash, Read
---

# Verify MeetStream Account

A quick, read-only health check before building. It creates no bots.

If no key is set (`MEETSTREAM_API_KEY` or `meetstream login`), run `getting-started` first.
Never print the key.

## Fastest path

With the `meetstream` CLI, run these and report each line as ok / not ok:

```bash
meetstream auth status --json --no-input   # "valid": true = key works; exit 2 = not signed in
meetstream balance --json --no-input        # exit 3 "balance_unavailable" = use the billing page
meetstream mia list --json --no-input       # voice agent configs (Agents API)
meetstream calendar list --json --no-input  # connected calendars
```

**Install the CLI** (when this agent runs commands for the user): `npx -y @meetstream/cli <command>` works with no install; or `npm install -g @meetstream/cli`, `pipx install meetstream-cli`, `brew install meetstream-ai/tap/meetstream`. Sign in with `meetstream login` (it opens the browser and stores a key; never ask for the key in the chat) or set `MEETSTREAM_API_KEY`. Always pass `--json --no-input`. Exit codes: 0 ok, 1 API error, 2 usage or not signed in, 3 not ready yet, 4 transcript failed. JSON shapes: `skills/meetstream/references/meetstream-cli.md`.

Without the CLI:

```bash
H="Authorization: Token $MEETSTREAM_API_KEY"
B=https://api.meetstream.ai/api/v1
curl -s -o /dev/null -w "key: %{http_code}\n"      -H "$H" "$B/bots"             # 200 = key valid; 401/403 = new key at https://app.meetstream.ai/api-keys
curl -s -w "\nbalance: %{http_code}\n"            -H "$H" "$B/billing/balance"  # read only; "not available" or 404 = use the billing page
curl -s -o /dev/null -w "agents: %{http_code}\n"   -H "$H" "$B/mia"              # voice agent configs (Agents API)
curl -s -o /dev/null -w "calendar: %{http_code}\n" -H "$H" "$B/calendar"         # connected calendars
```

Node (`npm install @meetstream/sdk`): `await new MeetStream().bots.list()`.
Python (`pip install meetstream-sdk`): `MeetStream().bots.list()`. Both read
`MEETSTREAM_API_KEY`; a 401 or 403 means the key is wrong.

From the user's agent with the MCP tools connected: `list_bots` proves the sign-in works.
If the MCP `get_balance` tool says the balance is not available, send the user to
https://app.meetstream.ai/billing.

## How to read the report

- **Key** 200 = valid. 401 or 403 = missing or wrong key.
- **Balance**: the billing page https://app.meetstream.ai/billing shows it and adds
  credits. `GET /api/v1/billing/balance` (API v1.10.0) may not be on for every account
  yet: "not available" or 404 is expected, not a fault; use the billing page. Low credits
  stop new bots (`403 Low credits please recharge`).
- **Providers**: `meetstream` (post-call, +$0.10 per hour) and `meetstream_streaming`
  (live) work on every account with no provider key. `deepgram`, `assemblyai`, `sarvam`,
  `jigsawstack` and the other provider names need the user's own key under dashboard
  Configure > Integrations. A missing or rejected key shows up when the transcript runs:
  `transcription.failed`, and `get_transcript` returns 422 with the reason.
- **Webhook URL**: must be public HTTPS. Test it with a plain `curl -X POST <url>`; for
  local development use a tunnel (`webhooks` skill).

## After the report

- Everything ok: build with `meetstream` transcription (post-call) or
  `meetstream_streaming` (live) unless the user saved another provider key.
- Want to watch a real bot end to end: `test-bot`.

## Latest docs

- Authentication: https://docs.meetstream.ai/api-reference/authentication
- Dashboard setup and API key: https://docs.meetstream.ai/guides/get-started/dashboard-setup
- Transcription providers: https://docs.meetstream.ai/guides/transcription-recordings/providers/transcription-providers

For the latest details, fetch the page with `.md` appended, read https://docs.meetstream.ai/llms.txt, or connect the docs MCP server at https://docs.meetstream.ai/_mcp/server.
