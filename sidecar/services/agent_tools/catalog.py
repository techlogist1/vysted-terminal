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

SAFETY (§6.5): Vysted has no brokerage connection and no trading path (D81). No
capability id here contains ``place_order`` / ``submit_order`` / ``execute_order``
(:data:`FORBIDDEN_TOOL_SUBSTRINGS`), and ``tests/test_no_trading_surface.py``
pins that no order, broker or simulated-account capability exists.
This module is pure data: it imports nothing from the ``agent_tools`` package or
``models.custom_agent`` so it can be a dependency of both without a cycle. Its
one import, ``services.indicators.SUPPORTED_INDICATORS``, is the indicator
registry the ``set_chart_indicators`` enum derives from (C10).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Literal

from services import model_registry
from services.indicators import SUPPORTED_INDICATORS
from services.research.depth import DEPTH_DEEP, DEPTH_ULTRA, PROFILES

#: The agent's arrange_layout templates and the panels each places (contract C8,
#: R15-AGENT-055): the same file the frontend planner builds its plans from, so
#: the tool description never promises a panel the host does not place. It sits
#: beside model_registry.json in ``config/`` (bundled whole by the sidecar build).
LAYOUT_TEMPLATES: dict[str, dict[str, Any]] = {
    template_id: entry
    for template_id, entry in json.loads(
        (model_registry._registry_path().parent / "layout_templates.json").read_text(
            encoding="utf-8"
        )
    ).items()
    if not template_id.startswith("_")
}


def _layout_templates_prose() -> str:
    """One clause per template: its id, what it is for, the panels it places."""
    return "; ".join(
        f"'{template_id}' ({entry['summary']}; places {' + '.join(entry['panels'])})"
        for template_id, entry in LAYOUT_TEMPLATES.items()
    )


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
    "news",
    "workspace",
    "agents",
    "workflows",
    "terminal",
]

#: Context admission on a window-bound lane (D-B4-1, R15-AGENT-008): when the
#: full tool set would crowd the model's window, these domains ride every turn
#: and a specialist domain joins only when one of its cue words (matched at a
#: word start, lower-cased) appears in the prompt or the recent user turns.
ALWAYS_ON_DOMAINS: frozenset[Domain] = frozenset(
    {
        "quotes",
        "charts",
        "indicators",
        "research",
        "fundamentals",
        "news",
        "terminal",
        "workspace",
        "portfolio",
    }
)
DOMAIN_CUES: dict[Domain, tuple[str, ...]] = {
    "screener": ("screen", "filter", "stocks with", "stocks under", "p/e under", "scan"),
    "macro": ("macro", "gdp", "inflation", "cpi", "unemployment", "interest rate", "economy"),
    "earnings": ("earnings", "eps", "quarterly result", "guidance", "concall", "transcript"),
    "analyst": ("analyst", "rating", "price target", "upgrade", "downgrade", "consensus"),
    "filings": (
        "filing",
        "10-k",
        "10-q",
        "8-k",
        "edgar",
        "insider",
        "announcement",
        "disclosure",
        "shareholding",
        "promoter",
        "bulk deal",
        "block deal",
        "sast",
        "corporate action",
        "dividend",
        "bonus",
        "stock split",
    ),
    "quant": (
        "option",
        "greeks",
        "black-scholes",
        "bond",
        "yield curve",
        "implied vol",
        "open interest",
        "f&o",
    ),
    "agents": ("agent", "delegate"),
    "workflows": ("backtest", "strategy", "workflow"),
}

# How the host resolves an invocation of this capability:
#   read_handler  — a handler registered in the agent_tools registry.
#   per_invocation — resolved inside ``invoke_agent`` from request scope.
#   host_action    — executed by the frontend (drives the cockpit).
#   mcp_endpoint   — projected only to the external MCP surface (F5), bound to a
#                    sidecar HTTP route or runtime call rather than a registry id.
ToolKind = Literal["read_handler", "per_invocation", "host_action", "mcp_endpoint"]

