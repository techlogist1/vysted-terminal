"""Phase 6 workflow nodes — SEC EDGAR filings (Teammate F).

Two node types the Node Editor surfaces so a user can compose:

  - ``data.fetch_sec_filing`` — pull a parsed filing by accession (with
    section list) into the workflow run as JSON; downstream nodes can
    feed it into an agent invoke for analysis.
  - ``data.fetch_insider_transactions`` — pull Form 3/4/5 transactions
    for an issuer into the workflow.

Both handlers shim into :mod:`services.sec_filings_provider` and obey
the established node handler signature (``async def(inputs, config) ->
outputs``). Configuration errors raise :class:`ValueError` so the
workflow engine emits a ``node-error`` event with a clean message.
"""

from __future__ import annotations

from typing import Any

from services import workflow_engine


async def fetch_sec_filing(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Fetch a parsed SEC filing by accession + identifier.

    Config keys (overridable by inputs):
        accession — SEC accession number (required).
        identifier — CIK or symbol used to find the filing (required).

    Outputs:
        ``{"filing": <FilingDetail JSON>}``.
    """
    accession = inputs.get("accession") or config.get("accession")
    identifier = (
        inputs.get("identifier")
        or inputs.get("symbol")
        or inputs.get("cik")
        or config.get("identifier")
        or config.get("symbol")
        or config.get("cik")
    )
    if not accession:
        raise ValueError("data.fetch_sec_filing: missing 'accession' (provide via input or config)")
    if not identifier:
        raise ValueError("data.fetch_sec_filing: missing 'identifier' / 'symbol' / 'cik'")

    from services import sec_filings_provider

    detail = await sec_filings_provider.get_filing(str(accession), cik_or_symbol=str(identifier))
    return {"filing": detail.model_dump(mode="json")}


async def fetch_insider_transactions(
    inputs: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Fetch recent insider transactions for an issuer.

    Config keys (overridable by inputs):
        identifier — CIK or symbol (required).
        form — ``"3" | "4" | "5"`` filter (optional).
        limit — max rows (default 30).
    """
    identifier = (
        inputs.get("identifier")
        or inputs.get("symbol")
        or inputs.get("cik")
        or config.get("identifier")
        or config.get("symbol")
        or config.get("cik")
    )
    if not identifier:
        raise ValueError("data.fetch_insider_transactions: missing 'identifier' / 'symbol' / 'cik'")
    form = inputs.get("form") or config.get("form")
    limit_raw = inputs.get("limit") or config.get("limit") or 30
    try:
        limit = int(limit_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"data.fetch_insider_transactions: bad 'limit' {limit_raw!r}") from exc

    from services import sec_filings_provider

    response = await sec_filings_provider.list_insider_transactions(
        str(identifier), form_type=form, limit=limit
    )
    return {"transactions": response.model_dump(mode="json")}


def register() -> None:
    """Register the two SEC workflow node types against the engine."""
    workflow_engine.register_node_type("data.fetch_sec_filing", fetch_sec_filing)
    workflow_engine.register_node_type(
        "data.fetch_insider_transactions", fetch_insider_transactions
    )


__all__ = ["fetch_insider_transactions", "fetch_sec_filing", "register"]
