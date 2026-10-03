"""Tests for ``services.research.relevance`` — the entity gate on web rows (R8).

ROUTE-shaped fixtures mirror the live 69-junk-sources failure: a Route Mobile
(NSE: ROUTE) deep run whose bare-ticker web queries pulled crypto "Router
Protocol" pages, OTHER companies' exchange filings, and "what is support and
resistance" SEO junk into the brief's numbered sources.
"""

from __future__ import annotations

from typing import Any

import pytest

from services.research import relevance
from services.research.target import target_from_payload


def _target(symbol: str = "ROUTE", name: str = "Route Mobile Limited", **kw: Any):
    resolved: dict[str, Any] = {
        "symbol": symbol,
        "name": name,
        "exchange": "NSE",
        "region": "IN",
        "asset_class": "equity",
        "confidence": 0.95,
    }
    resolved.update(kw)
    target = target_from_payload({"ok": True, "resolved": resolved})
    assert target is not None
    return target


ROUTE = _target()


def _row(url: str, title: str, snippet: str = "") -> dict[str, Any]:
    return {"url": url, "title": title, "snippet": snippet}


# --- the ROUTE regression fixtures -------------------------------------------


def test_route_mobile_rows_are_kept() -> None:
    rows = [
        _row(
            "https://www.routemobile.com/investors/",
            "Route Mobile — Investor Relations",
            "Quarterly results and presentations",
        ),
        _row(
            "https://economictimes.indiatimes.com/route-mobile-q4",
            "Route Mobile Q4 results: revenue up",
            "Route Mobile Limited reported",
        ),
        _row(
            "https://www.nseindia.com/get-quotes/equity?symbol=ROUTE",
            "ROUTE — National Stock Exchange quote",
        ),
    ]
    for row in rows:
        assert relevance.row_relevant(row, target=ROUTE), row["url"]


def test_crypto_router_protocol_rows_are_dropped() -> None:
    rows = [
        _row(
            "https://coinmarketcap.com/currencies/router-protocol/",
            "Router Protocol (ROUTE) price today",
            "Live ROUTE token price, market cap",
        ),
        _row(
            "https://www.coingecko.com/en/coins/router-protocol",
            "Router Protocol price chart",
        ),
    ]
    for row in rows:
        assert not relevance.row_relevant(row, target=ROUTE), row["url"]


def test_other_companys_filing_is_dropped() -> None:
    # The CMTL payload carried other issuers' exchange PDFs as Reliance sources.
    row = _row(
        "https://www.bseindia.com/xml-data/corpfiling/AttachHis/5f2162c6.pdf",
        "Nestle India Limited — outcome of board meeting",
        "Financial results for the quarter",
    )
    assert not relevance.row_relevant(row, target=ROUTE)


def test_seo_junk_titles_are_dropped() -> None:
    rows = [
        _row("https://blog.example/sr", "What is support and resistance in trading?"),
        _row("https://blog.example/howto", "How to read candlestick charts for beginners"),
        _row("https://blog.example/pred", "ROUTE price prediction 2030"),
    ]
    for row in rows:
        assert not relevance.row_relevant(row, target=ROUTE), row["url"]


def test_junk_hosts_are_always_dropped() -> None:
    for host in ("scribd.com", "www.youtube.com", "instagram.com", "pinterest.com", "quora.com"):
        row = _row(f"https://{host}/x", "Route Mobile Limited Q4 results discussion")
        assert not relevance.row_relevant(row, target=ROUTE), host


def test_crypto_hosts_kept_for_a_crypto_target() -> None:
    btc = _target(symbol="BTC-USD", name="Bitcoin", asset_class="crypto")
    row = _row("https://coinmarketcap.com/currencies/bitcoin/", "Bitcoin price today")
    assert relevance.row_relevant(row, target=btc)


def test_verified_symbol_rows_always_pass() -> None:
    # Exchange-disclosure rows are keyed to the bound symbol by provenance —
    # they pass even when the headline never names the company.
    row = {
        "url": "https://nsearchives.nseindia.com/corporate/results.pdf",
        "title": "Outcome of board meeting",
        "verified_symbol": "ROUTE",
    }
    assert relevance.entity_match(row, target=ROUTE) == 1.0
    # …but only for the SAME symbol.
    row["verified_symbol"] = "NESTLEIND"
    assert relevance.entity_match(row, target=ROUTE) < 1.0


def test_symbol_word_boundary_does_not_match_router() -> None:
    # "Router" must not satisfy a \bROUTE\b symbol check.
    row = _row("https://techblog.example/router", "Best wifi router protocols compared")
    assert not relevance.row_relevant(row, target=ROUTE)


