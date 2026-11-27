"""Split a large Markdown reference into parts under a size limit.

Some agent harnesses do not read a file larger than about 20 KB in one go (GitHub Copilot CLI
skipped every skill file above that size in the cross-harness build tests, MS-2485). This
keeps the original file name as an index (its intro plus a list of parts) and moves the `##`
sections into `<stem>-<slug>.md` files of at most LIMIT bytes.

  python3 scripts/split_md.py skills/meetstream/references/api-reference.md [...]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

LIMIT = 18000   # bytes per part; the guard in build_stores.py fails above 20000


def _slug(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return "-".join(s.split("-")[:5]) or "part"


def _sections(body: str, level: str) -> list[str]:
    out, cur = [], []
    for line in body.split("\n"):
        if line.startswith(level + " ") and cur:
            out.append("\n".join(cur).rstrip() + "\n")
            cur = []
        cur.append(line)
    if cur:
        out.append("\n".join(cur).rstrip() + "\n")
    return out


def split(text: str, stem: str, limit: int = LIMIT) -> dict[str, str] | None:
    """Return {file name: text} with the index under `<stem>.md`, or None when it already fits."""
    if len(text.encode()) <= limit + 2000:
        return None
    m = re.search(r"^## ", text, re.M)
    if not m:
        return None
    intro, body = text[: m.start()], text[m.start():]
    secs = [s for s in _sections(body, "##") if not s.startswith("## Contents")]
    # A section that alone is too big is split at its ### headings.
    pieces: list[str] = []
    for s in secs:
        if len(s.encode()) > limit:
            head, *subs = _sections(s, "###")
            pieces.append(head)
            pieces.extend(subs)
        else:
            pieces.append(s)
    parts: list[list[str]] = [[]]
    for p in pieces:
        if parts[-1] and len("".join(parts[-1] + [p]).encode()) > limit:
            parts.append([])
        parts[-1].append(p)
    title = (re.search(r"^# (.+)$", intro, re.M) or [None, stem])[1]
    files: dict[str, str] = {}
    lines = []
    for chunk in parts:
        first = re.match(r"#+ (.+)", chunk[0]).group(1)
        name = f"{stem}-{_slug(first)}.md"
        n = 2
        while name in files:
            name = f"{stem}-{_slug(first)}-{n}.md"; n += 1
        heads = [re.match(r"#+ (.+)", c).group(1) for c in chunk if re.match(r"#+ ", c)]
        files[name] = f"# {title}: {first}\n\n> Part of [`{stem}.md`]({stem}.md), split so each file stays under 20 KB.\n\n" + "\n".join(chunk)
        lines.append(f"- [`{name}`]({name}): " + "; ".join(heads))
    intro = re.sub(r"\n## Contents\n.*", "\n", intro, flags=re.S).rstrip()
    files[f"{stem}.md"] = intro + "\n\n## Parts\n\nThis reference is split into files under 20 KB. Open the part you need:\n\n" + "\n".join(lines) + "\n"
    return files


def split_file(path: Path) -> list[str]:
    res = split(path.read_text(encoding="utf-8"), path.stem)
    if not res:
        return []
    for name, text in res.items():
        (path.parent / name).write_text(text, encoding="utf-8")
    return sorted(res)


if __name__ == "__main__":
    for a in sys.argv[1:]:
        print(a, "->", split_file(Path(a)) or "fits, unchanged")
