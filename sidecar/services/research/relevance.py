"""Entity relevance gate for gathered web evidence (R8).

Root cause of the 69-junk-sources defect: ``_record_web`` folded EVERY row a
web engine returned into the brief's sources and coverage — crypto "Router
Protocol" pages on a Route Mobile run, other companies' exchange filings, and
"what is support and resistance"-style SEO junk all became numbered ``[n]``
citations. This module scores each row against the run's bound
:class:`~services.research.target.ResearchTarget` (or, when no instrument is
bound, against the user's query tokens) and the loops DROP rows below the
floor — they never become sources and never count toward the coverage floor.

Pure functions, no network, no LLM — fully unit-testable.
"""

from __future__ import annotations

import re
from typing import Any

from services.research import finance
from services.research.target import ResearchTarget

#: Hosts that are never research evidence for a finance brief.
JUNK_HOSTS: frozenset[str] = frozenset(
    {
        "scribd.com",
        "youtube.com",
        "youtu.be",
        "instagram.com",
        "pinterest.com",
        "facebook.com",
        "quora.com",
    }
)

#: Crypto data/exchange hosts — junk when the bound target is an EQUITY (the
#: "Router Protocol price" rows on a Route Mobile run). Kept when the target IS
#: a crypto asset, or when no target is bound (asset class unknown).
CRYPTO_HOSTS: frozenset[str] = frozenset(
    {
        "coinmarketcap.com",
        "coingecko.com",
        "coinbase.com",
        "binance.com",
        "kraken.com",
        "crypto.com",
        "coinpaprika.com",
        "messari.io",
        "livecoinwatch.com",
        "coincodex.com",
    }
)

#: Exchange-filing title grammar — when a row's TITLE is another company's
#: regulatory filing, a passing mention of the target in the SNIPPET must not
#: admit it (the RELIANCE audit found SWSOLAR/other corporates' filings counted
#: as coverage because their snippets mentioned RIL). A filing-shaped title must
#: name the TARGET in the title itself to be evidence.
_FILING_TITLE_RX = re.compile(
    r"(?i)\b(has\s+(informed|submitted)\s+(to\s+)?the\s+exchange"
    r"|outcome\s+of\s+(the\s+)?board\s+meeting"
    r"|intimation\s+under\s+reg"
    r"|announcement\s+under\s+regulation"
    r"|compliance[s]?\s*-\s*reg"
    r"|newspaper\s+publication)\b"
)

#: Generic-educational / SEO title shapes that answer nobody's research
#: question about a SPECIFIC company. Matched against the row TITLE only.
_SEO_TITLE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*what\s+is\b", re.I),
    re.compile(r"^\s*how\s+to\b", re.I),
    re.compile(r"\bfor\s+beginners\b", re.I),
    re.compile(r"\bsupport\s+and\s+resistance\b", re.I),
    re.compile(r"\bexplained\b\s*[:!?]?\s*$", re.I),
    re.compile(r"^\s*top\s+\d+\b", re.I),
    re.compile(r"\bprice\s+prediction\b", re.I),
)

#: Corporate-suffix / glue tokens that carry no entity identity.
_NAME_STOPWORDS: frozenset[str] = frozenset(
    {
        "limited",
        "ltd",
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "plc",
        "co",
        "company",
        "holdings",
        "the",
        "and",
        "of",
        "&",
    }
)

#: SECTOR/DESCRIPTOR name tokens that carry near-zero entity identity on their
#: own — "mobile" matching a Zomato delivery article must never admit it as a
#: Route Mobile source (the R9 V11 partial-token leak). A row may still match
#: on these when ALL of the name's distinctive tokens appear together in the
#: title; one generic token alone is never a strong signal.
_GENERIC_NAME_TOKENS: frozenset[str] = frozenset(
    {
        "mobile",
        "industries",
        "international",
        "india",
        "indian",
        "global",
        "group",
        "tech",
        "technology",
        "technologies",
        "solutions",
        "systems",
        "services",
        "digital",
        "info",
        "infotech",
        "communications",
        "telecom",
        "energy",
        "power",
        "finance",
        "financial",
        "capital",
        "bank",
        "banking",
        "insurance",
        "motors",
        "auto",
        "pharma",
        "pharmaceuticals",
        "labs",
        "laboratories",
        "life",
        "sciences",
        "healthcare",
        "foods",
        "consumer",
        "products",
        "projects",
        "infrastructure",
        "infra",
        "enterprises",
        "ventures",
        "resources",
        "steel",
        "cement",
        "chemicals",
        "textiles",
        "retail",
        "media",
        "entertainment",
        "exports",
        "trading",
        "agro",
        "green",
        "renewables",
    }
)

