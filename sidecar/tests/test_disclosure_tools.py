"""The disclosure agent tools (``corporate_announcements``,
``shareholding_pattern``): the announcements cache lives in the service, so the
tool, research and the panel route share one fetch (R15-DATA-074)."""

from __future__ import annotations

import asyncio
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.announcements import AnnouncementWindow
from routers import disclosures
from services import corporate_disclosures, data_cache, symbol_resolver
from services.agent_tools import disclosure_tools


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield tmp_path
    data_cache.reset_for_tests()


@pytest.fixture
def lane_calls(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Count the exchange-lane fetches behind the merged feed."""
    calls: list[str] = []

    def lane(name: str):  # noqa: ANN202
        def fetch(bare: str, limit: int):  # noqa: ANN202
            calls.append(name)
            return [], AnnouncementWindow(window_start=None, window_end=date(2026, 9, 23))

        return fetch

    monkeypatch.setattr(symbol_resolver, "is_nse_symbol", lambda s: True)
    monkeypatch.setattr(symbol_resolver, "is_bse_symbol", lambda s: True)
    monkeypatch.setattr(corporate_disclosures, "_fetch_nse_announcements", lane("NSE"))
    monkeypatch.setattr(corporate_disclosures, "_fetch_bse_announcements", lane("BSE"))
    return calls


def test_two_tool_calls_fetch_the_lanes_once(lane_calls: list[str]) -> None:
    for _ in range(2):
        result = asyncio.run(disclosure_tools._corporate_announcements({"symbol": "RELIANCE"}))
        assert result["ok"] is True
    assert lane_calls == ["NSE", "BSE"]


def test_router_then_tool_fetch_the_lanes_once(lane_calls: list[str]) -> None:
    app = FastAPI()
    app.include_router(disclosures.router)
    resp = TestClient(app).get(
        "/disclosures/announcements", params={"symbol": "RELIANCE", "limit": 20}
    )
    assert resp.status_code == 200

    result = asyncio.run(
        disclosure_tools._corporate_announcements({"symbol": "RELIANCE", "limit": 20})
    )
    assert result["ok"] is True
    assert lane_calls == ["NSE", "BSE"]
