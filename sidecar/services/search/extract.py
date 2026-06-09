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


async def fetch_page(
    url: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    fetch=None,  # noqa: ANN001 — injectable httpx-lane fetch for tests
    fallback_fetch=None,  # noqa: ANN001 — injectable impersonation lane
    resolver=None,  # noqa: ANN001 — injectable DNS for the SSRF guard
) -> dict[str, Any]:
    """Fetch ``url`` and extract its readable main content. Never raises."""
    if not is_public_http_url(url, resolver=resolver):
        return {"ok": False, "url": url, "error": "blocked non-public or non-http(s) URL"}

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
    """
    try:
        page = await fetch_page(url, max_chars=max_chars)
    except Exception:  # noqa: BLE001 — belt-and-suspenders; fetch_page shouldn't raise
        return None
    if not page.get("ok"):
        return None
    content = str(page.get("content") or "")
    return content or None


__all__ = [
    "DEFAULT_MAX_CHARS",
    "RESEARCH_VISIT_MAX_CHARS",
    "fetch_page",
    "is_public_http_url",
    "visit_for_research",
]
