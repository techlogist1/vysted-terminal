"""HTTP transports for the keyless T1 search tier (R7 Component 1).

Two lanes, chosen per host:

  * **httpx** — the friendly-host lane (Mojeek, most article pages). Pooled,
    boring, already a first-class sidecar dependency.
  * **curl_cffi impersonation** — ``curl_cffi.requests.AsyncSession(
    impersonate="chrome")`` presents a real Chrome TLS/JA3 fingerprint for
    hosts that fingerprint-block plain httpx (Brave's HTML SERP outright;
    DuckDuckGo intermittently with a 403). curl_cffi is already pinned in
    requirements.txt for the NSE providers, so this adds no new dependency.

Both lanes collapse to one :class:`FetchResult` shape (status + text + final
URL) so engine adapters and the full-page extractor parse one thing. A
transport-level failure raises :class:`TransportError` — the caller (engine
adapter / extractor) translates it into its own typed error; nothing here
fabricates an empty success.

The curl_cffi import is deferred to call time: a missing/broken native wheel
must degrade that one fetch, never break ``services.search`` at import (the
PyInstaller onefile rule).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

#: One desktop Chrome UA used on BOTH lanes so the header story matches the
#: TLS story (an impersonated TLS hello with a curl UA is its own tell).
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

#: Browser-shaped accept headers for HTML endpoints.
BROWSER_HEADERS: dict[str, str] = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.8",
}

DEFAULT_TIMEOUT_SECS = 12.0

#: The Chrome build curl_cffi impersonates ("chrome" tracks its newest profile).
IMPERSONATE_PROFILE = "chrome"


class TransportError(Exception):
    """A transport-level failure (DNS, TLS, timeout, broken impersonation lib)."""


@dataclass(slots=True)
class FetchResult:
    """The uniform reply both lanes produce."""

    status_code: int
    text: str
    url: str
    content_type: str = ""


def _merged_headers(headers: dict[str, str] | None) -> dict[str, str]:
    merged = dict(BROWSER_HEADERS)
    if headers:
        merged.update(headers)
    return merged


async def httpx_fetch(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECS,
    client: httpx.AsyncClient | None = None,
) -> FetchResult:
    """Fetch via httpx (GET, or POST when ``data`` is given) — the friendly lane.

    ``client`` is injectable for tests/pooling; without one a one-shot client
    with redirect-following is used. Raises :class:`TransportError` on any
    transport failure (HTTP statuses are returned, not raised — the caller
    decides what a 403/429 means for ITS engine).
    """

    async def _go(http: httpx.AsyncClient) -> FetchResult:
        try:
            if data is not None:
                resp = await http.post(
                    url, params=params, data=data, headers=_merged_headers(headers)
                )
            else:
                resp = await http.get(url, params=params, headers=_merged_headers(headers))
        except httpx.HTTPError as exc:
            raise TransportError(f"httpx transport failed for {url}: {exc}") from exc
        return FetchResult(
            status_code=resp.status_code,
            text=resp.text,
            url=str(resp.url),
            content_type=resp.headers.get("content-type", ""),
        )

    if client is not None:
        return await _go(client)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as http:
        return await _go(http)


async def impersonated_fetch(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECS,
    session: Any | None = None,
) -> FetchResult:
    """Fetch with a Chrome TLS fingerprint via curl_cffi — the hostile-host lane.

    GET by default, POST when ``data`` is given. ``session`` is injectable for
    tests (anything with async ``get``/``post``). Raises :class:`TransportError`
    when curl_cffi is unavailable or the request fails at transport level.
    """

    async def _go(sess: Any) -> FetchResult:
        try:
            if data is not None:
                resp = await sess.post(
                    url, params=params, data=data, headers=_merged_headers(headers), timeout=timeout
                )
            else:
                resp = await sess.get(
                    url, params=params, headers=_merged_headers(headers), timeout=timeout
                )
        except Exception as exc:  # curl_cffi raises its own exception zoo
            raise TransportError(f"impersonated transport failed for {url}: {exc}") from exc
        return FetchResult(
            status_code=int(getattr(resp, "status_code", 0)),
            text=str(getattr(resp, "text", "")),
            url=str(getattr(resp, "url", url)),
            content_type=str((getattr(resp, "headers", None) or {}).get("content-type", "")),
        )

    if session is not None:
        return await _go(session)
    try:
        from curl_cffi.requests import AsyncSession
    except Exception as exc:  # pragma: no cover — import is environment-dependent
        raise TransportError(f"curl_cffi unavailable: {exc}") from exc
    async with AsyncSession(impersonate=IMPERSONATE_PROFILE) as sess:
        return await _go(sess)


__all__ = [
    "BROWSER_HEADERS",
    "DEFAULT_TIMEOUT_SECS",
    "IMPERSONATE_PROFILE",
    "USER_AGENT",
    "FetchResult",
    "TransportError",
    "httpx_fetch",
    "impersonated_fetch",
]
