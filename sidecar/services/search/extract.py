"""Full-page extraction for the research ``visit`` step (R7 Component 1).

Fetches a result URL over the SAME dual-lane transport the T1 engines use
(httpx first; one Chrome-impersonation retry when an anti-bot wall answers)
and reduces the page to its readable main content with BeautifulSoup
heuristics — so a researcher can read PAST the two-line SERP snippet without
a headless browser.

Heuristic pipeline (main-content extraction adapted from odysseus (MIT)
github.com/pewdiepie-archdaemon/odysseus, ``services/search/content.py``):

  1. SSRF guard: http(s) only; loopback/private/link-local/internal hosts are
     refused (literal IPs checked directly, hostnames via the injectable
     resolver) — a research visit must never become a port-scan of localhost.
  2. Strip ``script/style/noscript/template/nav/header/footer/aside/form/
     iframe`` — boilerplate that poisons text extraction.
  3. Prefer semantic containers: ``main`` / ``article``, then ``section`` /
     ``div`` whose class names look content-ish. When the pick is THIN
     (< :data:`_THIN_CONTENT_CHARS`), fall back to whole-body text so app/
     landing pages don't read as empty.
  4. Paragraph assembly: block-level texts, with consent/cookie boilerplate
     paragraphs dropped via the shared low-quality markers.
  5. Truncate at a PARAGRAPH boundary (never mid-sentence): paragraphs are
     accumulated while they fit ``max_chars``; an oversized first paragraph is
     cut at the last sentence end under the cap.

Returns honest dicts, never raises: ``{"ok": True, url, title, content,
truncated, chars}`` or ``{"ok": False, url, error}``. The research-shaped
:func:`visit_for_research` narrows that to "scrubbed excerpt or None".
"""

from __future__ import annotations

import io
import ipaddress
import re
import socket
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .keyless import is_low_quality
from .transport import TransportError, httpx_fetch, impersonated_fetch

#: Default cap on extracted content (characters).
DEFAULT_MAX_CHARS = 8000

#: Hard cap on a fetched PDF body (bytes) — a 15MB annual report is the
#: ceiling; anything larger is refused rather than buffered into memory.
PDF_MAX_BYTES = 15 * 1024 * 1024

#: Excerpt budget for a PDF on the research visit path — results filings carry
#: their numbers deep in tables, so the PDF budget is wider than the HTML one.
PDF_RESEARCH_MAX_CHARS = 4000

#: Exchange-archive filings get a WIDER budget still (R9 gate 7): the outcome
#: letter's dividend-aggregate line and a presentation's income statement both
#: sit past 4k chars of selected pages — a primary filing that was fetched must
#: yield its figures, so the disclosure lane reads deeper. Bounded; prompts
#: fence the text as untrusted either way.
PDF_EXCHANGE_MAX_CHARS = 9000

#: How many pages of a long PDF are read at most (text extraction cost guard).
_PDF_MAX_PAGES = 60

#: How many finance-relevant pages are kept when a long PDF must be reduced.
_PDF_KEEP_PAGES = 6

#: Finance-relevance keywords for page selection in long PDFs (results filings,
#: annual reports): a page mentioning these + dense in digits carries the
#: numbers a researcher needs. R9: the Indian quarterly-results grammar is
#: first-class — "standalone"/"consolidated" statement headers and the
#: "quarter ended"/"year ended" column captions are what the results annexure
#: pages actually say ("crore"/"lakh" also count their plural forms via
#: substring counting).
_PDF_FINANCE_KEYWORDS = (
    "revenue",
    "profit",
    "pat",
    "ebitda",
    "margin",
    "dividend",
    "quarter",
    "results",
    "crore",
    "lakh",
    "income",
    "eps",
    "earnings",
    "standalone",
    "consolidated",
    "quarter ended",
    "year ended",
    "net sales",
)

