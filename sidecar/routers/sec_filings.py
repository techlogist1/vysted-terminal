"""SEC EDGAR filings router — ``/sec/...``.

Phase 6 (v0.6.0) Teammate F. Surfaces the sec-edgar-mcp subprocess's
Company / Filings / Financials / Insider-Trading tool surface as a
small, typed REST API consumed by the SecFilingsPanel frontend.

Routes:

  * ``GET /sec/filings?cik=&symbol=&form_type=&limit=`` — filings list
    for a company. Either ``cik`` or ``symbol`` is required.
  * ``GET /sec/filings/{accession}?identifier=`` — full FilingDetail
    (filing metadata + parsed sections).
  * ``GET /sec/filings/{accession}/sections?identifier=`` — sections
    list only, for the FilingViewer's section navigation rail.
  * ``GET /sec/insider/{identifier}?form=3|4|5&limit=`` — recent
    insider transactions for an issuer.
  * ``GET /sec/filings/search?q=&limit=`` — company-name search for the
    panel's symbol field.
  * ``GET /sec/status`` — plugin-manager observability.

When the sec-edgar-mcp subprocess is not bundled (Tauri Rust registered
port=0), :func:`sec_filings_provider.is_available` returns ``False`` and
every route except ``/sec/status`` responds with 501.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from models.sec import (
    FilingDetail,
    FilingFormType,
    FilingSection,
    FilingsListResponse,
    InsiderTransactionsResponse,
)
from services import sec_filings_provider
from services.errors import ProviderError

router = APIRouter(prefix="/sec", tags=["sec"])


def _require_available() -> None:
    """Raise 501 when the sec-edgar-mcp subprocess is not bundled."""
    if not sec_filings_provider.is_available():
        raise HTTPException(
            status_code=501,
            detail=(
                "sec-edgar-mcp subprocess is not bundled in this build. "
                "Run `pnpm sec-edgar-mcp-sidecar:build` and restart the app."
            ),
        )


@router.get("/status")
async def get_status() -> dict[str, object]:
    """Lightweight status probe for the plugin-manager UI."""
    return await sec_filings_provider.status()


@router.get("/filings/search")
async def search_companies(
    q: str = Query(..., min_length=1, description="Company name search query"),
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, list[dict[str, object]]]:
    """Search the EDGAR company index by name."""
    _require_available()
    try:
        results = await sec_filings_provider.search_companies(q, limit=limit)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # Wrap in a dict so the FastAPI response schema is stable and the
    # FastMCP-tool layer (if it ever proxies this) does not hit the
    # "bare list" CLAUDE.md gotcha.
    return {"results": results}


@router.get("/filings")
async def list_filings(
    cik: str | None = Query(None, description="Company CIK (preferred)"),
    symbol: str | None = Query(None, description="Ticker symbol (fallback)"),
    form_type: FilingFormType | None = Query(
        None,
        alias="form_type",
        description="Restrict to one form type",
    ),
    limit: int = Query(40, ge=1, le=200),
) -> FilingsListResponse:
    """List recent filings for a company."""
    _require_available()
    identifier = cik or symbol
    if not identifier:
        raise HTTPException(
            status_code=400, detail="either 'cik' or 'symbol' is required"
        )
    try:
        return await sec_filings_provider.list_filings(
            identifier, form_type=form_type, limit=limit
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/filings/{accession}")
async def get_filing(
    accession: str,
    identifier: str = Query(..., description="CIK or symbol used to find the filing"),
) -> FilingDetail:
    """Return the parsed filing detail (metadata + sections)."""
    _require_available()
    try:
        return await sec_filings_provider.get_filing(accession, cik_or_symbol=identifier)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/filings/{accession}/sections")
async def get_filing_sections(
    accession: str,
    identifier: str = Query(..., description="CIK or symbol used to find the filing"),
) -> dict[str, list[FilingSection]]:
    """Return the sections list for an accession."""
    _require_available()
    try:
        sections = await sec_filings_provider.get_filing_sections(
            accession, cik_or_symbol=identifier
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    # Wrap to keep the schema dict-shaped (CLAUDE.md FastMCP-tool gotcha).
    return {"sections": sections}


# Insider form type accepted as a query param. Mirrors models.sec.InsiderFormType
# but restated explicitly so FastAPI's OpenAPI schema renders cleanly.
_InsiderForm = Literal["3", "4", "5"]


@router.get("/insider/{identifier}")
async def list_insider_transactions(
    identifier: str,
    form: _InsiderForm | None = Query(None, description="Restrict to Form 3, 4, or 5"),
    limit: int = Query(50, ge=1, le=200),
) -> InsiderTransactionsResponse:
    """Recent insider transactions for an issuer."""
    _require_available()
    try:
        return await sec_filings_provider.list_insider_transactions(
            identifier, form_type=form, limit=limit
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
