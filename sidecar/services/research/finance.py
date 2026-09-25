"""R7 finance tuning — domain ranking, query bias, and recency for research.

The research loops are general-purpose; this module is the finance moat layered
into them (R7 Component 4):

  - **Source prioritization.** A domain-rank table puts exchange / regulator /
    filings domains first (NSE, BSE, SEBI, RBI, SEC, company investor-relations
    pages), Tier-1 financial press second (ET, Bloomberg, Reuters, FT, WSJ,
    Moneycontrol, Livemint), everything else third. Source numbering is
    append-only (a ``[n]`` never moves once minted); :func:`rank_sources`
    orders only sources numbered TOGETHER, so a primary source gathered
    alongside a blog takes the lower new number, and :func:`priority_note`
    names the tier of every number in the list the synthesis prompt carries.

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

import functools
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from services.research.models import ResearchSource

#: Vendored upstream Public Suffix List (fetched at write time, never at
#: runtime — see the file's own header for the source URL and fetch date).
_PSL_PATH = Path(__file__).parent / "psl" / "public_suffix_list.dat"

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
#: every issuer: a dedicated IR host like ``ir.nvidia.com`` /
#: ``investors.apple.com`` marks the company's own disclosure surface. A path
#: marker (``/investor…``, ``/ir/``) is NOT enough: any blog post about
#: investing carries one, and the tier decides which source is "the record".
_IR_HOST_PREFIXES = ("ir.", "investor.", "investors.")

#: Publishing platforms where anyone can host an ``ir.``/``investors.``-looking
#: page, and that are NOT themselves Public Suffix List entries (so the PSL
#: registrable-domain check below cannot already exclude them). Every entry
#: that IS a PSL suffix (github.io, gitlab.io, wixsite.com, netlify.app,
#: vercel.app, pages.dev, blogspot.com, ...) was removed here on purpose —
#: `_looks_like_ir` excludes those generically via the PSL now.
_IR_PLATFORM_DENYLIST: frozenset[str] = frozenset(
    {
        "medium.com",
        "wordpress.com",
        "substack.com",
        "seekingalpha.com",
        "reddit.com",
        "linkedin.com",
        "hubpages.com",
        "weebly.com",
        "tumblr.com",
        # Not (or no longer) in the vendored PSL as of its fetch date; pinned
        # explicitly (R15-RESEARCH-007 batch-12 verifier fresh case).
        "glitch.me",
    }
)

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

#: Sub-question shapes where an INDUSTRY token sharpens the web query — a
#: fundamentals/valuation question benefits from the sector context, a bare
#: price/news question does not (the industry term would only dilute recall).
_FUNDAMENTALS_QUERY_KEYWORDS = (
    "fundamental",
    "valuation",
    "earnings",
    "revenue",
    "profit",
    "margin",
    "debt",
    "cash flow",
    "balance sheet",
    "dividend",
    "growth",
    "financial",
    "book value",
)


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


@functools.cache
def _psl_rules() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """Parse the vendored PSL once into (normal, wildcard, exception) rule
    sets, each holding dot-joined lowercase label suffixes with the rule's own
    ``*.``/``!`` marker stripped. Covers both the ICANN and PRIVATE sections —
    the registrable-domain algorithm below does not distinguish them."""
    normal: set[str] = set()
    wildcard: set[str] = set()
    exception: set[str] = set()
    for line in _PSL_PATH.read_text(encoding="utf-8").splitlines():
        rule = line.strip()
        if not rule or rule.startswith("//"):
            continue
        rule = rule.lower()
        if rule.startswith("!"):
            exception.add(rule[1:])
        elif rule.startswith("*."):
            wildcard.add(rule[2:])
        else:
            normal.add(rule)
    return frozenset(normal), frozenset(wildcard), frozenset(exception)


def _public_suffix(host: str) -> str:
    """The public suffix of ``host`` per the standard PSL algorithm: scan from
    the most specific candidate (the whole host) down to the least specific
    (its last label); the first rule that matches — an exception rule always
    wins the position it matches at — is the longest (most specific) match.
    Falls back to the default rule (the last label alone) when nothing in the
    list matches at all."""
    labels = host.split(".")
    normal, wildcard, exception = _psl_rules()
    for i in range(len(labels)):
        candidate = ".".join(labels[i:])
        if candidate in exception:
            return ".".join(labels[i + 1 :])
        if candidate in normal:
            return candidate
        if i + 1 < len(labels) and ".".join(labels[i + 1 :]) in wildcard:
            return candidate
    return labels[-1]


def _registrable_domain(host: str) -> str:
    """The registrable domain of ``host``: its public suffix plus one extra
    label. Equal to ``host`` itself when the host has no label beyond its
    public suffix (e.g. ``investors.github.io`` — a whole PSL private-suffix
    registration, not a subdomain of one)."""
    labels = host.split(".")
    suffix_labels = _public_suffix(host).split(".")
    if len(labels) <= len(suffix_labels):
        return host
    return ".".join(labels[len(labels) - len(suffix_labels) - 1 :])


def _looks_like_ir(host: str) -> bool:
    """Is this a company investor-relations host? Needs a dedicated IR host
    prefix (``ir.``/``investor.``/``investors.``) that is a true SUBDOMAIN of
    the host's PSL registrable domain — so a host that IS its own registrable
    domain (``investors.com`` the news site; ``investors.github.io``, a whole
    PSL-private-suffix registration) never qualifies — a host not on the
    publishing-platform denylist, and not a blogspot host on a ccTLD the PSL
    doesn't cover (only ``blogspot.com`` is a PSL entry; ``blogspot.in`` /
    ``blogspot.co.uk`` etc. are not, so the registrable-domain check alone
    would miss them)."""
    if "blogspot" in host.split("."):
        return False
    if not any(host.startswith(prefix) for prefix in _IR_HOST_PREFIXES):
        return False
    if _matches(host, _IR_PLATFORM_DENYLIST):
        return False
    return host != _registrable_domain(host)


def domain_tier(url_or_domain: str) -> int:
    """Rank a URL/domain: 1 = primary record, 2 = Tier-1 press, 3 = general."""
    host = domain_of(url_or_domain)
    if not host:
        return TIER_GENERAL
    if _matches(host, PRIMARY_DOMAINS) or _looks_like_ir(host):
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

    Primary-record sources first, then Tier-1 press, then the general web.
    Structured ``vysted://`` provenance sources rank as general (tier 3).
    Orders sources that are about to be numbered together — never a list whose
    ``[n]`` numbers are already minted (numbering is append-only).
    """
    return sorted(sources, key=source_tier)


