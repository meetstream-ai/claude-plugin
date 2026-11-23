#!/usr/bin/env python3
"""Build the per-store plugin folders from one source tree ("one plugin, many stores").

Source (edit these):
  skills/<name>/SKILL.md        canonical skills (also the root Claude Code plugin)
  agents/*.md                   canonical subagent
  .claude-plugin/plugin.json    root Claude Code plugin; its "version" is the version of every build
  listing/listing.json          names, descriptions, URLs, prompts, review cases
  listing/brand/icon-*.png      icons

Output (GENERATED, committed, never edit by hand):
  plugins/claude-directory/     strict Claude Directory build (unverified org profile)
  plugins/cursor/               Cursor Marketplace (.cursor-plugin)
  plugins/agent-plugin/         Agent Plugins 1.0 (OpenAI ChatGPT/Codex directory, Kiro, Hermes portable, Goose)
  plugins/antigravity/          Antigravity (.antigravity-plugin)
  plugins/openclaw/             OpenClaw / ClawHub (openclaw.plugin.json)
  gemini-extension.json         Gemini CLI gallery (repo root, reuses root skills/ and agents/)
  .cursor-plugin/marketplace.json

plugins/hermes/ is NOT generated: it is the native Hermes Python plugin, maintained by hand.

Usage:
  python3 scripts/build_stores.py           write the generated files
  python3 scripts/build_stores.py --check   exit 1 if the committed files differ from a fresh build

Python standard library only.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LISTING = json.loads((ROOT / "listing" / "listing.json").read_text(encoding="utf-8"))
VERSION = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
CLI_DOC = LISTING["urls"]["cli"]
MCP_NAME = LISTING["mcp"]["name"]
MCP_URL = LISTING["mcp"]["url"]

# Store folders that this script owns completely (deleted and rewritten on each build).
GENERATED_DIRS = ["plugins/claude-directory", "plugins/cursor", "plugins/agent-plugin",
                  "plugins/antigravity", "plugins/openclaw"]
# Single generated files outside those folders.
GENERATED_FILES = ["gemini-extension.json", ".cursor-plugin/marketplace.json"]

# Frontmatter keys from the Agent Skills spec. Non-spec keys (for example mcp_server) are dropped.
SPEC_SKILL_KEYS = ("name", "description", "license", "compatibility", "metadata", "allowed-tools")

# ---------------------------------------------------------------------------------------------
# Claude Directory rules (portal findings of 23 Nov 2026 for an unverified org):
# only .md/.json/.png files; skill frontmatter = name + description; no env credential reads;
# no download-and-run commands; subagent tools limited to read-only tools.
# ---------------------------------------------------------------------------------------------
CLI_TEXT = f"the meetstream CLI (to install it, see {CLI_DOC})"

# (pattern, replacement) applied in order to every skill and agent file in the Claude Directory build.
DIRECTORY_TEXT_RULES: list[tuple[str, str]] = [
    # The shared "Install the CLI" sentence.
    (r"\*\*Install the CLI\*\* \(when this agent runs commands for the user\):[^\n]*?or set `MEETSTREAM_API_KEY`\.",
     f"**Install the meetstream CLI** (see {CLI_DOC}). Sign in with `meetstream login` (it opens the browser "
     "and stores a key; never ask for the key in the chat)."),
    # Download-and-run CLI mentions.
    (r"`npx -y @meetstream/cli(?: <command>)?`(?:\s+(?:runs it with no install|works with no install|"
     r"if it is not\s+installed)|\s*\(no install\))?", CLI_TEXT),
    (r"npx -y @meetstream/cli\b", "meetstream"),
    (r"`npx @meetstream/cli`", "`npm install -g @meetstream/cli`"),
    (r"`uvx --from meetstream-cli meetstream`", "`pipx install meetstream-cli`"),
    (r"uvx --from meetstream-cli meetstream\b", "meetstream"),
    (r"npx @meetstream/migrate\b", "meetstream-migrate"),
    # API key read from the user's environment -> placeholder.
    (r"YOUR_MEETSTREAM_API_KEY", "YOUR_API_KEY"),
    (r"\{os\.environ\[['\"]MEETSTREAM_API_KEY['\"]\]\}", "YOUR_API_KEY"),
    (r"os\.environ(?:\.get\(|\[)['\"]MEETSTREAM_API_KEY['\"][\])]", '"YOUR_API_KEY"'),
    (r"process\.env\.MEETSTREAM_API_KEY", '"YOUR_API_KEY"'),
    (r"\$\{?MEETSTREAM_API_KEY\}?", "YOUR_API_KEY"),
    (r"reads `?MEETSTREAM_API_KEY`?", "takes your API key"),
    (r"`MEETSTREAM_API_KEY`", "your MeetStream API key"),
    (r"MEETSTREAM_API_KEY", "your MeetStream API key"),
]

# Required replacements of whole Markdown sections (heading up to the next heading of the same
# or a higher level). A missing heading fails the build, so source edits cannot slip through.
DIRECTORY_SECTION_RULES: dict[str, dict[str, str]] = {
    "meetstream": {
        "### First-time users - invoke `getting-started` skill BEFORE anything else": (
            "### First-time users - invoke `getting-started` skill BEFORE anything else\n\n"
            "If the MeetStream MCP tools are not connected, or a tool answers 401 or \"not signed in\", "
            "sign in through the MeetStream MCP: the client opens app.meetstream.ai in the browser, the user "
            "signs in and clicks **Allow**. No key is copied. For the user's own app code, the user creates an "
            "API key at https://app.meetstream.ai/api-keys and keeps it in the app's own secret store; the "
            "examples in this skill show it as `YOUR_API_KEY`. The `getting-started` skill walks a new user "
            "through signup, sign-in and the first bot.\n\n"
            "Base URL: `https://api.meetstream.ai/api/v1` (no trailing slash in canonical examples).\n\n"
            "Default language: **Python** unless the user specifies otherwise.\n\n"
            "---\n\n"
        ),
    },
    "getting-started": {
        "## When to invoke this skill": (
            "## When to invoke this skill\n\n"
            "Invoke this skill first when the user is new to MeetStream, has no account, or the MeetStream MCP "
            "tools are missing or answer 401 or \"not signed in\". Skip it when a MeetStream MCP tool (for "
            "example `list_bots`) already answers, or when the user says they already have a working key.\n\n"
        ),
        "## Step 1: Check if API key is already configured": (
            "## Step 1: Check the connection\n\n"
            "Call the MeetStream MCP tool `list_bots`. A list, or an empty list, means the user is signed in: "
            "go to Step 6. A 401 or \"not signed in\" means: sign in through the MeetStream MCP (the client opens "
            "app.meetstream.ai; the user signs in and clicks **Allow**; no key is copied).\n\n"
        ),
        "## Step 4: Set the API key in their shell": (
            "## Step 4: Store the API key for app code\n\n"
            "Only the user's own app code needs the key. The user keeps it in the app's secret store or in a "
            "`.env` file that is in `.gitignore`, never in the chat and never in git. The code examples in these "
            "skills show it as `YOUR_API_KEY`.\n\n"
        ),
        "## Step 5: Validate the key": (
            "## Step 5: Validate the key\n\n"
            "Call `list_bots` through the MeetStream MCP. For app code, one request from the app checks the key: "
            "`GET https://api.meetstream.ai/api/v1/bots` with the header `Authorization: Token YOUR_API_KEY`. "
            "Expected: `200`.\n\n"
            "If `401` or `403`: key is wrong, re-do Step 3.\n"
            "If anything else: network issue, ask user to retry.\n\n"
        ),
    },
}

# Required single-string replacements per skill (also fail the build when the text is gone).
DIRECTORY_EXACT_RULES: dict[str, list[tuple[str, str]]] = {
    "getting-started": [
        ("- Make sure they exported it: `echo $MEETSTREAM_API_KEY` should print the key (not empty)",
         "- Make sure the app loads the key from its secret store or `.env` file"),
    ],
    "migrate-from-recall": [
        ("# Scan only (no changes)", "# Install the migration kit once\nnpm install -g @meetstream/migrate\n\n# Scan only (no changes)"),
    ],
}

DIRECTORY_AGENT_TOOLS = "Read, Grep, Glob"
DIRECTORY_AGENT_NOTE = (
    "In this build you have no shell. Use the MeetStream MCP tools (`get_bot_detail`, `get_bot_status`, "
    "`get_transcript`) to read live state, or ask the user to run the commands below and paste the output.\n\n"
)
DIRECTORY_ALLOWED_EXT = {".md", ".json", ".png"}
DIRECTORY_EXCLUDE_SKILLS: set[str] = set()  # add a skill name here to leave it out of the Directory build

# Leftovers that must never appear in the Claude Directory build.
DIRECTORY_FORBIDDEN = [r"MEETSTREAM_API_KEY", r"\bnpx\b", r"\buvx\b", r"curl[^\n|]*\|\s*(?:ba|z)?sh\b",
                       r"^allowed-tools:", r"^mcp_server:"]


# ---------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------
def dump_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def split_frontmatter(text: str) -> tuple[list[tuple[str, list[str]]], str]:
    """Return ([(key, raw_lines)], body). Keeps each top-level key's raw YAML lines unchanged."""
    if not text.startswith("---\n"):
        raise SystemExit("file has no YAML frontmatter")
    end = text.index("\n---\n", 4)
    lines = text[4:end].split("\n")
    body = text[end + 5:]
    blocks: list[tuple[str, list[str]]] = []
    for line in lines:
        m = re.match(r"^([A-Za-z_][\w-]*):", line)
        if m:
            blocks.append((m.group(1), [line]))
        elif blocks:
            blocks[-1][1].append(line)
        else:
            raise SystemExit(f"cannot parse frontmatter line: {line!r}")
    return blocks, body


