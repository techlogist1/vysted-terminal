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

Registered via :func:`register` from the Phase 6 aggregator in
:mod:`services.agent_tools.registry_v0_6_0`.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool


async def _sec_filings_list(args: dict[str, Any]) -> dict[str, Any]:
    """Return the filings index for ``cik`` or ``symbol``.

    Args:
        cik: CIK (zero-padded or numeric). Either cik or symbol required.
        symbol: Ticker symbol — alternative to cik.
        form_type: Optional filter, one of ``"10-K" | "10-Q" | "8-K" | "DEF 14A" | "3" | "4" | "5"``.
        limit: Max filings to return (default 20).
    """
    identifier = args.get("cik") or args.get("symbol") or args.get("identifier")
    if not isinstance(identifier, str) or not identifier:
        return {"ok": False, "error": "missing cik/symbol"}
    form_type = args.get("form_type")
    limit_raw = args.get("limit", 20)
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 20

    from services import sec_filings_provider
    from services.errors import ProviderError

    if not sec_filings_provider.is_available():
        return {
            "ok": False,
            "error": "sec-edgar-mcp subprocess not bundled in this build",
        }
    try:
        response = await sec_filings_provider.list_filings(
            identifier, form_type=form_type, limit=limit
        )
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}

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
    """
    accession = args.get("accession")
    if not isinstance(accession, str) or not accession:
        return {"ok": False, "error": "missing accession"}
    identifier = args.get("identifier") or args.get("cik") or args.get("symbol")
    if not isinstance(identifier, str) or not identifier:
        return {"ok": False, "error": "missing identifier (cik or symbol)"}

    from services import sec_filings_provider
    from services.errors import ProviderError

    if not sec_filings_provider.is_available():
        return {
            "ok": False,
            "error": "sec-edgar-mcp subprocess not bundled in this build",
        }
    try:
        detail = await sec_filings_provider.get_filing(
            accession, cik_or_symbol=identifier
        )
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}

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
    limit_raw = args.get("limit", 30)
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError):
        limit = 30

    from services import sec_filings_provider
    from services.errors import ProviderError

    if not sec_filings_provider.is_available():
        return {
            "ok": False,
            "error": "sec-edgar-mcp subprocess not bundled in this build",
        }
    try:
        response = await sec_filings_provider.list_insider_transactions(
            identifier, form_type=form, limit=limit
        )
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}

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
