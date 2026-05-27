---
name: sales-coach
description: >
  Build a real-time AI sales coaching tool on MeetStream — live transcription
  streams to a server that detects objections, talk-time imbalance, missed
  questions, etc., and surfaces coach cards to the seller during the call.
  Use when the user says "real-time AI sales coach", "AI cue cards during
  calls", "live objection detection", "AI copilot for sales calls", "live
  conversation intelligence", "live meeting assistant", "real-time meeting
  intelligence", "live sales call analyzer", or "real-time AI call
  coaching". Scaffolds streaming-provider bot + webhook server + WebSocket
  push to the seller's browser tab.
---

# Sales Coach Scaffold

Build a real-time AI sales coaching tool on MeetStream. Live transcript chunks stream to your server, you run intent/signal detection, and you push coaching cards to the seller's browser via WebSocket.

## Step 0: Auth check (DO THIS FIRST)

If `MEETSTREAM_API_KEY` is missing or invalid (`curl -H "Authorization: Token $MEETSTREAM_API_KEY" https://api.meetstream.ai/api/v1/bots` returns non-200), **invoke the `getting-started` skill first.** It walks the user through signup at https://app.meetstream.ai → API key → env var. Resume this skill once the key validates.

## Step 1: Requirements

Ask in one message:

```
I'll build you a real-time sales coach. Quick config:

1. STACK?  Python (FastAPI) or Node.js (Next.js)? [default: Python + FastAPI]

2. COACHING SIGNALS?  Which to detect (pick any):
   a) Objections (price, timing, authority, need, competitor)
   b) Missed buying signals (budget mentions, decision-maker named, urgency)
   c) Talk-time imbalance (seller talking >70%)
   d) Long monologues (>60s without buyer response)
   e) Questions the seller dodged
   f) Action items the seller should commit to
   [default: a, b, c]

3. DELIVERY?  How does the seller see the coach cards?
   (The plugin scaffolds the browser-tab path end-to-end. Other channels
   are your own integration with that channel's own SDK.)
   a) Browser tab the seller keeps open during the call (scaffolded — uses WebSocket)
   b) Mobile push (you wire up FCM / APNS / your own push provider)
   c) Generic outbound webhook (you forward to whatever channel you want)
   [default: browser tab via WebSocket]

4. LLM?  For real-time inference:
   a) OpenAI gpt-4o-mini (fast, cheap)
   b) Claude Haiku
   c) Local model (Ollama)
   [default: gpt-4o-mini]
```

## Step 2: Architecture (the only one that works for real-time)

```
┌────────────────┐  live transcript chunks   ┌──────────────────┐
│  MeetStream    │ ─────────────────────────>│ Your FastAPI     │
│  bot in meeting│  POST /live (every ~250ms)│ /live endpoint   │
└────────────────┘                            └──────┬───────────┘
                                                     │
                                                     │ debounced batches (every 5s or on end_of_turn)
                                                     ▼
                                              ┌──────────────────┐
                                              │ Signal detector  │
                                              │ (LLM or regex)   │
                                              └──────┬───────────┘
                                                     │
                                                     │ if signal triggered
                                                     ▼
                                              ┌──────────────────┐
                                              │ WebSocket push   │
                                              │ to seller's      │
                                              │ browser tab      │
                                              └──────────────────┘
```

## Step 3: Reference implementation (Python + FastAPI)

`app/main.py`:
```python
import os
from fastapi import FastAPI, Request, WebSocket
from app.meetstream import create_coach_bot
from app.detector import process_chunk, register_seller, push_card

app = FastAPI(title="MeetStream Sales Coach")

@app.post("/calls/start")
async def start_call(meeting_link: str, seller_id: str):
    """Send a bot with live transcription. Tag with seller_id for WS routing."""
    bot_id = create_coach_bot(
        meeting_link=meeting_link,
        callback_url=f"{os.environ['PUBLIC_URL']}/webhook",
        live_transcript_url=f"{os.environ['PUBLIC_URL']}/live",
        custom_attributes={"seller_id": seller_id},
    )
    return {"bot_id": bot_id, "coach_url": f"{os.environ['PUBLIC_URL']}/coach/{seller_id}"}

@app.post("/live")
async def live_chunk(req: Request):
    # ALWAYS 200 fast — webhooks not retried on non-2xx
    chunk = await req.json()
    process_chunk(chunk)  # debounces + triggers LLM detection async
    return {"ok": True}

@app.post("/webhook")
async def webhook(req: Request):
    # Lifecycle events; mainly for bot.error (streaming provider failed)
    # and bot.stopped (cleanup)
    payload = await req.json()
    if payload.get("event") == "bot.error":
        push_card(payload.get("bot_id"), {
            "type": "warning",
            "text": f"Live transcription degraded: {payload.get('message')}",
        })
    return {"ok": True}

@app.websocket("/coach/{seller_id}")
async def coach_ws(ws: WebSocket, seller_id: str):
    """Seller's browser opens this WS; receives coach cards in real time."""
    await ws.accept()
    await register_seller(seller_id, ws)
    try:
        async for _ in ws.iter_text():
            pass  # ignore incoming; this is push-only
    finally:
        await unregister_seller(seller_id, ws)
```

