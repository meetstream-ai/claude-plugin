"""Hermes in Meetings: MeetStream meeting bots for Hermes Agent.

Tools to join Zoom / Google Meet / Teams calls and read their transcripts, a gateway platform for
meeting chat when it is available, and the ``hermes-in-meetings`` skill.
"""

from __future__ import annotations

from pathlib import Path

from . import adapter, guard, meetstream_tools as tools

_SKILLS = Path(__file__).resolve().parent / "skills"


def register(ctx) -> None:
    ctx.register_platform(
        name=adapter.PLATFORM, label="MeetStream (Hermes in Meetings)",
        adapter_factory=lambda cfg: adapter.MeetStreamAdapter(cfg, llm=getattr(ctx, "llm", None)),
        check_fn=adapter.check_requirements, validate_config=adapter.validate_config,
        is_connected=adapter.is_connected, required_env=[adapter.KEY_ENV],
        install_hint="no extra packages; httpx ships with Hermes",
        dashboard_description="Connect the MeetStream bot to the Hermes gateway. Live replies depend on live chat availability.",
        docs_url="https://github.com/meetstream-ai/hermes-meetstream#readme",
        allowed_users_env="MEETSTREAM_ALLOWED_USERS", allow_all_env="MEETSTREAM_ALLOW_ALL_USERS",
        max_message_length=adapter.api.MAX_CHAT, emoji="📞", pii_safe=False,
        allow_update_command=False, platform_hint=adapter.PLATFORM_HINT)
    for name, schema, handler, emoji in tools.TOOLS:
        ctx.register_tool(name=name, toolset="meetstream", schema=schema, handler=handler,
                          check_fn=tools.check_requirements, is_async=True,
                          description=schema["description"], emoji=emoji)
    ctx.register_hook("pre_llm_call", guard.on_pre_llm_call)
    ctx.register_hook("pre_tool_call", guard.on_pre_tool_call)
    ctx.register_hook("pre_tool_call", tools.schedule_approval)
    for skill_dir in sorted(p for p in _SKILLS.iterdir() if (p / "SKILL.md").is_file()):
        ctx.register_skill(skill_dir.name, skill_dir / "SKILL.md")
