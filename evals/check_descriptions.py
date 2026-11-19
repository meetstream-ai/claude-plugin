"""Check that each skill's frontmatter description carries its must-say lines.

Some agents (for example Codex) answer from the skill descriptions without opening
SKILL.md, so these facts must be in the description itself.
Usage: python3 evals/check_descriptions.py [repo_root]   (exit 1 on any miss)
"""
import os
import re
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

# skill -> list of (label, regex that must match the description)
MUST = {
    "troubleshooting": [("billing URL", r"https://app\.meetstream\.ai/billing"), ("no retry loop", r"never retry")],
    "join-meeting": [("billing URL", r"https://app\.meetstream\.ai/billing"), ("no retry loop", r"never retry"),
                     ("raise-hand REST", r"POST /api/v1/bots/\{bot_id\}/send_command.*raise_hand")],
    "realtime-streaming": [("raise-hand REST", r"POST /api/v1/bots/\{bot_id\}/send_command.*raise_hand")],
    "mia-voice-agents": [("managed keys first", r"[Dd]efault to MeetStream-managed keys.*key_source.*meetstream"),
                         ("own keys second", r"then the user's own (provider )?keys"),
                         ("Agent Kit warning", r"Agent Kit.*warning.*(meeting speech|what people say).*computer"),
                         ("computer stays on", r"computer must stay on")],
    "getting-started": [("post-call or live first", r"[Ff]irst ask.*after the call.*live")],
}


def description(path):
    text = open(path, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return ""
    fm = m.group(1)
    d = re.search(r"^description:\s*(>-?|\|-?)?\s*\n?(.*?)(?=^\S[^\n]*:|\Z)", fm, re.S | re.M)
    return " ".join((d.group(2) if d else "").split())


def main():
    misses = 0
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