def test_partial_name_token_keeps_press_rows() -> None:
    reliance = _target(symbol="RELIANCE", name="Reliance Industries Limited")
    row = _row(
        "https://www.reuters.com/markets/asia/x",
        "Reliance Q4 profit beats estimates",
    )
    assert relevance.row_relevant(row, target=reliance)


# --- the relaxed (no-target) floor --------------------------------------------


def test_relaxed_floor_matches_on_query_tokens() -> None:
    query = "best indian smallcap IT services stocks"
    kept = _row("https://example.com/a", "Smallcap IT services stocks in India to watch")
    dropped = _row("https://example.com/b", "Celebrity gossip roundup of the week")
    assert relevance.row_relevant(kept, target=None, query=query)
    assert not relevance.row_relevant(dropped, target=None, query=query)


def test_relaxed_floor_keeps_unjudgeable_rows_without_tokens() -> None:
    # No target AND no meaningful query tokens — only the blacklists apply.
    row = _row("https://example.com/a", "Some page")
    assert relevance.row_relevant(row, target=None, query="")
    junk = _row("https://scribd.com/doc/1", "Some page")
    assert not relevance.row_relevant(junk, target=None, query="")


def test_name_tokens_drop_corporate_suffixes() -> None:
    assert relevance.name_tokens("Route Mobile Limited") == ["route", "mobile"]
    assert relevance.name_tokens("Saksoft Limited") == ["saksoft"]
    # An all-suffix name still yields something to match on.
    assert relevance.name_tokens("Limited") == ["limited"]


# --- the R9 V11 last-mile fixtures: snippet passing-mentions never count ----------


SAKSOFT = _target(symbol="SAKSOFT", name="Saksoft Limited")


def test_roundup_rows_mentioning_target_in_snippet_are_dropped() -> None:
    """The live V11 leak: Coromandel and a Tea Post DRHP rode into a SAKSOFT
    run because their SNIPPETS mentioned Saksoft in passing. A title/host/url
    that never names the target is not evidence about the target."""
    rows = [
        _row(
            "https://www.businessdaily.example/coromandel-q4",
            "Coromandel International Q4 net profit rises 12%",
            "Other results today: Saksoft, Tea Post and three SME listings.",
        ),
        _row(
            "https://www.ipowatch.example/tea-post-drhp",
            "Tea Post Limited files DRHP for SME IPO",
            "Peers cited in the draft prospectus include Saksoft Limited.",
        ),
    ]
    for row in rows:
        assert relevance.entity_match(row, target=SAKSOFT) < relevance.MATCH_FLOOR, row["url"]
        assert not relevance.row_relevant(row, target=SAKSOFT), row["url"]


def test_generic_name_token_overlap_never_clears_the_floor() -> None:
    """ "mobile" in a Zomato/Nestle article must not admit it as a Route Mobile
    source — one generic sector token is not an entity match."""
    rows = [
        _row(
            "https://www.fooddaily.example/zomato-growth",
            "Zomato expands mobile ordering across tier-2 cities",
            "The mobile delivery market grew 40% this year.",
        ),
        _row(
            "https://www.fmcgnews.example/nestle-q4",
            "Nestle India Q4: packaged foods and mobile commerce lift sales",
            "Route to market strategies are shifting toward mobile.",
        ),
    ]
    for row in rows:
        assert not relevance.row_relevant(row, target=ROUTE), row["url"]


def test_target_named_in_title_host_or_url_is_kept() -> None:
    rows = [
        _row(
            "https://www.moneycontrol.com/saksoft-q4",
            "Saksoft Q4 results: PAT up 19.7%",
            "Quarterly results",
        ),
        _row("https://www.saksoft.com/investors", "Investor Relations", "Reports and filings"),
        _row(
            "https://www.nseindia.com/get-quotes/equity?symbol=SAKSOFT",
            "Equity quote",
            "",
        ),
    ]
    for row in rows:
        assert relevance.row_relevant(row, target=SAKSOFT), row["url"]


def test_brand_tokens_drop_sector_descriptors() -> None:
    assert relevance.brand_tokens("Route Mobile Limited") == ["route"]
    assert relevance.brand_tokens("Reliance Industries Limited") == ["reliance"]
    assert relevance.brand_tokens("Saksoft Limited") == ["saksoft"]
    # An all-generic name has NO brand token — it matches only when all its
    # distinctive tokens appear together (title) or compressed in the host.
    assert relevance.brand_tokens("Global Industries Limited") == []


def test_all_generic_name_requires_every_token_in_title() -> None:
    gil = _target(symbol="GIL", name="Global Industries Limited")
    kept = _row("https://press.example/a", "Global Industries posts record quarter")
    dropped = _row("https://press.example/b", "Global markets rally on rate cut hopes")
    assert relevance.row_relevant(kept, target=gil)
    assert not relevance.row_relevant(dropped, target=gil)


