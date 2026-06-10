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
    img = FetchResult(status_code=200, text="\x89PNG", url="u", content_type="image/png")
    out = _run(
        fetch_page("https://example.com/logo", fetch=_fetcher(img), resolver=_resolver_public)
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


# --- PDF extraction (R8) -------------------------------------------------------------


def _pdf_bytes(pages: list[str]) -> bytes:
    """Build a real text-bearing PDF in-test via the pypdf writer."""
    import io

    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        ops = ["BT", "/F1 12 Tf", "72 720 Td"]
        for i, line in enumerate(text.split("\n")):
            safe = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
            if i:
                ops.append("0 -16 Td")
            ops.append(f"({safe}) Tj")
        ops.append("ET")
        stream = DecodedStreamObject()
        stream.set_data("\n".join(ops).encode("latin-1"))
        stream_ref = writer._add_object(stream)
        font = DictionaryObject(
            {
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            }
        )
        font_ref = writer._add_object(font)
        page[NameObject("/Contents")] = stream_ref
        page[NameObject("/Resources")] = DictionaryObject(
            {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font_ref})}
        )
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


_RESULTS_PDF_PAGES = [
    "Saksoft Limited - Unaudited Financial Results\nFor the quarter ended 31 March 2026",
    "Revenue from operations grew 23% to Rs 1,234 crore.\n"
    "PAT stood at Rs 210 crore for the quarter.\n"
    "The Board declared a dividend of Rs 5 per share.",
]


def _pdf_fetcher(data: bytes, status: int = 200, calls: list[str] | None = None):
    async def _fetch(url):  # noqa: ANN001, ANN202
        if calls is not None:
            calls.append(url)
        return status, data

    return _fetch


def test_pdf_url_extracts_seeded_numbers() -> None:
    """The ROUTE Q4 regression: a results-filing PDF in hand must yield its
    numbers — not an 'unsupported content type' miss that becomes 'no
    quarterly results announced' in the brief."""
    data = _pdf_bytes(_RESULTS_PDF_PAGES)
    out = _run(
        fetch_page(
            "https://nsearchives.nseindia.com/corporate/results_q4.pdf",
            pdf_fetch=_pdf_fetcher(data),
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is True
    assert out["content_type"] == "application/pdf"
    assert "Rs 1,234 crore" in out["content"]
    assert "23%" in out["content"]
    assert "dividend of Rs 5 per share" in out["content"]


def test_pdf_content_type_without_pdf_path_rides_the_byte_lane() -> None:
    """A BSE attachment URL (no .pdf extension) served as application/pdf is
    refetched on the byte lane rather than parsed as mangled text."""
    served = FetchResult(
        status_code=200, text="%PDF-mangled", url="u", content_type="application/pdf"
    )
    calls: list[str] = []
    out = _run(
        fetch_page(
            "https://www.bseindia.com/xml-data/corpfiling/AttachHis/abc123",
            fetch=_fetcher(served),
            pdf_fetch=_pdf_fetcher(_pdf_bytes(_RESULTS_PDF_PAGES), calls=calls),
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is True
    assert calls == ["https://www.bseindia.com/xml-data/corpfiling/AttachHis/abc123"]
    assert "PAT stood at Rs 210 crore" in out["content"]


def test_long_pdf_selects_finance_relevant_pages() -> None:
    """A long document is reduced to its most finance-relevant pages (keyword +
    digit-density scoring) in document order, capped at paragraph bounds."""
    filler = "Forward looking statements and general legal boilerplate text. " * 40
    pages = [filler] * 8
    pages.append(
        "Quarterly results: revenue Rs 9,876 crore, profit Rs 543 crore, "
        "EBITDA margin 21.5%, dividend Rs 7 per share for the quarter."
    )
    pages.append(filler)
    data = _pdf_bytes(pages)
    out = _run(
        fetch_page(
            "https://example.com/annual-report.pdf",
            max_chars=600,
            pdf_fetch=_pdf_fetcher(data),
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is True
    assert "Rs 9,876 crore" in out["content"]
    assert 9 in out["pages_used"]  # the finance page survived the reduction
    assert out["truncated"] is True
    assert len(out["content"]) <= 600


def test_pdf_http_error_is_honest() -> None:
    out = _run(
        fetch_page(
            "https://example.com/missing.pdf",
            pdf_fetch=_pdf_fetcher(b"", status=404),
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is False and out["error"] == "HTTP 404"


def test_pdf_over_cap_is_refused() -> None:
    from services.search.extract import PDF_MAX_BYTES

    big = b"%PDF" + b"0" * (PDF_MAX_BYTES + 1)
    out = _run(
        fetch_page(
            "https://example.com/huge.pdf",
            pdf_fetch=_pdf_fetcher(big),
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is False and "cap" in out["error"]


def test_textless_pdf_is_an_honest_miss() -> None:
    """A scanned/image PDF (no extractable text) is a clean miss, never a
    fabricated empty success."""
    import io

    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    out = _run(
        fetch_page(
            "https://example.com/scanned.pdf",
            pdf_fetch=_pdf_fetcher(buf.getvalue()),
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is False and "scanned" in out["error"]


def test_garbage_pdf_body_is_an_honest_miss() -> None:
    out = _run(
        fetch_page(
            "https://example.com/broken.pdf",
            pdf_fetch=_pdf_fetcher(b"not a pdf at all"),
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is False and "PDF parse failed" in out["error"]


def test_extract_pdf_text_is_directly_callable() -> None:
    from services.search.extract import extract_pdf_text

    out = extract_pdf_text(_pdf_bytes(_RESULTS_PDF_PAGES))
    assert out["ok"] is True
    assert out["page_count"] == 2
    assert "Revenue from operations grew 23%" in out["content"]


def test_visit_for_research_widens_budget_for_pdf_urls(monkeypatch) -> None:  # noqa: ANN001
    from services.search import extract as extract_module

    seen: dict[str, int] = {}

    async def _capture(url, *, max_chars):  # noqa: ANN001, ANN202
        seen[url] = max_chars
        return {"ok": True, "content": "x", "url": url}

    monkeypatch.setattr(extract_module, "fetch_page", _capture)
    _run(visit_for_research("https://example.com/results.pdf"))
    _run(visit_for_research("https://example.com/article"))
    assert seen["https://example.com/results.pdf"] == extract_module.PDF_RESEARCH_MAX_CHARS
    assert seen["https://example.com/article"] == extract_module.RESEARCH_VISIT_MAX_CHARS
