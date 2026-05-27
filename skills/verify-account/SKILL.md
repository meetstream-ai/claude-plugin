---
name: verify-account
description: >
  Verify a MeetStream account's configuration before building. Checks API key
  validity, which transcription providers are configured (deepgram / assemblyai
  / sarvam / jigsawstack / meetstream), webhook URL reachability, and surfaces
  any missing provider keys. Use when the user says "verify my MeetStream
  account", "check setup", "which providers do I have", "test API key",
  "diagnose meetstream", or before any other build skill runs.
allowed-tools: Bash, Read, Write
---

# Verify MeetStream Account

Run a comprehensive health check on the user's MeetStream account before scaffolding anything. Catches the most common cause of build failures: missing or misconfigured provider keys.

## Step 0: Make sure there's an API key to verify

If `MEETSTREAM_API_KEY` is unset, **invoke the `getting-started` skill first** — without an account + key, there's nothing to verify. Signup is at https://app.meetstream.ai.

## What to do

1. **Get the API key.** Ask the user, or read it from `MEETSTREAM_API_KEY` env var. Never log it.

2. **Run the verification script.** Write it to a temp file and execute. Capture the report.

3. **Present the report.** Clearly mark each provider as ✅ configured / ❌ not configured / ⚠️ unknown.

4. **Recommend next steps** based on what works.

## The verification script

Write this to `/tmp/meetstream_verify.py` and run it:

