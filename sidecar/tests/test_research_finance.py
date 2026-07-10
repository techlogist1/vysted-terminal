"""Tests for ``services.research.finance`` — the R7 finance tuning layer.

Pure-function coverage: the domain-rank table (exchange/regulator/filings →
Tier-1 press → general, with the company-IR heuristic and suffix matching),
stable tier-ranked source ordering, the prompt-side citation-preference line,
the ``site:`` query bias (filings/fundamentals only; region-aware), and the
server-date recency directive. No network, no LLM.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

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


# --- corporate_action_directive (R12) -------------------------------------------


def test_corporate_action_directive_forbids_uncited_specifics() -> None:
    """R12: the confabulated-corporate-action battery finding — a narrative
    invented five specific filing dates matching no real filing (one
    chronologically impossible), stated with the same confidence as real
    cited data. Every synthesis prompt now carries this line: a date, filing
    number, or record date is stated ONLY when a numbered source gives it,
    and a suspected-but-unsourced corporate action must be called out as
    unverified rather than asserted."""
    line = finance.corporate_action_directive()
    assert "CORPORATE ACTIONS" in line
    assert "filing number" in line
    assert "record date" in line
    assert "ONLY when a numbered source" in line
    assert "unverified in this run" in line


def test_corporate_action_directive_is_wired_into_every_synthesis_prompt() -> None:
    """Every narrative-synthesis call site — across ALL three depth tiers
    (NORMAL has no LLM synthesis of its own; DEEP and ULTRA each have one
    primary path plus ULTRA's per-section webweaver path and its single-call
    fallback) — references the shared directive. Four call sites total, so a
    future fifth synthesis prompt that forgets to wire it in is caught here
    rather than shipping a narrative with a date/filing-discipline gap."""
    research_dir = Path(finance.__file__).resolve().parent
    deep_src = (research_dir / "deep.py").read_text(encoding="utf-8")
    iter_src = (research_dir / "iter.py").read_text(encoding="utf-8")
    assert deep_src.count("finance.corporate_action_directive()") == 1  # _final_synthesis
    assert iter_src.count("finance.corporate_action_directive()") == 3  # report/section/heavy


# --- R13 entity-anchoring: the corroborating identity token(s) --------------


def test_anchor_tokens_indian_listing_gets_exchange_qualifier() -> None:
    # A BSE-listed target gets the exchange token; NSE gets NSE.
    assert finance.anchor_tokens(region="IN", exchange="BSE", sub_question="news") == "BSE"
    assert finance.anchor_tokens(region="IN", exchange="NSE", sub_question="news") == "NSE"
    # Region IN with no explicit exchange still anchors (defaults to NSE listing).
    assert finance.anchor_tokens(region="IN", exchange=None, sub_question="news") == "NSE"


def test_anchor_tokens_us_target_is_empty() -> None:
    # A US name needs no exchange token — its quoted display name pins it.
    assert finance.anchor_tokens(region="US", exchange="US", sub_question="revenue") == ""
    assert finance.anchor_tokens(region=None, exchange=None, sub_question="revenue") == ""


def test_anchor_tokens_industry_only_on_fundamentals_questions() -> None:
    industry = "Oil, Gas & Consumable Fuels / Refineries & Marketing"
    # Fundamentals-shaped → exchange + a concise industry token.
    assert (
        finance.anchor_tokens(
            region="IN", exchange="NSE", industry=industry, sub_question="revenue growth"
        )
        == "NSE Refineries"
    )
    # News/price-shaped → exchange only (the industry word would dilute recall).
    assert (
        finance.anchor_tokens(
            region="IN", exchange="NSE", industry=industry, sub_question="recent news"
        )
        == "NSE"
    )


def test_anchor_tokens_absent_industry_contributes_nothing() -> None:
    # KSE's industry is genuinely None — the anchor is just the exchange token.
    assert (
        finance.anchor_tokens(
            region="IN", exchange="BSE", industry=None, sub_question="quarterly earnings"
        )
        == "BSE"
    )