def test_micro_cap_with_own_host_rows_still_finishes() -> None:
    """Tiered-floor sanity: a thin micro-cap whose only evidence is its own
    site + one titled article keeps BOTH rows — tightening must not starve
    legitimately thin runs."""
    micro = _target(symbol="TINYCO", name="Tinyco Specialty Limited")
    rows = [
        _row("https://www.tinyco.com/investors", "Financial information", ""),
        _row("https://smallcapwatch.example/t", "Tinyco Specialty wins export order", ""),
    ]
    for row in rows:
        assert relevance.row_relevant(row, target=micro), row["url"]


def test_other_companys_filing_title_is_never_evidence() -> None:
    # The RELIANCE audit: other corporates' exchange filings whose SNIPPETS
    # mention the target rode into the sources. A filing-shaped title must name
    # the target itself.
    target = _target(symbol="RELIANCE", name="Reliance Industries Limited")
    other = {
        "url": "https://nsearchives.nseindia.com/corporate/SWSOLAR_x.pdf",
        "title": "SW SOLAR LIMITED has informed the Exchange regarding Outcome of Board Meeting",
        "excerpt": "…contract win with Reliance Industries for solar modules…",
    }
    assert relevance.entity_match(other, target=target) == 0.0
    own = {
        "url": "https://nsearchives.nseindia.com/corporate/RELIANCE_x.pdf",
        "title": (
            "RELIANCE INDUSTRIES LIMITED has informed the Exchange "
            "regarding Outcome of Board Meeting"
        ),
        "excerpt": "Q4 results",
    }
    assert relevance.entity_match(own, target=target) >= relevance.MATCH_FLOOR


# --- R13 collision-proofing: ≤3-char tickers shadowed by foreign entities -----


def _kse():
    return _target(symbol="KSE", name="KSE Ltd", exchange="BSE")


def _itc():
    return _target(symbol="ITC", name="ITC Limited", exchange="NSE")


def test_karachi_titles_rejected_for_kse() -> None:
    """The live collision: KSE Ltd (BSE-only microcap, formerly Kerala Solvent
    Extractions) is shadowed on the open web by Karachi's KSE-100. A bare
    ≤3-char symbol match on a foreign-market row must NOT count."""
    kse = _kse()
    rows = [
        _row("https://tribune.com.pk/kse", "KSE-100 index falls 2% amid selloff"),
        _row("https://dawn.com/business", "Karachi Stock Exchange hits record high"),
        _row("https://example.com/psx", "Pakistan Stock Exchange KSE-100 rallies 500 points"),
        _row("https://example.com/idx", "KSE 100 closes higher on foreign inflows"),
    ]
    for row in rows:
        assert relevance.entity_match(row, target=kse) < relevance.MATCH_FLOOR, row["title"]
        assert not relevance.row_relevant(row, target=kse), row["title"]


def test_legit_indian_kse_rows_are_kept() -> None:
    """A real KSE Ltd row on an Indian finance host (or ₹-context) IS kept —
    the corroboration gate must not starve the true company's coverage."""
    kse = _kse()
    rows = [
        _row(
            "https://www.moneycontrol.com/india/stockpricequote/kse",
            "KSE Ltd Q4 results: net profit rises on cattle-feed demand",
            "KSE Ltd reported quarterly numbers",
        ),
        _row(
            "https://example.com/microcap",
            "KSE Ltd board approves dividend",
            "The BSE-listed company declared ₹5 per share",
        ),
    ]
    for row in rows:
        assert relevance.row_relevant(row, target=kse), row["title"]
    # Exchange-filing provenance still passes outright (verified_symbol).
    filing = {
        "url": "https://www.bseindia.com/xml-data/corpfiling/kse.pdf",
        "title": "Outcome of Board Meeting",
        "verified_symbol": "KSE",
    }
    assert relevance.entity_match(filing, target=kse) == 1.0


def test_short_symbol_itc_kept_on_indian_finance_host() -> None:
    """A legit short Indian ticker (ITC) titled with the bare symbol on a known
    Indian finance host is corroborated and kept — the gate must not break the
    ITC/SBI/M&M class the brief calls out."""
    itc = _itc()
    rows = [
        _row("https://www.moneycontrol.com/itc", "ITC Q4 results: PAT up 19.7%"),
        _row(
            "https://economictimes.indiatimes.com/itc",
            "ITC share price rises on FMCG growth",
        ),
        _row("https://www.nseindia.com/get-quotes/equity?symbol=ITC", "ITC — NSE quote"),
    ]
    for row in rows:
        assert relevance.row_relevant(row, target=itc), row["title"]