_TF_ENUM = ["1d", "1h", "1wk", "1mo"]
_ASSET_ENUM = ["equity", "crypto"]
#: The research wall range, read from the depth table so the schema can never
#: advertise a ceiling below a profile's own wall (R15-CODE-RESEARCH-001).
_RESEARCH_WALL_DESCRIPTION = (
    f"30-{max(300, *(p.wall_seconds for p in PROFILES.values()))} seconds "
    "(deep/heavy only). Omit it: each depth sets its own budget (deep "
    f"{PROFILES[DEPTH_DEEP].wall_seconds}, heavy {PROFILES[DEPTH_ULTRA].wall_seconds})."
)
_MACRO_PROVIDERS = ["fred", "ecb", "imf", "world-bank"]
_DATE = {"type": "string", "description": "ISO date, YYYY-MM-DD"}
# R10 (D40): the screener universes, including the full-market India universes
# resolved from the bundled resolver masters. Mirrors ScreenerUniverseId in
# models/screener.py / types/screener.ts (the contracts commit) — keep in sync.
_UNIVERSE_ENUM = ["sp500", "nifty50", "crypto-top50", "nse-all", "bse-all", "india-all", "custom"]


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
    #: Former ids of this capability. A stored agent's tool list still names a
    #: renamed tool by its old id; :func:`resolve_tool_ids` maps it here
    #: (R15-LIFECYCLE-025).
    aliases: tuple[str, ...] = field(default_factory=tuple)
    #: Granted to every FIRST-PARTY agent at load time (R10, E5): the loader
    #: unions each first-party spec's tools with :func:`default_grant_tool_ids`,
    #: so a tool can never fall out of the belt by agent-JSON drift. Custom
    #: agents stay author-picked.
    default_grant: bool = True
    #: Per-dispatch wall budget (R10, E7) enforced at the runtime's tool
    #: boundary via ``asyncio.wait_for``. ``None`` = no timeout (host actions /
    #: per-invocation locals are exempt).
    timeout_seconds: float | None = None
    #: The wall budget comes from the call's own args (``research``: its
    #: ``wall_seconds``/depth), computed by the runtime, so a fixed
    #: ``timeout_seconds`` cannot also be set (R15-AGENT-070).
    timeout_from_args: bool = False
    #: The result carries third-party text (web pages, news, exchange
    #: disclosures, research built from them). The runtime fences it with
    #: ``scrub.wrap_untrusted`` in the model-facing tool message, so injected
    #: instructions read as data, never as the user's request (R15-AGENT-021).
    untrusted_text: bool = False

    def __post_init__(self) -> None:
        if self.timeout_from_args and self.timeout_seconds is not None:
            raise ValueError(
                f"{self.id}: timeout_from_args derives the budget from the call's "
                "args; a fixed timeout_seconds would be ignored"
            )

    @property
    def internal(self) -> bool:
        """Projected to the internal copilot/persona adapters (every kind but ``mcp_endpoint``)."""
        return self.kind != "mcp_endpoint"

    @property
    def mcp(self) -> bool:
        """Projected to the external MCP server — derived from the ONE rule below, never set."""
        return self.kind == "read_handler" and self.id not in _MCP_INTERNAL_ONLY


# MCP projection rule (FR-020/022, R15-AGENT-083): the external MCP surface is
# READ-ONLY in 0.9. Every handler-backed read capability is exposed — EXCEPT
# those bound to local-only context: a backtest run_id lives only in this
# session, so neither its reader (backtest_summary) nor its writer
# (run_custom_backtest, which caches the run and would otherwise advertise
# readOnlyHint=true, R15-AGENT-066) is projected. Per-invocation reads are
# request-scoped and host actions mutate the cockpit behind the in-app
# proposed-changes gate, so neither is projected. Exposing writes through a
# host-side queue is a future operator decision. The exposed set is pinned by
# name in test_mcp_catalog_parity, so each new read_handler is an explicit
# expose-or-exclude decision (R15-AGENT-067).
_MCP_INTERNAL_ONLY: frozenset[str] = frozenset({"backtest_summary", "run_custom_backtest"})