def join_frontmatter(blocks: list[tuple[str, list[str]]], body: str) -> str:
    head = "\n".join(line for _, raw in blocks for line in raw)
    return f"---\n{head}\n---\n{body}"


def filter_frontmatter(text: str, keep: tuple[str, ...]) -> str:
    blocks, body = split_frontmatter(text)
    return join_frontmatter([b for b in blocks if b[0] in keep], body)


def replace_section(text: str, heading: str, new: str, where: str) -> str:
    level = len(heading) - len(heading.lstrip("#"))
    start = text.find("\n" + heading + "\n")
    if start < 0:
        raise SystemExit(f"{where}: section {heading!r} not found; update DIRECTORY_SECTION_RULES")
    start += 1
    # The section ends at the next heading of the same or a higher level, outside code fences
    # (a "# comment" line in a bash block is not a heading).
    nxt = re.compile(r"#{1,%d} " % level)
    pos, in_fence, end = start + len(heading) + 1, False, len(text)
    for line in text[pos:].splitlines(keepends=True):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and nxt.match(line):
            end = pos
            break
        pos += len(line)
    return text[:start] + new + text[end:]


def skill_names() -> list[str]:
    return sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())


def iter_files(base: Path):
    for path in sorted(base.rglob("*")):
        if path.is_file() and path.name != ".DS_Store":
            yield path