def priority_note(sources: list[ResearchSource]) -> str:
    """A one-line prompt hint naming which ``[n]`` markers are primary/press.

    Takes the SAME numbered list the synthesis prompt carries (in any order —
    it is never re-ranked) and names the tier of each actual number, so the
    model prefers citing the authoritative sources when several support a
    claim. Empty when no source beats the general tier.
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

    R13 note — news/general dims are DELIBERATELY not ``site:``-anchored: the
    exchange hosts (nseindia/bseindia) are poor NEWS sources, so a ``site:``
    filter there would starve the round. The entity anchoring news dims DO need
    (the exchange qualifier that pins "KSE" to the Indian listing, not Karachi)
    is applied UPSTREAM in :func:`anchor_tokens` — a query token, not a
    ``site:`` filter — since only the query builder holds the bound target's
    exchange. This function stays purely about the primary-record ``site:``
    filter for the two record-shaped dims.
    """
    if dim not in _BIASED_DIMS:
        return query
    hint = _SITE_HINTS_BY_REGION.get((region or "US").strip().upper())
    if not hint:
        hint = _SITE_HINTS_BY_REGION["US"]
    return f"{query} {hint}"


def _exchange_qualifier(region: str | None, exchange: str | None) -> str:
    """The one-word exchange token that anchors an Indian listing (BSE/NSE).

    Empty for a non-Indian target — its quoted display name already pins the
    entity, and a spurious exchange token would only narrow recall.
    """
    ex = (exchange or "").strip().upper()
    if ex in ("NSE", "BSE"):
        return ex
    if (region or "").strip().upper() == "IN":
        return "NSE"
    return ""


