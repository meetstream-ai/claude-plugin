"""Keep meeting chat away from powerful tools.

Meeting participants are identified only by the display name they choose, so a turn that comes from
meeting chat must not reach the terminal, files, code execution or anything that acts on the user's
accounts. Two layers, both on public plugin surfaces:

1. ``MeetStreamAdapter.toolsets_for_source`` returns ``MEETING_TOOLSETS``, so a meeting turn is built
   with web search only and no MCP servers (the gateway validates the list like a saved
   ``platform_toolsets`` entry; it replaces ``platform_toolsets.meetstream``).
2. Plugin toolsets (this plugin's join/leave/transcript tools, and any other plugin's) are added to
   every platform regardless of that list, so a ``pre_tool_call`` hook blocks every tool outside
   ``MEETING_TOOLS`` in sessions that ``pre_llm_call`` reported as coming from the meetstream platform.
"""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Any, Optional

PLATFORM = "meetstream"
MEETING_TOOLSETS = ["web", "no_mcp"]  # "no_mcp" is Hermes' sentinel for "no MCP servers"
MEETING_TOOLS = frozenset({"web_search", "web_extract"})
_MAX_TRACKED = 50_000  # far above concurrent meeting sessions; each hit refreshes its entry

# session_id / task_id of agent turns that run for meeting chat (bounded, oldest dropped first).
_MEETING_IDS: "OrderedDict[str, None]" = OrderedDict()
_MEETING_LOCK = Lock()


def _remember(*ids: str) -> None:
    with _MEETING_LOCK:
        for value in ids:
            if value:
                _MEETING_IDS[value] = None
                _MEETING_IDS.move_to_end(value)
        while len(_MEETING_IDS) > _MAX_TRACKED:
            _MEETING_IDS.popitem(last=False)


def _is_meetstream(platform: Any) -> bool:
    """True for ``"meetstream"``, ``Platform("meetstream")`` and ``"Platform.MEETSTREAM"``-style values."""
    value = getattr(platform, "value", platform)
    return str(value or "").strip().lower().rsplit(".", 1)[-1] == PLATFORM


def is_meeting_turn(session_id: str = "", task_id: str = "") -> bool:
    with _MEETING_LOCK:
        hits = [value for value in (session_id, task_id) if value and value in _MEETING_IDS]
        for value in hits:
            _MEETING_IDS.move_to_end(value)
        return bool(hits)


def on_pre_llm_call(session_id: str = "", task_id: str = "", platform: str = "", **_: Any) -> Optional[dict[str, str]]:
    """Fires once per turn, before any tool call: note the turns that come from meeting chat."""
    if _is_meetstream(platform):
        _remember(str(session_id or ""), str(task_id or ""))
        return None
    return {"context": (
        'For MeetStream meeting requests, load skill_view("meetstream:hermes-in-meetings") '
        "when available. Look up completed meetings and use decision_brief=true for requested notes on a new join. "
        "When decision_brief_queued is true, the durable gateway worker owns waiting, summarization "
        "and delivery to the requesting chat. Acknowledge the queued brief and finish this turn. "
        "Do not sleep, poll status, fetch the transcript or start a separate delegation to wait for "
        "that queued brief. A later user request for status or a transcript can use those tools. "
        "A pending chat artifact provides no evidence of live chat contents."
    )}


def on_pre_tool_call(tool_name: str = "", session_id: str = "", task_id: str = "",
                     **_: Any) -> Optional[dict[str, str]]:
    """Block every tool but web search in a meeting-chat turn. Never raises: Hermes lets a call
    through when a hook raises, so this stays a plain set lookup."""
    if tool_name in MEETING_TOOLS or not is_meeting_turn(str(session_id or ""), str(task_id or "")):
        return None
    return {"action": "block",
            "message": (f"{tool_name} is not available to requests from meeting chat: meeting participants "
                        "are not the user. Answer from the conversation or a web search, or ask the user to "
                        "run this outside the meeting.")}