#: Query glue words ignored when matching on raw query tokens (no target).
_QUERY_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "for",
        "in",
        "on",
        "to",
        "is",
        "are",
        "with",
        "about",
        "research",
        "analyse",
        "analyze",
        "analysis",
        "look",
        "into",
        "stock",
        "share",
        "price",
        "company",
        "news",
        "outlook",
        "best",
        "what",
        "why",
        "how",
    }
)

#: Score floor for a row to be KEPT when a target is bound.
MATCH_FLOOR = 0.34

#: Relaxed floor when NO target is bound (web-only run, query-token matching).
RELAXED_FLOOR = 0.2

#: Ceiling on a SNIPPET-ONLY match (R9 V11). A row whose title/host/url never
#: name the target — only its snippet does — is the passing-mention shape
#: (market roundups, peer lists, another company's prospectus) that let
#: Coromandel/Tea Post ride into a SAKSOFT run. Capped strictly below
#: :data:`MATCH_FLOOR` so it can NEVER count as a source.
WEAK_MATCH_CEILING = 0.25

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9.&-]*")


def _host_matches(host: str, table: frozenset[str]) -> bool:
    return any(host == entry or host.endswith("." + entry) for entry in table)


def name_tokens(name: str) -> list[str]:
    """The DISTINCTIVE tokens of a display name (suffixes/glue dropped)."""
    tokens = [t for t in _TOKEN_RE.findall((name or "").lower()) if len(t) >= 2]
    distinctive = [t for t in tokens if t not in _NAME_STOPWORDS]
    return distinctive or tokens


def query_tokens(query: str) -> list[str]:
    """The meaningful tokens of a free-text query (glue words dropped)."""
    tokens = [t for t in _TOKEN_RE.findall((query or "").lower()) if len(t) >= 3]
    return [t for t in tokens if t not in _QUERY_STOPWORDS]


def brand_tokens(name: str) -> list[str]:
    """The tokens of a display name that IDENTIFY the company on their own.

    Distinctive tokens minus the sector/descriptor vocabulary: "Route Mobile
    Limited" → ``["route"]``, "Reliance Industries Limited" → ``["reliance"]``,
    "Saksoft Limited" → ``["saksoft"]``. MAY be empty (a name made entirely of
    sector words, e.g. "Global Industries Limited") — such names match only
    via the ALL-distinctive-tokens-together rule in the strong-channel score,
    never on one generic word alone.
    """
    return [t for t in name_tokens(name) if t not in _GENERIC_NAME_TOKENS]


def _is_seo_junk(title: str) -> bool:
    return any(p.search(title or "") for p in _SEO_TITLE_PATTERNS)


def _haystacks(row: dict[str, Any]) -> tuple[str, str, str]:
    """``(text, host, url_lc)`` for one row — title+snippet, the bare host, url."""
    url = str(row.get("url") or "")
    title = str(row.get("title") or "")
    snippet = str(row.get("excerpt") or row.get("snippet") or "")
    text = f"{title} {snippet}".lower()
    host = finance.domain_of(url)
    return text, host, url.lower()


def _token_score(tokens: list[str], text: str, host: str) -> float:
    """Fraction of distinctive tokens present in the text / host.

    A token counts when it appears word-bounded in the text, or as a substring
    of the HOST (hosts compress names: ``routemobile.com``, ``saksoft.com``).
    URL paths are deliberately excluded — ``/router`` must never satisfy a
    ``route`` token (the symbol check below handles bounded path/query hits).
    """
    if not tokens:
        return 0.0
    hit = 0
    for token in tokens:
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text):
            hit += 1
        elif len(token) >= 4 and token in host:
            hit += 1
    return hit / len(tokens)


