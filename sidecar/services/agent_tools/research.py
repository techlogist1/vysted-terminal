"""Agent tool — ``research`` (the ONE research capability, depth-escalating).

After the R4 research collapse (FR-115 / SC-028) this is the SINGLE user-facing +
model-facing research capability. Depth is an INTERNAL escalation arg, not a user
knob, and "go deeper" escalates the SAME run in place. R7 names the depths
``normal`` | ``deep`` | ``ultra`` (the depth router in
:mod:`services.research.depth` is the ONE source of truth; legacy
``quick``/``heavy`` spellings map onto them forever):

- ``depth="normal"`` (default; legacy ``quick``) → the fast, single-pass gather
  (:func:`services.research.fast.gather_fast`): resolve the symbol + fan out to the
  read-only data tools (news, quotes, fundamentals, filings) plus one web round and
  return one grounded bundle the model summarises. No inner LLM loop.
- ``depth="deep"`` → the IterResearch evolving-report loop (the ONE deep loop),
  ~3 rounds × 3 researchers with the finance ``site:`` bias.
- ``depth="ultra"`` (legacy ``heavy``) → the expert panel of parallel research
  angles with stricter coverage (>=2 independent web domains) plus the numeric
  cross-check verification round.

Depth is per-query and ORTHOGONAL to the search tier (t1/t2/t3 — the tier rides
the request ContextVars; see :mod:`config`). ``deep``/``ultra`` are served by
:func:`services.agent_tools.deep_research.run_deep_brief` (the internal DEEP
engine — no longer a separate tool). The optional ``backend`` (``native`` |
``perplexity`` | ``sonar``) is internal too; the paid lanes are opt-in-per-run
and NEVER auto-selected.

The research/deep-research service is imported lazily inside the call so the module
imports cleanly even before the service lands, and so the test suite can monkeypatch
the service in place.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool


async def _research(args: dict[str, Any]) -> dict[str, Any]:
    """Run research for ``query`` at the requested internal ``depth``.

    ``depth="normal"`` (default) gathers a grounded bundle in one pass;
    ``"deep"``/``"ultra"`` run the budgeted deep loop at the profile's knobs.
    On a missing/blank query returns ``{"ok": False, "message": <human reason>}``
    — never a raw error blob.
    """
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {
            "ok": False,
            "message": "Research needs a query — tell me what to look into.",
        }
    query = query.strip()

    from services.research import depth as depth_mod

    depth = depth_mod.normalize_depth(args.get("depth"))

    if depth in (depth_mod.DEPTH_DEEP, depth_mod.DEPTH_ULTRA):
        from services.agent_tools.deep_research import run_deep_brief

        return await run_deep_brief(
            query,
            depth=depth,
            # ``None`` lets the depth profile supply the default (deep: 3 rounds
            # / 120s; ultra: 4 rounds / 240s); an explicit arg still wins.
            rounds=args.get("rounds"),
            wall_seconds=args.get("wall_seconds"),
            backend=args.get("backend"),
            api_key=args.get("api_key"),
        )

    import config
    from services import agent_tools
    from services.research import fast

    out = await fast.gather_fast(
        query,
        region=config.get_region(),
        tool_call=agent_tools.invoke_tool,
        # Forward steps LIVE to the runtime sink (Track A) so even the default
        # normal mode animates a working trace; ``None`` outside an agent run.
        on_step=config.get_step_sink(),
    )
    if isinstance(out, dict):
        out.setdefault("depth", depth_mod.DEPTH_NORMAL)
    return out


def register() -> None:
    """Register the ``research`` tool in the package registry."""
    register_tool("research", _research)


__all__ = ["_research", "register"]
