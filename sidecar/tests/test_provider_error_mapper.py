"""R15-DATA-061: one ProviderError -> HTTP mapper for every data route (C5).

Each kind maps to its status with ``{detail: <sentence>, code, action}``; a
classified failure never shows the raw upstream text, an unclassified one keeps
the provider layer's own message.
"""

from __future__ import annotations

from pathlib import Path

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
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Class pin: the earnings routes used to flatten every kind to 502 in their
    own except blocks."""
    from services import data_cache, earnings_provider

    # A fresh AAPL history row in the machine's real cache would answer 200
    # before the provider is ever called.
    data_cache.reset_for_tests(tmp_path / "cache.db")

    async def throttled(_symbol: str) -> object:
        raise ProviderError("yfinance earnings rate-limited for 'AAPL'", kind="rate_limited")

    monkeypatch.setattr(earnings_provider, "get_history", throttled)
    try:
        resp = client.get("/earnings/AAPL/history")
    finally:
        data_cache.reset_for_tests()
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


def test_wrapped_http_404_is_a_404_not_a_502(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-DATA-061 (D-B9-1): an unclassified ProviderError is classified from its
    ``__cause__`` (the IMF upstream 404 was reported as a 502)."""
    import requests

    from services.macro import imf_provider

    def gone(_series_id: str) -> object:
        resp = requests.Response()
        resp.status_code = 404
        try:
            raise requests.HTTPError("404 Client Error: Not Found for url", response=resp)
        except requests.HTTPError as exc:
            raise ProviderError(f"IMF upstream error: {exc}") from exc

    monkeypatch.setattr(imf_provider, "get_series", gone)
    resp = client.get("/macro/DATA061.GONE", params={"provider": "imf"})
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
    assert "Client Error" not in resp.text


def test_wrapped_library_error_gets_a_generic_sentence(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A wrapped unclassified error never shows library text (the live
    ``/history/XYZ%2FABC`` 'Response' object case)."""

    def broken(*_a: object, **_k: object) -> object:
        try:
            raise AttributeError("'Response' object has no attribute 'get'")
        except AttributeError as exc:
            raise ProviderError(f"yfinance history failed for 'XYZ/ABC': {exc}") from exc

    monkeypatch.setattr(provider_registry, "get_history", broken)
    resp = client.get("/history/XYZ%2FABC")
    assert resp.status_code == 502
    body = resp.json()
    assert body["code"] == "provider_error"
    assert body["detail"] == "The data provider returned an unexpected response."
    assert "'Response' object" not in resp.text


def test_authored_message_without_a_cause_is_kept(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from services.macro import fred_provider

    def keyless(_series_id: str) -> object:
        raise ProviderError("FRED needs a free API key")

    monkeypatch.setattr(fred_provider, "get_series", keyless)
    resp = client.get("/macro/DATA061.KEYLESS", params={"provider": "fred"})
    assert resp.status_code == 502
    assert resp.json()["detail"] == "FRED needs a free API key"


def test_fundamentals_wrapped_connection_error_is_a_503(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Class pin on a route the fix was not written against."""
    import requests

    async def offline(*_a: object, **_k: object) -> object:
        try:
            raise requests.ConnectionError("HTTPSConnectionPool: Max retries exceeded")
        except requests.ConnectionError as exc:
            raise ProviderError(f"openbb fundamentals failed: {exc}") from exc

    monkeypatch.setattr(provider_registry, "get_fundamentals", offline)
    resp = client.get("/fundamentals/AAPL")
    assert resp.status_code == 503
    assert resp.json()["code"] == "network"
    assert "Max retries" not in resp.text
