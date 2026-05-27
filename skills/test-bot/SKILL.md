---
name: test-bot
description: >
  Send a single test bot to a live meeting and stream every webhook event to
  the terminal in real time. Used to validate end-to-end MeetStream
  configuration before shipping. Use when the user says "test my MeetStream
  setup", "send a test bot", "validate my webhook", "watch bot events live",
  "debug a bot run", or "make sure everything works".
allowed-tools: Bash, Read, Write
---

# Send a Test Bot + Watch Webhooks Live

End-to-end smoke test for a MeetStream integration: send a bot to a real meeting, capture every webhook event the bot fires (via webhook.site or the user's own callback URL), and pretty-print them as they arrive.

## Step 0: Auth check (DO THIS FIRST)

If `MEETSTREAM_API_KEY` is missing or invalid, **invoke the `getting-started` skill first.** Walks the user through signup at https://app.meetstream.ai → API key → env var.

## What to do

1. **Ask the user:**
   - Meeting link (Google Meet preferred — easiest to admit a bot to)
   - Provider preference: `meetstream_streaming` (live, default — no external key) or a specific post-call provider
   - Webhook URL: their own, or "use webhook.site" to create a temporary capture URL

2. **Set up the capture URL** if needed (create webhook.site token via API).

3. **Send the bot** with the user's chosen provider.

4. **Stream events** to terminal in real time using polling (webhook.site) or a local tunnel.

5. **Summarize** at the end with timing per stage and any anomalies.

## Step 1: Create a webhook.site bucket (if user needs one)

```bash
RESP=$(curl -s -X POST "https://webhook.site/token" -H "Content-Type: application/json" -d '{}')
UUID=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
echo "Webhook URL: https://webhook.site/$UUID"
echo "Inspector:   https://webhook.site/#!/$UUID"
echo "$UUID" > /tmp/test_bot_uuid
```

## Step 2: Send the bot

```bash
WEBHOOK="https://webhook.site/$(cat /tmp/test_bot_uuid)"
curl -s -X POST "https://api.meetstream.ai/api/v1/bots/create_bot" \
  -H "Authorization: Token $MEETSTREAM_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"meeting_link\": \"$MEETING_LINK\",
    \"bot_name\": \"Test Bot — delete me\",
    \"video_required\": false,
    \"callback_url\": \"$WEBHOOK\",
    \"recording_config\": {
      \"transcript\": {\"provider\": {\"meetstream_streaming\": {}}},
      \"retention\": {\"type\": \"timed\", \"hours\": 24}
    },
    \"custom_attributes\": {\"test_run\": \"true\"},
    \"automatic_leave\": {
      \"waiting_room_timeout\": 600,
      \"everyone_left_timeout\": 600,
      \"voice_inactivity_timeout\": 600,
      \"in_call_recording_timeout\": 14400,
      \"recording_permission_denied_timeout\": 300
    }
  }" | python3 -m json.tool
```

Save the returned `bot_id` for monitoring.

## Step 3: Stream events live

Use the `Monitor` tool with this script. It polls webhook.site every 5s and emits one line per NEW event:

```bash
UUID=$(cat /tmp/test_bot_uuid)
BOT_ID="<from step 2>"
prev=""
while true; do
  cur=$(curl -s "https://webhook.site/token/$UUID/requests?sorting=newest&per_page=100" 2>/dev/null \
    | python3 -c "
import sys, json
try: d = json.load(sys.stdin)
except: sys.exit(0)
for r in reversed(d.get('data', [])):
    try: b = json.loads(r.get('content',''))
    except: continue
    if b.get('bot_id') != '$BOT_ID': continue
    ev = b.get('event', '?')
    bs = b.get('bot_status', '-')
    sc = b.get('status_code', '-')
    msg = (b.get('message','') or '')[:60]
    print(f'{ev}|{bs}|{sc}|{msg}')
" 2>/dev/null | sort -u)
  diff <(echo \"\$prev\") <(echo \"\$cur\") 2>/dev/null | grep --line-buffered '^>' | sed 's/^> //'
  prev=\"\$cur\"
  if echo \"\$cur\" | grep -qE 'bot.done|audio.processed.*\$BOT_ID'; then
    sleep 30  # give post-call events time
    break
  fi
  sleep 5
done
```

For local webhook URLs (not webhook.site), the user should `tail -f` their server logs directly.

## Step 4: Cleanup prompt

After the bot is done, the user might want to delete the data. Don't auto-delete. Prompt:

```
Test bot complete.

Bot ID: <bot_id>
Status: <final bot_status>
Events received: <count>

Want to delete the recording + transcript now? (y/N)
  → If y: DELETE /bots/<bot_id>/delete (DESTRUCTIVE — data gone forever)
  → If n: data auto-expires after the retention period (default 24h)
```

## Output format for the report

After streaming completes, print a summary:

```
═══ Test bot summary ═══
Bot ID:        <id>
Meeting:       <link>
Provider:      meetstream_streaming
Total events:  9
Duration:      147s (joining → audio.processed)

Lifecycle timeline:
  00:00  bot.joining          Joining
  00:34  bot.inmeeting        InMeeting
  00:34  bot.recording        Recording
  02:21  bot.leaving          Leaving
  02:21  bot.stopped          Stopped
  02:22  manifest.completed
  02:23  audio.processed      Success

Live transcript chunks: 47 (delivered to webhook.site)
Post-call events:       None (Path B — streaming-only, expected)

✅ End-to-end flow worked.
```

If anything fails, surface the message field from the failing event — it usually points directly at the cause (provider key missing, wrong meeting link format, etc.).

## Common test results

| Outcome | Most likely cause | Fix |
|---|---|---|
| Stuck at `bot.joining` for >2 min | Bot in waiting room; user needs to admit it | Admit the bot in the meeting UI |
| `bot.stopped` with `bot_status: NotAllowed` | Waiting room timed out | User didn't admit; or admit faster next time |
| `bot.stopped` with `bot_status: Denied` | Host blocked the bot | Ask host to allow bots, or use Google Signed-In setup |
| `bot.error` mid-meeting | Streaming provider auth issue | Check provider key in MeetStream dashboard |
| `transcription.failed` | Post-call provider missing key | Use `verify-account` skill to confirm; switch provider or add key |
| 0 live chunks | Streaming provider failed silently OR no one spoke | Check `bot.error` events; have someone speak in the meeting |