def _bounded(token: str, text: str) -> bool:
    """Word-bounded presence — ``route`` never matches inside ``router``."""
    return bool(re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", text))


def _strong_entity_score(target: ResearchTarget, *, title_lc: str, host: str, url_lc: str) -> float:
    """The STRONG-channel score: does the title/host/url itself name the target?

    Strong signals (any one suffices — the R9 V11 contract that an off-entity
    source never counts):

    - the SYMBOL, word-bounded in the title, as a host substring, or bounded in
      the url path/query (``/ROUTE`` / ``symbol=ROUTE``) — 1.0 (0.6 for short
      3-char symbols, which collide more);
    - a BRAND name token (sector descriptors excluded) word-bounded in the
      title, or inside the host (``routemobile.com``) — 1.0;
    - ALL distinctive name tokens together in the title (covers names whose
      every token is generic) — 1.0.

    Snippets are deliberately NOT consulted here: a snippet passing-mention is
    the leak shape (roundups, peer lists, prospectus mentions).
    """
    symbol = target.symbol.lower()
    if len(symbol) >= 3 and (
        _bounded(symbol, title_lc)
        or symbol in host
        or re.search(rf"[/=]{re.escape(symbol)}(?![a-z0-9])", url_lc)
    ):
        return 1.0 if len(symbol) >= 4 else 0.6
    branded = brand_tokens(target.name)
    if any(_bounded(t, title_lc) for t in branded):
        return 1.0
    if any(len(t) >= 4 and t in host for t in branded):
        return 1.0
    distinctive = name_tokens(target.name)
    if distinctive and all(_bounded(t, title_lc) for t in distinctive):
        return 1.0
    if not branded and distinctive and all(len(t) >= 4 and t in host for t in distinctive):
        # All-generic name compressed into the host (globalindustries.com).
        return 1.0
    return 0.0


def entity_match(
    row: dict[str, Any],
    *,
    target: ResearchTarget | None = None,
    query: str = "",
) -> float:
    """Score one web row's relevance to the bound target (or the query) in [0, 1].

    - Junk hosts (scribd/youtube/social/Q&A) → 0.
    - Crypto data hosts when the target is an equity → 0.
    - SEO-pattern titles ("what is support and resistance") → 0.
    - ``verified_symbol`` rows (exchange-disclosure provenance keyed to the
      target's own symbol) → 1.
    - Otherwise (R9 V11 tightening): the row must carry a STRONG entity
      signal — the symbol or a brand name token in the TITLE, HOST, or URL
      (:func:`_strong_entity_score`). A snippet-only passing mention (market
      roundups, peer lists, another company's DRHP) scores at most
      :data:`WEAK_MATCH_CEILING`, strictly below the keep floor — an
      off-entity source can never count as a source.
    - With NO target: query-token matching over title+snippet (unchanged —
      there is no entity to be off of).
    """
    text, host, url_lc = _haystacks(row)
    title = str(row.get("title") or "")

    verified = str(row.get("verified_symbol") or "").strip().upper()
    if target is not None and verified and verified == target.symbol:
        return 1.0
    if host and _host_matches(host, JUNK_HOSTS):
        return 0.0
    if target is not None and target.is_equity_like() and _host_matches(host, CRYPTO_HOSTS):
        return 0.0
    if _is_seo_junk(title):
        return 0.0
    if target is not None and _FILING_TITLE_RX.search(title):
        # A regulatory-filing title must name the TARGET in the title — another
        # company's filing whose snippet merely mentions the target is not
        # evidence about the target.
        title_lc = title.lower()
        sym = target.symbol.lower()
        named = any(
            re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", title_lc)
            for t in name_tokens(target.name)
        ) or (len(sym) >= 3 and re.search(rf"(?<![a-z0-9]){re.escape(sym)}(?![a-z0-9])", title_lc))
        if not named:
            return 0.0

    if target is None:
        tokens = query_tokens(query)
        if not tokens:
            # Nothing to judge against — keep (the blacklists above still apply).
            return 1.0
        return _token_score(tokens, text, host)

    strong = _strong_entity_score(target, title_lc=title.lower(), host=host, url_lc=url_lc)
    if strong > 0.0:
        return min(strong, 1.0)
    # Weak channel: the target appears only in the snippet (or via generic
    # tokens). Kept as a sub-floor score for debugging — never a kept source.
    weak = _token_score(name_tokens(target.name), text, host)
    return min(weak, WEAK_MATCH_CEILING)


def row_relevant(
    row: dict[str, Any],
    *,
    target: ResearchTarget | None = None,
    query: str = "",
) -> bool:
    """Keep/drop decision for one row — the floor scales with binding state."""
    floor = MATCH_FLOOR if target is not None else RELAXED_FLOOR
    return entity_match(row, target=target, query=query) >= floor


__all__ = [
    "CRYPTO_HOSTS",
    "JUNK_HOSTS",
    "MATCH_FLOOR",
    "RELAXED_FLOOR",
    "WEAK_MATCH_CEILING",
    "brand_tokens",
    "entity_match",
    "name_tokens",
    "query_tokens",
    "row_relevant",
]
