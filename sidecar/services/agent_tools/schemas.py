"""Provider-neutral tool schemas — the contract the model sees.

The agent runtime (``agent_runtime.invoke_agent``) runs a real tool-use loop,
but until Phase 10 no provider adapter ever sent a ``tools=`` definition, so no
model ever emitted a ``tool_use`` block and the loop never iterated. This module
is the missing keystone: it declares each tool once, provider-neutral, keyed by
the SAME id used in the ``agent_tools`` registry and in ``AgentSpec.tools``, and
serialises that catalog into each provider's native tool shape.

Read-tool ids (``price_data``, ``fundamentals``, …) map to the registered
handlers in this package. The per-invocation ids (``get_terminal_state``,
``get_portfolio``) and the host-action ids (``open_panel``, ``set_chart_symbol``,
``add_to_watchlist``, ``propose_order``) are resolved inside ``invoke_agent``
(they need request scope / drive the frontend) — they appear here only so the
model is told they exist.

SAFETY (§6.5): the broker action tool is named ``propose_order`` — never
``place_order``/``submit_order``/``execute_order`` (which
``tests/test_safety_end_to_end.py`` greps the registry for). It only ever
returns a proposal directive the user must review; the AI has no path to
``confirm_and_place``.
"""

from __future__ import annotations

from typing import Any

_TF_ENUM = ["1d", "1h", "1wk", "1mo"]
_ASSET_ENUM = ["equity", "crypto"]


