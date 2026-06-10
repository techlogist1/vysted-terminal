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
