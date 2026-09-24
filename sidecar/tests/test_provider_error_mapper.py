"""R15-DATA-061: one ProviderError -> HTTP mapper for every data route (C5).

Each kind maps to its status with ``{detail: <sentence>, code, action}``; a
classified failure never shows the raw upstream text, an unclassified one keeps
the provider layer's own message.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from models.market import Quote
from services import provider_registry
from services.errors import ProviderError

_RAW = "'PriceHistory' object has no attribute '_dividends'"


@pytest.mark.parametrize(
    ("kind", "status"),
    [("rate_limited", 429), ("not_found", 404), ("network", 503), (None, 502)],
)
def test_each_kind_maps_to_its_status_and_body(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, kind: str | None, status: int
) -> None:
    def boom(*_args: object, **_kwargs: object) -> Quote:
        raise ProviderError(f"yfinance quote failed for 'ZZZ': {_RAW}", kind=kind)  # type: ignore[arg-type]

    monkeypatch.setattr(provider_registry, "get_quote", boom)
    resp = client.get("/quotes/ZZZ")
    assert resp.status_code == status
    body = resp.json()
    assert isinstance(body["detail"], str) and body["detail"]
    assert body["code"] == (kind or "provider_error")
    assert isinstance(body["action"], str) and body["action"]
    if kind is not None:
        assert _RAW not in body["detail"]


def test_earnings_throttle_is_a_429_not_a_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Class pin: the earnings routes used to flatten every kind to 502 in their
    own except blocks."""
    from services import earnings_provider

    async def throttled(_symbol: str) -> object:
        raise ProviderError("yfinance earnings rate-limited for 'AAPL'", kind="rate_limited")

    monkeypatch.setattr(earnings_provider, "get_history", throttled)
    resp = client.get("/earnings/AAPL/history")
    assert resp.status_code == 429
    assert resp.json()["code"] == "rate_limited"


def test_macro_not_found_is_a_404_not_a_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Class pin: the macro routes' own blocks flattened a FRED not_found to 502."""
    from services.macro import fred_provider

    def missing(_series_id: str) -> object:
        raise ProviderError("FRED has no series 'NOPE'", kind="not_found")

    monkeypatch.setattr(fred_provider, "get_series", missing)
    resp = client.get("/macro/NOPE", params={"provider": "fred"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
