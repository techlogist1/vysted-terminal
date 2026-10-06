"""Phase 6 agent tools — SEC EDGAR filings (Teammate F).

Three read-only tools the Strategy Critic + research agents can call:

  - ``sec_filings_list`` — paginated filings index for a company.
  - ``sec_filing_content`` — parsed sections of one filing by accession.
  - ``sec_insider_transactions`` — recent Form 3/4/5 transactions for an
    issuer.

All three route through :mod:`services.sec_filings_provider`, which
reads through the data_cache TTL layer. Tool ids are deliberately
namespaced ``sec_*`` (no ``place_*`` / ``submit_*`` / ``execute_*`` /
``auto_approve`` substrings — the §6.5 grep check passes).

Registered via :func:`register` from the Phase 6 aggregator,
:func:`services.agent_tools.register_v0_6_0_tools`.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import clamp_int, register_tool

# Honest unavailability message (Phase 9.5 nit): the binary IS bundled; when
# unreachable it almost always failed to bind a port this launch (UC1 cold
# start), so "not available / did not bind" is accurate, not "not bundled".
_UNAVAILABLE_ERROR = (
    "sec-edgar-mcp is not available — the subprocess did not bind a port "
    "this launch (relaunch to retry)"
)

#: Row cap so a chatty backfill (a model-supplied 100000 or a stray -1)
#: never reaches the provider unclamped (R15-CODE-AGENT-015).
_MAX_LIMIT = 100


async def _sec_filings_list(args: dict[str, Any]) -> dict[str, Any]:
    """Return the filings index for ``cik`` or ``symbol``.

    Args:
        cik: CIK (zero-padded or numeric). Either cik or symbol required.
        symbol: Ticker symbol — alternative to cik.
        form_type: Optional filter — one of
            ``"10-K" | "10-Q" | "8-K" | "DEF 14A" | "3" | "4" | "5"``.
        limit: Max filings to return (default 20).
    """
    identifier = args.get("cik") or args.get("symbol") or args.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        return {"ok": False, "error": "missing cik/symbol"}
    form_type = args.get("form_type")
    limit = clamp_int(args, "limit", 20, minimum=1, maximum=_MAX_LIMIT)

    from services import sec_filings_provider

    if not sec_filings_provider.is_available():
        return {
            "ok": False,
            "error": _UNAVAILABLE_ERROR,
        }
    response = await sec_filings_provider.list_filings(identifier, form_type=form_type, limit=limit)

    return {
        "ok": True,
        "filings": response.model_dump(mode="json"),
    }


async def _sec_filing_content(args: dict[str, Any]) -> dict[str, Any]:
    """Return the parsed sections of one filing.

    Args:
        accession: SEC accession number, e.g. ``"0000320193-24-000123"``.
            Required.
        identifier: CIK or symbol that owns the filing. Required.
        form_type: The filing's form from ``sec_filings_list`` — a lookup
            hint (R15-LEAD-010). Optional.
    """
    accession = args.get("accession")
    if not isinstance(accession, str) or not accession:
        return {"ok": False, "error": "missing accession"}
    identifier = args.get("identifier") or args.get("cik") or args.get("symbol")
    if not isinstance(identifier, str) or not identifier:
        return {"ok": False, "error": "missing identifier (cik or symbol)"}

    from services import sec_filings_provider

    if not sec_filings_provider.is_available():
        return {
            "ok": False,
            "error": _UNAVAILABLE_ERROR,
        }
    detail = await sec_filings_provider.get_filing(
        accession, cik_or_symbol=identifier, form_type=args.get("form_type") or None
    )

    return {
        "ok": True,
        "filing": detail.model_dump(mode="json"),
    }


async def _sec_insider_transactions(args: dict[str, Any]) -> dict[str, Any]:
    """Return recent insider transactions (Forms 3/4/5) for an issuer.

    Args:
        cik: CIK. Either cik or symbol required.
        symbol: Ticker symbol.
        form: ``"3" | "4" | "5"`` — restrict to one form type. Optional.
        limit: Max rows (default 30).
    """
    identifier = args.get("cik") or args.get("symbol") or args.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        return {"ok": False, "error": "missing cik/symbol"}
    form = args.get("form") or args.get("form_type")
    limit = clamp_int(args, "limit", 30, minimum=1, maximum=_MAX_LIMIT)

    from services import sec_filings_provider

    if not sec_filings_provider.is_available():
        return {
            "ok": False,
            "error": _UNAVAILABLE_ERROR,
        }
    response = await sec_filings_provider.list_insider_transactions(
        identifier, form_type=form, limit=limit
    )

    return {
        "ok": True,
        "transactions": response.model_dump(mode="json"),
    }


def register() -> None:
    """Register the three SEC EDGAR agent tools."""
    register_tool("sec_filings_list", _sec_filings_list)
    register_tool("sec_filing_content", _sec_filing_content)
    register_tool("sec_insider_transactions", _sec_insider_transactions)


__all__ = [
    "_sec_filing_content",
    "_sec_filings_list",
    "_sec_insider_transactions",
    "register",
]
