"""Check that each skill's frontmatter description carries its must-say lines, and that
the skills and top-level docs follow the content rules.

Some agents (for example Codex) answer from the skill descriptions without opening
SKILL.md, so these facts must be in the description itself.
Content rules (round 5): every skill ends with a "Latest docs" section; no sample-app
scaffolds inside skills; the two ways to integrate open the core skill, getting-started,
README, AGENTS.md and INSTALL_FOR_AGENTS.md; no internal details in voice-agent text.
Usage: python3 evals/check_descriptions.py [repo_root]   (exit 1 on any miss)
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# skill -> list of (label, regex that must match the description)
MUST = {
    "meetstream": [("two paths: Bot API", r"Bot API"), ("two paths: Agents API on request", r"Agents API.{0,200}(only|on request|when the user asks)"),
                   ("post-call or live question", r"after the (call|meeting).{0,80}live|post-call.{0,40}live")],
    "troubleshooting": [("billing URL", r"https://app\.meetstream\.ai/billing"), ("no retry loop", r"never retry"),
                        ("422 transcript is final", r"422.{0,120}(final|do not retry|don.t retry)")],
    "join-meeting": [("billing URL", r"https://app\.meetstream\.ai/billing"), ("no retry loop", r"never retry"),
                     ("raise-hand REST", r"POST /api/v1/bots/\{bot_id\}/send_command.*raise_hand"),
                     ("connect step: Codex", r"codex mcp login meetstream"),
                     ("connect step: Claude Code", r"/mcp"),
                     ("connect step: Cursor", r"Settings.{0,4}MCP"),
                     ("REST create_bot fallback", r"POST /api/v1/bots/create_bot.*meeting_link"),
                     ("never say it cannot record", r"[Nn]ever say MeetStream can.?t record")],
    "realtime-streaming": [("raise-hand REST", r"POST /api/v1/bots/\{bot_id\}/send_command.*raise_hand")],
    "mia-voice-agents": [("inbuilt keys first", r"[Dd]efault.{0,40}MeetStream's inbuilt keys.*key_source.*meetstream"),
                         ("inbuilt providers", r"OpenAI and Deepgram"),
                         ("agent infrastructure price", r"\$0\.25 per hour"),
                         ("not-on fallback", r"not available.{0,160}own (provider )?keys"),
                         ("own keys second", r"then the user's own (provider )?keys"),
                         ("Agent Kit warning", r"Agent Kit.*warning.*(meeting speech|what people say).*computer"),
                         ("computer stays on", r"computer must stay on"),
                         ("managed and own keys are the recommended defaults", r"(managed|own).{0,120}recommended|recommended.{0,120}(managed|own)")],
    "getting-started": [("post-call or live first", r"[Ff]irst ask.*after the call.*live"),
                        ("two paths", r"Bot API.{0,300}Agents API")],
}

LATEST_DOCS_LINE = re.compile(r"llms\.txt.*_mcp/server|_mcp/server.*llms\.txt")
SCAFFOLD = re.compile(r"FastAPI\(|Flask\(|express\(\)|app\.listen\(|uvicorn\.run|requirements\.txt|package\.json|Dockerfile|[├└]── [\\w.-]+(/|\\.\\w+)")
INTERNALS = re.compile(r"mia_managed|managed catalog", re.I)
MAX_BLOCK = 90  # longer code blocks are app code, not an API guide


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
    # Two ways to integrate open the core skill, getting-started and the top-level docs.
    tops = [os.path.join("skills", "meetstream", "SKILL.md"), os.path.join("skills", "getting-started", "SKILL.md"),
            "README.md", "AGENTS.md", "INSTALL_FOR_AGENTS.md"]
    for rel in tops:
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            continue
        text = open(fp, encoding="utf-8").read()
        text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        head = "\n".join(text.split("\n")[:60])
        if not ("Bot API" in head and "Agents API" in head and head.index("Bot API") < head.index("Agents API")):
            misses += 1
            print(f"MISS {rel}: the first 60 lines do not give the two ways (Bot API, then Agents API)")
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
FORBIDDEN = re.compile(r"\b(stable|unstable|break|breaks|breaking|broken|pin|pinned|pinning|downgrade|downgrading)\b|can.?t promise", re.I)


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


def main():
    misses = version_wording_misses() + body_misses()
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
