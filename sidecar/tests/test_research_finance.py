"""Tests for ``services.research.finance`` — the R7 finance tuning layer.

Pure-function coverage: the domain-rank table (exchange/regulator/filings →
Tier-1 press → general, with the company-IR heuristic and suffix matching),
stable tier-ranked source ordering, the prompt-side citation-preference line,
the ``site:`` query bias (filings/fundamentals only; region-aware), and the
server-date recency directive. No network, no LLM.
"""

from __future__ import annotations

from datetime import UTC, datetime

from services.research import finance
from services.research.models import ResearchSource


def _src(url: str, domain: str | None = None) -> ResearchSource:
    return ResearchSource(url=url, title=url, excerpt="x", domain=domain)


# --- domain_of / domain_tier -------------------------------------------------


def test_domain_of_strips_scheme_www_and_port() -> None:
    assert finance.domain_of("https://www.sec.gov:443/filing/x") == "sec.gov"
    assert finance.domain_of("nseindia.com/quotes") == "nseindia.com"
    assert finance.domain_of("") == ""


def test_primary_record_domains_rank_first() -> None:
    for url in (
        "https://www.sec.gov/cgi-bin/browse-edgar",
        "https://efts.sec.gov/LATEST/search-index?q=x",  # subdomain suffix match
        "https://www.nseindia.com/get-quotes/equity?symbol=X",
        "https://www.bseindia.com/stock-share-price/x",
        "https://www.sebi.gov.in/enforcement/orders.html",
        "https://rbi.org.in/Scripts/NotificationUser.aspx",
    ):
        assert finance.domain_tier(url) == finance.TIER_PRIMARY, url


def test_company_ir_pages_rank_primary_by_heuristic() -> None:
    assert finance.domain_tier("https://ir.nvidia.com/financial-info") == finance.TIER_PRIMARY
    assert finance.domain_tier("https://investors.apple.com/") == finance.TIER_PRIMARY
    assert (
        finance.domain_tier("https://example.com/investor-relations/results")
        == finance.TIER_PRIMARY
    )


def test_tier1_press_ranks_second_and_general_third() -> None:
    assert finance.domain_tier("https://www.reuters.com/markets/x") == finance.TIER_PRESS
    assert finance.domain_tier("https://www.moneycontrol.com/news/x") == finance.TIER_PRESS
    assert (
        finance.domain_tier("https://economictimes.indiatimes.com/markets/x") == finance.TIER_PRESS
    )
    assert finance.domain_tier("https://randomblog.example/post") == finance.TIER_GENERAL


def test_seo_lookalike_does_not_rank_primary() -> None:
    """``notsec.gov.evil.com`` must not suffix-match ``sec.gov``."""
    assert finance.domain_tier("https://sec.gov.evil.com/x") == finance.TIER_GENERAL
    assert finance.domain_tier("https://fakereuters.com/x") == finance.TIER_GENERAL


# --- rank_sources / priority_note --------------------------------------------


def test_rank_sources_orders_by_tier_stable_within_tier() -> None:
    blog_a = _src("https://blog-a.example/x")
    press = _src("https://www.reuters.com/markets/y")
    blog_b = _src("https://blog-b.example/z")
    filing = _src("https://www.sec.gov/filing/10k")
    ranked = finance.rank_sources([blog_a, press, blog_b, filing])
    assert [s.url for s in ranked] == [filing.url, press.url, blog_a.url, blog_b.url]


def test_rank_sources_falls_back_to_domain_label() -> None:
    """A ``vysted://`` provenance source with a press domain label still ranks."""
    via_label = _src("vysted://news/X", domain="reuters.com")
    blog = _src("https://blog.example/x")
    ranked = finance.rank_sources([blog, via_label])
    assert ranked[0] is via_label


def test_priority_note_names_the_marker_numbers() -> None:
    sources = [
        _src("https://www.sec.gov/filing/10k"),
        _src("https://www.reuters.com/markets/y"),
        _src("https://blog.example/x"),
    ]
    note = finance.priority_note(sources)
    assert "primary record" in note and "[1]" in note
    assert "tier-1 press" in note and "[2]" in note


def test_priority_note_empty_when_all_general() -> None:
    assert finance.priority_note([_src("https://blog.example/x")]) == ""


# --- bias_query ----------------------------------------------------------------


def test_bias_query_filters_filings_to_regulators_by_region() -> None:
    assert "site:sec.gov" in finance.bias_query("NVDA 10-K", dim="filings", region="US")
    biased_in = finance.bias_query("RELIANCE filings", dim="filings", region="IN")
    assert "site:nseindia.com" in biased_in and "site:bseindia.com" in biased_in
    # Unknown / missing region floors to the US hint, never an unbiased query.
    assert "site:sec.gov" in finance.bias_query("q", dim="fundamentals", region=None)


def test_bias_query_leaves_news_and_price_unfiltered_for_recall() -> None:
    assert finance.bias_query("NVDA latest news", dim="news", region="US") == "NVDA latest news"
    assert finance.bias_query("NVDA price trend", dim="price", region="IN") == "NVDA price trend"


# --- date_directive -------------------------------------------------------------


def test_date_directive_carries_the_server_date_and_recency_preference() -> None:
    line = finance.date_directive()
    assert datetime.now(UTC).strftime("%Y-%m-%d") in line
    assert "Server date" in line
    assert "recently dated" in line