`app/meetstream.py`:
```python
import os, requests

BASE = "https://api.meetstream.ai/api/v1"
HEADERS = {"Authorization": f"Token {os.environ['MEETSTREAM_API_KEY']}",
           "Content-Type": "application/json"}

def create_coach_bot(meeting_link: str, callback_url: str,
                     live_transcript_url: str, custom_attributes: dict) -> str:
    """
    Path B (streaming-only). Lifecycle ends at audio.processed.
    NO transcription.processed event will fire. If you also want a post-call
    transcript, call POST /bots/{bot_id}/transcribe after bot.stopped.
    """
    resp = requests.post(f"{BASE}/bots/create_bot", headers=HEADERS, json={
        "meeting_link": meeting_link,
        "bot_name": "Sales Coach",
        "video_required": False,
        "callback_url": callback_url,
        "live_transcription_required": {"webhook_url": live_transcript_url},
        "custom_attributes": {k: str(v) for k, v in custom_attributes.items()},
        "recording_config": {
            "transcript": {
                # meetstream_streaming: free, no external key, works on stock accounts
                "provider": {"meetstream_streaming": {}}
            },
            "retention": {"type": "timed", "hours": 24},
        },
        "automatic_leave": {
            "waiting_room_timeout": 600,
            "everyone_left_timeout": 600,
            "voice_inactivity_timeout": 600,
            "in_call_recording_timeout": 14400,
            "recording_permission_denied_timeout": 300,
        },
    })
    resp.raise_for_status()
    return resp.json()["bot_id"]
```

`app/detector.py`:
```python
import asyncio, json
from collections import defaultdict
from openai import OpenAI

client = OpenAI()
buffers = defaultdict(list)  # bot_id -> recent chunks
sellers = defaultdict(set)   # seller_id -> set[WebSocket]

SIGNAL_PROMPT = """You are a real-time sales coach. The seller is in a call.
Read the last 60 seconds of the meeting transcript below and tell me:

1. Is there an OBJECTION? (price / timing / authority / need / competitor) → JSON {type: "objection", subtype, suggestion}
2. A BUYING SIGNAL the seller is missing? (budget, decision-maker, urgency mentioned) → JSON {type: "signal", subtype, suggestion}
3. Is the seller MONOLOGUING (>40 words without buyer response)? → JSON {type: "monologue", suggestion: "ask an open-ended question"}

If NONE apply, return: {"type": "none"}

Be concise. JSON only, no prose."""

def process_chunk(chunk: dict):
    """Buffer chunks; on end_of_turn, run detection."""
    bot_id = chunk.get("bot_id")
    buffers[bot_id].append({
        "speaker": chunk.get("speakerName"),
        "text": chunk.get("transcript"),
        "ts": chunk.get("timestamp"),
        "is_final": chunk.get("is_final"),
        "end_of_turn": chunk.get("end_of_turn"),
    })
    # Trigger detection on end of turn (or rolling every N chunks)
    if chunk.get("end_of_turn"):
        asyncio.create_task(detect_and_push(bot_id))

async def detect_and_push(bot_id: str):
    recent = buffers[bot_id][-30:]  # last 30 utterances ~ 60s
    formatted = "\n".join(f"{c['speaker']}: {c['text']}" for c in recent if c['text'])
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SIGNAL_PROMPT},
            {"role": "user", "content": formatted},
        ],
        response_format={"type": "json_object"},
    )
    signal = json.loads(resp.choices[0].message.content)
    if signal.get("type") != "none":
        # Look up seller via custom_attributes (cached on first webhook)
        seller_id = get_seller_id(bot_id)
        await push_card(seller_id, signal)

async def push_card(seller_id: str, card: dict):
    for ws in sellers.get(seller_id, []):
        await ws.send_json(card)

async def register_seller(seller_id: str, ws):
    sellers[seller_id].add(ws)

async def unregister_seller(seller_id: str, ws):
    sellers[seller_id].discard(ws)
```

