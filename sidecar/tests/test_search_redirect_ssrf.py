"""R15-DATA-045: every redirect hop is re-checked by the SSRF guard, in every lane.

A real local HTTP server plays both roles: ``/start`` (standing in for a public
page) answers 302 to ``http://127.0.0.1:<port>/secret``. The guard must refuse
that hop before any request to it, so the secret handler is never hit.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest

from services.search import extract
from services.search.extract import fetch_page, is_public_http_url
from services.search.transport import RedirectBlocked, httpx_fetch, impersonated_fetch


def _public(host: str) -> list[str]:
    return ["93.184.216.34"]


@pytest.fixture
def redirect_server() -> Iterator[dict[str, Any]]:
    state: dict[str, Any] = {"secret_hits": 0}

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 — stdlib hook name
            if self.path.startswith("/start"):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{state['port']}/secret")
                self.end_headers()
                return
            if self.path == "/secret":
                state["secret_hits"] += 1
                body = b"<html><body><main><p>INTERNAL SECRET</p></main></body></html>"
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(404)
            self.end_headers()

        def log_message(self, *args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    state["port"] = server.server_address[1]
    state["base"] = f"http://127.0.0.1:{state['port']}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()


def test_fetch_page_blocks_a_public_page_that_redirects_to_loopback(redirect_server) -> None:
    async def _via_local(url: str, **kw: Any):
        # The "public" page is served by the local test server.
        return await httpx_fetch(f"{redirect_server['base']}/start", **kw)

    out = asyncio.run(
        fetch_page("https://public.example/article", fetch=_via_local, resolver=_public)
    )
    assert out["ok"] is False
    assert "blocked redirect" in out["error"]
    assert redirect_server["secret_hits"] == 0


def test_pdf_lane_blocks_the_same_redirect(redirect_server) -> None:
    async def _via_local(url: str, **kw: Any):
        return await extract._default_pdf_fetch(f"{redirect_server['base']}/start.pdf", **kw)

    out = asyncio.run(
        fetch_page("https://public.example/report.pdf", pdf_fetch=_via_local, resolver=_public)
    )
    assert out["ok"] is False
    assert "blocked redirect" in out["error"]
    assert redirect_server["secret_hits"] == 0


def test_impersonated_lane_blocks_the_same_redirect(redirect_server) -> None:
    with pytest.raises(RedirectBlocked):
        asyncio.run(
            impersonated_fetch(f"{redirect_server['base']}/start", url_allowed=is_public_http_url)
        )
    assert redirect_server["secret_hits"] == 0


def test_an_allowed_redirect_is_still_followed(redirect_server) -> None:
    """The walk still follows a hop the guard accepts (engines pass no guard)."""
    out = asyncio.run(httpx_fetch(f"{redirect_server['base']}/start"))
    assert out.status_code == 200
    assert out.url.endswith("/secret")
    assert redirect_server["secret_hits"] == 1
