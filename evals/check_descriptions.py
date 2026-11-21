"""Check that each skill's frontmatter description carries its must-say lines, and that
the skills and top-level docs follow the content rules.

Some agents (for example Codex) answer from the skill descriptions without opening
SKILL.md, so these facts must be in the description itself.
Content rules (round 5): every skill ends with a "Latest docs" section; no sample-app
scaffolds inside skills; no internal details in voice-agent text.
Three flows (MS-2305, 21 Nov 2026): 1 recording (Bot API, default); 2 agents in meetings on
the user's own stack, recommended first when an agent is asked for (2a bridge server with
both sockets, bot price only; 2b own agent through local_agent and the Agent Kit, with the
warning); 3 managed agent infrastructure (Agents API, MIA: inbuilt keys, then own keys).
They open the core skill, getting-started, README, AGENTS.md and INSTALL_FOR_AGENTS.md in
that order, and the old a/b/c voice-agent order (inbuilt keys as the default) is gone.
Usage: python3 evals/check_descriptions.py [repo_root]   (exit 1 on any miss)
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# skill -> list of (label, regex that must match the description)
MUST = {
    "meetstream": [("version answer, exact two sentences (round 6)", r"Install or update to the current MeetStream plugin\. The MCP server is hosted at https://mcp\.meetstream\.ai/mcp; there is no npm package or server version to install\."),
                   ("version answer: those two sentences only, no qualifiers", r"(only|nothing else).{0,60}(no|without) (added )?qualifier"),
                   ("flow 1: Bot API", r"Bot API"),
                   ("flows in order: Bot API, then own-stack bridge, then hosted Agents API", r"Bot API.{0,400}bridge.{0,300}Agents API"),
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
                           ("flow 2a bridge: both sockets", r"live_audio_required\.websocket_url.{0,160}socket_connection_url\.websocket_url"),
                           ("flow 2a bridge: any models incl. local", r"local"),
                           ("flow 2a bridge: bot price only", r"bot price only")],
    "mia-voice-agents": [("own stack first: bridge server", r"bridge.{0,200}(first|recommended)"),
                         ("bridge: both sockets", r"live_audio_required.{0,80}socket_connection_url"),
                         ("bridge: bot price only", r"bot price only"),
                         ("hosted (flow 3): inbuilt keys first", r"MeetStream's inbuilt keys.{0,80}key_source.{0,20}meetstream"),
                         ("inbuilt providers", r"OpenAI and Deepgram"),
                         ("agent infrastructure price", r"\$0\.25 per hour"),
                         ("not-on fallback", r"not available.{0,160}own (provider )?keys"),
                         ("own keys after inbuilt keys", r"then (the user's )?own (provider )?keys"),
                         ("own agent stated positively (round 6)", r"Yes: your own agent \(Claude Code, Codex, Hermes, OpenClaw.{0,40}\) can be the voice agent's brain through .{0,4}model\.provider: .{0,2}local_agent.{0,4} and the MeetStream Agent Kit"),
                         ("Agent Kit warning", r"Agent Kit.*warning.*(meeting speech|what people say).*computer"),
                         ("computer stays on", r"computer must stay on"),
                         ("hosted bot: only agent_config_id, no bridge sockets", r"only agent_config_id")],
    "getting-started": [("post-call or live first", r"[Ff]irst ask.*after the call.*live"),
                        ("flows in order: Bot API, bridge, Agents API", r"Bot API.{0,300}bridge.{0,300}Agents API")],
}

LATEST_DOCS_LINE = re.compile(r"llms\.txt.*_mcp/server|_mcp/server.*llms\.txt")
SCAFFOLD = re.compile(r"FastAPI\(|Flask\(|express\(\)|app\.listen\(|uvicorn\.run|requirements\.txt|package\.json|Dockerfile|[├└]── [\\w.-]+(/|\\.\\w+)")
INTERNALS = re.compile(r"mia_managed|managed catalog", re.I)
MAX_BLOCK = 90  # longer code blocks are app code, not an API guide
BRIDGE_DOCS = "https://docs.meetstream.ai/guides/websockets/bridge-server-architecture"
STARTER = "https://github.com/meetstream-ai/meetstream-agent"
STALE_ORDER = re.compile(r"\bsetups? [abc]\b|\(only on request\)|inbuilt keys\W{0,4}\(default\)|[Tt]wo ways to integrate")


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
    # The three flows open the core skill, getting-started and the top-level docs, in order:
    # Bot API, then the own-stack bridge, then the hosted Agents API.
    tops = [os.path.join("skills", "meetstream", "SKILL.md"), os.path.join("skills", "getting-started", "SKILL.md"),
            "README.md", "AGENTS.md", "INSTALL_FOR_AGENTS.md"]
    for rel in tops:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            continue
        text = open(fp, encoding="utf-8").read()
        text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        head = "\n".join(text.split("\n")[:60])
        idx = [head.find(k) for k in ("Bot API", "bridge", "Agents API")]
        if min(idx) < 0 or not idx[0] < idx[1] < idx[2]:
            misses += 1
            print(f"MISS {rel}: the first 60 lines do not give the three flows in order (Bot API, bridge, Agents API)")
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
        if "/.git" in base or "/evals" in base:
            continue
        for name in files:
            if name.endswith(".md"):
                fp = os.path.join(base, name)
                for n, line in enumerate(open(fp, encoding="utf-8"), 1):
                    hit = STALE_ORDER.search(line)
                    if hit and not name == "CHANGELOG.md":
                        misses += 1
                        print(f"MISS {os.path.relpath(fp, ROOT)}:{n}: old voice-agent order '{hit.group(0)}'")
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
        if "/.git" in base or "/evals" in base:
            continue
        for name in files:
            if name.endswith((".md", ".json")):
                fp = os.path.join(base, name)
                if re.search(OLD_PACKAGE + r"(?![-\w])", open(fp, encoding="utf-8", errors="ignore").read()):
                    misses += 1
                    print(f"MISS {os.path.relpath(fp, ROOT)}: names the old npm package")
    return misses


def main():
    misses = version_wording_misses() + body_misses() + round6_misses()
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
