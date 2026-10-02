"""R15-CODE-RESEARCH-008 — the hosted research lane's shared HTTP-status mapping.

``perplexity.py`` (direct Perplexity BYOK) and ``sonar.py`` (Perplexity Sonar
via OpenRouter) are one hosted-research lane sharing ``services.research.
perplexity._HostedResearchLane`` for request/response plumbing and HTTP status
mapping. Before the fix the two had drifted: 402 ("insufficient credits") was
handled only on the OpenRouter side, so a Perplexity-direct 402 fell through to
a generic "failed with HTTP 402". This pins BOTH constructors mapping the SAME
status set, incl. 402, to a human message that names the vendor and never
leaks the key or the raw vendor JSON.

Offline: each backend is given a stub ``httpx.AsyncClient`` (``MockTransport``)
that returns the given status — no live call, ever.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
import pytest

from services.research.perplexity import PerplexityDeepBackend
from services.research.sonar import OpenRouterSonarBackend
from services.search.base import SearchError


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


def _status_client(status: int) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": {"message": "vendor detail"}})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


#: status -> a lowercase substring every lane's message must carry for it.
_STATUS_NEEDLES = {
    401: "key",
    402: "credits",
    403: "key",
    429: "rate limit",
    400: "bad query",
    500: "unavailable",
    503: "unavailable",
}


@pytest.mark.parametrize("status", sorted(_STATUS_NEEDLES))
def test_both_lanes_map_the_same_status_set_incl_402(status: int) -> None:
    needle = _STATUS_NEEDLES[status]
    perplexity_key = "pplx-secret-key"
    sonar_key = "sk-or-secret-key"

    perplexity_backend = PerplexityDeepBackend(perplexity_key, client=_status_client(status))
    with pytest.raises(SearchError) as perplexity_exc:
        _run(perplexity_backend.research("q"))
    perplexity_message = str(perplexity_exc.value)

    sonar_backend = OpenRouterSonarBackend(sonar_key, client=_status_client(status))
    with pytest.raises(SearchError) as sonar_exc:
        _run(sonar_backend.research("q"))
    sonar_message = str(sonar_exc.value)

    # Same status -> the same human-readable shape, differing only by vendor.
    assert needle in perplexity_message.lower(), perplexity_message
    assert needle in sonar_message.lower(), sonar_message
    assert "Perplexity" in perplexity_message
    assert "OpenRouter" in sonar_message

    # Never the raw vendor JSON, never the key, on either lane.
    for message, key in ((perplexity_message, perplexity_key), (sonar_message, sonar_key)):
        assert "{" not in message
        assert key not in message
        assert "vendor detail" not in message


def test_perplexity_402_is_no_longer_a_generic_fallback() -> None:
    # R15-CODE-RESEARCH-008: before the fix, Perplexity's 402 fell through to
    # the module's generic "failed with HTTP {status}" fallback message.
    backend = PerplexityDeepBackend("pplx-secret-key", client=_status_client(402))
    with pytest.raises(SearchError) as exc:
        _run(backend.research("q"))
    message = str(exc.value)
    assert "insufficient credits" in message.lower()
    assert "failed with HTTP 402" not in message