def copy_skills(dst: Path, keep_keys: tuple[str, ...] = SPEC_SKILL_KEYS, transform=None,
                exclude: set[str] | None = None, allowed_ext: set[str] | None = None) -> None:
    for name in skill_names():
        if exclude and name in exclude:
            continue
        src_dir = ROOT / "skills" / name
        for src in iter_files(src_dir):
            rel = src.relative_to(src_dir)
            if allowed_ext is not None and src.suffix not in allowed_ext:
                continue
            out = dst / "skills" / name / rel
            if src.suffix == ".md":
                text = src.read_text(encoding="utf-8")
                if rel.as_posix() == "SKILL.md":
                    text = filter_frontmatter(text, keep_keys)
                if transform:
                    text = transform(name, rel.as_posix(), text)
                write_text(out, text)
            else:
                copy_file(src, out)


def copy_agents(dst: Path, transform=None) -> None:
    for src in iter_files(ROOT / "agents"):
        text = src.read_text(encoding="utf-8")
        if transform:
            text = transform(src.name, text)
        write_text(dst / "agents" / src.name, text)


def base_manifest() -> dict:
    return {
        "name": LISTING["name"],
        "version": VERSION,
        "description": LISTING["description"],
        "author": dict(LISTING["author"]),
        "homepage": LISTING["homepage"],
        "repository": LISTING["repository"],
        "license": LISTING["license"],
        "keywords": list(LISTING["keywords"]),
    }


