---
name: getting-started
description: >
  First ask: notes after the call, or something live during the call? (one
  question, after the one sign-in step if the MeetStream tools are not
  connected). First-time setup for MeetStream - guides a brand-new user through
  account signup, API key creation, environment configuration, and a validation
  ping. MUST be invoked before any other MeetStream skill (notetaker,
  sales-coach, calendar-automation, etc.) if MEETSTREAM_API_KEY is missing.
  Auto-trigger when user says "get started", "help me get started with
  MeetStream", "help me use MeetStream", "how do I use MeetStream", "what can
  MeetStream do", "set up MeetStream", "I don't have a MeetStream account",
  "first time using MeetStream", "MeetStream onboarding", "create MeetStream API
  key", "MeetStream signup", "how do I start with MeetStream", or when a user
  invokes any other MeetStream skill without MEETSTREAM_API_KEY set.
allowed-tools: Bash, Read, Write, Edit
---

# MeetStream Getting Started - First-Time Setup

This skill is the **mandatory Step 0** for any MeetStream integration. If the user doesn't have an account or API key, no other skill can succeed. Walk them through it before scaffolding anything.

## Your first reply

1. If the MeetStream tools are missing or not signed in, give the one step to connect
   (see below) and keep going in the same reply.
2. Ask one question first: do you want results **after the meeting** (recording,
   transcript, notes) or something **live, during the call** (live transcript, live
   audio or video, chat, raise hand)? Do not lead with a voice agent.
3. Then follow the answer: after the meeting → `join-meeting` and `meeting-brief`; live →
   `realtime-streaming`. If they will write code, the API key steps below apply.

## Two ways in: pick by what the user wants

- **Use MeetStream from this agent** (send bots, get notes): no key needed. This plugin includes the hosted MeetStream MCP server. Sign in once: Claude Code `/mcp` → `meetstream` → **Authenticate**; Codex `codex mcp login meetstream`; Cursor Settings → MCP → **Connect**. The browser opens app.meetstream.ai; the user signs in or signs up and clicks **Allow**. Check with the `list_bots` tool, then ask the routing question below (after the meeting or live?) and hand over to `join-meeting` or `realtime-streaming`. New accounts start with $5 of credit.
- **Build an app on the API** (code, servers, CI): the code needs an API key. Follow the steps below.

## Intake routing (read this first)

MeetStream is meeting-bot and recording infrastructure: a bot joins Zoom, Google Meet or
Microsoft Teams, records and transcribes, and gives you recordings, transcripts and
webhooks. Start there.

1. **Post-call or live?** When the user has not said what they want, ask this one
   question first: do you want results **after the meeting** (recording, transcript,
   brief, action items) or something **live, during the call** (live transcription,
   live audio or video streams, chat, raise hand)?
   - Post-call → `join-meeting`, then `meeting-brief`; for apps also `webhooks` and
     `recordings-and-media`.
   - Live → `realtime-streaming` (chat and raise hand are in `join-meeting`).
   - Build requests count too: if a build request names only the trigger (a CLI, a
     calendar, a list of links) and not the outcome, ask once.
   - If the request already says which ("record my 3pm call and send me notes" is
     post-call), do not ask. Go.
2. **Voice agents only on request.** Do not suggest a bot that talks. Bring in
   `mia-voice-agents` only when the user asks for a "voice agent", an "agent in the
   meeting", or a bot that talks, answers or speaks (or names MIA, the API name). In
   replies say "voice agent"; most users do not know the word MIA.
3. **Voice agent setups, in this order** (details in `mia-voice-agents`):
   1. **MeetStream-managed keys** (default): `"key_source": "meetstream"` in each
      pipeline section, no provider keys to bring, billed per hour on the MeetStream
      account.
   2. **Your own provider keys**: the user brings their own transcription, LLM and voice
      keys and sets up the providers themselves.
   3. **Your own agent on your own computer** (for example a Claude Code or Codex
      subscription, through the MeetStream Agent Kit): only when the user asks for it.
      Warn first, in the same answer: anyone in the meeting can try to make that agent run commands or read files on the user's computer (prompt injection); use the lowest access level (read-only) and the activation code, and keep the computer, the bridge and the tunnel running for the whole meeting.
4. **Version questions:** reply with these two sentences, then continue with what the
   user wants to do: "Install or update to the current MeetStream plugin. The MCP
   server is hosted at https://mcp.meetstream.ai/mcp, so everyone uses the same
   server." Add nothing else about versions.