def test_short_symbol_foreign_namesake_rejected_for_itc() -> None:
    """ITC on the NYSE (ITC Holdings, a US utility) must NOT count for the Indian
    ITC — an uncorroborated short-symbol match with no India context is dropped."""
    itc = _itc()
    row = _row(
        "https://us-utilities.example/itc-holdings",
        "ITC Holdings reports Q3 transmission earnings",
        "ITC Holdings, the US electricity transmission utility, said…",
    )
    assert relevance.entity_match(row, target=itc) < relevance.MATCH_FLOOR
    assert not relevance.row_relevant(row, target=itc)


def test_marker_lists_are_data_driven_constants() -> None:
    """The gate is driven by module constants, not a KSE special-case."""
    assert "moneycontrol.com" in relevance.INDIA_FINANCE_HOSTS
    assert "kse-100" in relevance.FOREIGN_MARKET_MARKERS
    assert "karachi" in relevance.FOREIGN_MARKET_MARKERS
    assert {"bse", "nse", "₹"} <= relevance.INDIA_CONTEXT_MARKERS


def test_long_indian_symbols_unaffected_by_the_gate() -> None:
    """Distinctive names (ROUTE, RELIANCE) still score on their own — the
    corroboration gate is scoped strictly to the ≤3-char collision class."""
    reliance = _target(symbol="RELIANCE", name="Reliance Industries Limited")
    # A press row with no Indian-host and no ₹ marker is STILL kept (long brand).
    row = _row("https://www.bloomberg.com/x", "Reliance Industries Q4 profit beats estimates")
    assert relevance.row_relevant(row, target=reliance)


# --- R15-RESEARCH-021: a ticker followed by a number is not an index name ------


def test_ticker_headline_with_a_moving_average_is_kept() -> None:
    """'BAJFINANCE 200 DMA' is the stock, not an index called BAJFINANCE-200."""
    baj = _target(symbol="BAJFINANCE", name="Bajaj Finance Limited")
    row = _row("https://example.com/x", "BAJFINANCE 200 DMA breakout as stock nears record")
    assert relevance.entity_match(row, target=baj) == 1.0


def test_ticker_headline_with_a_52_week_high_is_kept() -> None:
    baj = _target(symbol="BAJFINANCE", name="Bajaj Finance Limited")
    row = _row("https://example.com/y", "BAJFINANCE 52-week high on strong loan growth")
    assert relevance.row_relevant(row, target=baj)


def test_hyphenated_foreign_index_is_still_dropped() -> None:
    row = _row("https://tribune.com.pk/kse", "KSE-100 index falls 2% amid selloff")
    assert not relevance.row_relevant(row, target=_kse())


# --- R15-RESEARCH-001: a short US ticker is not an English word ---------------

_ON_SEMI = "ON Semiconductor Corporation"


@pytest.mark.parametrize(
    ("symbol", "name", "title", "kept"),
    [
        # A ≤3-char ticker/brand token read as prose, or a sector word read as
        # the brand, is not the company.
        ("ON", _ON_SEMI, "Lockheed wins contract on hypersonic program", False),
        ("ON", _ON_SEMI, "On Holding announces buyback", False),
        ("ON", _ON_SEMI, "Nvidia semiconductor sales soar", False),
        ("ALL", "Allstate Corp", "All eyes on the Fed", False),
        # Naming the company, or writing a 3+ char ticker as a ticker, counts.
        ("ON", _ON_SEMI, "ON Semiconductor beats estimates", True),
        ("AMD", "Advanced Micro Devices, Inc.", "AMD beats estimates on data-center demand", True),
    ],
)
def test_short_us_ticker_needs_the_company_or_the_written_ticker(
    symbol: str, name: str, title: str, kept: bool
) -> None:
    """The title match is case-folded, so a non-IN short-only signal used to
    score an uncorroborated 0.6; it now needs the company named or the ticker
    written as a ticker. "onsemi" is a brand the name never carries,
    so it is no name signal here (ON's own per-symbol feed carries it)."""
    target = _target(symbol=symbol, name=name, exchange="NASDAQ", region="US")
    row = _row("https://news.example/x", title)
    assert relevance.row_relevant(row, target=target) is kept


# --- R15-LEAD-050/052: only a common-word ticker needs an anchored mention ----


