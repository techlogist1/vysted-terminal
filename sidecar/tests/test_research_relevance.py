"""Tests for ``services.research.relevance`` — the entity gate on web rows (R8).

ROUTE-shaped fixtures mirror the live 69-junk-sources failure: a Route Mobile
(NSE: ROUTE) deep run whose bare-ticker web queries pulled crypto "Router
Protocol" pages, OTHER companies' exchange filings, and "what is support and
resistance" SEO junk into the brief's numbered sources.
"""

from __future__ import annotations

from typing import Any

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