Minimal seller UI (`coach.html`) — uses safe DOM methods (no `innerHTML`) so LLM-generated card text can't break out and execute as HTML/JS:
```html
<!DOCTYPE html>
<html><head><title>Sales Coach</title>
<style>
  body{font-family:system-ui;padding:20px}
  .card{padding:15px;margin:10px 0;border-left:4px solid #2196F3;background:#f5f5f5}
  .objection{border-color:#f44336}
  .signal{border-color:#4caf50}
  .monologue{border-color:#ff9800}
  .card-title{font-weight:bold;margin:0 0 6px 0}
  .card-body{margin:0}
</style>
</head><body>
<h1>Coach feed</h1><div id="feed"></div>
<script>
// Whitelist of expected card types — never trust the type field for classnames blindly
const ALLOWED_TYPES = new Set(['objection', 'signal', 'monologue', 'warning', 'none']);

const sellerId = new URLSearchParams(location.search).get('seller');
const ws = new WebSocket(`wss://${location.host}/coach/${encodeURIComponent(sellerId)}`);

ws.onmessage = (e) => {
  let c;
  try { c = JSON.parse(e.data); } catch { return; }
  const type = ALLOWED_TYPES.has(c.type) ? c.type : 'signal';

  const card = document.createElement('div');
  card.className = `card ${type}`;

  const title = document.createElement('p');
  title.className = 'card-title';
  // textContent, not innerHTML — LLM output is treated as plain text
  title.textContent = type.toUpperCase() + (c.subtype ? ' — ' + c.subtype : '');
  card.appendChild(title);

  const body = document.createElement('p');
  body.className = 'card-body';
  body.textContent = c.suggestion ?? '';
  card.appendChild(body);

  document.getElementById('feed').prepend(card);
};
</script></body></html>
```

> **Why `textContent` not `innerHTML`:** the card text comes from an LLM, which could output `<script>` tags or HTML entities. Even though *you* control the LLM prompt, defense-in-depth says never trust generated content as HTML. If you ever extend this to render buyer chat messages (untrusted user input) into the same UI, the `innerHTML` version would be a direct XSS hole. Stick with `textContent`, or use [DOMPurify](https://github.com/cure53/DOMPurify) if you genuinely need HTML formatting.

## Step 4: Tell the user

```
✅ Sales coach scaffolded at ./sales-coach/

Architecture: streaming bot → live transcript webhook → LLM signal detection → WebSocket push to seller browser

Next steps:
  1. Set MEETSTREAM_API_KEY, OPENAI_API_KEY, PUBLIC_URL in .env
  2. uvicorn app.main:app --reload --port 3000
  3. ngrok http 3000 → set PUBLIC_URL
  4. Open coach.html?seller=alice in seller's browser
  5. curl -X POST /calls/start with meeting_link + seller_id="alice"
  6. Seller joins meeting; coach cards appear as objections/signals are detected

🎯 No external transcription key needed — uses meetstream_streaming (free on stock accounts).

🔧 Want a post-call transcript too? After bot.stopped, call:
   POST /bots/{bot_id}/transcribe with a post-call provider.
```

## Critical gotchas (live-verified)

- Streaming provider lifecycle ENDS at `audio.processed` — no `transcription.processed`, no `bot.done`. Don't wait for those.
- `bot.error` fires if the streaming provider hits an upstream issue (e.g. AssemblyAI insufficient funds). The bot keeps recording; only live transcription is degraded. Surface this to the seller as a warning card so they know to expect silence.
- Live transcript chunks lack `timestamp` for dedup — fall back to `{bot_id, message}` or skip dedup on lifecycle events.
- `meetstream_streaming` is the only streaming provider that works without external keys. Use it unless the user explicitly needs Deepgram/AssemblyAI streaming.