def readme(store: str, install: str) -> str:
    u = LISTING["urls"]
    return (
        f"# {LISTING['displayName']} for {store}\n\n"
        f"{LISTING['longDescription']}\n\n"
        "## Install\n\n"
        f"{install}\n\n"
        "## Sign in\n\n"
        f"The plugin connects to the hosted MeetStream MCP server at {MCP_URL}. The first time a MeetStream tool "
        "runs, your client opens app.meetstream.ai in the browser. Sign in (or create an account) and click "
        "**Allow**. No API key is pasted into the chat.\n\n"
        "## Try it\n\n"
        + "".join(f"- \"{p}\"\n" for p in LISTING["defaultPrompts"])
        + "\n## Links\n\n"
        f"- Documentation: {u['documentation']}\n"
        f"- Support: {u['support']}\n"
        f"- Privacy policy: {u['privacyPolicy']}\n"
        f"- Terms of use: {u['termsOfService']}\n"
        f"- Source: {LISTING['repository']} (this folder is generated by `scripts/build_stores.py`)\n"
    )


# ---------------------------------------------------------------------------------------------
# Store rule tables
# ---------------------------------------------------------------------------------------------
def directory_text(name: str, text: str, where: str) -> str:
    for heading, new in DIRECTORY_SECTION_RULES.get(name, {}).items():
        text = replace_section(text, heading, new, where)
    for old, new in DIRECTORY_EXACT_RULES.get(name, []):
        if old not in text:
            raise SystemExit(f"{where}: text {old!r} not found; update DIRECTORY_EXACT_RULES")
        text = text.replace(old, new)
    for pattern, repl in DIRECTORY_TEXT_RULES:
        text = re.sub(pattern, lambda _m, r=repl: r, text)
    return text


