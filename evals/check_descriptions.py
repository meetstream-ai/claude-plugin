"""Check that each skill's frontmatter description carries its must-say lines, and that
the skills and top-level docs follow the content rules.

Some agents (for example Codex) answer from the skill descriptions without opening
SKILL.md, so these facts must be in the description itself.
Content rules (round 5): every skill ends with a "Latest docs" section; no sample-app
scaffolds inside skills; no internal details in voice-agent text.
Build tracks (MS-2305, 22 Nov 2026; replace the three flows): 1 Recording bot (1a non-realtime
transcription, post-call; 1b real-time transcription, live), the default; 2 Bridge server (the
user's own stack, local: both sockets, a local tunnel, free local STT / LLM / TTS options or the
harness's own model, bot price only); 3 Agents API infra (MIA, hosted): 3a MeetStream's own
default keys (recommended for "just host it"), 3b bring your own agent infra (LiveKit, COMING
SOON), 3c bring your own keys, 3d the user's coding agent through meetstream setup (COMING SOON,
with the prompt-injection warning and no do-this-now steps). They open the core skill,
getting-started, README, AGENTS.md and INSTALL_FOR_AGENTS.md in that order; the old a/b/c order
and the old flow labels (flow 2a/2b/3, "three flows", own keys as 3b) are gone.
Zoom (Sid, 20 Nov 2026): no file says Zoom needs no setup or that the Zoom app is optional;
bots join through the customer's Zoom app with OBF or ZAK.
Signup gaps (MS-2305, 21 Nov 2026): the first-bot skills give the Zoom app step (OBF or ZAK,
with the Zoom setup link) and admission (waiting_room_timeout, NotAllowed, Denied); voice-agent
recipes by job and the xAI and Google realtime configs; a build-for-your-customers skill;
WhatsApp (Beta) setup and limits; the supported platforms; no undocumented `sendchat`.
Build feedback (MS-2305, 21 Nov 2026, 4 harnesses live): participant-keyed transcript shape;
full status flow (MediaProcessing, Done) and bounded polling; 0x04 frames on Google Meet;
pipeline wake word on by default; commands need InMeeting; remove the bot on exit; the Agent
Kit pairing token is dashboard-only; Cursor and OpenCode through serve --command; inbuilt keys
pipeline-only with own OpenAI key for realtime (Sid, 22 Nov) and mia_managed; no tunnels
or long-running processes unless asked; OpenCode and Cursor CLI setup.
Usage: python3 evals/check_descriptions.py [repo_root]   (exit 1 on any miss)
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def _generated(base):
    """True for plugins/ (store builds generated from skills/ by scripts/build_stores.py, and the
    separate Hermes plugin). The source files are checked once, at the repo root."""
    return os.path.relpath(base, ROOT).split(os.sep)[0] == "plugins"

# skill -> list of (label, regex that must match the description)
MUST = {
    "meetstream": [("version answer, exact two sentences (round 6)", r"Install or update to the current MeetStream plugin\. The MCP server is hosted at https://mcp\.meetstream\.ai/mcp; there is no npm package or server version to install\."),
                   ("version answer: those two sentences only, no qualifiers", r"(only|nothing else).{0,60}(no|without) (added )?qualifier"),
                   ("track 1: Recording bot, 1a post-call, 1b real-time", r"Recording bot.{0,200}1a.{0,120}1b"),
                   ("tracks in order: Recording bot, Bridge server, Agents API", r"Recording bot.{0,400}Bridge server.{0,400}Agents API"),
                   ("track 3a default keys for just host it", r"3a.{0,160}(just host it|default)"),
                   ("track 3c own keys", r"3c.{0,40}(own keys|bring your own keys)"),
                   ("3b LiveKit coming soon", r"3b.{0,60}LiveKit.{0,60}COMING SOON|3b.{0,60}LiveKit.{0,60}coming soon"),
                   ("3d local agent coming soon", r"3d.{0,160}(COMING SOON|coming soon)"),
                   ("unspecified agent: ask own stack or hosted", r"own stack.{0,120}host"),
                   ("post-call or live question", r"after the (call|meeting).{0,80}live|post-call.{0,40}live")],
    "troubleshooting": [("billing URL", r"https://app\.meetstream\.ai/billing"), ("no retry loop", r"never retry"),
                        ("422 transcript is final", r"422.{0,120}(final|do not retry|don.t retry)")],
    "join-meeting": [("billing URL", r"https://app\.meetstream\.ai/billing"), ("no retry loop", r"never retry"),
                     ("raise-hand REST", r"POST /api/v1/bots/\{bot_id\}/send_command.*raise_hand"),
                     ("connect step: Codex", r"codex mcp login meetstream"),
                     ("connect step: Claude Code", r"/mcp"),
                     ("connect step: Cursor", r"Settings.{0,4}MCP"),
                     ("REST create_bot fallback", r"POST /api/v1/bots/create_bot.*meeting_link"),
                     ("never say it cannot record", r"[Nn]ever say MeetStream can.?t record"),
                     ("one-off link needs no calendar integration (round 6)", r"(no|never|not).{0,40}calendar integration")],
    "realtime-streaming": [("raise-hand REST", r"POST /api/v1/bots/\{bot_id\}/send_command.*raise_hand"),
                           ("live transcripts by HTTPS POST (round 6)", r"HTTPS POST.{0,60}live_transcription_required\.webhook_url"),
                           ("server forwards to the browser (round 6)", r"forward.{0,80}browser"),
                           ("track 2 bridge: both sockets", r"live_audio_required\.websocket_url.{0,160}socket_connection_url\.websocket_url"),
                           ("track 2 bridge: named as track 2", r"[Tt]rack 2"),
                           ("track 2 bridge: local tunnel", r"tunnel"),
                           ("track 2 bridge: free local models", r"[Ww]hisper.{0,200}Ollama.{0,200}Piper"),
                           ("track 2 bridge: bot price only", r"bot price only")],
    "mia-voice-agents": [("track 2 bridge: both sockets", r"live_audio_required.{0,80}socket_connection_url"),
                         ("track 2 bridge: tunnel and free local models", r"tunnel.{0,200}([Ww]hisper|Parakeet).{0,200}(Ollama|LM Studio).{0,200}(Piper|Kokoro)|([Ww]hisper|Parakeet).{0,200}(Ollama|LM Studio).{0,200}(Piper|Kokoro).{0,200}tunnel"),
                         ("track 2 bridge: harness model as the LLM", r"harness"),
                         ("track 2 bridge: bot price only", r"bot price only"),
                         ("track 3a: default keys, key_source meetstream", r"3a.{0,120}key_source.{0,20}meetstream"),
                         ("track 3a recommended for just host it", r"just host it"),
                         ("inbuilt providers per mode", r"pipeline mode only.{0,80}Deepgram.{0,80}OpenAI"),
                         ("agent infrastructure price", r"\$0\.25 per hour"),
                         ("refused section falls back to 3c", r"(refused|not available).{0,80}3c"),
                         ("3b LiveKit coming soon", r"3b.{0,60}LiveKit.{0,60}(COMING SOON|coming soon)"),
                         ("3d local agent coming soon", r"3d.{0,200}(COMING SOON|coming soon)"),
                         ("3d warning: prompt injection", r"prompt injection"),
                         ("hosted bot: only agent_config_id, no bridge sockets", r"only agent_config_id")],
    "getting-started": [("post-call or live first", r"[Ff]irst ask.*after the call.*live"),
                        ("tracks in order: Recording bot, Bridge server, Agents API", r"Recording bot.{0,300}Bridge server.{0,300}Agents API")],
}

LATEST_DOCS_LINE = re.compile(r"llms\.txt.*_mcp/server|_mcp/server.*llms\.txt")
SCAFFOLD = re.compile(r"FastAPI\(|Flask\(|express\(\)|app\.listen\(|uvicorn\.run|requirements\.txt|package\.json|Dockerfile|[├└]── [\\w.-]+(/|\\.\\w+)")
INTERNALS = re.compile(r"managed catalog|\"rates\"|managed_agent", re.I)  # mia_managed is read by agents (build feedback, 21 Nov); its prices are never stated
MAX_BLOCK = 90  # longer code blocks are app code, not an API guide
BRIDGE_DOCS = "https://docs.meetstream.ai/guides/websockets/bridge-server-architecture"
STARTER = "https://github.com/meetstream-ai/meetstream-agent"
# Sid, 20 Nov 2026: Zoom bots join through the customer's Zoom app with OBF or ZAK; never say Zoom needs no setup.
ZOOM_NO_SETUP = re.compile(r"[Zz]oom needs (NO|no) setup|needs no setup|\(no setup\)|no-setup|[Zz]oom app is \*{0,2}optional|own Zoom app \(optional\)|no Zoom (Marketplace )?app, no|none needs setup|zoom\.variant")
STALE_ORDER = re.compile(r"\bsetups? [abc]\b|\(only on request\)|inbuilt keys\W{0,4}\(default\)|[Tt]wo ways to integrate"
                         r"|\b[Ff]lows? (1|2a|2b|3)\b|[Tt]hree flows|\b3b\W{1,6}(the user's |their |your )?own (provider )?keys")
# Build tracks: 3b (LiveKit) and 3d (local agent) are COMING SOON, so no file gives do-this-now steps for them.
COMING_SOON_STEPS = re.compile(r"(uv tool|pipx) install meetstream-agent-kit|serve --command|Integrations > Models > Local agent")
# meetstream CLI wrappers (MS-2371, 23 Nov 2026): the Go CLI replaces the Node CLI 0.x and the Python Agent Kit.
# No file names the Agent Kit, its pairing token, a Bridge URL or serve --tunnel, the wrong PyPI names, or old CLI commands.
OLD_KIT = re.compile(r"meetstream-agent-kit|Agent Kit|[Pp]airing token|Bridge URL|serve --tunnel"
                     r"|pipx install meetstream(?![-\w])|uvx meetstream(?![-\w])|auth set-key|meetstream bot create")
CLI_REF = os.path.join("skills", "meetstream", "references", "meetstream-cli.md")
# Skills that run commands for the user give the CLI install step and the agent flags.
CLI_SKILLS = ("meetstream", "cli-workflows", "getting-started", "join-meeting", "verify-account", "test-bot", "calendar-automation", "mia-voice-agents")


def cli_misses():
    misses = 0
    ref = os.path.join(ROOT, CLI_REF)
    if not os.path.exists(ref):
        print(f"MISS {CLI_REF}: missing (copy SKILL.md from github.com/meetstream-ai/cli)"); misses += 1
    else:
        t = open(ref, encoding="utf-8").read()
        for label, pat in (("copied-from note", r"\A<!-- Copied verbatim from SKILL\.md in github\.com/meetstream-ai/cli"),
                           ("agent flags", r"--json --no-input"), ("exit codes", r"`3` not ready")):
            if not re.search(pat, t):
                print(f"MISS {CLI_REF}: {label}"); misses += 1
    for skill in CLI_SKILLS:
        t = open(os.path.join(ROOT, "skills", skill, "SKILL.md"), encoding="utf-8").read()
        for label, pat in (("no-install CLI run", r"npx -y @meetstream/cli"), ("agent flags", r"--json --no-input")):
            if not re.search(pat, t):
                print(f"MISS {skill}: CLI {label}"); misses += 1
    for root, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in (".git", "evals", "node_modules") and not _generated(os.path.join(root, d))]
        for name in files:
            if not name.endswith(".md") or name == "CHANGELOG.md":
                continue
            fp = os.path.join(root, name)
            for i, line in enumerate(open(fp, encoding="utf-8"), 1):
                m = OLD_KIT.search(line)
                if m:
                    print(f"MISS {os.path.relpath(fp, ROOT)}:{i}: old CLI or Agent Kit text {m.group(0)!r}"); misses += 1
    return misses


def body_misses():
    misses = 0
    skills_dir = os.path.join(ROOT, "skills")
    for skill in sorted(os.listdir(skills_dir)):
        sdir = os.path.join(skills_dir, skill)
        path = os.path.join(sdir, "SKILL.md")
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        if len(description(path)) > 1024:
            misses += 1
            print(f"MISS {skill}: description is {len(description(path))} characters (max 1024 for Codex and the Agent Skills spec)")
        # Latest docs: the last H2, with 2 to 5 docs URLs and the llms.txt / .md / docs MCP line.
        h2 = [m.start() for m in re.finditer(r"^## ", text, re.M)]
        last = text[h2[-1]:] if h2 else ""
        if not last.startswith("## Latest docs"):
            misses += 1
            print(f"MISS {skill}: does not end with a '## Latest docs' section")
        else:
            urls = {u for u in re.findall(r"https://docs\.meetstream\.ai/[^\s)>`\]]+", last)
                    if "llms.txt" not in u and "_mcp" not in u}
            if not 2 <= len(urls) <= 5:
                misses += 1
                print(f"MISS {skill}: Latest docs has {len(urls)} doc URLs (want 2 to 5)")
            if not LATEST_DOCS_LINE.search(last) or "`.md`" not in last:
                misses += 1
                print(f"MISS {skill}: Latest docs lacks the .md / llms.txt / docs MCP line")
        # No sample-app scaffolds in any file of the skill.
        for root, _, files in os.walk(sdir):
            for name in files:
                fp = os.path.join(root, name)
                rel = os.path.relpath(fp, ROOT)
                if name.startswith("code-patterns"):
                    misses += 1
                    print(f"MISS {rel}: app code-pattern file inside a skill")
                    continue
                body = open(fp, encoding="utf-8").read()
                hit = SCAFFOLD.search(body) or re.search(r"^#{1,4} .*\b[Ss]caffold\b.*$", body, re.M)
                if hit:
                    misses += 1
                    print(f"MISS {rel}: app scaffold marker '{hit.group(0)}'")
                for m in re.finditer(r"^\s*```[^\n]*\n(.*?)^\s*```", body, re.S | re.M):
                    n = m.group(1).count("\n")
                    if n > MAX_BLOCK:
                        misses += 1
                        print(f"MISS {rel}: code block of {n} lines (max {MAX_BLOCK})")
                hit = INTERNALS.search(body)
                if hit:
                    misses += 1
                    print(f"MISS {rel}: internal detail '{hit.group(0)}'")
    # The core skill says the docs win when they and the skill differ.
    core = open(os.path.join(skills_dir, "meetstream", "SKILL.md"), encoding="utf-8").read()
    if not re.search(r"docs are the source of truth", core):
        misses += 1
        print("MISS meetstream: does not say the docs are the source of truth when they differ")
    # The build tracks open the core skill, getting-started and the top-level docs, in order:
    # Recording bot, then the Bridge server, then the hosted Agents API.
    tops = [os.path.join("skills", "meetstream", "SKILL.md"), os.path.join("skills", "getting-started", "SKILL.md"),
            "README.md", "AGENTS.md", "INSTALL_FOR_AGENTS.md"]
    for rel in tops:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            continue
        text = open(fp, encoding="utf-8").read()
        text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        head = "\n".join(text.split("\n")[:60])
        idx = [head.find(k) for k in ("Recording bot", "Bridge server", "Agents API")]
        if min(idx) < 0 or not idx[0] < idx[1] < idx[2]:
            misses += 1
            print(f"MISS {rel}: the first 60 lines do not give the build tracks in order (Recording bot, Bridge server, Agents API)")
        for k in ("3a", "3b", "3c", "3d", "COMING SOON"):
            if k not in head:
                misses += 1
                print(f"MISS {rel}: the first 60 lines do not name {k}")
    # Every file that routes agents links the bridge docs; the bridge recipe owners also link the starter.
    for rel in tops + [os.path.join("skills", s, "SKILL.md") for s in ("mia-voice-agents", "realtime-streaming", "troubleshooting")]:
        fp = os.path.join(ROOT, rel)
        if os.path.exists(fp) and BRIDGE_DOCS not in open(fp, encoding="utf-8").read():
            misses += 1
            print(f"MISS {rel}: no link to the bridge server docs ({BRIDGE_DOCS})")
    for rel in [os.path.join("skills", s, "SKILL.md") for s in ("meetstream", "mia-voice-agents", "realtime-streaming")]:
        if STARTER not in open(os.path.join(ROOT, rel), encoding="utf-8").read():
            misses += 1
            print(f"MISS {rel}: no link to the bridge starter repo ({STARTER})")
    # realtime-streaming owns the bridge recipe: both sockets and the control commands from the public docs.
    rt = open(os.path.join(skills_dir, "realtime-streaming", "SKILL.md"), encoding="utf-8").read()
    for cmd in ("sendaudio", "sendmsg", "interrupt", "resume_audio", "sendimg"):
        if f'"command": "{cmd}"' not in rt and f"`{cmd}`" not in rt:
            misses += 1
            print(f"MISS realtime-streaming: bridge recipe does not give the control command {cmd}")
    # The old voice-agent order (a/b/c with inbuilt keys as the default, own agent only on request) is gone.
    for base, _, files in os.walk(ROOT):
        if "/.git" in base or "/evals" in base or _generated(base):
            continue
        for name in files:
            if name.endswith(".md"):
                fp = os.path.join(base, name)
                lines = open(fp, encoding="utf-8").read().split("\n")
                for n, line in enumerate(lines, 1):
                    near = " ".join((line + " " + (lines[n] if n < len(lines) else "")).split())  # wrapped lines
                    hit = STALE_ORDER.search(line)
                    if hit and not name == "CHANGELOG.md":
                        misses += 1
                        print(f"MISS {os.path.relpath(fp, ROOT)}:{n}: old voice-agent order '{hit.group(0)}'")
                    hit = COMING_SOON_STEPS.search(line)
                    if hit and not name == "CHANGELOG.md":
                        misses += 1
                        print(f"MISS {os.path.relpath(fp, ROOT)}:{n}: do-this-now step for a coming-soon track '{hit.group(0)}'")
                    if re.search(r"LiveKit", line) and not re.search(r"coming soon", near, re.I) and not name == "CHANGELOG.md":
                        misses += 1
                        print(f"MISS {os.path.relpath(fp, ROOT)}:{n}: LiveKit named without 'coming soon'")
                    hit = ZOOM_NO_SETUP.search(line)
                    if hit and not name == "CHANGELOG.md" and "Never" not in line and "Do not tell" not in line:
                        misses += 1
                        print(f"MISS {os.path.relpath(fp, ROOT)}:{n}: Zoom no-setup claim '{hit.group(0)}'")
    return misses


def description(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ""
    fm = m.group(1)
    d = re.search(r"^description:\s*(>-?|\|-?)?\s*\n?(.*?)(?=^\S[^\n]*:|\Z)", fm, re.S | re.M)
    return " ".join((d.group(2) if d else "").split())


# Words an agent paraphrases back to the user as version-stability advice. They must not
# appear in any description, nor on any line of a skill body that talks about versions.
FORBIDDEN = re.compile(r"\b(stable|unstable|break|breaks|breaking|broken|pin|pinned|pinning|downgrade|downgrading)\b|can.?t promise|always safe", re.I)


def version_wording_misses():
    misses = 0
    for skill in sorted(os.listdir(os.path.join(ROOT, "skills"))):
        path = os.path.join(ROOT, "skills", skill, "SKILL.md")
        if not os.path.exists(path):
            continue
        hit = FORBIDDEN.search(description(path))
        if hit:
            misses += 1
            print(f"MISS {skill}: description says '{hit.group(0)}'")
        for n, line in enumerate(open(path, encoding="utf-8"), 1):
            if re.search(r"version", line, re.I) and FORBIDDEN.search(line):
                misses += 1
                print(f"MISS {skill}:{n}: version line says '{FORBIDDEN.search(line).group(0)}'")
    return misses


EARLY = {"join-meeting": r"POST /api/v1/bots/\{bot_id\}/send_command.{0,40}raise_hand",
         "realtime-streaming": r"POST /api/v1/bots/\{bot_id\}/send_command.{0,40}raise_hand"}
OLD_PACKAGE = "@meetstream/" + "mcp"  # the old npm server; agents cite it as current if any file names it


def round6_misses():
    misses = 0
    for skill, pattern in EARLY.items():
        head = description(os.path.join(ROOT, "skills", skill, "SKILL.md"))[:300]
        ok = re.search(pattern, head) is not None
        misses += not ok
        print(f"{'ok  ' if ok else 'MISS'} {skill}: raise-hand REST call in the first 300 characters")
    ver = MUST["meetstream"][0][1]
    for rel in ("skills/meetstream/SKILL.md", "skills/getting-started/SKILL.md"):
        body = " ".join(open(os.path.join(ROOT, rel), encoding="utf-8").read().split())
        ok = re.search(ver, body) is not None
        misses += not ok
        print(f"{'ok  ' if ok else 'MISS'} {rel}: body gives the exact two version sentences")
    own = description(os.path.join(ROOT, "skills", "mia-voice-agents", "SKILL.md"))
    if re.search(r"[Nn]ot directly|needs? an API integration", own):
        misses += 1
        print("MISS mia-voice-agents: description hedges on the own agent")
    for base, _, files in os.walk(ROOT):
        if "/.git" in base or "/evals" in base or _generated(base):
            continue
        for name in files:
            if name.endswith((".md", ".json")):
                fp = os.path.join(base, name)
                if re.search(OLD_PACKAGE + r"(?![-\w])", open(fp, encoding="utf-8", errors="ignore").read()):
                    misses += 1
                    print(f"MISS {os.path.relpath(fp, ROOT)}: names the old npm package")
    return misses


def read_skill(name):
    fp = os.path.join(ROOT, "skills", name, "SKILL.md")
    return open(fp, encoding="utf-8").read() if os.path.exists(fp) else ""


# skill -> list of (label, regex that must match the SKILL.md body)
SIGNUP_BODY = {
    "notetaker": [("Zoom app step: OBF or ZAK", r"\bOBF\b.{0,200}\bZAK\b|\bZAK\b.{0,200}\bOBF\b"),
                  ("Zoom setup link", r"zoom-marketplace-app-setup|zoom-authenticated-bots"),
                  ("admission: waiting_room_timeout", r"waiting_room_timeout"),
                  ("admission: NotAllowed and Denied", r"NotAllowed.{0,600}Denied|Denied.{0,600}NotAllowed"),
                  ("transcript language is set, not fixed to en", r"languages-and-translation"),
                  ("invitee emails: calendar_email", r"calendar_email"),
                  ("calendar auto-join next step", r"calendar-automation")],
    "getting-started": [("Zoom app step: OBF or ZAK", r"\bOBF\b.{0,200}\bZAK\b|\bZAK\b.{0,200}\bOBF\b"),
                        ("Zoom setup link", r"zoom-marketplace-app-setup|zoom-authenticated-bots"),
                        ("admission: waiting_room_timeout", r"waiting_room_timeout"),
                        ("admission: NotAllowed and Denied", r"NotAllowed.{0,600}Denied|Denied.{0,600}NotAllowed"),
                        ("supported platforms, others rejected", r"Webex"),
                        ("other bot APIs: migration note", r"MeetingBaaS|Attendee")],
    "join-meeting": [("Zoom app step: OBF or ZAK", r"\bOBF\b.{0,200}\bZAK\b|\bZAK\b.{0,200}\bOBF\b"),
                     ("Zoom setup link", r"zoom-marketplace-app-setup|zoom-authenticated-bots"),
                     ("admission: waiting_room_timeout", r"waiting_room_timeout"),
                     ("supported platforms, others rejected", r"Webex"),
                     ("WhatsApp (Beta)", r"WhatsApp.{0,40}Beta")],
    "troubleshooting": [("admission: waiting_room_timeout", r"waiting_room_timeout"),
                        ("admission: NotAllowed and Denied", r"NotAllowed.{0,600}Denied|Denied.{0,600}NotAllowed"),
                        ("admission fix: signed-in bot", r"signed-in")],
    "mia-voice-agents": [("recipes by job", r"## Recipes"),
                         ("recipe: wake word or name", r"speak_only_when_asked"),
                         ("recipe: interviewer, wake word off", r"\"enabled\": false"),
                         ("realtime xAI (Grok) config", r"\"provider\": \"xai\""),
                         ("realtime Google (Gemini) config", r"\"provider\": \"google\""),
                         ("other languages", r"\"language\": \"(ru|es|de|pt|multi)\"")],
    "platform-setup": [("WhatsApp pairing step", r"Integrations > WhatsApp"),
                       ("WhatsApp limits: deepgram only", r"WhatsApp.{0,800}deepgram")],
    "for-your-customers": [("tenant tag", r"custom_attributes"), ("storage per customer", r"storage_id"),
                           ("calendar per end user", r"create_calendar"), ("rate limit", r"429.{0,200}Retry-After"),
                           ("per-speaker audio", r"audio_separate_streams")],
    "migrate-from-recall": [("other bot APIs", r"MeetingBaaS.{0,80}Attendee|Attendee.{0,80}MeetingBaaS")],
}
SIGNUP_DESC = {
    "for-your-customers": [("multi-tenant trigger", r"customers"), ("tenant tag", r"custom_attributes")],
    "mia-voice-agents": [("Grok routes to xAI", r"Grok.{0,60}xai|xAI")],
}


def signup_misses():
    misses = 0
    for skill, checks in SIGNUP_BODY.items():
        body = read_skill(skill)
        for label, pattern in checks:
            ok = bool(body) and re.search(pattern, body, re.S) is not None
            misses += not ok
            print(f"{'ok  ' if ok else 'MISS'} {skill} body: {label}")
    for skill, checks in SIGNUP_DESC.items():
        fp = os.path.join(ROOT, "skills", skill, "SKILL.md")
        desc = description(fp) if os.path.exists(fp) else ""
        for label, pattern in checks:
            ok = re.search(pattern, desc, re.S) is not None
            misses += not ok
            print(f"{'ok  ' if ok else 'MISS'} {skill} description: {label}")
    # `sendchat` is not a documented control command.
    for base, _, files in os.walk(os.path.join(ROOT, "skills")):
        for name in files:
            fp = os.path.join(base, name)
            if "sendchat" in open(fp, encoding="utf-8").read():
                misses += 1
                print(f"MISS {os.path.relpath(fp, ROOT)}: names the undocumented sendchat command")
    return misses


PER_MODE = r"Inbuilt keys work in pipeline mode only: Deepgram \(speech-to-text\) and OpenAI \(LLM and voice\)\. Realtime\s+mode runs on OpenAI and needs your own OpenAI key\. Any other provider: bring your own key\."
OLD_PER_MODE = re.compile(r"Realtime: OpenAI only")
BUILD_BODY = {
    "notetaker": [("transcript: participant.name", r"participant\.name"), ("transcript: words[].text", r"words\[\]\.text"),
                  ("poll until Done", r"MediaProcessing.{0,200}Done"), ("remove the bot on exit", r"remove_bot")],
    "meeting-brief": [("transcript: participant.name", r"participant\.name"), ("transcript: words[].text", r"words\[\]\.text")],
    "meetstream": [("transcript: participant-keyed default", r"participant\.name.{0,200}words\[\]\.text"),
                   ("list bots: limit 50", r"limit.{0,40}50"), ("inbuilt keys per mode", PER_MODE),
                   ("no tunnels unless asked", r"[Tt]unnel.{0,200}(unless|only when) the user"),
                   ("MCP tools for real bot data", r"get_bot_detail")],
    "join-meeting": [("full status flow", r"MediaProcessing.{0,300}Done"), ("commands need InMeeting (503)", r"503"),
                     ("list bots filters", r"status=|custom_attr")],
    "realtime-streaming": [("0x04 on Google Meet", r"Google Meet.{0,200}0x04|0x04.{0,200}Google Meet"),
                           ("0x04 header offset 6", r"offset 6|\[1:5\]"), ("NoSpeaker echo", r"NoSpeaker"),
                           ("secret path token", r"(secret|random).{0,40}token"), ("remove the bot on exit", r"remove_bot"),
                           ("no tunnels unless asked", r"[Tt]unnel.{0,200}(unless|only when) the user"),
                           ("track 2: ngrok and cloudflared", r"ngrok.{0,80}cloudflared|cloudflared.{0,80}ngrok"),
                           ("track 2 STT options", r"whisper\.cpp.{0,300}faster-whisper.{0,300}Parakeet.{0,300}parakeet-mlx.{0,300}Vosk.{0,300}Moonshine"),
                           ("track 2 LLM options", r"Ollama.{0,100}LM Studio.{0,100}llama\.cpp.{0,300}harness"),
                           ("track 2 TTS options", r"Piper.{0,100}Kokoro.{0,100}Chatterbox.{0,100}`say`"),
                           ("track 2 license line", r"[Ff]ree to run locally; check each model's license before commercial use")],
    "mia-voice-agents": [("inbuilt keys per mode", PER_MODE), ("read mia_managed", r"mia_managed"),
                         ("wake word on by default in fastest path", r"\"wake_word\": \{\"enabled\": false\}"),
                         ("never probe endpoints", r"[Nn]ever (probe|call) undocumented"),
                         ("3d: no do-this-now steps", r"(no|never give).{0,40}(setup|do-this-now|\"do this now\") steps"),
                         ("commands need InMeeting", r"InMeeting")],
    "getting-started": [("inbuilt keys per mode", PER_MODE), ("when MCP tools help", r"get_transcript.{0,200}(real|actual)")],
    "troubleshooting": [("silent agent: default wake word", r"wake word.{0,80}(on by default|default)")],
}
STALE_SHAPE = re.compile(r"text field is `transcript`|text is (in )?`transcript`, not `text`|always `0x01`|\(Google Meet, Teams\) is 48 kHz")


def build_misses():
    misses = 0
    for skill, checks in BUILD_BODY.items():
        body = read_skill(skill)
        for label, pattern in checks:
            ok = re.search(pattern, body, re.S) is not None
            misses += not ok
            print(f"{'ok  ' if ok else 'MISS'} {skill} body: {label}")
    for base, _, files in os.walk(os.path.join(ROOT, "skills")):
        for name in files:
            fp = os.path.join(base, name)
            for n, line in enumerate(open(fp, encoding="utf-8"), 1):
                hit = STALE_SHAPE.search(line)
                if hit:
                    misses += 1
                    print(f"MISS {os.path.relpath(fp, ROOT)}:{n}: stale shape '{hit.group(0)}'")
    for base, _, files in os.walk(ROOT):
        if "/.git" in base or "/evals" in base or _generated(base):
            continue
        for name in files:
            if name.endswith(".md") and name != "CHANGELOG.md":
                fp = os.path.join(base, name)
                if OLD_PER_MODE.search(open(fp, encoding="utf-8").read()):
                    misses += 1
                    print(f"MISS {os.path.relpath(fp, ROOT)}: old realtime inbuilt-keys wording")
    for rel, pattern in (("INSTALL_FOR_AGENTS.md", r"OpenCode"), ("README.md", r"OpenCode"), ("setup", r"opencode\)"),
                         ("INSTALL_FOR_AGENTS.md", r"cursor-agent"), ("INSTALL_FOR_AGENTS.md", r"OPENCODE_DISABLE_CLAUDE_CODE")):
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            continue  # the Cursor repo has no setup script or INSTALL_FOR_AGENTS.md
        ok = re.search(pattern, open(fp, encoding="utf-8").read()) is not None
        misses += not ok
        print(f"{'ok  ' if ok else 'MISS'} {rel}: {pattern}")
    return misses


# MCP 0.6.0 (MS-2305): with the MCP connected, skills create and check agents with the MCP tools.
MCP_BODY = {
    "mia-voice-agents": [("list_agents first", r"list_agents"), ("create_agent", r"create_agent"),
                         ("check_local_agent", r"check_local_agent"), ("take_screenshot", r"take_screenshot"),
                         ("system_prompt required", r"system_prompt.{0,40}required"),
                         ("REST fallback with no MCP", r"no MCP.{0,200}POST /api/v1/mia|POST /api/v1/mia.{0,200}no MCP")],
    "meetstream": [("list_agents", r"list_agents"), ("create_agent", r"create_agent"), ("take_screenshot", r"take_screenshot")],
    "getting-started": [("list_agents", r"list_agents"), ("create_agent", r"create_agent")],
    "troubleshooting": [("check_local_agent", r"check_local_agent"), ("missing system_prompt 400", r"Missing model\.system_prompt")],
}
MCP_DESC = {"mia-voice-agents": [("MCP: list_agents then create_agent", r"list_agents.{0,80}create_agent")]}
STALE_MCP = re.compile(r"[Aa]gent configs are REST-only|[Tt]here is no MCP tool|REST only, not MCP tools|MIA agent configs, calendar connection")


def mcp_misses():
    misses = 0
    for skill, checks in MCP_BODY.items():
        body = read_skill(skill)
        for label, pattern in checks:
            ok = re.search(pattern, body, re.S) is not None
            misses += not ok
            print(f"{'ok  ' if ok else 'MISS'} {skill} body: {label}")
    for skill, checks in MCP_DESC.items():
        desc = description(os.path.join(ROOT, "skills", skill, "SKILL.md"))
        for label, pattern in checks:
            ok = re.search(pattern, desc, re.S) is not None
            misses += not ok
            print(f"{'ok  ' if ok else 'MISS'} {skill}: {label}")
    for base, _, files in os.walk(ROOT):
        if "/.git" in base or "/evals" in base or _generated(base):
            continue
        for name in files:
            if name.endswith(".md") and name != "CHANGELOG.md":
                fp = os.path.join(base, name)
                for n, line in enumerate(open(fp, encoding="utf-8"), 1):
                    hit = STALE_MCP.search(line)
                    if hit:
                        misses += 1
                        print(f"MISS {os.path.relpath(fp, ROOT)}:{n}: stale MCP wording '{hit.group(0)}'")
    return misses


def main():
    misses = version_wording_misses() + body_misses() + round6_misses() + signup_misses() + build_misses() + mcp_misses() + cli_misses()
    for skill, checks in MUST.items():
        desc = description(os.path.join(ROOT, "skills", skill, "SKILL.md"))
        for label, pattern in checks:
            ok = re.search(pattern, desc, re.S) is not None
            misses += not ok
            print(f"{'ok  ' if ok else 'MISS'} {skill}: {label}")
    print(f"{misses} missing")
    return 1 if misses else 0


if __name__ == "__main__":
    sys.exit(main())