**If the MeetStream tools are missing or not signed in** (no `meetstream` tools, or a tool
answers 401 or "not signed in"): give the user the one step to connect, and in the same
reply keep helping. Do not stop at "sign in first".
- Claude Code: `/mcp` → `meetstream` → sign in. Cursor: Settings → MCP → **Connect** next
  to `meetstream`. Codex: `codex mcp login meetstream` (full steps:
  https://github.com/meetstream-ai/claude-plugin/blob/main/INSTALL_FOR_AGENTS.md).
- Then go on: give the plan, the `create_bot` fields you will send once the tools work,
  or the REST call (`curl` with `Authorization: Token $MEETSTREAM_API_KEY`).

## When to invoke this skill

**Always** invoke this skill first if any of these are true:

1. The user explicitly says they're new to MeetStream / don't have an account
2. `MEETSTREAM_API_KEY` environment variable is missing
3. A different MeetStream skill (notetaker, sales-coach, calendar-automation, verify-account, test-bot) was invoked and the API key check failed
4. The user pastes an obviously-wrong API key (e.g. `YOUR_API_KEY`, `ms_xxxxx`, empty string)

**Skip** if:
- `MEETSTREAM_API_KEY` is set AND a quick ping to `GET /bots` returns 200
- The user explicitly says "I already have my key, just build X"

## Step 1: Check if API key is already configured

```bash
# Quick check
if [ -z "$MEETSTREAM_API_KEY" ]; then
  echo "No API key set - starting onboarding"
else
  # Validate it
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Token $MEETSTREAM_API_KEY" \
    "https://api.meetstream.ai/api/v1/bots")
  if [ "$STATUS" = "200" ]; then
    echo "✅ API key already valid - skipping onboarding"
    exit 0
  else
    echo "❌ API key set but invalid (HTTP $STATUS) - re-running onboarding"
  fi
fi
```

If invalid or missing, continue to Step 2.

## Step 2: Sign up for a MeetStream account (if needed)

Tell the user:

```
You'll need a MeetStream account to use this. Free tier includes credits to
get you started - no credit card needed up front.

👉 Open https://app.meetstream.ai in your browser

  1. Sign up with your work email (Google sign-in works too)
  2. Confirm your email if prompted
  3. You'll land on the dashboard

Reply "done" when you're signed in and I'll walk you through the API key.
```

Wait for the user to confirm before continuing.

## Step 3: Create an API key

Tell the user:

```
Now create an API key:

👉 Open https://app.meetstream.ai/api-keys

  1. Click "Create API Key" (or similar - top right of the page)
  2. Name it something memorable (e.g. "claude-code-dev")
  3. Copy the key - it starts with "ms_..."
  4. ⚠ Save it now - you usually can't view it again after closing the modal

Paste the key here when ready (I'll redact it from logs).
```

When the user pastes the key, do NOT echo it back. Acknowledge with just `"Got it - key starts with ms_xxxx... (length: N chars)"`.

## Step 4: Set the API key in their shell

Detect the user's shell + suggest the right persistence approach:

```bash
echo $SHELL  # /bin/zsh, /bin/bash, etc.
```

### For zsh / bash users (most common)

```bash
# For this session only:
export MEETSTREAM_API_KEY=ms_xxxxx

# To persist across sessions (zsh):
echo 'export MEETSTREAM_API_KEY=ms_xxxxx' >> ~/.zshrc
source ~/.zshrc

# Or bash:
echo 'export MEETSTREAM_API_KEY=ms_xxxxx' >> ~/.bashrc
source ~/.bashrc
```

### For project-scoped (.env) - recommended for application code

If the user is building an app (notetaker / coach / etc.), they'll also want it in `.env`:

```bash
# In the project root
echo "MEETSTREAM_API_KEY=ms_xxxxx" >> .env

# Make sure .env is gitignored
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

> **Never commit `.env` to git.** If the key leaks, rotate it immediately at https://app.meetstream.ai/api-keys.

## Step 5: Validate the key

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  -H "Authorization: Token $MEETSTREAM_API_KEY" \
  "https://api.meetstream.ai/api/v1/bots"
```

Expected: `200`.

If `401` or `403`: key is wrong, re-do Step 3.
If anything else: network issue, ask user to retry.

## Step 6: Verify provider configuration (optional but recommended)

After a valid key, suggest:

```
✅ Your API key works.

One more recommended step: verify which transcription providers are configured
on your account. This catches "provider missing" errors before you build anything.

Run the `verify-account` skill, or I can run it now - want me to?
```

If yes, hand off to the `verify-account` skill.

## Step 7: Suggest next action

Based on what the user originally wanted, route them:

| User originally said | Hand off to |
|---|---|
| "build a notetaker" | `notetaker` skill |
| "build a sales coach" | `sales-coach` skill |
| "auto-record my calendar" | `calendar-automation` skill |
| "test a bot" | `test-bot` skill |
| "I just want to look around" | Suggest reading the `meetstream` core skill |

If they didn't originally have a goal, suggest the most common starting point:

```
You're all set. Most users start with one of these:

  🎙️  AI Meeting Notetaker         → "build me an AI notetaker"
  🎯  Real-Time AI Sales Coach     → "build a real-time sales coach"
  📅  Calendar Auto-Recording      → "auto-record every meeting on my calendar"
  🧪  Just send a test bot         → "send a test bot to https://meet.google.com/..."

Which one?
```

## Troubleshooting

### "I see the dashboard but no 'Create API Key' button"
Direct them to https://app.meetstream.ai/api-keys (deep link). Account may need email verification first - check inbox.

### "The key I created returns 401"
- Make sure they copied the WHOLE key (it's long - usually starts with `ms_` then 30+ characters)
- Make sure there are no leading/trailing whitespace characters
- Make sure they exported it: `echo $MEETSTREAM_API_KEY` should print the key (not empty)

### "I have no credits / billing question"
Direct to https://app.meetstream.ai → Billing section. Free tier covers a meaningful amount; paid plans at https://meetstream.ai/pricing.

### "I want to use a team account / shared key"
- Each team member should create their own key from their own account
- For server-side production use, create a dedicated key (e.g. "production") and store in a secret manager (AWS Secrets Manager, Doppler, Vault)

### "Can I rotate my key without breaking my deployment?"
- Create a new key first (don't delete the old one)
- Deploy the new key to your environment
- Once the new key is in use, delete the old one from the dashboard

## Constraints

- **Never log the API key value.** Show only the first 4 + length when acknowledging.
- **Never commit the key to git.** Always insist on `.env` + `.gitignore`.
- **Never POST the key anywhere except api.meetstream.ai.**
- **Never proceed with any build skill until Step 5 succeeds.** Better to ask once more than to scaffold a broken app.
