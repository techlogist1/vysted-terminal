"""Tests for the dual-lane search transport (``services.search.transport``)."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from services.search.transport import (
    BROWSER_HEADERS,
    FetchResult,
    TransportError,
    httpx_fetch,
    impersonated_fetch,
)


def _run(coro):
    return asyncio.run(coro)


# --- httpx lane ---------------------------------------------------------------


class _FakeHttpxResponse:
    def __init__(self, status: int = 200, text: str = "<html>ok</html>") -> None:
        self.status_code = status
        self.text = text
        self.url = "https://www.mojeek.com/search?q=x"
        self.headers = {"content-type": "text/html; charset=utf-8"}


class _FakeHttpxClient:
    def __init__(self, resp: _FakeHttpxResponse | None = None, exc: Exception | None = None):
        self._resp = resp or _FakeHttpxResponse()
        self._exc = exc
        self.calls: list[dict] = []

    async def get(self, url, params=None, headers=None):  # noqa: ANN001, ANN201
        self.calls.append({"method": "GET", "url": url, "params": params, "headers": headers})
        if self._exc:
            raise self._exc
        return self._resp

    async def post(self, url, params=None, data=None, headers=None):  # noqa: ANN001, ANN201
        self.calls.append({"method": "POST", "url": url, "data": data, "headers": headers})
        if self._exc:
            raise self._exc
        return self._resp


def test_httpx_fetch_get_returns_uniform_result() -> None:
    client = _FakeHttpxClient()
    out = _run(httpx_fetch("https://www.mojeek.com/search", params={"q": "x"}, client=client))
    assert isinstance(out, FetchResult)
    assert out.status_code == 200
    assert "ok" in out.text
    assert out.content_type.startswith("text/html")
    assert client.calls[0]["method"] == "GET"
    # Browser-shaped headers ride every request.
    assert client.calls[0]["headers"]["User-Agent"] == BROWSER_HEADERS["User-Agent"]


def test_httpx_fetch_post_when_data_given() -> None:
    client = _FakeHttpxClient()
    _run(httpx_fetch("https://html.duckduckgo.com/html/", data={"q": "x"}, client=client))
    assert client.calls[0]["method"] == "POST"
    assert client.calls[0]["data"] == {"q": "x"}


def test_httpx_fetch_blocked_status_is_returned_not_raised() -> None:
    client = _FakeHttpxClient(_FakeHttpxResponse(status=403, text="denied"))
    out = _run(httpx_fetch("https://x", client=client))
    assert out.status_code == 403  # the ENGINE decides what a 403 means


def test_httpx_fetch_transport_failure_raises_transport_error() -> None:
    client = _FakeHttpxClient(exc=httpx.ConnectError("dns down"))
    with pytest.raises(TransportError):
        _run(httpx_fetch("https://x", client=client))


def test_httpx_fetch_caller_headers_override_defaults() -> None:
    client = _FakeHttpxClient()
    _run(httpx_fetch("https://x", headers={"Accept": "application/json"}, client=client))
    assert client.calls[0]["headers"]["Accept"] == "application/json"
    assert "User-Agent" in client.calls[0]["headers"]


# --- impersonated (curl_cffi) lane ---------------------------------------------


class _FakeImpersonatedResponse:
    status_code = 200
    text = "<html>brave</html>"
    url = "https://search.brave.com/search?q=x"
    headers = {"content-type": "text/html"}


class _FakeSession:
    def __init__(self, resp=None, exc: Exception | None = None) -> None:  # noqa: ANN001
        self._resp = resp or _FakeImpersonatedResponse()
        self._exc = exc
        self.calls: list[dict] = []

    async def get(self, url, params=None, headers=None, timeout=None):  # noqa: ANN001, ANN201
        self.calls.append({"method": "GET", "url": url, "params": params, "headers": headers})
        if self._exc:
            raise self._exc
        return self._resp

    async def post(self, url, params=None, data=None, headers=None, timeout=None):  # noqa: ANN001, ANN201
        self.calls.append({"method": "POST", "url": url, "data": data})
        if self._exc:
            raise self._exc
        return self._resp


def test_impersonated_fetch_uses_injected_session() -> None:
    session = _FakeSession()
    out = _run(
        impersonated_fetch("https://search.brave.com/search", params={"q": "x"}, session=session)
    )
    assert out.status_code == 200
    assert "brave" in out.text
    assert session.calls[0]["method"] == "GET"
    assert session.calls[0]["headers"]["User-Agent"] == BROWSER_HEADERS["User-Agent"]


def test_impersonated_fetch_post_when_data_given() -> None:
    session = _FakeSession()
    _run(impersonated_fetch("https://html.duckduckgo.com/html/", data={"q": "x"}, session=session))
    assert session.calls[0]["method"] == "POST"


def test_impersonated_fetch_failure_raises_transport_error() -> None:
    session = _FakeSession(exc=RuntimeError("curl blew up"))
    with pytest.raises(TransportError):
        _run(impersonated_fetch("https://x", session=session))


def test_impersonated_fetch_real_session_constructs() -> None:
    # The real curl_cffi AsyncSession must be constructible offline (no request
    # is made) — guards the PyInstaller/native-lib packaging story.
    from curl_cffi.requests import AsyncSession

    async def _go() -> bool:
        async with AsyncSession(impersonate="chrome") as sess:
            return sess is not None

    assert _run(_go()) is True