def _industry_query_token(industry: str | None) -> str:
    """A concise 1-word anchor from a verbose industry label.

    ``"Oil, Gas & Consumable Fuels / Refineries & Marketing"`` → ``"Refineries"``
    (the most-specific segment's leading word). Empty when the label is absent —
    an uncovered micro-cap (KSE) simply contributes no industry token.
    """
    text = (industry or "").strip()
    if not text:
        return ""
    segment = text.split("/")[-1].strip()  # most-specific classification
    for chunk in re.split(r"[,&/]", segment):
        words = chunk.split()
        if words:
            return words[0]
    return ""


def is_fundamentals_shaped(sub_question: str) -> bool:
    """Is this sub-question about the company's financials/valuation?"""
    low = (sub_question or "").lower()
    return any(k in low for k in _FUNDAMENTALS_QUERY_KEYWORDS)


def anchor_tokens(
    *,
    region: str | None,
    exchange: str | None,
    industry: str | None = None,
    sub_question: str = "",
) -> str:
    """The corroborating identity token(s) a DEEP/ULTRA researcher web query
    carries BEYOND the quoted display name (R13).

    - The exchange qualifier (``BSE`` / ``NSE``) for an Indian listing — the one
      token that pins a ≤3-char ticker to the Indian exchange instead of its
      famous foreign namesake ("KSE" → the BSE micro-cap, not the Karachi index).
    - A concise industry term additionally, but ONLY when the sub-question is
      fundamentals-shaped AND the industry is known — a sector word sharpens a
      valuation query without diluting a news/price query.

    Empty for a target that needs no anchor (US names, no exchange). Kept SHORT
    on purpose: keyless engines choke on long queries.
    """
    tokens: list[str] = []
    qualifier = _exchange_qualifier(region, exchange)
    if qualifier:
        tokens.append(qualifier)
    if industry and is_fundamentals_shaped(sub_question):
        industry_token = _industry_query_token(industry)
        if industry_token:
            tokens.append(industry_token)
    return " ".join(tokens)


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


def corporate_action_directive() -> str:
    """The corporate-action date/filing discipline line every synthesis
    prompt carries (R12: a narrative invented five specific filing dates
    matching no real filing, one of them chronologically impossible, stated
    with the same confidence as real cited data).

    Distinct from each synthesis prompt's general PROVENANCE GUARANTEE (every
    numeric/dated claim needs a ``[n]`` citation): a fabricated corporate-
    action story reads as ordinary prose, not a bare figure, and can slip
    past a citation check aimed at numbers — so corporate actions get their
    own explicit, harder line.
    """
    return (
        "CORPORATE ACTIONS: a specific date, filing number, record date, or "
        "other corporate-action detail (a split, buyback, rights issue, "
        "merger, delisting) may be stated ONLY when a numbered source above "
        "states it. If you suspect a corporate action but no source here "
        "confirms its specifics, say so plainly ('a corporate action may be "
        "pending; unverified in this run') rather than asserting dates, "
        "filing numbers, or record dates you were not given."
    )


__all__ = [
    "PRESS_DOMAINS",
    "PRIMARY_DOMAINS",
    "TIER_GENERAL",
    "TIER_PRESS",
    "TIER_PRIMARY",
    "anchor_tokens",
    "bias_query",
    "corporate_action_directive",
    "date_directive",
    "domain_of",
    "domain_tier",
    "is_fundamentals_shaped",
    "priority_note",
    "rank_sources",
    "source_tier",
]