def build_claude_directory(out: Path) -> None:
    d = out / "plugins" / "claude-directory"
    u = LISTING["urls"]
    manifest = base_manifest()
    manifest.update({
        "icon": "icon.png",
        "privacyPolicyUrl": u["privacyPolicy"],
        "termsOfServiceUrl": u["termsOfService"],
        "supportUrl": u["support"],
        "documentationUrl": u["documentation"],
        "mcpServers": "./.mcp.json",
    })
    dump_json(d / ".claude-plugin" / "plugin.json", manifest)
    dump_json(d / ".mcp.json", {"mcpServers": {MCP_NAME: {"type": "http", "url": MCP_URL}}})
    copy_file(ROOT / "listing" / "brand" / "icon-512.png", d / "icon.png")
    copy_file(ROOT / "LICENSE", d / "LICENSE")
    write_text(d / "README.md", readme(
        "Claude", "Install **MeetStream** from the Claude plugin directory. Developers can also add the full "
        "plugin with `/plugin marketplace add meetstream-ai/meetstream-plugin`."))

    def skill_transform(name: str, rel: str, text: str) -> str:
        if rel != "SKILL.md":
            name = f"{name}/{rel}"
        return directory_text(name, text, f"claude-directory skills/{name}")

    copy_skills(d, keep_keys=("name", "description"), transform=skill_transform,
                exclude=DIRECTORY_EXCLUDE_SKILLS, allowed_ext=DIRECTORY_ALLOWED_EXT)

    def agent_transform(fname: str, text: str) -> str:
        blocks, body = split_frontmatter(text)
        blocks = [(k, [f"tools: {DIRECTORY_AGENT_TOOLS}"] if k == "tools" else raw) for k, raw in blocks]
        if not any(k == "tools" for k, _ in blocks):
            blocks.append(("tools", [f"tools: {DIRECTORY_AGENT_TOOLS}"]))
        body = "\n" + DIRECTORY_AGENT_NOTE + body.lstrip("\n")
        return directory_text(fname, join_frontmatter(blocks, body), f"claude-directory agents/{fname}")

    copy_agents(d, transform=agent_transform)

    # Final gate: only allowed file types, and no forbidden text anywhere.
    for path in iter_files(d):
        rel = path.relative_to(d).as_posix()
        if path.suffix not in DIRECTORY_ALLOWED_EXT and rel != "LICENSE":
            raise SystemExit(f"claude-directory: file type not allowed: {rel}")
        if path.suffix == ".md":
            text = path.read_text(encoding="utf-8")
            for pattern in DIRECTORY_FORBIDDEN:
                m = re.search(pattern, text, re.M)
                if m:
                    raise SystemExit(f"claude-directory: {rel} still contains {m.group(0)!r}; add a rule")
    if len(re.findall(r"\w+", (d / "README.md").read_text(encoding="utf-8"))) < 40:
        raise SystemExit("claude-directory: README.md needs at least 40 words")


def build_cursor(out: Path) -> None:
    d = out / "plugins" / "cursor"
    c = LISTING["cursor"]
    manifest = {
        "$schema": "https://cursor.com/schemas/cursor-plugin/plugin.json",
        "name": LISTING["name"],
        "displayName": LISTING["displayName"],
        "version": VERSION,
        "description": LISTING["description"],
        "author": dict(c["author"]),
        "homepage": c["homepage"],
        "repository": LISTING["repository"],
        "license": LISTING["license"],
        "keywords": list(c["keywords"]),
        "logo": "assets/logo.png",
        "skills": "./skills",
        "agents": "./agents",
        "mcpServers": "./mcp.json",
    }
    dump_json(d / ".cursor-plugin" / "plugin.json", manifest)
    dump_json(d / "mcp.json", {"mcpServers": {MCP_NAME: {"url": MCP_URL}}})
    copy_file(ROOT / "listing" / "brand" / "icon-512.png", d / "assets" / "logo.png")
    copy_file(ROOT / "LICENSE", d / "LICENSE")
    write_text(d / "README.md", readme(
        "Cursor", "Install **MeetStream** from the Cursor Marketplace. To test it locally, copy this folder to "
        "`~/.cursor/plugins/local/meetstream` and run **Developer: Reload Window**."))
    copy_skills(d)
    copy_agents(d)