#: Hosts whose downloads must ride the Chrome-impersonation lane (exchange
#: archives reject plain httpx the same way their HTML endpoints do).
_PDF_IMPERSONATED_SUFFIXES = ("nseindia.com", "bseindia.com")

#: Below this, the semantic-container pick is "thin" and body text is tried.
_THIN_CONTENT_CHARS = 600

#: Statuses that look like an anti-bot wall → one impersonated retry.
_WALL_STATUSES = frozenset({403, 429, 503})

#: Tags that never contain readable main content.
_NOISE_TAGS = (
    "script",
    "style",
    "noscript",
    "template",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "iframe",
)

#: Class-name heuristic for content-ish containers (odysseus pattern).
_CONTENT_CLASS_RE = re.compile("content|main|body|article|post|entry|text", re.I)

#: Hostnames that are local/internal regardless of DNS.
_LOCAL_HOSTNAMES = frozenset({"localhost", "metadata", "metadata.google.internal"})
_LOCAL_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".intranet")

#: Sentence-end candidates for the oversized-first-paragraph cut.
_SENTENCE_END_RE = re.compile(r"[.!?][\"')\]]?\s")


def _is_private_address(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_reserved
        or addr.is_multicast
        or addr.is_unspecified
    )


def _default_resolver(hostname: str) -> list[str]:
    """Resolve ``hostname`` to IP strings (injectable for offline tests)."""
    try:
        infos = socket.getaddrinfo(hostname, None)
    except OSError:
        return []
    return [info[4][0] for info in infos]


