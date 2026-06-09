"""Tests for full-page extraction (``services.search.extract``). All offline."""

from __future__ import annotations

import asyncio

from services.search.extract import (
    fetch_page,
    is_public_http_url,
    visit_for_research,
)
from services.search.transport import FetchResult, TransportError

_ARTICLE = """
<html>
  <head><title>  NVDA   Deep Dive </title></head>
  <body>
    <nav><a href="/">Home</a> Site navigation junk</nav>
    <header>Big site header</header>
    <article>
      <h1>NVDA Deep Dive</h1>
      <p>Datacenter revenue grew 94% year over year, reaching new records.</p>
      <p>Gross margin expanded to 76%, driven by the Blackwell ramp.</p>
      <script>alert("should never appear")</script>
    </article>
    <aside>Related links junk</aside>
    <footer>Copyright footer junk. We use cookies — accept all cookies.</footer>
  </body>
</html>
"""

# No semantic containers, tiny divs — exercises the thin-content body fallback.
_LANDING = """
<html><head><title>App</title></head><body>
  <div class="hero">Welcome to the app landing page with a long description body
  that should be recovered from the whole-body fallback when no article exists.</div>
</body></html>
"""


def _fetcher(result: FetchResult, calls: list[str] | None = None):
    async def _fetch(url, **kw):  # noqa: ANN001, ANN202
        if calls is not None:
            calls.append(url)
        return result

    return _fetch


def _resolver_public(host: str) -> list[str]:
    return ["93.184.216.34"]


def _run(coro):
    return asyncio.run(coro)


def _page(html: str, **kw):
    fetched = FetchResult(
        status_code=200, text=html, url="https://example.com/a", content_type="text/html"
    )
    return _run(
        fetch_page(
            "https://example.com/a", fetch=_fetcher(fetched), resolver=_resolver_public, **kw
        )
    )


# --- SSRF guard -----------------------------------------------------------------


def test_non_http_scheme_blocked() -> None:
    assert is_public_http_url("file:///etc/passwd") is False
    assert is_public_http_url("ftp://example.com/x") is False


def test_localhost_and_internal_hostnames_blocked() -> None:
    assert is_public_http_url("http://localhost:8000/admin") is False
    assert is_public_http_url("http://metadata.google.internal/computeMetadata") is False
    assert is_public_http_url("http://router.lan/") is False