def build_agent_plugin(out: Path) -> None:
    d = out / "plugins" / "agent-plugin"
    u = LISTING["urls"]
    o = LISTING["openai"]
    interface = {
        "displayName": LISTING["displayName"],
        "shortDescription": LISTING["shortDescription"],
        "longDescription": LISTING["longDescription"],
        "developerName": LISTING["developerName"],
        "category": LISTING["category"],
        "capabilities": list(LISTING["capabilities"]),
        "websiteURL": u["website"],
        "supportURL": u["support"],
        "privacyPolicyURL": u["privacyPolicy"],
        "termsOfServiceURL": u["termsOfService"],
        "defaultPrompt": list(LISTING["defaultPrompts"]),
        "brandColor": LISTING["brandColor"],
        "logo": "./assets/icon.png",
        "composerIcon": "./assets/icon.png",
    }
    for key, limit in (("displayName", 30), ("shortDescription", 30), ("longDescription", 4000),
                       ("developerName", 80)):
        if len(interface[key]) > limit:
            raise SystemExit(f"agent-plugin: interface.{key} is longer than {limit} characters")
    if len(interface["defaultPrompt"]) > 3 or any(len(p) > 128 for p in interface["defaultPrompt"]):
        raise SystemExit("agent-plugin: defaultPrompt needs at most 3 prompts of at most 128 characters")
    if len(interface["capabilities"]) > 20 or any(len(c) > 120 for c in interface["capabilities"]):
        raise SystemExit("agent-plugin: capabilities needs at most 20 items of at most 120 characters")
    cases = o["test_cases"]
    if len(cases["positive"]) != 5 or len(cases["negative"]) != 3:
        raise SystemExit("agent-plugin: OpenAI review needs exactly 5 positive and 3 negative test cases")
    manifest = {"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json", **base_manifest()}
    manifest["extensions"] = {
        "com.openai": {
            "interface": interface,
            "review": {"test_cases": cases, "demo_recording_url": o["demo_recording_url"]},
            "commerce": o["commerce"],
            "publication": {"release_notes": o["release_notes"]},
        }
    }
    dump_json(d / "plugin.json", manifest)
    dump_json(d / "mcp.json", {
        "$schema": "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json",
        "mcpServers": {MCP_NAME: {
            "type": "streamable-http",
            "url": MCP_URL,
            "extensions": {"com.openai": {"auth": {"type": "oauth", "client": {"mode": "dcr"}}}},
        }},
    })
    copy_file(ROOT / "listing" / "brand" / "icon-512.png", d / "assets" / "icon.png")
    copy_file(ROOT / "LICENSE", d / "LICENSE")
    write_text(d / "README.md", readme(
        "Agent Plugins hosts (ChatGPT, Codex, Kiro, Hermes, Goose)",
        "ChatGPT and Codex: install **MeetStream** from the OpenAI plugin directory. Kiro: Powers panel > Add "
        "Custom Power > GitHub URL of this folder. Hermes: `hermes plugins install` with this folder. Goose: add "
        "this folder as a plugin. The subagent is not part of this build (Agent Plugins 1.0 has no agent slot)."))
    copy_skills(d)


def build_antigravity(out: Path) -> None:
    d = out / "plugins" / "antigravity"
    manifest = {
        "name": LISTING["name"],
        "displayName": LISTING["displayName"],
        "version": VERSION,
        "description": LISTING["description"],
        "author": dict(LISTING["author"]),
        "homepage": LISTING["homepage"],
        "repository": LISTING["repository"],
        "license": LISTING["license"],
        "logo": "assets/icon.png",
        "suggestedPrompts": list(LISTING["antigravity"]["suggestedPrompts"]),
    }
    dump_json(d / ".antigravity-plugin" / "plugin.json", manifest)
    dump_json(d / "mcp_config.json", {"mcpServers": {MCP_NAME: {"serverUrl": MCP_URL}}})
    copy_file(ROOT / "listing" / "brand" / "icon-512.png", d / "assets" / "icon.png")
    copy_file(ROOT / "LICENSE", d / "LICENSE")
    write_text(d / "README.md", readme(
        "Antigravity", "Run `agy plugin install https://github.com/meetstream-ai/meetstream-plugin` and pick "
        "this folder, or copy it to `~/.gemini/config/plugins/meetstream`, then `agy plugin validate --strict`."))
    copy_skills(d)
    copy_agents(d)


