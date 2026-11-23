"""Capture and resolve a brief's private messaging destination."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from gateway.platforms.plugin_delivery import capture_private_origin, resolve_private_delivery
except ImportError:  # Earlier Hermes builds can still deliver briefs into local history.
    capture_private_origin = resolve_private_delivery = None

PLATFORMS = frozenset({"telegram", "whatsapp"})


def capture_origin(session_id: str, stored_source: str | None) -> dict | None:
    if stored_source not in PLATFORMS or capture_private_origin is None:
        return None
    origin = capture_private_origin(session_id)
    return origin if origin and origin["platform"] == stored_source else None


def resolve_sender(runner, origin: dict, profile: str | None):
    """Keep the brief in one transport message at the captured private destination."""
    if resolve_private_delivery is None or origin.get("platform") not in PLATFORMS:
        return None
    target = resolve_private_delivery(runner, origin, profile=profile)
    if target is None:
        return None
    telegram_root = origin["platform"] == "telegram" and not origin.get("thread_id")

    async def send(text: str):
        if telegram_root and len(text.encode("utf-16-le")) > 3600:
            with TemporaryDirectory(prefix="hermes-meetstream-") as directory:
                path = Path(directory) / "decision-brief.txt"
                path.write_text(text, encoding="utf-8")
                return await target.send_document(str(path), caption="MeetStream decision brief")
        return await target.send(one_message(text))

    return send


def one_message(text: str) -> str:
    """Keep a phone notification in one platform message. The saved history keeps the full brief."""
    if len(text.encode("utf-16-le")) // 2 <= 1800:
        return text
    clipped = text.encode("utf-16-le")[:3400].decode("utf-16-le", errors="ignore")
    return (clipped.rsplit("\n", 1)[0] or clipped).rstrip() + "\n\nThe full brief is saved in Hermes history."