@pytest.mark.parametrize(
    ("symbol", "name", "title", "kept"),
    [
        ("GE", "GE Aerospace", "GE beats estimates on jet engine demand", True),
        ("BP", "BP p.l.c.", "BP beats estimates on refining margins", True),
        ("ALL", "Allstate Corp", "ALL EYES ON THE FED AS RATE DECISION LOOMS", False),
        ("ON", _ON_SEMI, "Shares of (NASDAQ: ON) jump", True),
    ],
)
def test_written_ticker_counts_unless_it_is_a_common_word(
    symbol: str, name: str, title: str, kept: bool
) -> None:
    """A ticker written upper-case names the company at any length (GE, BP);
    a common-word ticker (ALL, ON) only when anchored as a ticker, so an
    ALL-CAPS headline's prose never passes."""
    target = _target(symbol=symbol, name=name, exchange="NYSE", region="US")
    row = _row("https://news.example/x", title)
    assert relevance.row_relevant(row, target=target) is kept


def test_junk_filter_host_match_delegates_to_finance() -> None:
    """R15-CODE-RESEARCH-012: the junk-host filter's suffix match is
    ``finance.host_matches`` itself, not a second copy of the same rule — a
    host the domain-tier table matches (suffix-aware) is matched identically
    by the junk filter, because it's the SAME function."""
    from services.research import finance

    # efts.sec.gov is a subdomain of a PRIMARY_DOMAINS entry (sec.gov):
    # finance.host_matches says yes via the suffix rule.
    assert finance.host_matches("efts.sec.gov", finance.PRIMARY_DOMAINS) is True
    # The junk filter runs the exact same suffix rule against JUNK_HOSTS: a
    # subdomain of a junk host is dropped too.
    row = _row("https://www.youtube.com/watch?v=x", "Route Mobile Q4 results discussion")
    assert not relevance.row_relevant(row, target=ROUTE)
    assert finance.host_matches("www.youtube.com".removeprefix("www."), relevance.JUNK_HOSTS)


def test_common_word_in_ticker_needs_the_full_name_or_a_ticker_anchor() -> None:
    """R15-FINAL-004: an Indian target whose symbol IS an English word (FOCUS =
    Focus Lighting and Fixtures; SUPER = Super Auto Forge) was kept on any
    headline carrying the word. The word alone is prose; the company's other name
    tokens (or a ``NSE: FOCUS`` anchor) are what name it."""
    cases = [
        (
            _target(symbol="FOCUS", name="Focus Lighting and Fixtures Limited"),
            ["Focus on flying, not selfies", "European shares focus on inflation data"],
            ["Focus Lighting Q1 results", "NSE: FOCUS shares rally"],
        ),
        (
            _target(symbol="SUPER", name="Super Auto Forge Limited"),
            ["Super Bowl ad prices hit a record", "Super weekend for markets"],
            ["Super Auto Forge Q2 results"],
        ),
    ]
    for target, dropped, kept in cases:
        for title in dropped:
            row = _row("https://example.com/a", title)
            assert relevance.entity_match(row, target=target) <= relevance.WEAK_MATCH_CEILING
            assert not relevance.row_relevant(row, target=target), title
        for title in kept:
            row = _row("https://example.com/a", title)
            assert relevance.row_relevant(row, target=target), title


# --- R15-LEAD-136: ANY dictionary-word Indian name needs an anchor ------------

_WORD_NAME_CASES = [
    # (symbol, resolved name, prose headlines, company headlines)
    (
        "CAMPUS",
        "Campus Activewear Limited",
        ["Campus placements surge as IT hiring revives", "Back to campus: retailers bet on demand"],
        ["Campus Activewear Q2 profit rises 18%", "Campus shares jump after brokerage upgrade"],
    ),
    (
        "SAFARI",
        "Safari Industries (India) Limited",
        [
            "Safari tourism booms in Kenya as visitors return",
            "Apple Safari update fixes security flaw",
        ],
        [
            "Safari Industries Q1 results beat estimates",
            "Safari Industries stock hits 52-week high",
        ],
    ),
    (
        "ETERNAL",
        "ETERNAL LIMITED",
        ["The eternal debate: growth vs value investing"],
        ["Eternal shares rise as Blinkit orders grow", "Eternal Ltd Q2 profit falls on costs"],
    ),
    # Three more real NSE symbols that are English words and are in no curated
    # list — the rule is the dictionary property, not an enumeration.
    (
        "PERSISTENT",
        "Persistent Systems Limited",
        ["Persistent inflation keeps the RBI cautious"],
        ["Persistent Systems wins $100 million deal", "Persistent Q3 revenue grows 5%"],
    ),
    (
        "TRIDENT",
        "Trident Limited",
        ["Trident missile test draws scrutiny"],
        ["Trident shares rally on export orders", "NSE: TRIDENT hits upper circuit"],
    ),
    (
        "SYMPHONY",
        "Symphony Limited",
        ["A symphony of rate cuts lifts bond markets"],
        ["Symphony Q4 profit doubles on summer demand", "SYMPHONY gains 6% after results"],
    ),
]