```python
#!/usr/bin/env python3
"""MeetStream account verifier. Reports which providers/features are configured."""
import json, os, sys, urllib.request, urllib.error

KEY = os.environ.get("MEETSTREAM_API_KEY") or (sys.argv[1] if len(sys.argv) > 1 else "")
if not KEY:
    print("❌ No API key. Set MEETSTREAM_API_KEY or pass as arg.")
    sys.exit(2)

BASE = "https://api.meetstream.ai/api/v1"
HEADERS = {"Authorization": f"Token {KEY}", "Content-Type": "application/json"}

def req(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    r = urllib.request.Request(url, headers=HEADERS, data=data, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except: body = {}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}

print("=" * 60)
print("MeetStream account verification")
print("=" * 60)

# 1. API key validity
print("\n[1] API key validity")
code, body = req("GET", "/bots")
if code == 200:
    print(f"   ✅ API key valid. {len(body.get('bots',[]))} bots visible on first page.")
elif code in (401, 403):
    print(f"   ❌ API key rejected (HTTP {code}). Get a fresh key at https://app.meetstream.ai/api-keys")
    sys.exit(1)
else:
    print(f"   ⚠ Unexpected: HTTP {code}: {body}")

# 2. Probe each post-call provider by creating a tiny test bot and reading the error message
print("\n[2] Post-call transcription providers")
providers = {
    "deepgram":   {"deepgram": {"model": "nova-3", "language": "en"}},
    "assemblyai": {"assemblyai": {"speech_models": ["universal-2"], "language_code": "en_us",
                                    "speaker_labels": True, "punctuate": True, "format_text": True,
                                    "filter_profanity": False, "redact_pii": False,
                                    "auto_chapters": False, "entity_detection": False}},
    "sarvam":     {"sarvam": {"model": "saaras:v3", "language_code": "en-IN", "mode": "transcribe", "with_diarization": True}},
    "jigsawstack": {"jigsawstack": {"language": "auto", "translate": False, "by_speaker": True}},
    "meetstream": {"meetstream": {"language": "en", "translate": False}},
}

probe_bots = []
for name, provider in providers.items():
    payload = {
        "meeting_link": f"https://meet.google.com/verify-probe-{name}",
        "bot_name": f"verify-{name}",
        "video_required": False,
        "recording_config": {
            "transcript": {"provider": provider},
            "retention": {"type": "timed", "hours": 1},
        },
        "automatic_leave": {
            "waiting_room_timeout": 600, "everyone_left_timeout": 600,
            "voice_inactivity_timeout": 600, "in_call_recording_timeout": 600,
            "recording_permission_denied_timeout": 300,
        },
    }
    code, body = req("POST", "/bots/create_bot", payload)
    if code == 201:
        # Provider config accepted by API. transcript_id presence indicates the provider is set up.
        tid = body.get("transcript_id")
        probe_bots.append(body.get("bot_id"))
        if tid:
            print(f"   ✅ {name:12} configured (transcript_id reserved)")
        else:
            print(f"   ⚠ {name:12} accepted but no transcript_id returned")
    elif code == 400:
        # 400 often indicates config validation issue (could be missing key)
        msg = body.get("message", str(body))[:100]
        print(f"   ❌ {name:12} rejected: {msg}")
    else:
        print(f"   ⚠ {name:12} HTTP {code}: {body}")

# 3. Probe streaming providers (similar — but with live webhook URL)
print("\n[3] Streaming providers")
streaming = {
    "meetstream_streaming": {"meetstream_streaming": {}},
    "meeting_captions":     {"meeting_captions": {}},
}
for name, provider in streaming.items():
    payload = {
        "meeting_link": f"https://meet.google.com/verify-probe-{name}",
        "bot_name": f"verify-{name}",
        "video_required": False,
        "live_transcription_required": {"webhook_url": "https://example.com/probe"},
        "recording_config": {
            "transcript": {"provider": provider},
            "retention": {"type": "timed", "hours": 1},
        },
        "automatic_leave": {
            "waiting_room_timeout": 600, "everyone_left_timeout": 600,
            "voice_inactivity_timeout": 600, "in_call_recording_timeout": 600,
            "recording_permission_denied_timeout": 300,
        },
    }
    code, body = req("POST", "/bots/create_bot", payload)
    if code == 201:
        probe_bots.append(body.get("bot_id"))
        print(f"   ✅ {name:24} configured")
    else:
        msg = body.get("message", str(body))[:100]
        print(f"   ❌ {name:24} HTTP {code}: {msg}")

# 4. Endpoint reachability
print("\n[4] Core endpoints")
for label, method, path in [
    ("GET /bots",               "GET",  "/bots"),
    ("GET /calendar",           "GET",  "/calendar"),
    ("GET /mia (list agents)",  "GET",  "/mia"),
]:
    code, _ = req(method, path)
    status = "✅" if 200 <= code < 300 else f"⚠ {code}"
    print(f"   {status:6} {label}")

# 5. Cleanup probe bots
print("\n[5] Cleanup probe bots")
for bid in probe_bots:
    code, _ = req("DELETE", f"/bots/{bid}/delete")
    print(f"   {'✅' if code == 200 else '⚠ ' + str(code)} deleted {bid}")

print("\n" + "=" * 60)
print("Done. See summary above.")
print("=" * 60)
```

## How to read the report

- ✅ on a provider = it's configured in your account, post-call/streaming bots with that provider will work
- ❌ on a provider = key missing or invalid in MeetStream dashboard. Either add the key at https://app.meetstream.ai → Integrations, or use a different provider
- `meetstream_streaming` and `meeting_captions` should always be ✅ — they don't need external keys

## After the report

Recommend a build strategy based on what's configured:

- **All ✅** → user can pick any provider freely. Recommend `deepgram` (post-call accuracy) or `meetstream_streaming` (live, free)
- **Only `meetstream_streaming` works** → recommend the live-streaming pattern + `/transcribe` fallback with whatever they DO have for post-call
- **No post-call providers, only `meetstream_streaming`** → guide them to add at least one provider key in the dashboard before building the notetaker; otherwise `/transcribe` will fail too

## Safety note

This skill **does** create real bots (1 per provider) against fake meeting links and immediately deletes them. The bots never join any actual meeting. Cleanup is automatic via `DELETE /bots/{id}/delete`. The script will print each deletion so the user can audit.

> The destructive `/delete` is **intentional and explicit** in this verification context — the bots created here have no value. Outside this skill, do NOT auto-call `/delete`.
