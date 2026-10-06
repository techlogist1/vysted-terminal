"""R7 depth router — the ONE source of truth for NORMAL / DEEP / ULTRA.

Depth is the per-query "how hard to think" knob, ORTHOGONAL to the search tier
(t1_local / t2_searxng / t3_hosted — :mod:`config`). The surface naming is
``normal`` / ``deep`` / ``ultra``; each maps onto one of the three existing,
proven loops rather than a new one (the loops are good — R7 rebuilds what is
AROUND them):

  ========  ========  ====================================================
  depth     loop      what runs
  ========  ========  ====================================================
  NORMAL    fast      :func:`services.research.fast.gather_fast` — the
                      NO-LLM structured bundle + one web round; the agent
                      writes the prose.
  DEEP      iter      :func:`services.research.iter.run_iter_research` —
                      the IterResearch evolving-report loop (~3 rounds ×
                      3 researchers).
  ULTRA     heavy     :func:`services.research.iter.run_heavy_research` —
                      the expert panel (3 angles × iter) with STRICTER
                      coverage (>=2 independent web domains) plus the
                      numeric cross-check verification round
                      (:mod:`services.research.verify`).
  ========  ========  ====================================================

Every knob the loops expose scales with depth through ONE
:class:`DepthProfile` table — rounds, researcher fan-out, panel width, the
iter working-report char cap, the default wall budget, coverage strictness,
the finance ``site:`` query bias, and whether the cross-check round runs.
Callers resolve a profile via :func:`profile_for` and thread its fields; the
panel threshold is :data:`PANEL_MIN_ANGLES` here too (read via
:attr:`DepthProfile.is_panel` and by the heavy loop's angle clamp). The hosted
research-model lane's wall/cost tables in
:mod:`services.agent_tools.deep_research` are that separate engine's own
knobs, not copies of these.

Legacy spellings stay accepted forever (``quick`` → normal, ``heavy`` →
ultra, plus the loose aliases the old tool tolerated) so an older agent
prompt or the current catalog enum never dead-ends.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

DEPTH_NORMAL = "normal"
DEPTH_DEEP = "deep"
DEPTH_ULTRA = "ultra"

#: The canonical depth ids, in escalation order.
DEPTHS = (DEPTH_NORMAL, DEPTH_DEEP, DEPTH_ULTRA)

#: Loose/legacy spellings → canonical depth. ``quick``/``heavy`` are the
#: pre-R7 tier names (still emitted by the catalog schema until the lead
#: updates it); the rest are the tolerated aliases of the old normalizer.
_ALIASES: dict[str, str] = {
    "": DEPTH_NORMAL,
    "quick": DEPTH_NORMAL,
    "fast": DEPTH_NORMAL,
    "n": DEPTH_NORMAL,
    "iter": DEPTH_DEEP,
    "thorough": DEPTH_DEEP,
    "single": DEPTH_DEEP,
    "d": DEPTH_DEEP,
    "heavy": DEPTH_ULTRA,
    "panel": DEPTH_ULTRA,
    "all out": DEPTH_ULTRA,
    "all-out": DEPTH_ULTRA,
    "u": DEPTH_ULTRA,
}


def normalize_depth(value: Any) -> str:
    """Coerce any depth spelling to one of :data:`DEPTHS` (default ``normal``).

    Tolerant by design — a malformed/legacy depth must never break a research
    call; an unknown value floors to the cheap NORMAL pass, never silently to
    a more expensive one.
    """
    if value is True:
        return DEPTH_ULTRA
    text = str(value or "").strip().lower()
    if text in DEPTHS:
        return text
    return _ALIASES.get(text, DEPTH_NORMAL)


#: The panel threshold: a profile with at least this many angles runs the heavy
#: expert panel, and the panel never runs narrower than this.
PANEL_MIN_ANGLES = 2


#: SC-016: a research brief cites at least this many distinct sources.
MIN_CITED_SOURCES = 3


def source_floor_leg(urls: Iterable[Any]) -> dict[str, Any]:
    """The brief's distinct cited sources measured against the SC-016 floor, as a
    ``structured`` leg (R15-RESEARCH-042). Below the floor its ``note`` is the
    honest "N sources (below 3)" marker instead of the brief asserting nothing."""
    cited = len({u for u in urls if isinstance(u, str) and u})
    leg: dict[str, Any] = {
        "ok": True,
        "provider": "derived",
        "data": {"cited": cited, "floor": MIN_CITED_SOURCES},
    }
    if cited < MIN_CITED_SOURCES:
        leg["note"] = f"{cited} source{'' if cited == 1 else 's'} (below {MIN_CITED_SOURCES})"
    return leg


@dataclass(frozen=True, slots=True)
class DepthProfile:
    """The scaled knob set one depth runs with — read-only, table-driven."""

    #: Canonical depth id (``normal`` / ``deep`` / ``ultra``).
    depth: str
    #: Which loop serves it: ``fast`` | ``iter`` | ``heavy``.
    loop: str
    #: Research rounds budgeted for the loop (sizes the step ceiling).
    rounds: int
    #: Researcher fan-out per round.
    researchers: int
    #: Heavy-panel width (1 = no panel; >=2 = the expert panel).
    angles: int
    #: Char cap on the iter working report (0 = n/a for the fast pass).
    report_char_cap: int
    #: Default wall-clock budget in seconds (0 = n/a for the fast pass).
    wall_seconds: int
    #: Coverage strictness — distinct web DOMAINS required before the loop
    #: may declare the floor met (independence, not just volume).
    min_web_domains: int
    #: Whether the post-synthesis numeric cross-check round runs (ULTRA).
    cross_check: bool
    #: Whether researcher web queries carry the finance ``site:`` bias
    #: toward exchange/regulator/filings domains (DEEP/ULTRA rounds).
    site_bias: bool
    #: Token ceiling for the run's research LLM calls (0 = n/a: the fast pass
    #: makes none). A breach takes the loop's abort→synthesize path.
    max_tokens: int
    #: Estimated-spend ceiling in USD (0 = n/a), priced by
    #: :func:`services.budget_guard.estimate_spend_usd` per metered call.
    max_spend_usd: float

    @property
    def is_panel(self) -> bool:
        """Whether this depth runs the heavy expert panel."""
        return self.angles >= PANEL_MIN_ANGLES


#: THE depth table. Change a knob here and every surface (tool, router,
#: loops, tests) follows — there is no second copy.
PROFILES: dict[str, DepthProfile] = {
    DEPTH_NORMAL: DepthProfile(
        depth=DEPTH_NORMAL,
        loop="fast",
        rounds=0,
        researchers=0,
        angles=1,
        report_char_cap=0,
        wall_seconds=0,
        min_web_domains=0,
        cross_check=False,
        site_bias=False,
        max_tokens=0,
        max_spend_usd=0.0,
    ),
    DEPTH_DEEP: DepthProfile(
        depth=DEPTH_DEEP,
        loop="iter",
        rounds=3,
        researchers=3,
        angles=1,
        report_char_cap=6000,
        # 120 -> 180 (R13): a live DEEP run on the funded OpenRouter lane spent
        # 60s of its first 90s round slice on PLANNING alone, starving the
        # researchers; the run wound down with "no findings". The round-1 planning
        # LLM turn is now skipped (iter seeds the fan-out deterministically) AND
        # the round slice adapts to observed LLM latency — this wall bump gives
        # those two fixes real headroom for a genuine second round. Report cap
        # unchanged (the brief length is the same; only the time budget grew).
        wall_seconds=180,
        min_web_domains=1,
        cross_check=False,
        site_bias=True,
        # ~20 calls a run (plan + 3 distills + reflect per round over 3 rounds,
        # synthesis, citecheck) at <=10k tokens each is ~200k; the ceilings give
        # 3x headroom and stop a runaway loop on a premium model near $3.
        max_tokens=600_000,
        max_spend_usd=3.0,
    ),
    DEPTH_ULTRA: DepthProfile(
        depth=DEPTH_ULTRA,
        loop="heavy",
        rounds=4,
        researchers=3,
        angles=3,
        report_char_cap=9000,
        # 240 -> 360 (R9, V14): two live ULTRA runs showed the heavy panel
        # consuming the wall and the cross-check round honestly skipping; the
        # verification round is ULTRA's point, so it gets real headroom.
        wall_seconds=360,
        min_web_domains=2,
        cross_check=True,
        site_bias=True,
        # The panel is 3 angles of the DEEP loop plus the lead synthesis and
        # the cross-check round: 3x DEEP's ceilings.
        max_tokens=1_800_000,
        max_spend_usd=9.0,
    ),
}


def profile_for(value: Any) -> DepthProfile:
    """Resolve any depth spelling to its :class:`DepthProfile`."""
    return PROFILES[normalize_depth(value)]


__all__ = [
    "DEPTH_DEEP",
    "DEPTH_NORMAL",
    "DEPTH_ULTRA",
    "DEPTHS",
    "MIN_CITED_SOURCES",
    "PROFILES",
    "PANEL_MIN_ANGLES",
    "DepthProfile",
    "normalize_depth",
    "profile_for",
    "source_floor_leg",
]
