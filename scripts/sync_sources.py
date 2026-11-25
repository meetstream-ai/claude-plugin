#!/usr/bin/env python3
"""Refresh the pinned sources that the generated skill references are built from.

Sources (written to sources/, committed):
  openapi.json        https://docs.meetstream.ai/openapi.yaml, converted to JSON (needs PyYAML)
  llms.txt            https://docs.meetstream.ai/llms.txt (the docs page list)
  cli-commands.json   `meetstream commands --json` from the CLI binary given with --cli-bin
  cli-released.json   command paths of the released CLI (--cli-released 1.0.1, run through npx)
  mcp-tools.json      the hosted MCP tool list (--mcp-tools path/to/tools.json from meetstream-mcp-deploy)
  lock.json           hash, URL, fetch time and version of each source, plus a hash of every docs
                      page that data/*.json cites, so a changed page shows up in review

Usage:
  python3 scripts/sync_sources.py                    refresh the public docs sources and page hashes
  python3 scripts/sync_sources.py --cli-bin ./meetstream --cli-released 1.0.1 --mcp-tools ../tools.json
  python3 scripts/sync_sources.py --check-pages      exit 1 and list pages whose content changed (nightly)

Run this, then: python3 scripts/gen_references.py && python3 scripts/build_stores.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sources"
DATA = ROOT / "data"
OPENAPI_URL = "https://docs.meetstream.ai/openapi.yaml"
LLMS_URL = "https://docs.meetstream.ai/llms.txt"
# Tools that tools.json lists but the server turns on only with a flag (tools.go `on:`).
MCP_GATED = {"wait_for_meeting_event": "off by default; the server enables it with its live-events setting"}
UA = {"User-Agent": "meetstream-plugin-sync/1 (+https://github.com/meetstream-ai/meetstream-plugin)"}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as res:
        return res.read()


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_lock() -> dict:
    p = SRC / "lock.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {"sources": {}, "pages": {}}


def save_lock(lock: dict) -> None:
    (SRC / "lock.json").write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cited_pages() -> list[str]:
    """Every docs URL that data/*.json cites (source and also fields)."""
    urls: set[str] = set()
    for f in sorted(DATA.glob("*.json")):
        for m in re.finditer(r'"(https://docs\.meetstream\.ai/[^"#]+)"', f.read_text(encoding="utf-8")):
            urls.add(m.group(1))
    return sorted(urls)


def page_hash(url: str) -> str:
    md = url if url.endswith(".md") else url + ".md"
    return sha(fetch(md))


def keep_time(lock: dict, key: str, new: dict) -> dict:
    """Keep the old fetch time when the content did not change, so an unchanged source makes no diff."""
    old = lock.get("sources", {}).get(key, {})
    if old.get("sha256") == new.get("sha256") and old.get("fetched"):
        new["fetched"] = old["fetched"]
    return new


def sync_docs(lock: dict) -> None:
    import yaml  # only the sync step needs PyYAML; the generator is standard library only

    raw = fetch(OPENAPI_URL)
    spec = yaml.safe_load(raw)
    (SRC / "openapi.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    lock["sources"]["openapi"] = keep_time(lock, "openapi", {"url": OPENAPI_URL, "sha256": sha(raw), "fetched": now(),
                                                         "version": str(spec.get("info", {}).get("version", ""))})
    llms = fetch(LLMS_URL)
    (SRC / "llms.txt").write_bytes(llms)
    lock["sources"]["llms"] = keep_time(lock, "llms", {"url": LLMS_URL, "sha256": sha(llms), "fetched": now()})
    lock["pages"] = {u: page_hash(u) for u in cited_pages()}


def sync_cli(lock: dict, binary: str) -> None:
    out = subprocess.run([binary, "commands", "--json", "--no-input"], capture_output=True, text=True,
                         check=True, env={"MEETSTREAM_TELEMETRY": "0", "PATH": "/usr/bin:/bin"}).stdout
    data = json.loads(out)
    (SRC / "cli-commands.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    lock["sources"]["cli"] = keep_time(lock, "cli", {"version": data.get("version", ""), "sha256": sha(out.encode()),
                                                 "fetched": now(), "from": "meetstream commands --json"})


def help_paths(run, prefix: list[str]) -> list[str]:
    """Walk `meetstream <path> --help` and return every command path (released CLIs have no catalog)."""
    text = run(prefix + ["--help"])
    paths = []
    block = False
    for line in text.splitlines():
        if re.match(r"^(Available Commands|Get started|Meetings|Your agent in the call|Tools):", line):
            block = True
            continue
        if block and not line.strip():
            block = False
            continue
        m = re.match(r"^\s{2}([a-z][a-z0-9-]*)\s{2,}", line) if block else None
        if m and m.group(1) not in ("help", "completion"):
            sub = prefix + [m.group(1)]
            paths.append(" ".join(sub))
            paths += help_paths(run, sub)
    return paths


def sync_cli_released(lock: dict, version: str) -> None:
    def run(args: list[str]) -> str:
        return subprocess.run(["npx", "-y", f"@meetstream/cli@{version}"] + args, capture_output=True, text=True,
                              env={"MEETSTREAM_TELEMETRY": "0", "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin"}
                              ).stdout
    paths = sorted(set(help_paths(run, [])))
    (SRC / "cli-released.json").write_text(json.dumps({"version": version, "paths": paths}, indent=1) + "\n",
                                           encoding="utf-8")
    lock["sources"]["cli_released"] = keep_time(lock, "cli_released", {"version": version, "count": len(paths), "fetched": now(),
                                                                   "sha256": sha(json.dumps(paths).encode())})


def sync_mcp(lock: dict, path: str) -> None:
    raw = Path(path).read_bytes()
    tools = json.loads(raw)
    tools = tools.get("tools", tools) if isinstance(tools, dict) else tools
    keep = []
    for t in tools:
        schema = t.get("inputSchema") or t.get("input_schema") or {}
        props = schema.get("properties") or {}
        keep.append({"name": t["name"], "title": t.get("title", ""), "description": t.get("description", ""),
                     "enabled": t["name"] not in MCP_GATED, "note": MCP_GATED.get(t["name"], ""),
                     "inputs": sorted(props), "required": sorted(schema.get("required") or [])})
    (SRC / "mcp-tools.json").write_text(json.dumps(keep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    lock["sources"]["mcp"] = keep_time(lock, "mcp", {"sha256": sha(raw), "fetched": now(), "count": len(keep),
                                                 "from": "meetstream-mcp-deploy go/internal/tools/tools.json"})


def check_pages(lock: dict) -> int:
    changed = []
    for url in cited_pages():
        try:
            h = page_hash(url)
        except Exception as e:  # noqa: BLE001 - report every failure, keep going
            changed.append(f"{url} (could not fetch: {e})")
            continue
        if lock.get("pages", {}).get(url) != h:
            changed.append(url)
    for line in changed:
        print("changed:", line)
    print(f"{len(changed)} cited page(s) changed since the last sync")
    return 1 if changed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--cli-bin", help="CLI binary that has `commands --json`")
    ap.add_argument("--cli-released", help="released CLI version to list (npx @meetstream/cli@VERSION)")
    ap.add_argument("--mcp-tools", help="path to the MCP tools.json")
    ap.add_argument("--no-docs", action="store_true", help="skip the public docs sources")
    ap.add_argument("--check-pages", action="store_true", help="exit 1 if a cited docs page changed")
    a = ap.parse_args()
    SRC.mkdir(exist_ok=True)
    lock = load_lock()
    if a.check_pages:
        return check_pages(lock)
    if not a.no_docs:
        sync_docs(lock)
    if a.cli_bin:
        sync_cli(lock, a.cli_bin)
    if a.cli_released:
        sync_cli_released(lock, a.cli_released)
    if a.mcp_tools:
        sync_mcp(lock, a.mcp_tools)
    save_lock(lock)
    print("sources updated:", ", ".join(sorted(lock["sources"])), f"· {len(lock.get('pages', {}))} cited pages hashed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