def _obj(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


#: {tool_id: {description, input_schema}}. input_schema is JSON Schema (the
#: draft-07 subset Anthropic + OpenAI + Gemini all accept).
TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
    # --- read tools (registered handlers in this package) ------------------
    "price_data": {
        "description": (
            "Recent OHLCV bars + the latest quote for a symbol. Use to check "
            "price, recent action, volatility, or drawdown."
        ),
        "input_schema": _obj(
            {
                "symbol": {"type": "string", "description": "Ticker, e.g. AAPL or BTC/USDT"},
                "timeframe": {"type": "string", "enum": _TF_ENUM, "default": "1d"},
                "range": {"type": "string", "default": "6mo", "description": "e.g. 1mo, 6mo, 1y"},
                "asset_class": {"type": "string", "enum": _ASSET_ENUM, "default": "equity"},
            },
            ["symbol"],
        ),
    },
    "fundamentals": {
        "description": (
            "Valuation ratios (P/E, P/B, market cap, margins) + a company "
            "profile for a symbol. Use for value/quality analysis."
        ),
        "input_schema": _obj(
            {"symbol": {"type": "string", "description": "Equity ticker, e.g. AAPL"}},
            ["symbol"],
        ),
    },
    "screener_run": {
        "description": (
            "Screen a universe of symbols against numeric/string criteria and "
            "return the matches. Use to find names that fit a thesis."
        ),
        "input_schema": _obj(
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
    },
    "macro_series": {
        "description": "Fetch a macroeconomic time series (e.g. DGS10, CPIAUCSL, UNRATE).",
        "input_schema": _obj(
            {"series_id": {"type": "string", "description": "FRED-style series id, e.g. DGS10"}},
            ["series_id"],
        ),
    },
    "earnings_history": {
        "description": "Historical EPS surprises (actual vs estimate) for a symbol.",
        "input_schema": _obj({"symbol": {"type": "string"}}, ["symbol"]),
    },
    "analyst_history": {
        "description": "Analyst rating + price-target history for a symbol.",
        "input_schema": _obj({"symbol": {"type": "string"}}, ["symbol"]),
    },
    "sec_filings_list": {
        "description": "List recent SEC filings (10-K, 10-Q, 8-K, …) for a symbol.",
        "input_schema": _obj({"symbol": {"type": "string"}}, ["symbol"]),
    },
    # --- per-invocation read tools (resolved in invoke_agent) --------------
    "get_terminal_state": {
        "description": (
            "Read what the user is currently looking at: open panels, the "
            "focused chart symbol + timeframe + indicators, the watchlist, and a "
            "portfolio summary. Call this whenever the user says 'this', 'it', "
            "'my chart', 'my watchlist', or 'my portfolio'."
        ),
        "input_schema": _obj({}),
    },
    "get_portfolio": {
        "description": "Read the user's local (manually-entered) portfolio positions with P&L.",
        "input_schema": _obj({}),
    },
    "broker_portfolio": {
        "description": (
            "Read the user's REAL connected-broker account (positions, equity, "
            "buying power, per-position unrealized P&L) for analysis. Read-only — "
            "never places an order. `broker` defaults to 'kite' (Zerodha)."
        ),
        "input_schema": _obj(
            {"broker": {"type": "string", "enum": ["kite", "dhan", "angelone"], "default": "kite"}}
        ),
    },
    # --- host-action tools that DRIVE the terminal (host-executed) ---------
    "open_panel": {
        "description": (
            "Open or focus a terminal panel by id (chart, watchlist, news, "
            "portfolio, equity-overview, screener, macro, earnings, ...)."
        ),
        "input_schema": _obj({"panel": {"type": "string"}}, ["panel"]),
    },
    "set_chart_symbol": {
        "description": "Load a symbol (and optional timeframe) into the chart panel.",
        "input_schema": _obj(
            {
                "symbol": {"type": "string"},
                "timeframe": {"type": "string", "enum": _TF_ENUM},
            },
            ["symbol"],
        ),
    },
    "add_to_watchlist": {
        "description": "Add a symbol to the user's watchlist.",
        "input_schema": _obj(
            {
                "symbol": {"type": "string"},
                "asset_class": {"type": "string", "enum": _ASSET_ENUM, "default": "equity"},
            },
            ["symbol"],
        ),
    },
    "propose_order": {
        "description": (
            "Prepare a broker order for the user to REVIEW. This NEVER places an "
            "order — it opens a confirmation dialog the user must explicitly "
            "approve. Use only when the user explicitly asks to buy or sell. "
            "Tell the user to review and confirm; never claim you placed it."
        ),
        "input_schema": _obj(
            {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "quantity": {"type": "number"},
                "order_type": {"type": "string", "enum": ["market", "limit"], "default": "market"},
                "limit_price": {"type": "number", "description": "Required for a limit order."},
            },
            ["symbol", "side", "quantity"],
        ),
    },
}

#: Ids resolved inside invoke_agent rather than the global registry.
PER_INVOCATION_READ_TOOLS = ("get_terminal_state", "get_portfolio")
HOST_ACTION_TOOLS = ("open_panel", "set_chart_symbol", "add_to_watchlist", "propose_order")


def _known(tool_ids: list[str]) -> list[str]:
    return [tid for tid in tool_ids if tid in TOOL_SCHEMAS]


def anthropic_tools(tool_ids: list[str]) -> list[dict[str, Any]]:
    """``[{name, description, input_schema}]`` for the Anthropic Messages API."""
    return [
        {
            "name": tid,
            "description": TOOL_SCHEMAS[tid]["description"],
            "input_schema": TOOL_SCHEMAS[tid]["input_schema"],
        }
        for tid in _known(tool_ids)
    ]


def openai_tools(tool_ids: list[str]) -> list[dict[str, Any]]:
    """``[{type:'function', function:{...}}]`` for OpenAI / DeepSeek / xAI / Groq."""
    return [
        {
            "type": "function",
            "function": {
                "name": tid,
                "description": TOOL_SCHEMAS[tid]["description"],
                "parameters": TOOL_SCHEMAS[tid]["input_schema"],
            },
        }
        for tid in _known(tool_ids)
    ]


def gemini_tools(tool_ids: list[str]) -> list[dict[str, Any]]:
    """Gemini ``function_declarations`` shape (single tool with N declarations)."""
    known = _known(tool_ids)
    if not known:
        return []
    return [
        {
            "function_declarations": [
                {
                    "name": tid,
                    "description": TOOL_SCHEMAS[tid]["description"],
                    "parameters": TOOL_SCHEMAS[tid]["input_schema"],
                }
                for tid in known
            ]
        }
    ]
