"""Tests for the static-IP detector (Kite Connect UX surface)."""

from __future__ import annotations

import httpx
import pytest

from services import static_ip_detector


def _mock_transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_detect_returns_clean_ip() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="203.0.113.42")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        ip = await static_ip_detector.detect_public_ip(client=client)
    assert ip == "203.0.113.42"


@pytest.mark.asyncio
async def test_detect_returns_none_on_non_200() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="server down")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        ip = await static_ip_detector.detect_public_ip(client=client)
    assert ip is None


@pytest.mark.asyncio
async def test_detect_returns_none_on_malformed_body() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not an ip at all")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        ip = await static_ip_detector.detect_public_ip(client=client)
    assert ip is None


@pytest.mark.asyncio
async def test_detect_returns_none_on_network_error() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unreachable")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        ip = await static_ip_detector.detect_public_ip(client=client)
    assert ip is None


# ---------------------------------------------------------------------------
# status comparison
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_status_matches_when_detected_equals_configured() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="203.0.113.42")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        status = await static_ip_detector.static_ip_status("203.0.113.42", client=client)
    assert status.matches is True
    assert status.detected_ip == "203.0.113.42"
    assert status.configured_ip == "203.0.113.42"


@pytest.mark.asyncio
async def test_status_mismatch_when_detected_differs() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="10.0.0.1")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        status = await static_ip_detector.static_ip_status("203.0.113.42", client=client)
    assert status.matches is False
    assert "differs from the configured" in status.message


@pytest.mark.asyncio
async def test_status_when_no_configured_ip() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="203.0.113.42")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        status = await static_ip_detector.static_ip_status(None, client=client)
    assert status.matches is False
    assert "No static IP configured" in status.message


@pytest.mark.asyncio
async def test_status_when_detection_fails() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("network unreachable")

    async with httpx.AsyncClient(transport=_mock_transport(_handler)) as client:
        status = await static_ip_detector.static_ip_status("203.0.113.42", client=client)
    assert status.matches is False
    assert status.detected_ip is None
    assert "Could not detect public IP" in status.message
