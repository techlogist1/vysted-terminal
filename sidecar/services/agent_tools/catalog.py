"""The single capability catalog — one source of truth for every terminal tool.

Constitution Principle II ("One Capability Catalog, Many Consumers"): every
terminal capability is declared **once** here and projected to all consumers by
transformation, never by hand-maintained duplicate surfaces. The consumers are:

  - the internal copilot/persona adapters (Anthropic / OpenAI-family / Gemini),
    which serialise the ``internal`` entries via :mod:`services.agent_tools.schemas`;
  - the external MCP server (:mod:`services.mcp_server`), which projects the
    ``mcp`` entries to FastMCP tools (added in F5);
  - the Custom Agent Builder allow-list (:data:`models.custom_agent.KNOWN_TOOL_IDS`),
    which is exactly the set of agent-selectable internal entries.

Each entry carries a ``domain`` tag and a ``read_only`` flag. ``read_only`` is
the single declaration that drives BOTH the internal mutation gate and the
external MCP ``readOnlyHint`` — a capability cannot be read-only for one consumer
and mutating for another.

SAFETY (§6.5): no capability id here contains ``place_order`` / ``submit_order``
/ ``execute_order`` (the substrings ``tests/test_safety_end_to_end.py`` greps the
*registry* for). The one broker-action capability is ``propose_order``, which
only ever opens a review dialog — the AI has no path to ``confirm_and_place``.
This module is pure data: it imports nothing from the ``agent_tools`` package or
``models`` so it can be a dependency of both without a cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Literal

# Domains a capability can belong to. Used for grouping in the catalog and for
# the domain tag projected to the MCP surface (FR-021).
Domain = Literal[
    "quotes",
    "charts",
    "indicators",
    "research",
    "fundamentals",
    "screener",
    "macro",
    "earnings",
    "analyst",
    "filings",
    "quant",
    "portfolio",
    "brokers",
    "news",
    "workspace",
    "agents",
    "workflows",
    "terminal",
]

# How the host resolves an invocation of this capability:
#   read_handler  — a handler registered in the agent_tools registry.
#   per_invocation — resolved inside ``invoke_agent`` from request scope.
#   host_action    — executed by the frontend (drives the cockpit).
#   mcp_endpoint   — projected only to the external MCP surface (F5), bound to a
#                    sidecar HTTP route or runtime call rather than a registry id.
ToolKind = Literal["read_handler", "per_invocation", "host_action", "mcp_endpoint"]

_TF_ENUM = ["1d", "1h", "1wk", "1mo"]
_ASSET_ENUM = ["equity", "crypto"]
_MACRO_PROVIDERS = ["fred", "ecb", "imf", "world-bank"]
_DATE = {"type": "string", "description": "ISO date, YYYY-MM-DD"}


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


@dataclass(frozen=True)
class Capability:
    """One terminal capability — the single declaration projected to all consumers."""

    id: str
    description: str
    input_schema: dict[str, Any]
    domain: Domain
    read_only: bool
    kind: ToolKind
    #: Projected to the internal copilot/persona adapters.
    internal: bool = True
    #: Projected to the external MCP server (wired in F5).
    mcp: bool = False
    #: Aliases an external consumer may already know this capability by. Lets the
    #: MCP projection keep a familiar name while the internal name stays canonical.
    aliases: tuple[str, ...] = field(default_factory=tuple)


def _cap(
    id: str,
    *,
    description: str,
    input_schema: dict[str, Any],
    domain: Domain,
    read_only: bool,
    kind: ToolKind,
    internal: bool = True,
    mcp: bool = False,
    aliases: tuple[str, ...] = (),
) -> tuple[str, Capability]:
    return id, Capability(
        id=id,
        description=description,
        input_schema=input_schema,
        domain=domain,
        read_only=read_only,
        kind=kind,
        internal=internal,
        mcp=mcp,
        aliases=aliases,
    )


# ---------------------------------------------------------------------------
# The catalog — declared once, in domain order.
# ---------------------------------------------------------------------------

CAPABILITY_CATALOG: dict[str, Capability] = dict(
    [
        # --- quotes / charts -------------------------------------------------
        _cap(
            "price_data",
            description=(
                "Recent OHLCV bars + the latest quote for a symbol. Use to check "
                "price, recent action, volatility, or drawdown."
            ),
            input_schema=_obj(
                {
                    "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC/USDT"},
                    "timeframe": {"type": "string", "enum": _TF_ENUM, "default": "1d"},
                    "range": {
                        "type": "string",
                        "default": "6mo",
                        "description": "e.g. 1mo, 6mo, 1y",
                    },
                    "asset_class": {"type": "string", "enum": _ASSET_ENUM, "default": "equity"},
                },
                ["symbol"],
            ),
            domain="quotes",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "resolve_symbol",
            description=(
                "Resolve a free-text company name or ticker to a concrete "
                "instrument (ticker, exchange, region, asset class), locale-aware "
                "— 'Tata Steel' -> TATASTEEL on NSE, 'GOLDBEES' -> the NSE gold "
                "ETF. Returns disambiguation candidates when confidence is low. "
                "Call this FIRST when the user names a company so you load the "
                "right instrument and never dead-end on a name."
            ),
            input_schema=_obj(
                {
                    "query": {
                        "type": "string",
                        "description": "Company name or ticker, e.g. 'Tata Steel' or 'AAPL'.",
                    },
                    "region": {
                        "type": "string",
                        "enum": ["US", "IN", "GLOBAL"],
                        "description": "Optional locale override; defaults to the active region.",
                    },
                },
                ["query"],
            ),
            domain="quotes",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "compare_symbols",
            description=(
                "Compare 2-4 instruments side by side — latest quote, valuation "
                "(P/E, market cap, margins), and recent relative performance. Use "
                "when the user asks to compare names (e.g. 'NVDA vs AMD'). Pair it "
                "with arrange_layout(pattern='compare') to build the dual-chart cockpit."
            ),
            input_schema=_obj(
                {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "2-4 tickers to compare, e.g. ['NVDA','AMD'].",
                    },
                    "timeframe": {"type": "string", "enum": _TF_ENUM, "default": "1d"},
                    "asset_class": {"type": "string", "enum": _ASSET_ENUM, "default": "equity"},
                },
                ["symbols"],
            ),
            domain="quotes",
            read_only=True,
            kind="read_handler",
        ),
        # --- fundamentals ----------------------------------------------------
        _cap(
            "fundamentals",
            description=(
                "Valuation ratios (P/E, P/B, market cap, margins) + a company "
                "profile for a symbol. Use for value/quality analysis."
            ),
            input_schema=_obj(
                {"symbol": {"type": "string", "description": "Equity ticker, e.g. AAPL"}},
                ["symbol"],
            ),
            domain="fundamentals",
            read_only=True,
            kind="read_handler",
        ),
        # --- news ------------------------------------------------------------
        _cap(
            "news",
            description=(
                "Recent news headlines with sentiment, optionally filtered to a "
                "list of symbols. Use to check what's happening with a name."
            ),
            input_schema=_obj(
                {
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional ticker filter, e.g. ['AAPL','MSFT'].",
                    },
                    "limit": {"type": "integer", "default": 20},
                }
            ),
            domain="news",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "market_overview",
            description=(
                "Locale-aware market-state snapshot in ONE call — call this FIRST "
                "for a broad market question ('how's the market today', 'what "
                "moved'). Resolves the user's benchmark indices (US: S&P 500 / "
                "Nasdaq / Dow + SPY/QQQ; IN: Nifty 50 / Sensex), fetches a live "
                "quote for each, and pulls recent market headlines. Returns "
                "{region, indices:[...], headlines:[...]}. Synthesize from it — "
                "never answer market state from memory."
            ),
            input_schema=_obj(
                {
                    "region": {
                        "type": "string",
                        "enum": ["US", "IN", "GLOBAL"],
                        "description": ("Optional locale override; defaults to the active region."),
                    }
                }
            ),
            domain="news",
            read_only=True,
            kind="read_handler",
        ),
        # --- web search (Pass B / Pillar C) ----------------------------------
        _cap(
            "web_search",
            description=(
                "Search the web for current context to ground an answer — recent "
                "developments, analyst takes, macro events. Returns results + "
                "normalized citations (url/title/excerpt). Uses the user's configured "
                "search tier (their model's native search, a BYOK Exa key, or a local "
                "SearXNG). Cite what you use. If no backend is configured the result "
                "says so honestly — never fabricate a source."
            ),
            input_schema=_obj(
                {
                    "query": {"type": "string", "description": "The web search query."},
                    "num_results": {"type": "integer", "default": 6},
                    "category": {
                        "type": "string",
                        "enum": ["general", "news", "financial"],
                        "default": "general",
                        "description": "Bias retrieval toward news/financial sources.",
                    },
                },
                ["query"],
            ),
            domain="research",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "research",
            description=(
                "The ONE research capability — call it for 'research X' / 'set me up "
                "to look at X' / 'go deeper on X'. Resolves the symbol, pulls price, "
                "fundamentals, recent news, and filings, and (depth permitting) runs a "
                "budget-bounded search→read→reflect loop, returning a provenance-tagged "
                "bundle + a synthesized cited brief that auto-publishes into the brief "
                "panel (you need NOT call publish_brief for a deep run). Depth "
                "ESCALATES IN PLACE — start at 'quick', deepen only when the user asks "
                "to 'go deeper':\n"
                "- depth='quick' (default): one fast pass — price/fundamentals/news/"
                "filings + one web round. Instant; use this for the first 'research X' "
                "(then arrange the research-cockpit, load the chart, and write the "
                "cited brief with publish_brief, mode='FAST').\n"
                "- depth='deep': the IterResearch loop (a central evolving report, "
                "rebuilt each round so context never bloats). Use when the user says "
                "'go deeper' / wants a thorough multi-round answer — its brief "
                "auto-publishes, so you need NOT call publish_brief.\n"
                "- depth='heavy': the expert PANEL — several parallel research angles "
                "synthesized into one brief. Use only for the deepest ask ('go all "
                "out'). Higher cost.\n"
                "Bounded by rounds + wall-clock; on the budget ceiling it synthesizes "
                "from what it has (never times out into nothing). mode/angles are "
                "INTERNAL — drive depth, not those. The Perplexity backend is "
                "opt-in-per-run + paid and is NEVER auto-selected."
            ),
            input_schema=_obj(
                {
                    "query": {
                        "type": "string",
                        "description": (
                            "The company name or ticker, optionally followed by a "
                            "plain-language focus (e.g. 'Route Mobile — latest "
                            "quarterly results'). LEAD with the instrument name; "
                            "never a bare keyword list."
                        ),
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["normal", "deep", "ultra", "quick", "heavy"],
                        "default": "normal",
                        "description": (
                            "'quick' (default) = one fast pass. 'deep' = the "
                            "IterResearch evolving-report loop (use on 'go deeper'). "
                            "'heavy' = the expert panel of parallel angles (deepest, "
                            "higher cost). Escalate in place — never start at heavy."
                        ),
                    },
                    "rounds": {
                        "type": "integer",
                        "default": 3,
                        "description": "1-5 (deep/heavy only).",
                    },
                    "wall_seconds": {
                        "type": "integer",
                        "default": 120,
                        "description": "30-300 (deep/heavy only).",
                    },
                    "backend": {
                        "type": "string",
                        "enum": ["native", "perplexity"],
                        "default": "native",
                        "description": (
                            "INTERNAL. 'perplexity' (opt-in-per-run, paid, needs a "
                            "Perplexity key) is NEVER auto-selected — only reachable on "
                            "an explicit per-run opt-in. Otherwise the built-in "
                            "'native' loop."
                        ),
                    },
                },
                ["query"],
            ),
            domain="research",
            read_only=True,
            kind="read_handler",
        ),
        # --- screener --------------------------------------------------------
        _cap(
            "screener_run",
            description=(
                "Screen a universe of symbols against numeric/string criteria and "
                "return the matches. Use to find names that fit a thesis."
            ),
            input_schema=_obj(
                {
                    "formula": {
                        "type": "string",
                        "description": (
                            "Optional boolean formula evaluated server-side per symbol, "
                            "AND-combined with criteria. Fields: any numeric screener field "
                            "(pe_ratio, market_cap, roe, ...; aliases pe, marketCap, pb, ...). "
                            "Operators: + - * /, comparisons, and/or/not; functions abs/min/max. "
                            "E.g. 'pe < 15 and roe > 0.2' or 'market_cap / volume > 1e6'. "
                            "Rows missing a referenced field are skipped and itemized in "
                            "skip_details as missing_field:<f>."
                        ),
                    },
                    "universe": {
                        "type": "string",
                        "enum": ["sp500", "nifty50", "crypto-top50", "custom"],
                    },
                    "criteria": {
                        "type": "array",
                        "description": (
                            "Discriminated-union filters, AND-combined, e.g. "
                            '[{"field":"pe_ratio","operator":"lt","value":15}]'
                        ),
                        "items": {"type": "object"},
                    },
                    "group": {
                        "type": "object",
                        "description": (
                            "Optional AND/OR boolean tree (supersedes the flat "
                            "AND-only 'criteria' when present). Shape: "
                            '{"combinator":"and"|"or","criteria":[<criterion>|<group>...]}. '
                            "Nestable — a child may itself be a group. Use for OR "
                            "sweeps, e.g. (P/E<15 AND ROE>0.2) OR dividend_yield>0.04."
                        ),
                    },
                    "custom_symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Required when universe is 'custom'.",
                    },
                    "limit": {"type": "integer", "default": 50},
                },
                ["universe", "criteria"],
            ),
            domain="screener",
            read_only=True,
            kind="read_handler",
        ),
        # --- macro -----------------------------------------------------------
        _cap(
            "macro_series",
            description=(
                "Fetch a macroeconomic time series (e.g. DGS10, CPIAUCSL, UNRATE) "
                "from a named provider."
            ),
            input_schema=_obj(
                {
                    "series_id": {
                        "type": "string",
                        "description": "Provider-native series id, e.g. DGS10 (FRED)",
                    },
                    "provider": {
                        "type": "string",
                        "enum": _MACRO_PROVIDERS,
                        "description": "Which macro provider serves the series.",
                    },
                },
                ["series_id", "provider"],
            ),
            domain="macro",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "macro_search",
            description="Search a macro provider's catalog by free-text query.",
            input_schema=_obj(
                {
                    "q": {"type": "string", "description": "Free-text query, e.g. 'unemployment'"},
                    "provider": {"type": "string", "enum": _MACRO_PROVIDERS},
                    "limit": {"type": "integer", "default": 10},
                },
                ["q", "provider"],
            ),
            domain="macro",
            read_only=True,
            kind="read_handler",
        ),
        # --- earnings --------------------------------------------------------
        _cap(
            "earnings_upcoming",
            description=(
                "Scheduled earnings events in the next N days, optionally filtered "
                "to a watchlist of symbols."
            ),
            input_schema=_obj(
                {
                    "days": {
                        "type": "integer",
                        "default": 7,
                        "description": "Window length in days (1-60).",
                    },
                    "watchlist": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional symbol filter.",
                    },
                }
            ),
            domain="earnings",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "earnings_history",
            description="Historical EPS surprises (actual vs estimate) for a symbol.",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="earnings",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "earnings_estimates",
            description="Analyst estimate detail for a symbol's next upcoming report.",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="earnings",
            read_only=True,
            kind="read_handler",
        ),
        # --- analyst ratings -------------------------------------------------
        _cap(
            "analyst_history",
            description="Analyst rating-change history for a symbol (newest first).",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="analyst",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "analyst_individual",
            description="Per-firm currently-active analyst forecasts for a symbol.",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="analyst",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "price_target_history",
            description="Price-target change timeline for a symbol (newest first).",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="analyst",
            read_only=True,
            kind="read_handler",
        ),
        # --- SEC filings -----------------------------------------------------
        _cap(
            "sec_filings_list",
            description=(
                "List recent SEC filings (10-K, 10-Q, 8-K, DEF 14A, 3/4/5) for a company. "
                "Identify the company by symbol OR cik (provide at least one)."
            ),
            input_schema=_obj(
                {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker — provide this OR cik.",
                    },
                    "cik": {
                        "type": "string",
                        "description": "CIK — provide this OR symbol.",
                    },
                    "form_type": {
                        "type": "string",
                        "enum": ["10-K", "10-Q", "8-K", "DEF 14A", "3", "4", "5"],
                        "description": "Optional form-type filter.",
                    },
                    "limit": {"type": "integer", "default": 20},
                },
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "sec_filing_content",
            description="Parsed sections of one SEC filing identified by accession number.",
            input_schema=_obj(
                {
                    "accession": {
                        "type": "string",
                        "description": "SEC accession number, e.g. 0000320193-24-000123",
                    },
                    "identifier": {
                        "type": "string",
                        "description": "CIK or ticker that owns the filing.",
                    },
                },
                ["accession", "identifier"],
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "sec_insider_transactions",
            description=(
                "Recent insider transactions (Forms 3/4/5) for an issuer. "
                "Identify the issuer by symbol OR cik (provide at least one)."
            ),
            input_schema=_obj(
                {
                    "symbol": {
                        "type": "string",
                        "description": "Ticker — provide this OR cik.",
                    },
                    "cik": {
                        "type": "string",
                        "description": "CIK — provide this OR symbol.",
                    },
                    "form": {
                        "type": "string",
                        "enum": ["3", "4", "5"],
                        "description": "Optional form-type filter.",
                    },
                    "limit": {"type": "integer", "default": 30},
                },
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
        ),
        # --- India corporate disclosures (NSE+BSE) ----------------------------
        _cap(
            "corporate_announcements",
            description=(
                "Recent corporate announcements an Indian (NSE/BSE) listed company "
                "filed with its exchanges — results notices, board meetings, investor "
                "presentations, pledges, regulatory disclosures. Merged from BOTH "
                "exchange feeds and deduplicated, newest first; each item carries the "
                "exchange, category, attachment (PDF) URL, and timestamp. Use for "
                "'what has the company itself disclosed lately' on Indian names — the "
                "India counterpart of sec_filings_list."
            ),
            input_schema=_obj(
                {
                    "symbol": {
                        "type": "string",
                        "description": "NSE/BSE ticker, e.g. RELIANCE or TATASTEEL.",
                    },
                    "exchange": {
                        "type": "string",
                        "enum": ["NSE", "BSE"],
                        "description": "Optional single-exchange filter; omit to merge both.",
                    },
                    "limit": {"type": "integer", "default": 20},
                },
                ["symbol"],
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "shareholding_pattern",
            description=(
                "Quarterly shareholding pattern for an NSE-listed Indian company — "
                "promoter(+group), public, and employee-trust percentages per quarter, "
                "newest first, with each quarter's XBRL filing link (which carries the "
                "full FII/DII split). Use to check promoter-stake trends and ownership "
                "shifts on Indian names."
            ),
            input_schema=_obj(
                {
                    "symbol": {
                        "type": "string",
                        "description": "NSE ticker, e.g. RELIANCE.",
                    }
                },
                ["symbol"],
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
        ),
        # --- quant (QuantLib pricing) ---------------------------------------
        _cap(
            "price_option",
            description=(
                "Price one option via Black-Scholes, binomial, or Monte-Carlo. "
                "Read-only math — no broker or order side effects."
            ),
            input_schema=_obj(
                {
                    "exercise": {"type": "string", "enum": ["european", "american"]},
                    "payoff": {"type": "string", "enum": ["call", "put"]},
                    "spot": {"type": "number"},
                    "strike": {"type": "number"},
                    "risk_free_rate": {"type": "number", "description": "Annualised, e.g. 0.04"},
                    "dividend_yield": {"type": "number", "description": "Annualised, e.g. 0.0"},
                    "volatility": {"type": "number", "description": "Annualised, e.g. 0.2"},
                    "valuation_date": _DATE,
                    "expiry_date": _DATE,
                    "method": {
                        "type": "string",
                        "enum": ["black-scholes", "binomial", "monte-carlo"],
                    },
                    "binomial_steps": {
                        "type": "integer",
                        "description": "For the binomial method.",
                    },
                    "monte_carlo_paths": {"type": "integer", "description": "For Monte-Carlo."},
                    "monte_carlo_seed": {"type": "integer"},
                },
                [
                    "exercise",
                    "payoff",
                    "spot",
                    "strike",
                    "risk_free_rate",
                    "dividend_yield",
                    "volatility",
                    "valuation_date",
                    "expiry_date",
                    "method",
                ],
            ),
            domain="quant",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "compute_greeks",
            description=(
                "Analytic Greeks (+ the Black-Scholes price) for a European vanilla option."
            ),
            input_schema=_obj(
                {
                    "payoff": {"type": "string", "enum": ["call", "put"]},
                    "spot": {"type": "number"},
                    "strike": {"type": "number"},
                    "risk_free_rate": {"type": "number"},
                    "dividend_yield": {"type": "number"},
                    "volatility": {"type": "number"},
                    "valuation_date": _DATE,
                    "expiry_date": _DATE,
                },
                [
                    "payoff",
                    "spot",
                    "strike",
                    "risk_free_rate",
                    "dividend_yield",
                    "volatility",
                    "valuation_date",
                    "expiry_date",
                ],
            ),
            domain="quant",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "price_bond",
            description="Price a fixed-rate bond: clean/dirty price, accrued, duration, convexity.",
            input_schema=_obj(
                {
                    "face_value": {"type": "number", "default": 1000.0},
                    "coupon_rate": {"type": "number", "description": "Annual, e.g. 0.05"},
                    "coupons_per_year": {"type": "integer", "enum": [1, 2, 4]},
                    "issue_date": _DATE,
                    "maturity_date": _DATE,
                    "settlement_date": _DATE,
                    "yield_to_maturity": {"type": "number", "description": "Annual, e.g. 0.045"},
                },
                [
                    "coupon_rate",
                    "coupons_per_year",
                    "issue_date",
                    "maturity_date",
                    "settlement_date",
                    "yield_to_maturity",
                ],
            ),
            domain="quant",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "yield_curve_value",
            description="Bootstrap a yield curve from deposit/swap instruments and sample it.",
            input_schema=_obj(
                {
                    "valuation_date": _DATE,
                    "instruments": {
                        "type": "array",
                        "items": _obj(
                            {
                                "type": {"type": "string", "enum": ["deposit", "swap"]},
                                "tenor": {"type": "integer"},
                                "tenor_unit": {"type": "string", "enum": ["months", "years"]},
                                "rate": {"type": "number"},
                            },
                            ["type", "tenor", "tenor_unit", "rate"],
                        ),
                    },
                    "sample_count": {"type": "integer", "description": "Points to sample (>=2)."},
                },
                ["valuation_date", "instruments", "sample_count"],
            ),
            domain="quant",
            read_only=True,
            kind="read_handler",
        ),
        # --- backtest --------------------------------------------------------
        _cap(
            "backtest_summary",
            description=(
                "Digest a cached backtest run (metrics, best/worst/recent trades, "
                "walk-forward slices) by its run_id."
            ),
            input_schema=_obj(
                {"run_id": {"type": "string", "description": "Run id from backtest_engine."}},
                ["run_id"],
            ),
            domain="workflows",
            read_only=True,
            kind="read_handler",
        ),
        _cap(
            "run_custom_backtest",
            description=(
                "Author and run a CUSTOM backtest strategy from declarative "
                "entry/exit rules over indicator comparisons (e.g. entry "
                "'sma(20) > sma(50)', exit 'rsi(14) > 70'). Fields: open, high, "
                "low, close, volume. Functions: sma(n), ema(n), rsi(n), "
                "highest(n), lowest(n), stdev(n), change(n). Operators: "
                "+ - * /, comparisons, and/or/not. Parsed server-side with a "
                "restricted grammar (never eval) and executed in the SIMULATED "
                "backtest engine — §6.5: no order path is reachable. Returns "
                "the digest (metrics, best/worst/recent trades) plus the runId; "
                "the full result renders in the backtest panel and resolves via "
                "backtest_summary."
            ),
            input_schema=_obj(
                {
                    "entry": {
                        "type": "string",
                        "description": "Entry rule, e.g. 'sma(20) > sma(50)'.",
                    },
                    "exit": {
                        "type": "string",
                        "description": "Exit rule, e.g. 'rsi(14) > 70'.",
                    },
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tickers to trade.",
                    },
                    "start_date": _DATE,
                    "end_date": _DATE,
                    "position_size": {
                        "type": "number",
                        "default": 100,
                        "description": "Fixed share quantity per trade.",
                    },
                    "initial_capital": {"type": "number", "default": 100000},
                    "walk_forward_slices": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 1,
                    },
                },
                ["entry", "exit", "symbols", "start_date", "end_date"],
            ),
            domain="workflows",
            read_only=True,
            kind="read_handler",
        ),
        # --- brokers (read-only) --------------------------------------------
        _cap(
            "broker_portfolio",
            description=(
                "Read the user's REAL connected-broker account (positions, equity, "
                "buying power, per-position unrealized P&L) for analysis. Read-only — "
                "never places an order. `broker` defaults to 'kite' (Zerodha)."
            ),
            input_schema=_obj(
                {
                    "broker": {
                        "type": "string",
                        "enum": ["kite", "dhan", "angelone"],
                        "default": "kite",
                    }
                }
            ),
            domain="brokers",
            read_only=True,
            kind="read_handler",
        ),
        # --- per-invocation reads (resolved in invoke_agent) -----------------
        _cap(
            "get_terminal_state",
            description=(
                "Read what the user is currently looking at: open panels, the "
                "focused chart symbol + timeframe + indicators, the watchlist, and a "
                "portfolio summary. Call this whenever the user says 'this', 'it', "
                "'my chart', 'my watchlist', or 'my portfolio'."
            ),
            input_schema=_obj({}),
            domain="terminal",
            read_only=True,
            kind="per_invocation",
        ),
        _cap(
            "get_portfolio",
            description="Read the user's local (manually-entered) portfolio positions with P&L.",
            input_schema=_obj({}),
            domain="portfolio",
            read_only=True,
            kind="per_invocation",
        ),
        # --- host actions that DRIVE the terminal (mutations -> diff gate) ----
        _cap(
            "open_panel",
            description=(
                "Open or focus a terminal panel by id (chart, watchlist, news, "
                "portfolio, equity-overview, screener, macro, earnings, ...). "
                "For a symbol-aware panel (equity-overview, chart) ALWAYS pass "
                "`symbol` too, so the panel opens ON that company instead of "
                "empty — never open equity-overview for a named company "
                "without its symbol."
            ),
            input_schema=_obj(
                {
                    "panel": {"type": "string"},
                    "symbol": {
                        "type": "string",
                        "description": (
                            "Optional ticker to load into a symbol-aware panel "
                            "(equity-overview, chart) as it opens, e.g. "
                            "SAKSOFT.NS. Ignored by panels with no symbol."
                        ),
                    },
                },
                ["panel"],
            ),
            domain="terminal",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "set_chart_symbol",
            description="Load a symbol (and optional timeframe) into the chart panel.",
            input_schema=_obj(
                {
                    "symbol": {"type": "string"},
                    "timeframe": {"type": "string", "enum": _TF_ENUM},
                },
                ["symbol"],
            ),
            domain="charts",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "open_company_overview",
            description=(
                "Open the Equity Overview panel ON a company (fundamentals, "
                "statements, ratings) by ticker. Optional `highlight` names ONE "
                "metric to spotlight for the user (e.g. pe_ratio, market_cap, "
                "dividend_yield) — use it when explaining a specific metric "
                "('what is a P/E ratio? show me on X')."
            ),
            input_schema=_obj(
                {
                    "symbol": {"type": "string"},
                    "highlight": {
                        "type": "string",
                        "description": "Metric key to spotlight (optional).",
                    },
                },
                ["symbol"],
            ),
            domain="terminal",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "set_chart_indicators",
            description=(
                "Apply (or replace) the chart's technical indicators by key — e.g. "
                "sma, ema, rsi, macd, bollinger, vwap, volume. Pass the full desired "
                "set (it replaces the current selection). When the user says 'add a "
                "200-day average' or 'set me up to study NVDA', pick a sensible set "
                "for the asset class. Indicators are server-computed and overlay or "
                "drop into a sub-pane automatically."
            ),
            input_schema=_obj(
                {
                    "indicators": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Indicator keys, e.g. ['sma','volume','rsi','macd']. "
                            "Replaces the current selection."
                        ),
                    },
                    "symbol": {
                        "type": "string",
                        "description": "Optional — defaults to the focused chart's symbol.",
                    },
                    "timeframe": {"type": "string", "enum": _TF_ENUM},
                },
                ["indicators"],
            ),
            domain="indicators",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "add_to_watchlist",
            description="Add a symbol to the user's watchlist.",
            input_schema=_obj(
                {
                    "symbol": {"type": "string"},
                    "asset_class": {"type": "string", "enum": _ASSET_ENUM, "default": "equity"},
                },
                ["symbol"],
            ),
            domain="portfolio",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "propose_order",
            description=(
                "Prepare a broker order for the user to REVIEW. This NEVER places an "
                "order — it opens a confirmation dialog the user must explicitly "
                "approve. Use only when the user explicitly asks to buy or sell. "
                "Tell the user to review and confirm; never claim you placed it."
            ),
            input_schema=_obj(
                {
                    "symbol": {"type": "string"},
                    "side": {"type": "string", "enum": ["buy", "sell"]},
                    "quantity": {"type": "number"},
                    "order_type": {
                        "type": "string",
                        "enum": ["market", "limit"],
                        "default": "market",
                    },
                    "limit_price": {"type": "number", "description": "Required for a limit order."},
                },
                ["symbol", "side", "quantity"],
            ),
            domain="brokers",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "close_panel",
            description=(
                "Close a terminal panel by id (chart, watchlist, news, portfolio, "
                "equity-overview, screener, macro, earnings, ...). Use when the user "
                "asks to close, hide, or remove a panel."
            ),
            input_schema=_obj({"panel": {"type": "string"}}, ["panel"]),
            domain="terminal",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "focus_panel",
            description=(
                "Bring an already-open panel to the front and focus it, by id. Use "
                "when the user asks to focus, switch to, or surface a panel."
            ),
            input_schema=_obj({"panel": {"type": "string"}}, ["panel"]),
            domain="terminal",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "arrange_layout",
            description=(
                "Arrange the cockpit using a named template, for the user to review. "
                "'auto' arranges the panels ALREADY OPEN around their content — a "
                "published brief gets the dominant column, the chart gets width, the "
                "watchlist parks in a side rail; pick 'auto' whenever the user asks to "
                "arrange/organise/tidy their windows without naming a layout. "
                "Templates: 'single-focus' (full-width chart + stats — a quick look); "
                "'research-cockpit' (chart + fundamentals + news/filings + brief — the "
                "flagship deep dive); 'compare' (dual charts side by side, pass two "
                "tickers as `symbols`); 'macro-scan' (heatmap + chart + screener). "
                "'default' resets the layout; 'focus' maximises one panel (pass `panel`); "
                "'custom' places exactly the panels you name in `panels` ('put the chart "
                "here and news there') — use it for an ad-hoc arrangement no template fits. "
                "When the user says 'set me up to research X' pick 'research-cockpit'; "
                "for 'compare X vs Y' pick 'compare'. Choose the arrangement yourself "
                "— do not ask the user how to arrange."
            ),
            input_schema=_obj(
                {
                    "pattern": {
                        "type": "string",
                        "enum": [
                            "auto",
                            "default",
                            "focus",
                            "single-focus",
                            "research-cockpit",
                            "compare",
                            "macro-scan",
                            "custom",
                        ],
                        "default": "default",
                    },
                    "panel": {"type": "string", "description": "Required when pattern='focus'."},
                    "symbol": {
                        "type": "string",
                        "description": "Primary symbol for single-focus / research-cockpit.",
                    },
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Two tickers for pattern='compare'.",
                    },
                    "panels": {
                        "type": "array",
                        "description": (
                            "For pattern='custom': the panels to place, in order. Each item "
                            "is a panel name (chart|watchlist|news|portfolio|equity-overview|"
                            "macro|screener|brief) OR {panel, direction:left|right|above|below, "
                            "reference}. The first anchors; bare items tile coherently."
                        ),
                        "items": {"type": ["string", "object"]},
                    },
                },
                ["pattern"],
            ),
            domain="terminal",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "publish_brief",
            description=(
                "Publish a synthesized research brief into the brief panel (the B+A "
                "research output). Pass the markdown body (with inline [n] citation "
                "markers), the sources, the mode (FAST|DEEP), and metadata. Use after "
                "gathering data with research (a deep/heavy research run "
                "auto-publishes, so you need not call this for it). If web sources were "
                "unavailable, set web_available=false and say so in the brief — never "
                "fabricate a source."
            ),
            input_schema=_obj(
                {
                    "markdown": {"type": "string", "description": "The brief body (markdown)."},
                    "sources": {
                        "type": "array",
                        "items": _obj(
                            {
                                "url": {"type": "string"},
                                "title": {"type": "string"},
                                "excerpt": {"type": "string"},
                                "domain": {"type": "string"},
                            }
                        ),
                        "description": "Cited sources, in [n] order.",
                    },
                    "mode": {"type": "string", "enum": ["FAST", "DEEP"], "default": "FAST"},
                    "depth": {
                        "type": "string",
                        "enum": ["quick", "deep", "heavy"],
                        "description": (
                            "The true depth TIER reached (quick < deep < heavy). Sets the "
                            "brief's in-place 'Go deeper' escalation: omit it on a re-publish "
                            "of the same run and the prior tier is preserved (a heavy run is "
                            "never clobbered back to quick); set it explicitly to deepen."
                        ),
                    },
                    "query": {"type": "string"},
                    "symbol": {"type": "string"},
                    "web_available": {"type": "boolean", "default": True},
                    "note": {
                        "type": "string",
                        "description": "e.g. the honest no-web-search note.",
                    },
                    "structured": {
                        "type": "object",
                        "description": (
                            "The provenance-tagged structured bundle "
                            "(price/fundamentals/news/filings) from the research result — "
                            "pass it through verbatim so the panel renders native metric "
                            "cards. Optional; omit if you have none."
                        ),
                    },
                },
                ["markdown"],
            ),
            domain="research",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "write_screener_filters",
            description=(
                "Write/configure the screener's filter criteria into the panel for the "
                "user to REVIEW and run. This does NOT run the screener — it stages the "
                "filters in the screener panel; the user reviews them and clicks Run. "
                "Pass a flat `criteria` list (each: {field, operator, value} where "
                "operator is gt|lt|gte|lte|between|eq|in; numeric fields like pe_ratio, "
                "market_cap, roe, dividend_yield, debt_to_equity, price, volume — "
                "fractions for ratios e.g. roe 0.2 = 20%). For OR / nested logic, pass a "
                "`group` tree {combinator:'and'|'or', criteria:[... leaf or nested group]} "
                "which supersedes the flat list. Optionally set `universe` "
                "(sp500|nifty50|crypto-top50|custom) and `limit`. Use when the user asks "
                "to screen/scan for stocks by fundamentals."
            ),
            input_schema=_obj(
                {
                    "criteria": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": (
                            "Flat AND-combined leaf criteria, each {field, operator, value}."
                        ),
                    },
                    "group": {
                        "type": "object",
                        "description": (
                            "Optional nested AND/OR tree {combinator, criteria:[...]} — "
                            "supersedes the flat criteria. A child may itself be a group."
                        ),
                    },
                    "universe": {
                        "type": "string",
                        "enum": ["sp500", "nifty50", "crypto-top50", "custom"],
                        "description": "Optional universe to screen.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional max rows (default 200).",
                    },
                },
                ["criteria"],
            ),
            domain="screener",
            read_only=False,
            kind="host_action",
        ),
    ]
)

# MCP projection rule (FR-020/022): every handler-backed READ capability is
# exposed to the external MCP surface — EXCEPT those that need local-only
# context (a backtest run_id lives only in this session). Per-invocation reads
# and host actions are inherently local (terminal/request scope) and are never
# projected. Driving `mcp` from this ONE rule keeps the internal copilot surface
# and the external MCP surface a single source of truth (the SC-004 parity audit
# locks it).
_MCP_INTERNAL_ONLY: frozenset[str] = frozenset({"backtest_summary"})

CAPABILITY_CATALOG = {
    cid: replace(cap, mcp=(cap.kind == "read_handler" and cid not in _MCP_INTERNAL_ONLY))
    for cid, cap in CAPABILITY_CATALOG.items()
}


# ---------------------------------------------------------------------------
# Projections — the only sanctioned way consumers read the catalog.
# ---------------------------------------------------------------------------

#: Forbidden order-placement substrings (mirrors the §6.5 audit grep). A catalog
#: id containing any of these would be a safety regression; asserted in tests.
FORBIDDEN_TOOL_SUBSTRINGS = ("place_order", "submit_order", "execute_order", "auto_approve")


def internal_capabilities() -> list[Capability]:
    """Capabilities projected to the internal copilot/persona adapters."""
    return [c for c in CAPABILITY_CATALOG.values() if c.internal]


def internal_tool_ids() -> list[str]:
    """Ids of every capability the internal copilot can be given (allow-list domain)."""
    return [c.id for c in internal_capabilities()]


def mcp_capabilities() -> list[Capability]:
    """Capabilities projected to the external MCP server (FR-020/022).

    The same capabilities the internal copilot uses, by the SAME name — so an
    external agent builds on Vysted with no divergence. Read-only is honoured
    via each capability's ``read_only`` flag (the MCP ``readOnlyHint``).
    """
    return [c for c in CAPABILITY_CATALOG.values() if c.mcp]


def mcp_tool_ids() -> list[str]:
    """Ids of every capability exposed on the external MCP surface."""
    return [c.id for c in mcp_capabilities()]


def read_handler_ids() -> list[str]:
    """Ids of internal capabilities backed by a registered agent_tools handler.

    These are exactly the ids a registry-completeness audit expects to find in
    :func:`services.agent_tools.registered_tools` once all tools are registered.
    """
    return [c.id for c in internal_capabilities() if c.kind == "read_handler"]


def agent_selectable_tool_ids() -> frozenset[str]:
    """The Custom Agent Builder allow-list — every agent-selectable internal id.

    A custom agent may select any tool the first-party copilot can use; each id
    resolves at the host (registry handler, per-invocation closure, or host
    action). Safety is host-enforced regardless of selection (``propose_order``
    only proposes; §6.5 governs placement).
    """
    return frozenset(internal_tool_ids())


def domain_of(tool_id: str) -> Domain | None:
    cap = CAPABILITY_CATALOG.get(tool_id)
    return cap.domain if cap else None


def is_read_only(tool_id: str) -> bool | None:
    cap = CAPABILITY_CATALOG.get(tool_id)
    return cap.read_only if cap else None


__all__ = [
    "CAPABILITY_CATALOG",
    "Capability",
    "Domain",
    "FORBIDDEN_TOOL_SUBSTRINGS",
    "ToolKind",
    "agent_selectable_tool_ids",
    "domain_of",
    "internal_capabilities",
    "internal_tool_ids",
    "is_read_only",
    "mcp_capabilities",
    "mcp_tool_ids",
    "read_handler_ids",
]