@pytest.mark.parametrize(("symbol", "name", "dropped", "kept"), _WORD_NAME_CASES)
def test_dictionary_word_indian_name_needs_an_anchor(
    symbol: str, name: str, dropped: list[str], kept: list[str]
) -> None:
    """R15-LEAD-136: an NSE name that is a dictionary word but in no curated list
    scored 1.0 on any headline carrying the word, so a brief cited "Apple Safari
    update" as Safari Industries news. The word alone is prose; it names the
    company only when anchored (another name token, Ltd/shares/Qn after it, the
    ALL-CAPS ticker, an NSE/BSE marker)."""
    from services import symbol_resolver

    assert symbol_resolver.is_nse_symbol(symbol)
    assert symbol not in relevance.COMMON_WORD_TICKERS
    target = _target(symbol=symbol, name=name)
    for title in dropped:
        row = _row("https://economictimes.indiatimes.com/a", title)
        assert relevance.entity_match(row, target=target) <= relevance.WEAK_MATCH_CEILING, title
        assert not relevance.row_relevant(row, target=target), title
    for title in kept:
        row = _row("https://economictimes.indiatimes.com/a", title)
        assert relevance.row_relevant(row, target=target), title


def test_word_symbol_in_host_or_path_is_prose_but_quote_url_is_the_ticker() -> None:
    target = _target(symbol="SAFARI", name="Safari Industries (India) Limited")
    assert not relevance.row_relevant(
        _row("https://www.safaribookings.com/safari-tours", "Best tours this winter"),
        target=target,
    )
    assert relevance.row_relevant(
        _row("https://www.nseindia.com/get-quotes/equity?symbol=SAFARI", "Equity quote"),
        target=target,
    )


def test_non_word_and_marquee_indian_names_unchanged() -> None:
    """Non-word names (INFY, ROUTE's own name) and marquee family names (Reliance
    — a dictionary word the resolver binds as the brand) still count alone."""
    reliance = _target(symbol="RELIANCE", name="Reliance Industries Limited")
    infy = _target(symbol="INFY", name="Infosys Limited")
    assert relevance.row_relevant(
        _row("https://x.example/a", "Reliance to buy stake in X"), target=reliance
    )
    assert relevance.row_relevant(
        _row("https://x.example/a", "Infosys wins European deal"), target=infy
    )
    assert relevance.row_relevant(
        _row("https://x.example/a", "Route Mobile wins telecom deal"), target=ROUTE
    )