def is_public_http_url(url: str, *, resolver=None) -> bool:  # noqa: ANN001
    """True only for an http(s) URL whose host resolves to PUBLIC addresses."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host or host in _LOCAL_HOSTNAMES or host.endswith(_LOCAL_SUFFIXES):
        return False
    try:
        return not _is_private_address(ipaddress.ip_address(host))
    except ValueError:
        pass  # not a literal IP — resolve it
    resolve = resolver or _default_resolver
    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for raw in resolve(host):
        try:
            addresses.append(ipaddress.ip_address(raw))
        except ValueError:
            continue
    return bool(addresses) and not any(_is_private_address(a) for a in addresses)


def _paragraphs(soup: BeautifulSoup) -> list[str]:
    """Readable paragraphs from the (already de-noised) document.

    Prefers semantic containers (``main``/``article``, then content-classed
    ``section``/``div``); thin picks fall back to whole-body text. Block-level
    texts become paragraphs; consent/cookie boilerplate blocks are dropped.
    """
    containers = soup.find_all(["main", "article"])
    if not containers:
        containers = soup.find_all(["section", "div"], class_=_CONTENT_CLASS_RE)[:3]

    def _blocks(scope) -> list[str]:  # noqa: ANN001 — bs4 Tag or BeautifulSoup
        nodes = scope.find_all(["p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "blockquote"])
        if nodes:
            texts = [" ".join(n.get_text(" ", strip=True).split()) for n in nodes]
        else:
            whole = " ".join(scope.get_text(" ", strip=True).split())
            texts = [whole] if whole else []
        return [t for t in texts if t]

    paragraphs: list[str] = []
    seen: set[str] = set()
    for container in containers:
        for text in _blocks(container):
            if text not in seen:
                seen.add(text)
                paragraphs.append(text)

    if sum(len(p) for p in paragraphs) < _THIN_CONTENT_CHARS:
        body = soup.find("body") or soup
        body_paragraphs: list[str] = []
        body_seen: set[str] = set()
        for text in _blocks(body):
            if text not in body_seen:
                body_seen.add(text)
                body_paragraphs.append(text)
        if sum(len(p) for p in body_paragraphs) > sum(len(p) for p in paragraphs):
            paragraphs = body_paragraphs

    return [p for p in paragraphs if not is_low_quality(p)]


def _truncate_at_paragraph(paragraphs: list[str], max_chars: int) -> tuple[str, bool]:
    """Join paragraphs up to ``max_chars``, cutting only at paragraph bounds.

    An oversized FIRST paragraph (nothing fits) is cut at the last sentence end
    under the cap (last space as the final fallback) so the excerpt still ends
    cleanly. Returns ``(content, truncated)``.
    """
    kept: list[str] = []
    used = 0
    for paragraph in paragraphs:
        cost = len(paragraph) + (2 if kept else 0)  # "\n\n" joiner
        if used + cost > max_chars:
            break
        kept.append(paragraph)
        used += cost
    if kept:
        return "\n\n".join(kept), len(kept) < len(paragraphs)
    if not paragraphs:
        return "", False
    head = paragraphs[0][:max_chars]
    cut = 0
    for match in _SENTENCE_END_RE.finditer(head):
        cut = match.end()
    if cut == 0:
        space = head.rfind(" ")
        cut = space if space > 0 else len(head)
    return head[:cut].rstrip(), True


def _is_pdf_url(url: str) -> bool:
    """True when the URL path names a ``.pdf`` resource."""
    try:
        return urlparse(url).path.lower().endswith(".pdf")
    except ValueError:
        return False


def _needs_impersonated_pdf_lane(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return any(host == s or host.endswith("." + s) for s in _PDF_IMPERSONATED_SUFFIXES)


async def _default_pdf_fetch(url: str) -> tuple[int, bytes]:
    """Download a PDF body as bytes — ``(status_code, body)``.

    Exchange archives (nsearchives.nseindia.com, bseindia.com attachment
    endpoints) reject plain httpx, so they ride the curl_cffi Chrome
    impersonation lane directly; everyone else gets httpx (streamed, so the
    15MB cap aborts the download rather than buffering past it) with ONE
    impersonated retry on an anti-bot wall status. Raises
    :class:`TransportError` on a transport-level failure.
    """
    import httpx

    from .transport import (
        BROWSER_HEADERS,
        DEFAULT_TIMEOUT_SECS,
        IMPERSONATE_PROFILE,
        USER_AGENT,
    )

    headers = dict(BROWSER_HEADERS)
    headers["Accept"] = "application/pdf,*/*;q=0.8"
    headers["User-Agent"] = USER_AGENT

    async def _impersonated() -> tuple[int, bytes]:
        try:
            from curl_cffi.requests import AsyncSession
        except Exception as exc:  # pragma: no cover — environment-dependent import
            raise TransportError(f"curl_cffi unavailable: {exc}") from exc
        try:
            async with AsyncSession(impersonate=IMPERSONATE_PROFILE) as session:
                resp = await session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT_SECS * 2)
        except Exception as exc:
            raise TransportError(f"impersonated PDF fetch failed for {url}: {exc}") from exc
        body = bytes(getattr(resp, "content", b"") or b"")
        if len(body) > PDF_MAX_BYTES:
            raise TransportError(f"PDF exceeds the {PDF_MAX_BYTES // (1024 * 1024)}MB cap")
        return int(getattr(resp, "status_code", 0)), body

    if _needs_impersonated_pdf_lane(url):
        return await _impersonated()

    try:
        async with httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT_SECS * 2, follow_redirects=True
        ) as client:
            async with client.stream("GET", url, headers=headers) as resp:
                if resp.status_code not in _WALL_STATUSES:
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in resp.aiter_bytes():
                        size += len(chunk)
                        if size > PDF_MAX_BYTES:
                            raise TransportError(
                                f"PDF exceeds the {PDF_MAX_BYTES // (1024 * 1024)}MB cap"
                            )
                        chunks.append(chunk)
                    return resp.status_code, b"".join(chunks)
    except httpx.HTTPError as exc:
        raise TransportError(f"PDF fetch failed for {url}: {exc}") from exc

    # Anti-bot wall — one retry over the Chrome-impersonation lane.
    return await _impersonated()


def _pdf_paragraphs(page_texts: list[str]) -> list[str]:
    """Flatten extracted page texts into readable paragraph candidates."""
    paragraphs: list[str] = []
    for text in page_texts:
        for block in re.split(r"\n\s*\n|\n", text):
            cleaned = " ".join(block.split())
            if cleaned:
                paragraphs.append(cleaned)
    return paragraphs


def _pdf_page_score(text: str) -> float:
    """Finance relevance of one PDF page: keyword hits + digit density.

    The haystack is whitespace-normalized so multi-word keywords ("quarter
    ended") match across the line breaks pypdf injects into table captions.
    """
    low = " ".join(text.lower().split())
    keyword_hits = sum(low.count(k) for k in _PDF_FINANCE_KEYWORDS)
    digits = sum(ch.isdigit() for ch in low)
    density = digits / max(len(low), 1)
    return keyword_hits * 2.0 + density * 100.0


#: A page whose extracted text is shorter than this is an EMPTY page for the
#: per-page honesty signal — raster scans sometimes leak a stray watermark
#: character, which must not hide that the page has no real text layer.
_EMPTY_PAGE_CHARS = 16

#: Digit density below which an extracted excerpt is "digit-sparse" — i.e. it
#: cannot be carrying a results table. Calibrated on the real SAKSOFT Q4 FY26
#: outcome filing: cover letters/notes run 3–7% digits (CINs, dates, DINs);
#: genuine results-table text runs 25–45%.
_DIGIT_SPARSE_DENSITY = 0.10

#: Excerpts shorter than this carry too little signal to judge density on.
_DIGIT_SPARSE_MIN_CHARS = 200

#: How many selected pages may get the pypdf layout-mode retry (cost guard).
_PDF_LAYOUT_RETRY_MAX = 8

#: WELL-FORMED financial numbers ("24,884.50", "1,00,719.12", "2.81") — a
#: cleanly bounded grouped/decimal figure. Layout mode wins a page when it
#: separates MORE of them than plain extraction: plain mode can fuse adjacent
#: table cells into runs like "24,884.5023,998.71", which parse as malformed
#: (4-decimal) figures and stop counting as well-formed.
_FIN_NUMBER_RE = re.compile(r"(?<![\d.,])(?:\d{1,3}(?:,\d{2,3})+|\d+)(?:\.\d{1,2})?(?![\d.,])")


def is_digit_sparse(text: str | None) -> bool:
    """True when ``text`` cannot plausibly contain a financial results table.

    Used by the research loop's digital-twin fallback: a disclosure visit that
    came back digit-sparse (a cover letter, a procedural intimation) triggers
    ONE bounded visit of the next disclosure row. Empty/short text is sparse.
    """
    if not text:
        return True
    flat = " ".join(text.split())
    if len(flat) < _DIGIT_SPARSE_MIN_CHARS:
        return True
    digits = sum(ch.isdigit() for ch in flat)
    return digits / len(flat) < _DIGIT_SPARSE_DENSITY


#: Marker phrase carried by the scanned-pages note — detection key for the
#: research loop (and a grep-stable contract for tests).
SCANNED_NOTE_MARKER = "no extractable text"


def scanned_pages_note(pages_empty: int, page_count: int) -> str:
    """The honest one-line note appended when a PDF has image-only pages."""
    return (
        f"[Document note: {pages_empty} of {page_count} pages have "
        f"{SCANNED_NOTE_MARKER} — financial tables are likely scanned images. "
        "Figures missing from this excerpt are UNPARSED, not absent; prefer a "
        "digital companion filing (earnings presentation / press release) for "
        "the numbers.]"
    )


def has_scanned_pages_note(text: str | None) -> bool:
    """Does an extracted excerpt carry the scanned-pages honesty note?"""
    return bool(text) and SCANNED_NOTE_MARKER in str(text)


def _layout_retry(pages: Any, page_texts: list[str], indices: list[int]) -> None:
    """Re-extract selected pages in pypdf layout mode where layout WINS.

    Plain extraction can fuse adjacent table cells into one unreadable digit
    run ("Revenue24,884.5023,998.71"); layout mode preserves the column
    whitespace. A page's layout text replaces the plain text only when it
    yields strictly MORE well-formed financial numbers — never on ties, so
    prose pages keep the cheaper plain extraction. Bounded at
    :data:`_PDF_LAYOUT_RETRY_MAX` pages; any layout failure keeps plain.
    """
    for i in indices[:_PDF_LAYOUT_RETRY_MAX]:
        plain = page_texts[i]
        if len(plain.strip()) < _EMPTY_PAGE_CHARS:
            continue  # no text layer — layout mode cannot conjure one
        try:
            layout = pages[i].extract_text(extraction_mode="layout") or ""
        except Exception:  # noqa: BLE001 — layout mode is best-effort
            continue
        if len(_FIN_NUMBER_RE.findall(layout)) > len(_FIN_NUMBER_RE.findall(plain)):
            page_texts[i] = layout


def extract_pdf_text(data: bytes, *, max_chars: int = PDF_RESEARCH_MAX_CHARS) -> dict[str, Any]:
    """Reduce a PDF body to its most finance-relevant readable text.

    Reads up to :data:`_PDF_MAX_PAGES` pages via pypdf; when the document is
    longer than the budget, the :data:`_PDF_KEEP_PAGES` highest-scoring pages
    (keyword + digit-density scoring — results tables win) are kept; the
    excerpt is cut at a paragraph boundary, never mid-sentence.

    R9 honesty + assembly:

    - ``pages_empty`` counts pages with NO extractable text (raster scans).
      Partially scanned filings (the common Indian outcome shape: digital
      cover letter + image-only results tables) return ``ok: True`` WITH the
      count so the caller can say "scanned tables", never a false "parsed".
    - Selected table-ish pages get one pypdf layout-mode retry where layout
      separates more numeric runs than plain extraction.
    - When the selected text exceeds the budget, pages are ASSEMBLED in score
      order (best finance page first) so letterhead pages can never starve
      the results table out of the excerpt; document order is kept when
      everything fits.

    Returns the same honest dict shape as :func:`fetch_page` minus transport
    fields — never raises.
    """
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data))
        pages = reader.pages[:_PDF_MAX_PAGES]
        page_texts: list[str] = []
        for page in pages:
            try:
                page_texts.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001 — one broken page must not kill the doc
                page_texts.append("")
        title = ""
        try:
            meta_title = reader.metadata.title if reader.metadata else None
            title = " ".join(str(meta_title).split()) if meta_title else ""
        except Exception:  # noqa: BLE001 — metadata is best-effort
            title = ""
    except Exception as exc:  # noqa: BLE001 — malformed/encrypted PDFs are a soft miss
        return {"ok": False, "error": f"PDF parse failed: {exc}"}

    pages_empty = sum(1 for t in page_texts if len(t.strip()) < _EMPTY_PAGE_CHARS)

    total_chars = sum(len(t) for t in page_texts)
    if total_chars > max_chars * 2 and len(page_texts) > _PDF_KEEP_PAGES:
        scores = [_pdf_page_score(t) for t in page_texts]
        ranked = sorted(range(len(page_texts)), key=lambda i: scores[i], reverse=True)
        top = scores[ranked[0]]
        # Keep only MEANINGFULLY finance-relevant pages (a fifth of the best
        # page's score, floored at one keyword hit) so legal-boilerplate pages
        # can't ride a tie into the budget ahead of the results table.
        keep = [i for i in ranked[:_PDF_KEEP_PAGES] if scores[i] >= max(2.0, top * 0.2)]
        if not keep:
            keep = ranked[:_PDF_KEEP_PAGES]
        keep = sorted(keep)  # document order for pages_used + assembly
    else:
        keep = list(range(len(page_texts)))

    _layout_retry(pages, page_texts, keep)
    pages_used = [i + 1 for i in keep]

    # Assembly order: document order when the selection fits the budget;
    # score order (best finance page first, stable on ties) when truncation
    # is inevitable — a results table must never be starved by letterhead.
    if sum(len(page_texts[i]) for i in keep) > max_chars:
        keep_scores = {i: _pdf_page_score(page_texts[i]) for i in keep}
        assembly = sorted(keep, key=lambda i: (-keep_scores[i], i))
    else:
        assembly = keep
    paragraphs: list[str] = []
    for i in assembly:
        paragraphs.extend(_pdf_paragraphs([page_texts[i]]))

    content, truncated = _truncate_at_paragraph(paragraphs, max_chars)
    if not content:
        return {
            "ok": False,
            "error": "no extractable text in PDF (likely a scanned/image document)",
            "pages_empty": pages_empty,
            "page_count": len(page_texts),
        }
    return {
        "ok": True,
        "title": title,
        "content": content,
        "truncated": truncated or len(pages_used) < len(page_texts),
        "chars": len(content),
        "pages_used": pages_used,
        "page_count": len(page_texts),
        "pages_empty": pages_empty,
    }


async def _fetch_pdf_page(
    url: str,
    *,
    max_chars: int,
    pdf_fetch=None,  # noqa: ANN001 — injectable byte fetch for tests
) -> dict[str, Any]:
    """The PDF lane of :func:`fetch_page`: bytes → finance-relevant text."""
    fetch_bytes = pdf_fetch or _default_pdf_fetch
    try:
        status, body = await fetch_bytes(url)
    except TransportError as exc:
        return {"ok": False, "url": url, "error": f"fetch failed: {exc}"}
    if status >= 400:
        return {"ok": False, "url": url, "error": f"HTTP {status}"}
    if not body:
        return {"ok": False, "url": url, "error": "empty PDF body"}
    if len(body) > PDF_MAX_BYTES:
        return {
            "ok": False,
            "url": url,
            "error": f"PDF exceeds the {PDF_MAX_BYTES // (1024 * 1024)}MB cap",
        }
    extracted = extract_pdf_text(body, max_chars=max_chars)
    if not extracted.get("ok"):
        miss: dict[str, Any] = {"ok": False, "url": url, "error": str(extracted.get("error"))}
        # Carry the per-page honesty signal through a textless miss so the
        # research visit can say "scanned filing", never a false "not parsed".
        for key in ("pages_empty", "page_count"):
            if key in extracted:
                miss[key] = extracted[key]
        return miss
    extracted["url"] = url
    extracted["final_url"] = url
    extracted["content_type"] = "application/pdf"
    return extracted


async def fetch_page(
    url: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    fetch=None,  # noqa: ANN001 — injectable httpx-lane fetch for tests
    fallback_fetch=None,  # noqa: ANN001 — injectable impersonation lane
    resolver=None,  # noqa: ANN001 — injectable DNS for the SSRF guard
    pdf_fetch=None,  # noqa: ANN001 — injectable PDF byte fetch for tests
) -> dict[str, Any]:
    """Fetch ``url`` and extract its readable main content. Never raises.

    R8: a ``.pdf`` URL (or a reply served as ``application/pdf``) rides the PDF
    lane — bytes (15MB cap; exchange archives over the impersonated curl_cffi
    transport) → pypdf text → finance-relevant page selection. Other non-HTML
    content types stay honestly rejected.
    """
    if not is_public_http_url(url, resolver=resolver):
        return {"ok": False, "url": url, "error": "blocked non-public or non-http(s) URL"}

    if _is_pdf_url(url):
        return await _fetch_pdf_page(url, max_chars=max_chars, pdf_fetch=pdf_fetch)

    primary = fetch or httpx_fetch
    fallback = fallback_fetch or impersonated_fetch
    try:
        fetched = await primary(url)
    except TransportError as exc:
        return {"ok": False, "url": url, "error": f"fetch failed: {exc}"}

    if fetched.status_code in _WALL_STATUSES:
        # Anti-bot wall — one retry over the Chrome-impersonation lane.
        try:
            fetched = await fallback(url)
        except TransportError as exc:
            return {"ok": False, "url": url, "error": f"fetch failed after wall: {exc}"}
    if fetched.status_code >= 400:
        return {"ok": False, "url": url, "error": f"HTTP {fetched.status_code}"}

    content_type = (fetched.content_type or "").lower()
    if "pdf" in content_type:
        # Served as a PDF without a .pdf path — refetch on the byte lane (the
        # text lane has already mangled the binary body).
        return await _fetch_pdf_page(url, max_chars=max_chars, pdf_fetch=pdf_fetch)
    if content_type and ("html" not in content_type and not content_type.startswith("text/")):
        return {"ok": False, "url": url, "error": f"unsupported content type: {content_type}"}

    soup = BeautifulSoup(fetched.text, "html.parser")
    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()
    title_tag = soup.find("title")
    title = " ".join(title_tag.get_text(strip=True).split()) if title_tag else ""

    content, truncated = _truncate_at_paragraph(_paragraphs(soup), max_chars)
    if not content:
        return {"ok": False, "url": url, "error": "no readable content extracted"}
    return {
        "ok": True,
        "url": url,
        "final_url": fetched.url,
        "title": title,
        "content": content,
        "truncated": truncated,
        "chars": len(content),
    }


#: Excerpt budget for the research visit (kept small — it rides an LLM prompt).
RESEARCH_VISIT_MAX_CHARS = 1800


async def visit_for_research(url: str, *, max_chars: int = RESEARCH_VISIT_MAX_CHARS) -> str | None:
    """The research-shaped visit: extracted page text, or ``None`` on any miss.

    Soft by design — a researcher with no page text still has the SERP
    snippets; a visit failure must never fail the round. The caller is
    responsible for fencing the returned text with
    :func:`services.search.scrub.wrap_untrusted` before it enters a prompt.

    A ``.pdf`` URL gets the wider :data:`PDF_RESEARCH_MAX_CHARS` budget —
    results filings carry their numbers deep in tables, and starving them was
    the "no quarterly results announced" failure mode.

    R9 scanned-filing honesty: a PDF with image-only pages gets the one-line
    :func:`scanned_pages_note` APPENDED to its excerpt (partial text layer) or
    RETURNED as the excerpt (no text layer at all) — the researcher prompt then
    treats the missing figures as unparsed scans, never as "not announced".
    """
    budget = max(max_chars, PDF_RESEARCH_MAX_CHARS) if _is_pdf_url(url) else max_chars
    if _is_pdf_url(url) and _needs_impersonated_pdf_lane(url):
        # Exchange-archive filing: the primary document for the run — read deeper.
        budget = max(budget, PDF_EXCHANGE_MAX_CHARS)
    try:
        page = await fetch_page(url, max_chars=budget)
    except Exception:  # noqa: BLE001 — belt-and-suspenders; fetch_page shouldn't raise
        return None
    pages_empty = int(page.get("pages_empty") or 0)
    page_count = int(page.get("page_count") or 0)
    if not page.get("ok"):
        if pages_empty and page_count:
            # Fully scanned filing: the honest note IS the visit text, so the
            # researcher learns WHY there are no figures instead of a silent miss.
            return scanned_pages_note(pages_empty, page_count)
        return None
    content = str(page.get("content") or "")
    if content and pages_empty and page_count:
        content = content.rstrip() + "\n\n" + scanned_pages_note(pages_empty, page_count)
    return content or None


__all__ = [
    "DEFAULT_MAX_CHARS",
    "PDF_MAX_BYTES",
    "PDF_EXCHANGE_MAX_CHARS",
    "PDF_RESEARCH_MAX_CHARS",
    "SCANNED_NOTE_MARKER",
    "extract_pdf_text",
    "fetch_page",
    "has_scanned_pages_note",
    "is_digit_sparse",
    "is_public_http_url",
    "scanned_pages_note",
    "visit_for_research",
]