def test_private_literal_ips_blocked() -> None:
    for ip in ("127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "0.0.0.0"):
        assert is_public_http_url(f"http://{ip}/x") is False, ip


def test_hostname_resolving_private_blocked() -> None:
    assert (
        is_public_http_url("https://rebind.example.com/x", resolver=lambda h: ["127.0.0.1"])
        is False
    )


def test_public_hostname_allowed() -> None:
    assert is_public_http_url("https://example.com/x", resolver=_resolver_public) is True


def test_unresolvable_hostname_blocked() -> None:
    assert is_public_http_url("https://nx.example.com/x", resolver=lambda h: []) is False


def test_fetch_page_refuses_private_url_without_network() -> None:
    out = _run(fetch_page("http://127.0.0.1:8000/secrets"))
    assert out["ok"] is False and "blocked" in out["error"]


# --- extraction heuristics --------------------------------------------------------


def test_extracts_main_content_strips_chrome() -> None:
    out = _page(_ARTICLE)
    assert out["ok"] is True
    assert out["title"] == "NVDA Deep Dive"
    assert "Datacenter revenue grew 94%" in out["content"]
    assert "Gross margin expanded to 76%" in out["content"]
    # nav/header/footer/aside/script never leak into the content.
    for junk in ("navigation junk", "site header", "Related links", "alert(", "Copyright footer"):
        assert junk not in out["content"], junk
    assert out["truncated"] is False
    assert out["chars"] == len(out["content"])


def test_thin_semantic_pick_falls_back_to_body() -> None:
    out = _page(_LANDING)
    assert out["ok"] is True
    assert "landing page" in out["content"]


def test_cookie_boilerplate_paragraphs_dropped() -> None:
    html = _ARTICLE.replace(
        "<h1>NVDA Deep Dive</h1>",
        "<h1>NVDA Deep Dive</h1><p>We use cookies — accept all cookies to continue.</p>",
    )
    out = _page(html)
    assert "accept all cookies" not in out["content"]
    assert "Datacenter revenue" in out["content"]


def test_truncates_at_paragraph_boundary() -> None:
    out = _page(_ARTICLE, max_chars=80)
    assert out["ok"] is True
    assert out["truncated"] is True
    # The cut never lands mid-paragraph: content is whole paragraphs only.
    assert out["content"] in (
        "NVDA Deep Dive",
        "NVDA Deep Dive\n\nDatacenter revenue grew 94% year over year, reaching new records.",
    )


def test_oversized_first_paragraph_cut_at_sentence_end() -> None:
    long_para = "First sentence here. " * 30  # one giant paragraph
    html = f"<html><body><article><p>{long_para}</p></article></body></html>"
    out = _page(html, max_chars=100)
    assert out["ok"] is True and out["truncated"] is True
    assert len(out["content"]) <= 100
    assert out["content"].endswith("here.")  # sentence-end cut, not mid-word


def test_no_readable_content_is_honest_error() -> None:
    out = _page("<html><body><script>x()</script></body></html>")
    assert out["ok"] is False
    assert "no readable content" in out["error"]


# --- transport behavior -------------------------------------------------------------


def test_anti_bot_wall_falls_back_to_impersonation() -> None:
    walls: list[str] = []
    blocked = FetchResult(status_code=403, text="denied", url="u", content_type="text/html")
    fine = FetchResult(status_code=200, text=_ARTICLE, url="u", content_type="text/html")

    async def _walled(url, **kw):  # noqa: ANN001, ANN202
        return blocked

    async def _impersonated(url, **kw):  # noqa: ANN001, ANN202
        walls.append(url)
        return fine

    out = _run(
        fetch_page(
            "https://example.com/a",
            fetch=_walled,
            fallback_fetch=_impersonated,
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is True
    assert walls == ["https://example.com/a"]


def test_hard_http_error_is_honest() -> None:
    err = FetchResult(status_code=404, text="nope", url="u", content_type="text/html")
    out = _run(fetch_page("https://example.com/a", fetch=_fetcher(err), resolver=_resolver_public))
    assert out["ok"] is False and out["error"] == "HTTP 404"


def test_non_html_content_type_is_honest() -> None:
    pdf = FetchResult(status_code=200, text="%PDF-1.7", url="u", content_type="application/pdf")
    out = _run(
        fetch_page("https://example.com/a.pdf", fetch=_fetcher(pdf), resolver=_resolver_public)
    )
    assert out["ok"] is False and "unsupported content type" in out["error"]


def test_transport_error_is_honest() -> None:
    async def _boom(url, **kw):  # noqa: ANN001, ANN202
        raise TransportError("dns down")

    out = _run(fetch_page("https://example.com/a", fetch=_boom, resolver=_resolver_public))
    assert out["ok"] is False and "fetch failed" in out["error"]


# --- the research-shaped visit -------------------------------------------------------


def test_visit_for_research_returns_content(monkeypatch) -> None:  # noqa: ANN001
    from services.search import extract as extract_module

    async def _fake_fetch_page(url, *, max_chars):  # noqa: ANN001, ANN202
        return {"ok": True, "content": "Readable page text.", "url": url}

    monkeypatch.setattr(extract_module, "fetch_page", _fake_fetch_page)
    assert _run(visit_for_research("https://example.com/a")) == "Readable page text."


def test_visit_for_research_swallows_misses(monkeypatch) -> None:  # noqa: ANN001
    from services.search import extract as extract_module

    async def _fail(url, *, max_chars):  # noqa: ANN001, ANN202
        return {"ok": False, "error": "HTTP 404", "url": url}

    monkeypatch.setattr(extract_module, "fetch_page", _fail)
    assert _run(visit_for_research("https://example.com/a")) is None

    async def _raise(url, *, max_chars):  # noqa: ANN001, ANN202
        raise RuntimeError("boom")

    monkeypatch.setattr(extract_module, "fetch_page", _raise)
    assert _run(visit_for_research("https://example.com/a")) is None
