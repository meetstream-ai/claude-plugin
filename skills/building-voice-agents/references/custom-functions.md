# Custom functions: tools a hosted agent calls during the meeting

Source: https://docs.meetstream.ai/guides/mia/mia-custom-configurations and the
`agent.custom_functions[]` table in https://docs.meetstream.ai/guides/mia/mia-api-guide .

## Register the tool on the agent (`POST /api/v1/mia` or `PUT /api/v1/mia`)

```json
{ "agent": { "custom_functions": [ {
    "name": "lookup_order",
    "description": "Look up an order's status by its id.",
    "url": "https://tools.example.com/orders/lookup",
    "method": "POST",
    "headers": { "Authorization": "Bearer <CUSTOM_FUNCTION_TOKEN>" },
    "parameters": { "type": "object", "required": ["order_id"],
                    "properties": { "order_id": { "type": "string", "description": "Order id like ORD-1234" } } },
    "timeout_s": 20, "retries": 2,
    "speak_during_execution": true, "speak_during_prompt": "One moment while I pull that up.",
    "response_variables": [ { "name": "latest_order_status", "path": "data.order.status" } ]
} ] } }
```

Rules (the API answers `400` otherwise):
- `name`: lowercase, starts with a letter, `^[a-z][a-z0-9_]{0,63}$`, unique; not `current_time`
  or `weather_now`; no `meetstream_`, `mia_` or `lk_` prefix.
- `description` and `url` are required. `url` must be `https://` on a host that resolves to a
  public IP. On a laptop, expose your tool server with a tunnel (ngrok or cloudflared).
- At most 20 functions. `method` is `POST` (default), `GET`, `PUT`, `PATCH` or `DELETE`.
- `timeout_s` 1 to 120 (default 30), `retries` 0 to 5 (default 2; 5xx and network errors
  are retried with backoff).

## What your endpoint receives

`POST`, `PUT` and `PATCH` (default body):

```json
{ "name": "lookup_order",
  "bot": { "bot_id": "83acdd72-3257-4b06-a2e9-0d879dc571ff", "dynamic_vars": {} },
  "args": { "order_id": "ORD-1234" } }
```

- The tool arguments are in **`args`**, not at the top level.
- `bot.agent_id` and `bot.speaker` (with `include_speaker_details: true`) may also be present.
- `dynamic_vars` holds values from earlier `response_variables`, not `agent_config_params`.
- `"payload_args_only": true` makes the body just the `args` object.
- `GET` and `DELETE` send **no body** unless `payload_args_only` is `true`, so the
  arguments do not reach you. Use `POST` for tools with arguments.

Headers:

| Header | Value |
|---|---|
| `X-Bot-ID` | The bot (meeting) that called. Always sent; use it as the session id |
| `X-Agent-ID` | The agent config id, when available. Do not require it |
| `Content-Type` | `application/json` when there is a body |
| your `headers` | Sent as configured, after `{{variable}}` substitution |

There is **no signature header**. Protect the endpoint with a function-specific secret in
`headers` (for example `Authorization: Bearer <token>`) and check it. Header values are
stored in the agent config and visible to anyone who can read it, so use a narrow token.

The SDKs (1.5.0) parse it for you: `parseCustomFunctionCall(body, headers, {payloadArgsOnly})`
(Node) or `parse_custom_function_call(body, headers, payload_args_only=...)` (Python) return the
name, the bot id (from `X-Bot-ID` first) and the args. Say which shape your function uses; the
parser does not guess it from the body, because the args come from the model. Every field is
unauthenticated until your endpoint checks its own secret.

## What to answer

Return JSON with any 2xx status; the body (capped at `response_cap_chars`, default 15000)
goes to the LLM. A non-2xx body also goes to the LLM so the agent can recover. With
`response_variables`, the value at each `path` becomes `{{name}}` for the rest of the session.

## Minimal endpoint (Python, standard library)

```python
import json, os
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("CUSTOM_FUNCTION_TOKEN", "")

class Tool(BaseHTTPRequestHandler):
    def do_POST(self):
        if TOKEN and self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401); self.end_headers(); return
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        args = body.get("args", body)            # body is args only with payload_args_only
        bot_id = self.headers.get("X-Bot-ID") or body.get("bot", {}).get("bot_id")
        out = json.dumps({"order_id": args.get("order_id"), "status": "shipped"}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), Tool).serve_forever()
```
