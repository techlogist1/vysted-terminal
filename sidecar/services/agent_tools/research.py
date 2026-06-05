"""Agent tool — ``research`` (the ONE research capability, depth-escalating).

After the R4 research collapse (FR-115 / SC-028) this is the SINGLE user-facing +
model-facing research capability. Depth is an INTERNAL escalation arg, not a user
knob, and "go deeper" escalates the SAME run in place:

- ``depth="quick"`` (default) → the fast, single-pass gather
  (:func:`services.research.fast.gather_fast`): resolve the symbol + fan out to the
  read-only data tools (news, quotes, fundamentals, filings) plus one web round and
  return one grounded bundle the model summarises. No inner LLM loop.
- ``depth="deep"`` → the IterResearch evolving-report loop (the ONE deep loop).
- ``depth="heavy"`` → the expert panel of parallel research angles.

``deep``/``heavy`` are served by :func:`services.agent_tools.deep_research.run_deep_brief`
(the internal DEEP engine — no longer a separate tool). The optional ``backend``
(``native`` | ``perplexity``) is internal too; Perplexity is opt-in-per-run, paid,
and NEVER auto-selected.

The research/deep-research service is imported lazily inside the call so the module
imports cleanly even before the service lands, and so the test suite can monkeypatch
the service in place.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool

#: The internal depth tiers, in escalation order. ``quick`` is the FAST single-pass
#: gather; ``deep``/``heavy`` run the ONE deep loop at increasing fan-out.
_DEPTHS = ("quick", "deep", "heavy")


def _normalize_depth(value: Any) -> str:
    """Coerce a depth arg to one of :data:`_DEPTHS`, defaulting to ``"quick"``.

    Tolerates legacy/loose values so an older agent prompt never dead-ends:
    ``"fast"`` → quick; ``"iter"`` → deep; ``True``/``"all out"`` → heavy.
    """
    if value is True:
        return "heavy"
    text = str(value or "").strip().lower()
    if text in _DEPTHS:
        return text
    if text in ("fast", ""):
        return "quick"
    if text in ("iter", "thorough", "single"):
        return "deep"
    if text in ("panel", "all out", "all-out"):
        return "heavy"
    return "quick"


async def _research(args: dict[str, Any]) -> dict[str, Any]:
    """Run research for ``query`` at the requested internal ``depth``.

    ``depth="quick"`` (default) gathers a grounded bundle in one pass; ``"deep"``/
    ``"heavy"`` run the budgeted deep loop. On a missing/blank query returns
    ``{"ok": False, "message": <human reason>}`` — never a raw error blob.
    """
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "message": "Research needs a query — tell me what to look into.",
        }
    query = query.strip()

    depth = _normalize_depth(args.get("depth"))

    if depth in ("deep", "heavy"):
        from services.agent_tools.deep_research import run_deep_brief

        return await run_deep_brief(
            query,
            depth=depth,
            rounds=args.get("rounds", 3),
            wall_seconds=args.get("wall_seconds", 120),
            backend=args.get("backend"),
            api_key=args.get("api_key"),
        )

    import config
    from services import agent_tools
    from services.research import fast

    return await fast.gather_fast(
        query,
        region=config.get_region(),
        tool_call=agent_tools.invoke_tool,
        # Forward steps LIVE to the runtime sink (Track A) so even the default
        # quick mode animates a working trace; ``None`` outside an agent run.
        on_step=config.get_step_sink(),
    )


def register() -> None:
    """Register the ``research`` tool in the package registry."""
    register_tool("research", _research)


__all__ = ["_research", "register"]
