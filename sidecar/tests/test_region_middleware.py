"""Pass B (B1) — config.get_region + the ASGI region middleware (FR-060)."""

from __future__ import annotations

import asyncio

import config
from app import _RegionMiddleware


def test_normalize_region() -> None:
    assert config.normalize_region("IN") == "IN"
    assert config.normalize_region("in") == "IN"
    assert config.normalize_region("GLOBAL") == "GLOBAL"
    assert config.normalize_region("nonsense") == "US"
    assert config.normalize_region(None) == "US"
    assert config.normalize_region("") == "US"


def test_get_region_default_and_contextvar() -> None:
    assert config.get_region() == "US"
    token = config.set_request_region("IN")
    try:
        assert config.get_region() == "IN"
    finally:
        config.reset_request_region(token)
    assert config.get_region() == "US"


def test_middleware_sets_region_for_the_request() -> None:
    seen: dict[str, str] = {}

    async def inner_app(scope, receive, send):  # noqa: ANN001
        seen["region"] = config.get_region()

    mw = _RegionMiddleware(inner_app)

    async def drive(header_value: bytes | None) -> None:
        headers = [(b"x-vysted-region", header_value)] if header_value is not None else []
        scope = {"type": "http", "headers": headers}
        await mw(scope, None, None)

    asyncio.run(drive(b"IN"))
    assert seen["region"] == "IN"
    asyncio.run(drive(b"US"))
    assert seen["region"] == "US"
    asyncio.run(drive(None))  # no header → default US
    assert seen["region"] == "US"
    # The ContextVar is reset after the request — no leakage.
    assert config.get_region() == "US"


def test_middleware_passes_through_non_http() -> None:
    called = {"n": 0}

    async def inner_app(scope, receive, send):  # noqa: ANN001
        called["n"] += 1

    mw = _RegionMiddleware(inner_app)
    asyncio.run(mw({"type": "lifespan"}, None, None))
    assert called["n"] == 1