def _cap(id: str, **fields: Any) -> tuple[str, Capability]:
    """``(id, Capability)`` — an entry passes only what it sets; defaults live on the class."""
    return id, Capability(id=id, **fields)


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
                "price, recent action, volatility, or drawdown. Returns at most "
                "the newest 90 bars: bars_returned, bars_available and "
                "window_start say which window the bars actually cover, so compute "
                "a figure over that window (or a shorter range), not the one asked."
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
            timeout_seconds=15.0,
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
            timeout_seconds=15.0,
        ),
        _cap(
            "compare_symbols",
            description=(
                "Compare 2-4 instruments side by side — latest quote, valuation "
                "(P/E, market cap, margins), and recent relative performance. Use "
                "when the user asks to compare names (e.g. 'NVDA vs AMD'). Pair it "
                "with arrange_layout(pattern='compare') to chart the pair together."
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
            timeout_seconds=15.0,
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
            timeout_seconds=15.0,
        ),
        _cap(
            "financial_statements",
            description=(
                "One financial statement for a company — income, balance sheet or "
                "cash flow — annual (fiscal years) or quarterly (ISO period-end "
                "dates), newest first, capped at the newest 8 periods "
                "(periods_available says how many exist). Use for revenue, margin, "
                "debt or cash-flow series over years or quarters; fundamentals "
                "gives only point-in-time ratios."
            ),
            input_schema=_obj(
                {
                    "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or TCS.NS"},
                    "statement": {"type": "string", "enum": ["income", "balance", "cashflow"]},
                    "period": {
                        "type": "string",
                        "enum": ["annual", "quarterly"],
                        "default": "annual",
                    },
                },
                ["symbol", "statement"],
            ),
            domain="fundamentals",
            read_only=True,
            kind="read_handler",
            timeout_seconds=30.0,
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
            timeout_seconds=20.0,
            untrusted_text=True,
        ),
        _cap(
            "market_overview",
            description=(
                "Locale-aware market-state snapshot in ONE call — call this FIRST "
                "for a broad market question ('how's the market today', 'what "
                "moved'). Resolves the user's benchmark indices (US: S&P 500 / "
                "Nasdaq / Dow + SPY/QQQ; IN: Nifty 50 / Sensex), fetches a live "
                "quote for each, and pulls recent market headlines. Returns "
                "{region, indices:[...], headlines:[...]}; headlines_error is set "
                "when the news feed is down (then say headlines are unavailable, "
                "not that there is no news). Synthesize from it — "
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
            timeout_seconds=20.0,
            untrusted_text=True,
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
            timeout_seconds=25.0,
            untrusted_text=True,
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
                        "description": _RESEARCH_WALL_DESCRIPTION,
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
            timeout_from_args=True,
            untrusted_text=True,
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
                        "enum": _UNIVERSE_ENUM,
                    },
                    "criteria": {
                        "type": "array",
                        "description": (
                            "Discriminated-union filters, AND-combined. Four shapes: "
                            'numeric threshold {"field":"pe_ratio","operator":"lt","value":15} '
                            "(gt|lt|gte|lte; fractions for ratios — roe 0.15 = 15%); numeric "
                            'between {"field":"pe_ratio","operator":"between",'
                            '"value":{"min":10,"max":20}}; '
                            "string equality on sector/industry/currency "
                            '{"field":"sector","operator":"eq","value":"Technology"}; set '
                            'membership {"field":"symbol","operator":"in","value":["A","B"]} '
                            "(set fields: symbol|sector|industry). For a sector-scoped screen "
                            "ALWAYS filter server-side via the sector/industry criterion — "
                            "post-filtering a limit-capped sweep client-side can silently "
                            "drop matches."
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
            timeout_seconds=150.0,
        ),
        # --- macro -----------------------------------------------------------
        _cap(
            "macro_series",
            aliases=("macro",),
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
            timeout_seconds=20.0,
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
            timeout_seconds=20.0,
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
            timeout_seconds=20.0,
        ),
        _cap(
            "earnings_history",
            description="Historical EPS surprises (actual vs estimate) for a symbol.",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="earnings",
            read_only=True,
            kind="read_handler",
            timeout_seconds=20.0,
        ),
        _cap(
            "earnings_estimates",
            description="Analyst estimate detail for a symbol's next upcoming report.",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="earnings",
            read_only=True,
            kind="read_handler",
            timeout_seconds=20.0,
        ),
        # --- analyst ratings -------------------------------------------------
        _cap(
            "analyst_history",
            description="Analyst rating-change history for a symbol (newest first).",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="analyst",
            read_only=True,
            kind="read_handler",
            timeout_seconds=20.0,
        ),
        _cap(
            "analyst_individual",
            description="Per-firm currently-active analyst forecasts for a symbol.",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="analyst",
            read_only=True,
            kind="read_handler",
            timeout_seconds=20.0,
        ),
        _cap(
            "price_target_history",
            description="Price-target change timeline for a symbol (newest first).",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="analyst",
            read_only=True,
            kind="read_handler",
            timeout_seconds=20.0,
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
            timeout_seconds=30.0,
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
                    "form_type": {
                        "type": "string",
                        "description": (
                            "Optional: the filing's form as sec_filings_list reported it "
                            "(e.g. 10-K). Needed to find an older filing — without it, "
                            "only the issuer's most recent filings of any form are searched."
                        ),
                    },
                },
                ["accession", "identifier"],
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
            timeout_seconds=30.0,
            untrusted_text=True,
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
            timeout_seconds=30.0,
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
            timeout_seconds=30.0,
            untrusted_text=True,
        ),
        _cap(
            "shareholding_pattern",
            description=(
                "Quarterly shareholding pattern for an NSE- or BSE-listed Indian "
                "company, newest quarter first: promoter(+group), public (incl. "
                "institutions) and the non-institutional float, the FII/DII/"
                "institutions split, and the promoter pledge (pledged or encumbered, "
                "percent of the promoter holding; 0 when the filing declares none, "
                "null when it declares nothing). source/split_source/split_as_of/"
                "split_basis state where each figure came from. Use to check "
                "promoter-stake and pledge trends and ownership shifts on Indian names."
            ),
            input_schema=_obj(
                {
                    "symbol": {
                        "type": "string",
                        "description": "NSE/BSE ticker, e.g. RELIANCE.",
                    }
                },
                ["symbol"],
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
            timeout_seconds=30.0,
        ),
        _cap(
            "corporate_actions",
            description=(
                "Corporate actions of an Indian (NSE/BSE) listed company from BOTH "
                "exchanges — dividends, bonuses, splits, rights issues and buybacks, "
                "newest ex-date first. Each row: kind, the exchange's verbatim "
                "purpose, ratio (e.g. '7:24'), amount_per_share, ex_date, "
                "record_date, payment_date and exchange ('NSE+BSE' when both carry "
                "it). Use for 'last dividend and its dates', bonus/split history or "
                "dilution on Indian names."
            ),
            input_schema=_obj(
                {"symbol": {"type": "string", "description": "NSE/BSE ticker, e.g. JONJUA."}},
                ["symbol"],
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
            timeout_seconds=30.0,
        ),
        _cap(
            "exchange_deals",
            description=(
                "Bulk deals, block deals and SAST (SEBI Reg 29 substantial-"
                "acquisition) disclosures for an Indian (NSE/BSE) listed company, "
                "newest first — who bought or sold a large block, at what price, and "
                "(SAST) their holding after. Each row: kind, date, party, side, "
                "quantity, price, value, percent_after, exchange, source_url. NSE "
                "listings get all three (bulk/block over the last year); a BSE-only "
                "scrip gets BSE bulk/block. The India counterpart of "
                "sec_insider_transactions."
            ),
            input_schema=_obj(
                {
                    "symbol": {"type": "string", "description": "NSE/BSE ticker, e.g. KOPRAN."},
                    "kind": {
                        "type": "string",
                        "enum": ["bulk", "block", "sast"],
                        "description": "Optional filter; omit for every kind.",
                    },
                },
                ["symbol"],
            ),
            domain="filings",
            read_only=True,
            kind="read_handler",
            timeout_seconds=45.0,
        ),
        _cap(
            "earnings_call_transcript",
            description=(
                "The earnings-call (concall) transcript an Indian (NSE/BSE) listed "
                "company filed with its exchanges, read from the filed PDF: what "
                "management said on the call and in the Q&A. Returns text (the "
                "transcript's most finance-relevant pages when it is long), "
                "filing_date, url and source exchange; available: false with a reason "
                "when no transcript was filed in the feed window or the symbol is not "
                "NSE/BSE-listed. Omit quarter for the latest call."
            ),
            input_schema=_obj(
                {
                    "symbol": {"type": "string", "description": "NSE/BSE ticker, e.g. TCS."},
                    "quarter": {
                        "type": "string",
                        "description": (
                            "The quarter-end date the call discussed, YYYY-MM-DD "
                            "(2026-06-30 for Apr-Jun 2026, Q1 FY27). Omit for the latest."
                        ),
                    },
                },
                ["symbol"],
            ),
            domain="earnings",
            read_only=True,
            kind="read_handler",
            timeout_seconds=45.0,
            untrusted_text=True,
        ),
        # --- quant (QuantLib pricing) ---------------------------------------
        _cap(
            "price_option",
            description=(
                "Price one option via Black-Scholes, binomial, or Monte-Carlo. "
                "Read-only math — no side effects."
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
            timeout_seconds=30.0,
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
            timeout_seconds=30.0,
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
            timeout_seconds=30.0,
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
            timeout_seconds=30.0,
        ),
        _cap(
            "option_chain",
            description=(
                "The listed option chain for one expiry with exchange-published open "
                "interest: per strike, call and put OI, change in OI, last/settle price, "
                "volume (and implied volatility on US listings). India F&O underlyings "
                "(NIFTY, BANKNIFTY, RELIANCE) come from the NSE F&O bhavcopy; US from "
                "yfinance. End-of-day research data dated by as_of, never live. Returns "
                "the strikes nearest spot (max_strikes) and every listed expiry."
            ),
            input_schema=_obj(
                {
                    "symbol": {
                        "type": "string",
                        "description": "Underlying, e.g. NIFTY, RELIANCE or AAPL.",
                    },
                    "expiry": {
                        **_DATE,
                        "description": "Expiry date YYYY-MM-DD; omit for the nearest.",
                    },
                    "max_strikes": {
                        "type": "integer",
                        "default": 20,
                        "description": "Strikes nearest spot to return.",
                    },
                },
                ["symbol"],
            ),
            domain="quant",
            read_only=True,
            kind="read_handler",
            timeout_seconds=45.0,
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
            timeout_seconds=15.0,
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
                "backtest engine. Returns "
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
            timeout_seconds=120.0,
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
        _cap(
            "read_notes",
            description=(
                "Read the user's own notes (their thesis) for a scope. Call it "
                "before write_note with mode 'replace', and whenever the user refers "
                "to their notes, thesis or plan for a stock."
            ),
            input_schema=_obj(
                {
                    "scope": {
                        "type": "string",
                        "description": "'global' or a symbol, e.g. 'BDL'",
                    }
                },
                ["scope"],
            ),
            domain="workspace",
            read_only=True,
            kind="per_invocation",
        ),
        _cap(
            "ask_user",
            description=(
                "Pause this background run and ask the user ONE question you "
                "cannot answer yourself: a missing choice, an ambiguity, or an "
                "approval. The run stops here and resumes with their answer as the "
                "next message. Ask only when you are blocked; otherwise decide, and "
                "say what you assumed."
            ),
            input_schema=_obj(
                {"question": {"type": "string", "description": "The one question, in full."}},
                ["question"],
            ),
            domain="agents",
            read_only=True,
            # The runtime offers it to every Delegate run and to nothing else, so
            # it is no agent's grant; a per-invocation capability, so never
            # projected to MCP (FR-028).
            kind="per_invocation",
            default_grant=False,
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
                    "run_id": {
                        "type": "string",
                        "description": (
                            "For panel=backtest: the run id a run_custom_backtest "
                            "call returned, to display that run."
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
                "sma, ema, rsi, macd, bollinger, vwap, volume. Use only the listed "
                "keys: one unknown key fails the whole set. Pass the full desired "
                "set (it replaces the current selection). When the user says 'add a "
                "200-day average' or 'set me up to study NVDA', pick a sensible set "
                "for the asset class. Indicators are server-computed and overlay or "
                "drop into a sub-pane automatically."
            ),
            input_schema=_obj(
                {
                    "indicators": {
                        "type": "array",
                        # The registry the chart's /indicators fetch validates
                        # against (C10) — never a hand copy.
                        "items": {"type": "string", "enum": list(SUPPORTED_INDICATORS)},
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
            "add_chart_drawing",
            description=(
                "Draw on the open chart, on the symbol and timeframe it shows: a "
                "horizontal-line at one price (support, resistance, a target) or a "
                "trendline between two bars. Each point's time is a bar timestamp "
                "exactly as price_data returns it for that timeframe; a "
                "horizontal-line takes one point and needs no time. Staged through "
                "the review gate like every host action."
            ),
            input_schema=_obj(
                {
                    "kind": {"type": "string", "enum": ["horizontal-line", "trendline"]},
                    "points": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 2,
                        "items": _obj(
                            {
                                "time": {
                                    "type": "string",
                                    "description": "Bar timestamp (ISO) from price_data.",
                                },
                                "price": {"type": "number"},
                            },
                            ["price"],
                        ),
                    },
                    "panelId": {
                        "type": "string",
                        "description": "Optional — defaults to the open chart panel.",
                    },
                },
                ["kind", "points"],
            ),
            domain="charts",
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
                f"Templates: {_layout_templates_prose()}. "
                "'default' resets the panel arrangement (chart drawings and module "
                "choices are kept); 'focus' maximises one panel (pass `panel`); "
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
                        "enum": ["auto", "default", "focus", *LAYOUT_TEMPLATES, "custom"],
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
                "fractions for ratios e.g. roe 0.2 = 20%; string fields sector/industry/"
                'currency take operator "eq", e.g. {"field":"sector","operator":"eq",'
                '"value":"Technology"} — filter sector-scoped screens server-side '
                "instead of post-filtering rows). For OR / nested logic, pass a "
                "`group` tree {combinator:'and'|'or', criteria:[... leaf or nested group]} "
                "which supersedes the flat list. Optionally set `universe` "
                "(sp500|nifty50|crypto-top50|nse-all|bse-all|india-all|custom) and "
                "`limit`. Use when the user asks to screen/scan for stocks by "
                "fundamentals."
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
                    "formula": {
                        "type": "string",
                        "description": (
                            "Optional boolean formula evaluated server-side per symbol, "
                            "AND-combined with the criteria — same grammar as "
                            "screener_run's formula (e.g. 'pe < 15 and roe > 0.2')."
                        ),
                    },
                    "run": {
                        "type": "boolean",
                        "description": (
                            "When true, ask the panel to RUN the staged screen "
                            "immediately after the user's gate applies it (instead of "
                            "waiting for a manual Run click)."
                        ),
                    },
                    "universe": {
                        "type": "string",
                        "enum": _UNIVERSE_ENUM,
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
        # --- data-write host actions (R10 E6/D41/D45) — tracked portfolio, notes,
        # saved screens/layouts, region. Each is a `data-write`/`settings`
        # proposed change on the frontend: auto-applicable under AUTO autonomy,
        # staged for review otherwise.
        _cap(
            "portfolio_add_position",
            description=(
                "Add a position to the user's LOCAL (manually-tracked) portfolio — "
                "symbol, quantity, and per-share cost basis. Edits the user's local "
                "tracked portfolio (manual holdings). Vysted has no brokerage "
                "connection. Use when the user says they bought/hold something and "
                "want it tracked. If the user did not give the price they paid, ASK "
                "for it before calling — never invent, estimate or zero a cost basis."
            ),
            input_schema=_obj(
                {
                    "symbol": {"type": "string"},
                    "quantity": {"type": "number"},
                    "cost_basis": {
                        "type": "number",
                        "description": (
                            "Per-share cost in the listing currency, as the user stated "
                            "it. Ask the user if they did not say; never guess."
                        ),
                    },
                    "asset_class": {"type": "string", "enum": _ASSET_ENUM, "default": "equity"},
                    "note": {"type": "string", "description": "Optional free-form note."},
                    "purchased_at": _DATE,
                },
                ["symbol", "quantity", "cost_basis"],
            ),
            domain="portfolio",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "portfolio_update_position",
            description=(
                "Update an existing LOCAL portfolio position by its id (quantity, "
                "cost basis, note, …). Read the current positions first with "
                "get_portfolio to learn the position_id. Edits the user's local "
                "tracked portfolio (manual holdings). Vysted has no brokerage "
                "connection. Send only the fields the user changed; for a new cost "
                "basis use the price the user gave — ask for it, never invent one."
            ),
            input_schema=_obj(
                {
                    "position_id": {"type": "string"},
                    "symbol": {"type": "string"},
                    "quantity": {"type": "number"},
                    "cost_basis": {
                        "type": "number",
                        "description": "Per-share cost in the listing currency.",
                    },
                    "asset_class": {"type": "string", "enum": _ASSET_ENUM},
                    "note": {"type": "string"},
                    "purchased_at": _DATE,
                },
                ["position_id"],
            ),
            domain="portfolio",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "portfolio_delete_position",
            description=(
                "Delete a LOCAL portfolio position by its id (from get_portfolio). "
                "Edits the user's local tracked portfolio (manual holdings). Vysted "
                "has no brokerage connection."
            ),
            input_schema=_obj({"position_id": {"type": "string"}}, ["position_id"]),
            domain="portfolio",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "write_note",
            description=(
                "Write to the user's notes surface. `scope` names the note bucket "
                "(e.g. 'global', or a symbol like 'NVDA' for that company's research "
                "note); mode 'append' adds to the existing note, 'replace' overwrites "
                "it. Use to capture analysis takeaways the user asks you to save."
            ),
            input_schema=_obj(
                {
                    "scope": {
                        "type": "string",
                        "description": "Note bucket — 'global' or a symbol, e.g. 'NVDA'.",
                    },
                    "text": {"type": "string"},
                    "mode": {"type": "string", "enum": ["replace", "append"], "default": "append"},
                },
                ["scope", "text"],
            ),
            domain="workspace",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "remove_from_watchlist",
            description="Remove a symbol from the user's watchlist.",
            input_schema=_obj({"symbol": {"type": "string"}}, ["symbol"]),
            domain="portfolio",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "save_layout",
            description=(
                "Save the CURRENT cockpit layout as a named workspace the user can "
                "restore later. Omit `name` to update the active saved layout."
            ),
            input_schema=_obj({"name": {"type": "string"}}),
            domain="workspace",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "save_screen",
            description=(
                "Save a screener configuration (criteria/group/formula + universe) "
                "under a name so the user can re-run it later. Use after a screen "
                "the user likes — it persists the recipe, it does not run it."
            ),
            input_schema=_obj(
                {
                    "name": {"type": "string"},
                    "criteria": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "Flat AND-combined leaf criteria.",
                    },
                    "group": {
                        "type": "object",
                        "description": "Optional nested AND/OR tree (supersedes criteria).",
                    },
                    "formula": {"type": "string", "description": "Optional boolean formula."},
                    "universe": {"type": "string", "enum": _UNIVERSE_ENUM},
                },
                ["name"],
            ),
            domain="screener",
            read_only=False,
            kind="host_action",
        ),
        _cap(
            "set_region",
            description=(
                "Switch the terminal's active market region (US / IN / GLOBAL) — "
                "drives locale-aware resolution, indices, and data routing. A "
                "settings change staged through the user's trust gate; use it only "
                "when the user asks to switch markets."
            ),
            input_schema=_obj(
                {"region": {"type": "string", "enum": ["US", "IN", "GLOBAL"]}},
                ["region"],
            ),
            domain="terminal",
            read_only=False,
            kind="host_action",
        ),
    ]
)


# ---------------------------------------------------------------------------
# Projections — the only sanctioned way consumers read the catalog.
# ---------------------------------------------------------------------------

#: Forbidden order-placement substrings. A catalog id containing any of these
#: would be a safety regression; asserted in tests.
FORBIDDEN_TOOL_SUBSTRINGS = ("place_order", "submit_order", "execute_order", "auto_approve")


def internal_capabilities() -> list[Capability]:
    """Capabilities projected to the internal copilot/persona adapters."""
    return [c for c in CAPABILITY_CATALOG.values() if c.internal]


def internal_tool_ids() -> list[str]:
    """Ids of every capability the internal copilot can be given (allow-list domain)."""
    return [c.id for c in internal_capabilities()]


def mcp_capabilities() -> list[Capability]:
    """Capabilities projected to the external MCP server (FR-020/022).

    The same read capabilities the internal copilot uses, by the SAME name — so
    an external agent builds on Vysted with no divergence. The surface is
    read-only in 0.9 (R15-AGENT-083): no host action or mutating capability is
    projected; those stay in-app behind the proposed-changes gate.
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
    """The Custom Agent Builder allow-list — equal to :func:`internal_tool_ids` by design.

    A custom agent may select any tool the first-party copilot can use, so no
    internal capability is withheld from the builder; each id resolves at the
    host (registry handler, per-invocation closure, or host action). Safety is
    host-enforced regardless of selection; no trading tool exists (D81).
    """
    return frozenset(internal_tool_ids())


def default_grant_tool_ids() -> list[str]:
    """Ids granted to every FIRST-PARTY agent at load time (R10, E5).

    The loader (:func:`services.agent_runtime._grant_first_party_hands`) unions
    each first-party spec's tools with this projection — capability maximization
    is catalog-driven, so a tool registered+catalogued can never silently fall
    out of an agent's belt by JSON drift (the E5 regression). Custom agents
    (the agents_store path) stay exactly author-picked.
    """
    return [c.id for c in internal_capabilities() if c.default_grant]


def resolve_tool_ids(tool_ids: Iterable[str]) -> tuple[list[str], list[str]]:
    """``(canonical ids, deduped in order; ids no capability or alias names)``.

    Every reader of a persisted tool list goes through this, so renaming a
    capability (keeping the old id in its ``aliases``) never orphans a stored
    agent (R15-LIFECYCLE-025).
    """
    by_alias = {alias: cap.id for cap in CAPABILITY_CATALOG.values() for alias in cap.aliases}
    resolved: list[str] = []
    unknown: list[str] = []
    for tool_id in tool_ids:
        canonical = tool_id if tool_id in CAPABILITY_CATALOG else by_alias.get(tool_id)
        if canonical is None:
            unknown.append(tool_id)
        elif canonical not in resolved:
            resolved.append(canonical)
    return resolved, unknown


def domain_of(tool_id: str) -> Domain | None:
    cap = CAPABILITY_CATALOG.get(tool_id)
    return cap.domain if cap else None


def is_read_only(tool_id: str) -> bool | None:
    cap = CAPABILITY_CATALOG.get(tool_id)
    return cap.read_only if cap else None


def is_untrusted_text(tool_id: str) -> bool:
    """True when the tool's result carries third-party text to fence (AGENT-021)."""
    cap = CAPABILITY_CATALOG.get(tool_id)
    return bool(cap and cap.untrusted_text)


def timeout_for(tool_id: str) -> float | None:
    """Per-dispatch wall budget for a tool (R10, E7); ``None`` = no timeout.

    Enforced by the runtime's ``_dispatch_tool`` via ``asyncio.wait_for`` for
    registry-backed tools only — host-action locals are frontend round-trips
    and per-invocation reads are in-memory, both exempt. A capability with
    ``timeout_from_args`` (``research``) declares no budget here: the runtime
    computes its outer guard from the call's own ``wall_seconds``/depth args.
    """
    cap = CAPABILITY_CATALOG.get(tool_id)
    return cap.timeout_seconds if cap else None


#: Per-domain "what next" lines appended to the honest timeout message (E7) —
#: the model relays them so a timed-out turn ends with a step, never a shrug.
TIMEOUT_HINTS: dict[str, str] = {
    "quotes": "retry, or check the symbol spelling/exchange suffix",
    "fundamentals": "retry, or check the symbol — coverage gaps look like hangs",
    "news": "retry with fewer symbols or a smaller limit",
    "research": "narrow the query or retry at a lighter depth",
    "screener": "narrow the universe or criteria, then run again",
    "macro": "check the series id/provider and retry",
    "earnings": "retry shortly — the provider may be slow",
    "analyst": "retry shortly — the provider may be slow",
    "filings": "retry with a smaller limit or a specific form type",
    "quant": "reduce the instrument count, steps, or paths and retry",
    "workflows": "narrow the date range or symbol list and retry",
}

#: Per-tool hints that override the domain line (R15-RESEARCH-008, C6):
#: ``web_search`` shares the ``research`` domain, but "retry at a lighter
#: depth" is the research tool's copy — search has no depth.
TOOL_TIMEOUT_HINTS: dict[str, str] = {
    "web_search": (
        "the configured search tier did not answer in time — retry once with a "
        "narrower query, or answer from what you already have and say search was slow"
    ),
}

#: Fallback hint for a domain not listed above.
DEFAULT_TIMEOUT_HINT = "try again — if it keeps timing out, narrow the request"


def timeout_hint_for(tool_id: str) -> str:
    """The next-step hint for a tool's timeout message (per tool, else per domain)."""
    if tool_id in TOOL_TIMEOUT_HINTS:
        return TOOL_TIMEOUT_HINTS[tool_id]
    return TIMEOUT_HINTS.get(domain_of(tool_id) or "", DEFAULT_TIMEOUT_HINT)


__all__ = [
    "CAPABILITY_CATALOG",
    "Capability",
    "DEFAULT_TIMEOUT_HINT",
    "Domain",
    "FORBIDDEN_TOOL_SUBSTRINGS",
    "TIMEOUT_HINTS",
    "TOOL_TIMEOUT_HINTS",
    "ToolKind",
    "agent_selectable_tool_ids",
    "default_grant_tool_ids",
    "domain_of",
    "internal_capabilities",
    "internal_tool_ids",
    "is_read_only",
    "is_untrusted_text",
    "mcp_capabilities",
    "mcp_tool_ids",
    "read_handler_ids",
    "resolve_tool_ids",
    "timeout_for",
    "timeout_hint_for",
]
