"""The deep-research wall clamp and the research schema follow ``depth.PROFILES``
(R15-CODE-RESEARCH-001): an explicit ULTRA wall is never cut below its own
profile, and the schema never advertises a ceiling below a profile's wall."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import pytest

from services.agent_tools import deep_research
from services.agent_tools.catalog import CAPABILITY_CATALOG
from services.research import depth as depth_mod


def _captured_wall(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> int:
    seen: dict[str, int] = {}

    async def fake_native(query: str, profile: Any, rounds: int, wall: int) -> dict[str, Any]:
        seen["wall"] = wall
        return {"ok": True}

    monkeypatch.setattr(deep_research, "_run_native", fake_native)
    asyncio.run(deep_research.run_deep_brief("RELIANCE", backend="native", **kwargs))
    return seen["wall"]


def test_explicit_ultra_wall_keeps_the_profile_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    ultra_wall = depth_mod.PROFILES[depth_mod.DEPTH_ULTRA].wall_seconds
    assert _captured_wall(monkeypatch, depth="ultra", wall_seconds=ultra_wall) == ultra_wall


def test_deep_without_wall_uses_the_profile_wall(monkeypatch: pytest.MonkeyPatch) -> None:
    assert (
        _captured_wall(monkeypatch, depth="deep")
        == depth_mod.PROFILES[depth_mod.DEPTH_DEEP].wall_seconds
    )


def test_research_schema_has_no_wall_default_and_covers_every_profile() -> None:
    wall_schema = CAPABILITY_CATALOG["research"].input_schema["properties"]["wall_seconds"]
    assert "default" not in wall_schema
    stated_max = int(re.match(r"30-(\d+)", wall_schema["description"]).group(1))
    assert all(stated_max >= p.wall_seconds for p in depth_mod.PROFILES.values())