def test_dictionary_gate_is_india_scoped() -> None:
    """A US brand that is a dictionary word (Apple) keeps its brand signal —
    the non-IN path has its own gates and trusts the per-symbol feed."""
    aapl = _target(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", region="US")
    assert relevance.row_relevant(
        _row("https://x.example/a", "Apple unveils new iPhone"), target=aapl
    )


# --- R15-LEAD-136 attempt 2: case-folded words + the occurrence-form rule -----


def _nse_word_symbols() -> list[tuple[str, str]]:
    """Every alphabetic NSE symbol (bundled master snapshot) that is a dictionary
    entry, matched case-insensitively against the bundled word list."""
    import json
    from importlib import resources

    raw = resources.files("services.resolver_masters").joinpath("nse_instruments.json")
    rows = json.loads(raw.read_text(encoding="utf-8"))["instruments"]
    words = relevance._english_words()
    return [(sym, name) for sym, name, *_ in rows if sym.isalpha() and sym.lower() in words]


def test_every_nse_word_symbol_needs_an_anchor() -> None:
    """The class, enumerated: for EVERY NSE symbol that is a dictionary entry
    (TITAN, CUPID, TRENT, APOLLO fall out of the enumeration, not a hand list), a
    lower-case word use is dropped and an anchored headline is kept."""
    pairs = _nse_word_symbols()
    print(f"NSE symbols in the word list: {len(pairs)}")
    found = {sym for sym, _ in pairs}
    assert {"TITAN", "CUPID", "TRENT", "APOLLO", "CAMPUS", "SAFARI", "ETERNAL"} <= found
    assert len(pairs) >= 200
    url = "https://economictimes.indiatimes.com/markets/stocks/news/a"
    failures = []
    for sym, name in pairs:
        target = _target(symbol=sym, name=name)
        word = sym.lower()
        for title in (f"the {word} of the matter", f"Why the {word} debate is back"):
            if relevance.row_relevant(_row(url, title), target=target):
                failures.append(("kept", sym, title))
        anchored = f"{sym} shares hit upper circuit on NSE"
        if not relevance.row_relevant(_row(url, anchored), target=target):
            failures.append(("dropped", sym, anchored))
    assert not failures, failures


def test_every_nse_word_symbol_needs_an_anchor_in_title_case() -> None:
    """R15-LEAD-141: the enumeration INCLUDES 3-letter words (ACE, DEN, CUB, PAR,
    KEN fall out of it), and a sentence-initial Title-Case word use is dropped for
    every symbol in it while an anchored headline is kept. Marquee family names
    (RELIANCE) are the brand written alone and stay exempt by design."""
    pairs = _nse_word_symbols()
    three = sorted(sym for sym, _ in pairs if len(sym) == 3)
    print(f"NSE symbols in the word list: {len(pairs)} ({len(three)} three-letter: {three})")
    assert {"ACE", "DEN", "CUB", "PAR", "KEN"} <= set(three)
    url = "https://economictimes.indiatimes.com/markets/stocks/news/a"
    marquee = relevance._marquee_families()
    failures = []
    for sym, name in pairs:
        target = _target(symbol=sym, name=name)
        title = f"{sym.capitalize()} of the day: what it means for your weekend"
        if sym.lower() not in marquee and relevance.row_relevant(_row(url, title), target=target):
            failures.append(("kept", sym, title))
        anchored = f"{sym} shares hit upper circuit on NSE"
        if not relevance.row_relevant(_row(url, anchored), target=target):
            failures.append(("dropped", sym, anchored))
    assert not failures, failures


_THREE_LETTER_WORD_CASES = [
    # (symbol, resolved name, prose headlines, company headlines)
    (
        "ACE",
        "Action Construction Equipment Limited",
        ["Ace shuttler PV Sindhu storms into final"],
        [
            "ACE shares jump 6% on order win",
            "Action Construction Equipment Q2 profit rises",
            "NSE: ACE hits 52-week high",
            "Ace Q2 results: profit up 30%",
        ],
    ),
    (
        "DEN",
        "Den Networks Limited",
        ["Den of thieves: police bust Mumbai cyber fraud ring"],
        ["Den Networks Q1 loss narrows", "DEN surges 8% after results"],
    ),
    (
        "CUB",
        "City Union Bank Limited",
        ["Cub reporter's scoop rattles Delhi"],
        ["City Union Bank Q2 net profit rises 12%", "CUB shares rally on NSE"],
    ),
    (
        "PAR",
        "Par Drugs And Chemicals Limited",
        ["Par for the course: markets shrug off Fed in India"],
        ["Par Drugs And Chemicals shares hit upper circuit", "PAR Drugs Q1 results"],
    ),
    (
        "KEN",
        "Ken Enterprises Limited",
        ["Ken Griffin's Citadel posts record gains, Indian desk grows"],
        ["Ken Enterprises IPO subscribed 3 times", "KEN shares list at premium on NSE"],
    ),
]


@pytest.mark.parametrize(("symbol", "name", "dropped", "kept"), _THREE_LETTER_WORD_CASES)
def test_three_letter_word_ticker_needs_an_anchor(
    symbol: str, name: str, dropped: list[str], kept: list[str]
) -> None:
    """R15-LEAD-141: a 3-letter word ticker used Title-Case or sentence-initial
    is prose on an India host, not the short-symbol tier's 0.60 keep."""
    target = _target(symbol=symbol, name=name)
    url = "https://economictimes.indiatimes.com/a"
    for title in dropped:
        row = _row(url, title)
        assert relevance.entity_match(row, target=target) <= relevance.WEAK_MATCH_CEILING, title
        assert not relevance.row_relevant(row, target=target), title
    for title in kept:
        assert relevance.row_relevant(_row(url, title), target=target), title


def test_three_letter_words_leave_brand_list_headlines_unchanged() -> None:
    """LEAD-142 is filed separately: the 3-letter word entries must not move the
    4+-letter brand/list headline scores (pinned to the b7d37fd9 values)."""
    url = "https://economictimes.indiatimes.com/a"
    titan = _target(symbol="TITAN", name="Titan Company Limited")
    trent = _target(symbol="TRENT", name="Trent Limited")
    pinned = {
        "Titan, Trent lead Nifty gains as consumer stocks rally": (0.25, 0.25),
        "Stocks to buy: Titan, Lenskart, Dabur among Nomura's 17 consumer picks": (0.25, 0.0),
        "Trent rallies 5% as Zudio store count crosses 800": (0.0, 0.25),
    }
    for title, (want_titan, want_trent) in pinned.items():
        assert relevance.entity_match(_row(url, title), target=titan) == want_titan, title
        assert relevance.entity_match(_row(url, title), target=trent) == want_trent, title
    # A 3-letter brand token that is not the ticker keeps its base score too.
    zee = _target(symbol="ZEEL", name="Zee Entertainment Enterprises Limited")
    assert relevance.entity_match(_row(url, "Zee bags cricket rights"), target=zee) == 0.6


_PROPER_NOUN_WORD_CASES = [
    # (symbol, resolved name, prose headlines, company headlines)
    (
        "TITAN",
        "Titan Company Limited",
        [
            "Tech titan Elon Musk unveils new rocket",
            "Media titan Murdoch steps down",
            "Titan submersible inquiry report released",
            "Tech titan co-founder steps down",
        ],
        [
            "Titan Company shares rise",
            "Titan Q2 profit jumps 20%",
            "NSE: TITAN hits record",
            "Titan Co Ltd Q1 FY27 revenue grows 41%",
            "Titan Co. slips Thursday, underperforms market",
        ],
    ),
    (
        "CUPID",
        "Cupid Limited",
        ["Cupid's arrow: Valentine's Day spending hits record"],
        ["Cupid Ltd shares hit upper circuit", "Cupid Q1 results: profit doubles"],
    ),
    (
        "TRENT",
        "Trent Limited",
        ["River Trent floods as storm lashes England"],
        [
            "Trent Q2 profit jumps as Zudio expands",
            "Trent shares fall 4% after results",
            "Indian fashion retailer Trent's quarterly profit jumps",
            "Tata's Trent sees 22% profit rise as Zudio expands",
        ],
    ),
    (
        "APOLLO",
        "Apollo Micro Systems Limited",
        ["Apollo 11 anniversary: NASA looks back", "The apollo of modern pop"],
        ["Apollo Micro Systems bags defence order", "APOLLO surges 10% on order win"],
    ),
]


@pytest.mark.parametrize(("symbol", "name", "dropped", "kept"), _PROPER_NOUN_WORD_CASES)
def test_proper_noun_dictionary_word_needs_an_anchor(
    symbol: str, name: str, dropped: list[str], kept: list[str]
) -> None:
    """Webster's lists "Titan", "Cupid", "Trent", "Apollo" only capitalised; the
    word property is case-folded, so they are ambiguous like CAMPUS/SAFARI."""
    target = _target(symbol=symbol, name=name)
    url = "https://economictimes.indiatimes.com/a"
    for title in dropped:
        row = _row(url, title)
        assert relevance.entity_match(row, target=target) <= relevance.WEAK_MATCH_CEILING, title
        assert not relevance.row_relevant(row, target=target), title
    for title in kept:
        assert relevance.row_relevant(_row(url, title), target=target), title


def test_lowercase_occurrence_is_word_use_without_any_list(monkeypatch) -> None:
    """The occurrence-form rule holds with NO word list at all: a ticker written
    only in lower case in a mixed-case title is word usage. A corroborating
    neighbour ("ixigo shares") still names the company, and a capitalised
    non-word brand is untouched."""
    monkeypatch.setattr(relevance, "_english_words", frozenset)
    titan = _target(symbol="TITAN", name="Titan Company Limited")
    url = "https://economictimes.indiatimes.com/a"
    for title in ("Tech titan Elon Musk unveils new rocket", "Media titan Murdoch steps down"):
        assert not relevance.row_relevant(_row(url, title), target=titan), title
    assert relevance.row_relevant(_row(url, "Titan shares rise 3%"), target=titan)
    ixigo = _target(symbol="IXIGO", name="Le Travenues Technology Limited")
    assert relevance.row_relevant(_row(url, "ixigo shares jump 10% on Q2 beat"), target=ixigo)
    aapl = _target(symbol="AAPL", name="Apple Inc.", exchange="NASDAQ", region="US")
    assert not relevance.row_relevant(
        _row("https://x.example/a", "Why an apple a day still beats the Fed"), target=aapl
    )
    assert relevance.row_relevant(
        _row("https://x.example/a", "Apple unveils new iPhone"), target=aapl
    )


def test_snippet_naming_the_company_corroborates_a_capitalised_title_word() -> None:
    """A brand-only headline ("Trent rallies as Zudio expands") is kept when the
    snippet names the company with a corroborating token ("Trent Ltd"); a
    lower-case title use is never rescued by the snippet."""
    trent = _target(symbol="TRENT", name="Trent Limited")
    url = "https://economictimes.indiatimes.com/a"
    snippet = "Shares of Trent Ltd rose after the Tata retailer's Zudio added 60 stores."
    assert relevance.row_relevant(
        _row(url, "Trent rallies as Zudio expands", snippet), target=trent
    )
    assert not relevance.row_relevant(_row(url, "Trent rallies as Zudio expands"), target=trent)
    titan = _target(symbol="TITAN", name="Titan Company Limited")
    assert not relevance.row_relevant(
        _row(url, "Tech titan Elon Musk unveils new rocket", "Titan Company shares were flat."),
        target=titan,
    )
