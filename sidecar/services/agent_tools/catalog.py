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

from dataclasses import dataclass, field
from typing import Any, Literal

# Domains a capability can belong to. Used for grouping in the catalog and for
# the domain tag projected to the MCP surface (FR-021).
Domain = Literal[
    "quotes",
    "charts",
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
            mcp=True,
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
            mcp=True,
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
                    "universe": {
                        "type": "string",
                        "enum": ["sp500", "nifty50", "crypto-top50", "custom"],
                    },
                    "criteria": {
                        "type": "array",
                        "description": (
                            "Discriminated-union filters, e.g. "
                            '[{"field":"pe_ratio","operator":"lt","value":15}]'
                        ),
                        "items": {"type": "object"},
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
            mcp=True,
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
            mcp=True,
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
                "portfolio, equity-overview, screener, macro, earnings, ...)."
            ),
            input_schema=_obj({"panel": {"type": "string"}}, ["panel"]),
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
    ]
)


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
    "read_handler_ids",
]
