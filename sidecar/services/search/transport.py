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

Neither lane lets its HTTP library follow redirects: both walk up to
:data:`MAX_REDIRECTS` hops by hand, and a caller-supplied ``url_allowed``
guard vets EVERY hop's target before it is requested (:func:`redirect_target`)
— so an SSRF guard that checked only the input URL can no longer be bypassed
by a public page that 302s to loopback / link-local / the LAN.

The curl_cffi import is deferred to call time: a missing/broken native wheel
must degrade that one fetch, never break ``services.search`` at import (the
PyInstaller onefile rule).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

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


class RedirectBlocked(TransportError):
    """A redirect pointed at a URL the caller's ``url_allowed`` guard refused."""


#: Redirect hops a lane follows by hand before giving up.
MAX_REDIRECTS = 5

#: Statuses that carry a ``Location`` to follow.
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})

#: A per-hop URL guard (e.g. the extractor's public-host SSRF check).
UrlGuard = Callable[[str], bool]


def redirect_target(
    current: str, status: int, location: str | None, url_allowed: UrlGuard | None
) -> str | None:
    """The absolute next hop for a redirect reply, or ``None`` when final.

    Raises :class:`RedirectBlocked` when ``url_allowed`` refuses the target —
    before any request to it is made.
    """
    if status not in _REDIRECT_STATUSES or not location:
        return None
    target = urljoin(current, location)
    if url_allowed is not None and not url_allowed(target):
        raise RedirectBlocked(f"redirect from {current} to a refused URL was blocked")
    return target


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
    url_allowed: UrlGuard | None = None,
) -> FetchResult:
    """Fetch via httpx (GET, or POST when ``data`` is given) — the friendly lane.

    ``client`` is injectable for tests/pooling; without one a one-shot client
    that does NOT auto-follow redirects is used, and redirects are walked here
    with every hop vetted by ``url_allowed`` (:func:`redirect_target`). A
    303/301/302 re-issues as GET; 307/308 keep the method and body. Raises
    :class:`TransportError` on any transport failure (HTTP statuses are
    returned, not raised — the caller decides what a 403/429 means for ITS
    engine) and :class:`RedirectBlocked` on a refused hop.
    """

    async def _go(http: httpx.AsyncClient) -> FetchResult:
        current, body, query = url, data, params
        for _ in range(MAX_REDIRECTS + 1):
            try:
                if body is not None:
                    resp = await http.post(
                        current, params=query, data=body, headers=_merged_headers(headers)
                    )
                else:
                    resp = await http.get(current, params=query, headers=_merged_headers(headers))
            except httpx.HTTPError as exc:
                raise TransportError(f"httpx transport failed for {url}: {exc}") from exc
            nxt = redirect_target(
                str(resp.url), resp.status_code, resp.headers.get("location"), url_allowed
            )
            if nxt is None:
                return FetchResult(
                    status_code=resp.status_code,
                    text=resp.text,
                    url=str(resp.url),
                    content_type=resp.headers.get("content-type", ""),
                )
            if resp.status_code not in (307, 308):
                body = None
            current, query = nxt, None
        raise TransportError(f"too many redirects for {url}")

    if client is not None:
        return await _go(client)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as http:
        return await _go(http)


async def impersonated_fetch(
    url: str,
    *,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECS,
    session: Any | None = None,
    url_allowed: UrlGuard | None = None,
) -> FetchResult:
    """Fetch with a Chrome TLS fingerprint via curl_cffi — the hostile-host lane.

    GET by default, POST when ``data`` is given. ``session`` is injectable for
    tests (anything with async ``get``/``post``). curl's own redirect following
    is off; redirects are walked here with every hop vetted by ``url_allowed``,
    exactly as :func:`httpx_fetch` does. Raises :class:`TransportError` when
    curl_cffi is unavailable or the request fails at transport level, and
    :class:`RedirectBlocked` on a refused hop.
    """

    async def _go(sess: Any) -> FetchResult:
        current, body, query = url, data, params
        for _ in range(MAX_REDIRECTS + 1):
            try:
                if body is not None:
                    resp = await sess.post(
                        current,
                        params=query,
                        data=body,
                        headers=_merged_headers(headers),
                        timeout=timeout,
                        allow_redirects=False,
                    )
                else:
                    resp = await sess.get(
                        current,
                        params=query,
                        headers=_merged_headers(headers),
                        timeout=timeout,
                        allow_redirects=False,
                    )
            except Exception as exc:  # curl_cffi raises its own exception zoo
                raise TransportError(f"impersonated transport failed for {url}: {exc}") from exc
            status = int(getattr(resp, "status_code", 0))
            resp_headers = getattr(resp, "headers", None) or {}
            final_url = str(getattr(resp, "url", current))
            nxt = redirect_target(final_url, status, resp_headers.get("location"), url_allowed)
            if nxt is None:
                return FetchResult(
                    status_code=status,
                    text=str(getattr(resp, "text", "")),
                    url=final_url,
                    content_type=str(resp_headers.get("content-type", "")),
                )
            if status not in (307, 308):
                body = None
            current, query = nxt, None
        raise TransportError(f"too many redirects for {url}")

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
    "MAX_REDIRECTS",
    "USER_AGENT",
    "FetchResult",
    "RedirectBlocked",
    "TransportError",
    "UrlGuard",
    "httpx_fetch",
    "impersonated_fetch",
    "redirect_target",
]
