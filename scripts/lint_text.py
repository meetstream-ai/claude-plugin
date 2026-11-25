#!/usr/bin/env python3
"""Fail on text that skills and agent docs must never contain.

Rules:
  zoom-setup   a sentence that says Zoom needs no setup or joins without the customer's Zoom app
  paste-key    asking the user to paste, type or send an API key (into the chat or anywhere)
  bearer-rest  `Bearer` auth in an example that calls the REST API (REST uses `Authorization: Token`)
  price        a dollar amount in prose that is not in data/prices.json (each allowed amount has a source)

Allow one line on purpose with an HTML comment on that line: <!-- lint-allow: RULE -->

Usage: python3 scripts/lint_text.py [paths...]   (default: the hand-written skills, agents, Hermes and docs)
Python standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ["skills", "agents", "plugins/hermes", "README.md", "AGENTS.md", "CLAUDE.md", "INSTALL_FOR_AGENTS.md",
           "llms-install.md", "listing/listing.json"]
TEXT_EXT = {".md", ".py", ".json", ".yaml", ".yml", ".txt"}

# The claim that Zoom needs no setup (product copy). Describing the API's `use_own_app: false` mode is allowed.
ZOOM_NEG = [r"\bneeds? no (?:zoom )?(?:setup|set-up|configuration|app)\b", r"\bno (?:zoom )?(?:setup|set-up) (?:is )?(?:needed|required)\b",
            r"\bwithout (?:any )?(?:setup|set-up|configuration)\b", r"\bzero[- ]setup\b", r"\bdoes(?:n't| not) need (?:a |any )?(?:setup|set-up|app)\b",
            r"\bno (?:zoom )?app (?:is )?(?:needed|required)\b", r"\bworks out of the box\b"]
ZOOM_OK = [r"always needs", r"needs (?:your|the customer'?s|their) (?:own )?zoom app", r"never (?:say|write|claim|tell)",
           r"do not (?:tell|say|write|claim)", r"saying zoom needs no setup", r"open question", r"lint"]
PASTE = re.compile(r"\b(?:paste|type|enter|send|share|give)\s+(?:me\s+)?(?:your|the|an?)?\s*(?:meetstream\s+)?(?:api\s+)?key\b"
                   r"|\bpaste (?:it|the key) here\b|\bpaste the key\b", re.I)
PASTE_OK = re.compile(r"\b(?:never|don'?t|do not|no need to|nothing to paste|not (?:paste|ask)|without pasting)\b", re.I)
PRICE = re.compile(r"\$\s?\d+(?:\.\d+)?")


def allowed_prices() -> set[str]:
    data = json.loads((ROOT / "data" / "prices.json").read_text(encoding="utf-8"))
    return {re.sub(r"\s", "", a["amount"]) for a in data["allowed"]}


def files(args: list[str]):
    for a in args or DEFAULT:
        p = ROOT / a
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.suffix in TEXT_EXT and "node_modules" not in f.parts and "__pycache__" not in f.parts:
                    yield f


def allow(line: str, rule: str) -> bool:
    return f"lint-allow: {rule}" in line


def sentences(text: str):
    """(line_no, sentence) pairs; sentences do not cross blank lines."""
    for para_start, para in paragraphs(text):
        for m in re.finditer(r"[^.!?]+[.!?]?", para):
            s = m.group(0)
            line_no = para_start + para[: m.start()].count("\n")
            yield line_no, s


def paragraphs(text: str):
    line = 1
    for block in re.split(r"(\n\s*\n)", text):
        if block.strip() and not re.fullmatch(r"\n\s*\n", block):
            yield line, block
        line += block.count("\n")


def strip_code(text: str) -> str:
    """Blank out fenced blocks and inline code, keeping line numbers."""
    text = re.sub(r"```.*?```", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.S)
    return re.sub(r"`[^`\n]*`", lambda m: " " * len(m.group(0)), text)


def lint_file(path: Path, prices: set[str]) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    rel = path.relative_to(ROOT).as_posix()
    out = []

    def where(n: int) -> str:
        return f"{rel}:{n}"

    for n, s in sentences(strip_code(text) if path.suffix == ".md" else text):
        low = s.lower()
        if "zoom" in low and any(re.search(p, low) for p in ZOOM_NEG) and not any(re.search(p, low) for p in ZOOM_OK):
            ln = lines[n - 1] if 0 < n <= len(lines) else ""
            if not allow(ln, "zoom-setup"):
                out.append(f"{where(n)}: zoom-setup: {' '.join(s.split())[:160]}")
    for i, ln in enumerate(lines, 1):
        if PASTE.search(ln) and not PASTE_OK.search(ln) and not allow(ln, "paste-key"):
            out.append(f"{where(i)}: paste-key: {ln.strip()[:160]}")
    for m in re.finditer(r"```.*?```", text, flags=re.S):
        block = m.group(0)
        if "api.meetstream.ai" in block and re.search(r"\bBearer\b", block):
            n = text[: m.start()].count("\n") + 1
            if not allow(lines[n - 1] if n <= len(lines) else "", "bearer-rest"):
                out.append(f"{where(n)}: bearer-rest: a REST example uses Bearer; REST takes Authorization: Token <key>")
    for i, ln in enumerate(lines, 1):
        if "api.meetstream.ai" in ln and re.search(r"\bBearer\b", ln) and "Token" not in ln and not allow(ln, "bearer-rest"):
            out.append(f"{where(i)}: bearer-rest: {ln.strip()[:160]}")
    prose = strip_code(text).splitlines() if path.suffix == ".md" else lines
    for i, ln in enumerate(prose, 1):
        for m in PRICE.finditer(ln):
            amount = re.sub(r"\s", "", m.group(0))
            if amount not in prices and not allow(lines[i - 1], "price"):
                out.append(f"{where(i)}: price: {amount} is not in data/prices.json (add it with a public source, or link the pricing page)")
    return out


def main() -> int:
    prices = allowed_prices()
    problems = []
    for f in files(sys.argv[1:]):
        problems += lint_file(f, prices)
    for p in problems:
        print(p)
    if problems:
        print(f"{len(problems)} problem(s). Fix the text, or allow one line on purpose with <!-- lint-allow: RULE -->.")
        return 1
    print("text lint: no banned text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
