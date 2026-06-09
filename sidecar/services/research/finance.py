"""R7 finance tuning — domain ranking, query bias, and recency for research.

The research loops are general-purpose; this module is the finance moat layered
into them (R7 Component 4):

  - **Source prioritization.** A domain-rank table puts exchange / regulator /
    filings domains first (NSE, BSE, SEBI, RBI, SEC, company investor-relations
    pages), Tier-1 financial press second (ET, Bloomberg, Reuters, FT, WSJ,
    Moneycontrol, Livemint), everything else third. :func:`rank_sources` orders
    gathered citations by that tier (stable within a tier) so primary sources
    own the low ``[n]`` markers and synthesis cites them preferentially;
    :func:`priority_note` renders the same preference as a prompt line.

  - **Query bias.** On DEEP/ULTRA rounds, researcher web queries for the
    filings/fundamentals dimensions carry ``site:`` hints toward the regulator/
    exchange domains for the session region (:func:`bias_query`). News/general
    queries stay unfiltered for recall — the press preference is applied at
    RANKING time instead, so a site-filter can never starve a round.

  - **Recency.** :func:`date_directive` renders the server date + a
    fresh-sources preference; the loops append it to every plan / extract /
    distill / reflect / synthesis prompt (the same anchor the agent preamble
    carries — research prompts must not drift onto training-data time).

Pure functions over the dataclasses in :mod:`services.research.models` — no
network, no LLM, fully unit-testable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urlparse

from services.research.models import ResearchSource

#: Domain tiers, best first. Tier 1 = the primary record (exchanges,
#: regulators, filings, company IR); tier 2 = Tier-1 financial press;
#: tier 3 = the general web (the default).
TIER_PRIMARY = 1
TIER_PRESS = 2
TIER_GENERAL = 3

#: Exchange / regulator / filings domains — the primary record.
PRIMARY_DOMAINS: frozenset[str] = frozenset(
    {
        "nseindia.com",
        "bseindia.com",
        "sebi.gov.in",
        "rbi.org.in",
        "sec.gov",
    }
)

#: Tier-1 financial press.
PRESS_DOMAINS: frozenset[str] = frozenset(
    {
        "economictimes.indiatimes.com",
        "economictimes.com",
        "bloomberg.com",
        "reuters.com",
        "ft.com",
        "wsj.com",
        "moneycontrol.com",
        "livemint.com",
    }
)

#: Company investor-relations hosts — primary-record tier without enumerating
#: every issuer: a host like ``ir.nvidia.com`` / ``investors.apple.com`` or an
#: ``/investor-relations`` path marks the company's own disclosure surface.
_IR_HOST_PREFIXES = ("ir.", "investor.", "investors.")
_IR_PATH_MARKERS = ("/investor", "/investor-relations", "/ir/")

#: Regulator/exchange ``site:`` groups per session region, used to bias the
#: filings/fundamentals researcher queries on DEEP/ULTRA rounds. Kept to two
#: hosts per group so an HTML engine's OR handling never starves the query.
_SITE_HINTS_BY_REGION: dict[str, str] = {
    "IN": "site:nseindia.com OR site:bseindia.com",
    "US": "site:sec.gov",
    "GLOBAL": "site:sec.gov",
}

#: Researcher dimensions whose answers live on the primary-record domains —
#: the only dims that get a ``site:`` filter (news/general keep full recall).
_BIASED_DIMS = frozenset({"fundamentals", "filings"})


def domain_of(url_or_domain: str) -> str:
    """The bare registrable-ish host of a URL or domain string, lowercased.

    Strips the scheme, port, and a leading ``www.`` — enough normalization for
    the tier table without pulling in a public-suffix dependency.
    """
    text = (url_or_domain or "").strip().lower()
    if not text:
        return ""
    host = urlparse(text).netloc if "//" in text else text.split("/", 1)[0]
    host = host.split("@")[-1].split(":")[0]
    return host.removeprefix("www.")


def _matches(host: str, table: frozenset[str]) -> bool:
    """Suffix-aware domain match: ``efts.sec.gov`` matches ``sec.gov``."""
    return any(host == entry or host.endswith("." + entry) for entry in table)


def _looks_like_ir(url: str, host: str) -> bool:
    """Heuristic: is this a company investor-relations page?"""
    if any(host.startswith(prefix) for prefix in _IR_HOST_PREFIXES):
        return True
    path = urlparse(url.lower()).path if "//" in url.lower() else ""
    return any(marker in path for marker in _IR_PATH_MARKERS)


def domain_tier(url_or_domain: str) -> int:
    """Rank a URL/domain: 1 = primary record, 2 = Tier-1 press, 3 = general."""
    host = domain_of(url_or_domain)
    if not host:
        return TIER_GENERAL
    if _matches(host, PRIMARY_DOMAINS) or _looks_like_ir(url_or_domain, host):
        return TIER_PRIMARY
    if _matches(host, PRESS_DOMAINS):
        return TIER_PRESS
    return TIER_GENERAL


def source_tier(source: ResearchSource) -> int:
    """Tier of a gathered source — by its URL, falling back to its domain label."""
    by_url = domain_tier(source.url)
    if by_url != TIER_GENERAL:
        return by_url
    return domain_tier(source.domain or "")


def rank_sources(sources: list[ResearchSource]) -> list[ResearchSource]:
    """Order sources by domain tier, STABLE within a tier (gathering order).

    Used for synthesis ordering and citation preference: primary-record sources
    take the low ``[n]`` markers, then Tier-1 press, then the general web.
    Structured ``vysted://`` provenance sources rank as general (tier 3) so web
    evidence keeps citation priority.
    """
    return sorted(sources, key=source_tier)


def priority_note(sources: list[ResearchSource]) -> str:
    """A one-line prompt hint naming which ``[n]`` markers are primary/press.

    Rendered against the ALREADY-RANKED numbered list the synthesis prompt
    carries, so the model prefers citing the authoritative sources when several
    support a claim. Empty when no ranked source beats the general tier.
    """
    primary = [str(i + 1) for i, s in enumerate(sources) if source_tier(s) == TIER_PRIMARY]
    press = [str(i + 1) for i, s in enumerate(sources) if source_tier(s) == TIER_PRESS]
    parts: list[str] = []
    if primary:
        parts.append("primary record (exchange/regulator/filings/IR): [" + ", ".join(primary) + "]")
    if press:
        parts.append("tier-1 press: [" + ", ".join(press) + "]")
    if not parts:
        return ""
    return (
        "Citation preference — when several sources support a claim, cite the "
        "most authoritative: " + "; ".join(parts) + "."
    )


def bias_query(query: str, *, dim: str, region: str | None = None) -> str:
    """Bias a researcher web query toward the primary-record domains.

    Only the filings/fundamentals dimensions are ``site:``-filtered (their
    answers genuinely live on the regulator/exchange domains); every other dim
    returns the query unchanged so recall never suffers — press preference is
    applied at ranking time instead.
    """
    if dim not in _BIASED_DIMS:
        return query
    hint = _SITE_HINTS_BY_REGION.get((region or "US").strip().upper())
    if not hint:
        hint = _SITE_HINTS_BY_REGION["US"]
    return f"{query} {hint}"


def date_directive() -> str:
    """The server-date + recency line every research prompt carries.

    The same anchor the agent session preamble uses (symptom #1 — answering
    time-sensitive questions from stale training memory), restated for the
    research loops: prefer freshly dated sources, state the as-of date.
    """
    now = datetime.now(UTC)
    return (
        f"Server date: {now:%Y-%m-%d} ({now:%A}). Your training data is stale — "
        "treat the gathered evidence as the present. For time-sensitive claims "
        "prefer the most recently dated sources and state the as-of date next "
        "to any figure."
    )


__all__ = [
    "PRESS_DOMAINS",
    "PRIMARY_DOMAINS",
    "TIER_GENERAL",
    "TIER_PRESS",
    "TIER_PRIMARY",
    "bias_query",
    "date_directive",
    "domain_of",
    "domain_tier",
    "priority_note",
    "rank_sources",
    "source_tier",
]