def build_openclaw(out: Path) -> None:
    d = out / "plugins" / "openclaw"
    oc = LISTING["openclaw"]
    manifest = {
        "id": oc["id"],
        "name": oc["packageName"],
        "displayName": LISTING["displayName"],
        "version": VERSION,
        "description": LISTING["description"],
        "author": dict(LISTING["author"]),
        "homepage": LISTING["homepage"],
        "repository": LISTING["repository"],
        "license": LISTING["license"],
        "categories": list(oc["categories"]),
        "icon": "assets/icon.png",
        "skills": "./skills",
        "mcpServers": {MCP_NAME: {"url": MCP_URL, "transport": "streamable-http", "auth": "oauth"}},
    }
    dump_json(d / "openclaw.plugin.json", manifest)
    copy_file(ROOT / "listing" / "brand" / "icon-512.png", d / "assets" / "icon.png")
    copy_file(ROOT / "LICENSE", d / "LICENSE")
    write_text(d / "README.md", readme(
        "OpenClaw",
        "Run `openclaw plugins install meetstream --marketplace meetstream-ai/meetstream-plugin`, then add the "
        f"hosted MCP server: `openclaw mcp set {MCP_NAME} '{{\"url\":\"{MCP_URL}\",\"transport\":"
        "\"streamable-http\",\"auth\":\"oauth\"}'` and sign in with `openclaw mcp login meetstream`. The skills "
        "in this folder are also published to ClawHub. Check: ask OpenClaw to call the MeetStream tool "
        "`list_bots`; a list of bots, or an empty list, means MeetStream is connected."))
    copy_skills(d)


def build_root_files(out: Path) -> None:
    dump_json(out / "gemini-extension.json", {
        "name": LISTING["name"],
        "version": VERSION,
        "description": LISTING["description"],
        "mcpServers": {MCP_NAME: {"httpUrl": MCP_URL}},
    })
    dump_json(out / ".cursor-plugin" / "marketplace.json", {
        "name": "meetstream-ai",
        "owner": {"name": "MeetStream", "email": LISTING["cursor"]["author"]["email"]},
        "metadata": {"description": "MeetStream plugins for Cursor", "version": VERSION},
        "plugins": [{"name": LISTING["name"], "source": "plugins/cursor", "description": LISTING["description"]}],
    })


BUILDERS = [build_claude_directory, build_cursor, build_agent_plugin, build_antigravity, build_openclaw,
            build_root_files]


# ---------------------------------------------------------------------------------------------
def build(out: Path) -> None:
    for builder in BUILDERS:
        builder(out)


def tree(base: Path) -> set[str]:
    return {p.relative_to(base).as_posix() for p in iter_files(base)} if base.exists() else set()


def check() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp)
        build(fresh)
        diffs: list[str] = []
        for rel in GENERATED_DIRS:
            want, have = tree(fresh / rel), tree(ROOT / rel)
            diffs += [f"missing: {rel}/{f}" for f in sorted(want - have)]
            diffs += [f"not generated (remove it): {rel}/{f}" for f in sorted(have - want)]
            diffs += [f"differs: {rel}/{f}" for f in sorted(want & have)
                      if not filecmp.cmp(fresh / rel / f, ROOT / rel / f, shallow=False)]
        for rel in GENERATED_FILES:
            if not (ROOT / rel).is_file():
                diffs.append(f"missing: {rel}")
            elif not filecmp.cmp(fresh / rel, ROOT / rel, shallow=False):
                diffs.append(f"differs: {rel}")
    for line in diffs:
        print(line)
    if diffs:
        print(f"{len(diffs)} generated file(s) out of date. Run: python3 scripts/build_stores.py")
        return 1
    print("generated store folders are up to date")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="fail if generated files are out of date")
    args = parser.parse_args()
    if args.check:
        return check()
    for rel in GENERATED_DIRS:
        shutil.rmtree(ROOT / rel, ignore_errors=True)
    build(ROOT)
    print("wrote " + ", ".join(GENERATED_DIRS + GENERATED_FILES))
    return 0


if __name__ == "__main__":
    sys.exit(main())
