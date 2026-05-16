"""sec-edgar-mcp provider — Phase 6 SEC EDGAR filings client.

Vysted's window onto the SEC EDGAR filing system. Wraps the
``sec-edgar-mcp`` (1.0.8) subprocess as an MCP client over Streamable-HTTP
and exposes a small, typed surface the ``/sec`` REST router consumes:

  - :func:`list_filings(cik_or_symbol, form_type, limit)` →
    :class:`FilingsListResponse` — the filings index for a company.
  - :func:`get_filing(accession)` → :class:`FilingDetail` (with sections).
  - :func:`get_filing_sections(accession)` → ``list[FilingSection]`` —
    the same parser output without the wrapping metadata; the panel
    uses this for the section-navigation rail.
  - :func:`list_insider_transactions(cik_or_symbol, form, limit)` →
    :class:`InsiderTransactionsResponse`.
  - :func:`search_companies(query, limit)` → lookup helper for the
    panel's symbol field.

The provider routes reads through :mod:`services.data_cache` with three
namespaces:

  - ``sec:filings:<cik>:<form_type>`` — filings index, TTL 1h (filings
    are mutable until amended; one-hour staleness is acceptable for the
    list view).
  - ``sec:filing:<accession>`` — filing contents, TTL 24h (filings can
    be amended but the accession-numbered version is content-immutable
    once on file).
  - ``sec:insider:<cik>:<form>`` — insider transactions, TTL 1h.

When the sec-edgar-mcp subprocess is not bundled (the Tauri Rust side
registered port=0), :func:`is_available` returns False and the router
translates that into 501. The same pattern as openbb_mcp_provider.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, date, datetime
from typing import Any

from models.sec import (
    Filing,
    FilingDetail,
    FilingFormType,
    FilingSection,
    InsiderFormType,
    InsiderTransaction,
    InsiderTransactionDirection,
    InsiderTransactionsResponse,
    FilingsListResponse,
)
from services import data_cache, mcp_client
from services.errors import ProviderError

PROVIDER = "sec-edgar-mcp"

_log = logging.getLogger(__name__)

# Env vars the Tauri core sets when ``src-tauri/src/sec_edgar_mcp.rs``
# spawned the subprocess successfully.
_PORT_ENV = "VYSTED_SEC_EDGAR_MCP_PORT"
_HOST_ENV = "VYSTED_SEC_EDGAR_MCP_HOST"

# Cached availability flag. ``None`` = not yet probed.
_AVAILABLE: bool | None = None

# In-memory state mirrors openbb_mcp_provider for plugin-manager observability.
_last_tool_call_ok: bool | None = None
_last_error: str | None = None

# Cache TTLs.
_FILINGS_INDEX_TTL = 3600.0  # 1h
_FILING_CONTENT_TTL = 86400.0  # 24h
_INSIDER_TTL = 3600.0  # 1h

# ---------------------------------------------------------------------------
# Port + availability discovery
# ---------------------------------------------------------------------------


def _resolve_endpoint() -> str | None:
    """Return the Streamable-HTTP endpoint, or ``None`` if not bundled.

    Mirrors :func:`openbb_mcp_provider._resolve_endpoint`. ``None`` means
    sec-edgar-mcp is not bundled in this build; the router 501s.
    """
    port = os.environ.get(_PORT_ENV)
    if not port or port == "0":
        return None
    host = os.environ.get(_HOST_ENV, "127.0.0.1")
    return f"http://{host}:{port}/mcp"


def is_available() -> bool:
    """Return whether the sec-edgar-mcp subprocess is reachable."""
    global _AVAILABLE
    if _AVAILABLE is None:
        _AVAILABLE = _resolve_endpoint() is not None
    return bool(_AVAILABLE)


async def status() -> dict[str, Any]:
    """Status payload for ``GET /sec/status`` (consumed by plugin manager)."""
    endpoint = _resolve_endpoint()
    available = endpoint is not None
    return {
        "available": available,
        "provider": PROVIDER,
        "endpoint": endpoint,
        "lastToolCallOk": _last_tool_call_ok,
        "lastError": _last_error,
    }


# ---------------------------------------------------------------------------
# Client + tool dispatch
# ---------------------------------------------------------------------------


async def _get_client() -> mcp_client.McpClient:
    """Return the cached :class:`McpClient` for the sec-edgar-mcp subprocess."""
    endpoint = _resolve_endpoint()
    if endpoint is None:
        raise ProviderError(
            "sec-edgar-mcp subprocess is not running — VYSTED_SEC_EDGAR_MCP_PORT not set."
        )
    return await mcp_client.get_client("sec-edgar-mcp", transport="http", endpoint=endpoint)


def _decode_tool_result(result: dict[str, Any], tool_name: str) -> Any:
    """Pull the JSON body out of an MCP tool result.

    sec-edgar-mcp returns either a JSON text block or a structured-content
    payload; we handle both, preferring the JSON text block when present.
    """
    if result.get("isError"):
        raise ProviderError(
            f"sec-edgar-mcp tool {tool_name!r} reported error: {result.get('content')!r}"
        )
    blocks = result.get("content") or []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            try:
                return json.loads(text)
            except (TypeError, ValueError):
                # Some tools (e.g. filing-content) return long-form prose;
                # surface as the raw text body.
                return text
    # Fallback: structured content (FastMCP 3.x with output_schema).
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    raise ProviderError(f"sec-edgar-mcp tool {tool_name!r} returned no content")


async def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Invoke a sec-edgar-mcp tool and return the decoded body."""
    global _last_tool_call_ok, _last_error
    client = await _get_client()
    try:
        raw = await client.call_tool(name, arguments)
    except Exception as exc:
        _last_tool_call_ok = False
        _last_error = f"{type(exc).__name__}: {exc}"
        raise ProviderError(f"sec-edgar-mcp call {name!r} failed: {exc}") from exc
    decoded = _decode_tool_result(raw, name)
    _last_tool_call_ok = True
    _last_error = None
    return decoded


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CIK_RE = re.compile(r"^\d+$")


def _normalize_identifier(cik_or_symbol: str) -> str:
    """Pass identifiers (CIK or ticker) through to upstream tools verbatim.

    sec-edgar-mcp accepts both — ``"AAPL"`` and ``"0000320193"`` both
    resolve correctly. Strip whitespace and uppercase tickers.
    """
    raw = (cik_or_symbol or "").strip()
    if not raw:
        raise ProviderError("identifier (cik or symbol) is required")
    if _CIK_RE.match(raw):
        # Zero-pad to 10 digits for cache-key stability.
        return raw.zfill(10)
    return raw.upper()


def _coerce_date(value: Any) -> date | None:
    """Best-effort parse of an ISO date string returned by sec-edgar-mcp."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _coerce_form_type(value: Any) -> FilingFormType | None:
    """Coerce the upstream form-type string to the Literal we surface."""
    if value is None:
        return None
    raw = str(value).strip().upper()
    # sec-edgar-mcp normalises common form types; map a few edge cases.
    mapping = {
        "10-K": "10-K",
        "10K": "10-K",
        "10-Q": "10-Q",
        "10Q": "10-Q",
        "8-K": "8-K",
        "8K": "8-K",
        "DEF 14A": "DEF 14A",
        "DEF14A": "DEF 14A",
        "3": "3",
        "4": "4",
        "5": "5",
    }
    return mapping.get(raw)  # type: ignore[return-value]


def _edgar_url(accession: str, cik: str) -> str:
    """Return the canonical EDGAR landing-page URL for an accession.

    Format: ``https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}``
    is the issuer-level page; the per-filing index lives at
    ``https://www.sec.gov/Archives/edgar/data/{CIK}/{accession-no-dashes}/``.
    """
    cik_stripped = str(int(cik)) if cik.isdigit() else cik.lstrip("0") or "0"
    acc_clean = accession.replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_stripped}/{acc_clean}/"


# ---------------------------------------------------------------------------
# Filing-list extraction — handle the multiple shapes upstream may return
# ---------------------------------------------------------------------------


def _filings_from_payload(
    payload: Any, fallback_cik: str | None = None
) -> tuple[str, str, str | None, list[Filing]]:
    """Pull ``(cik, company_name, symbol, filings)`` out of a sec-edgar-mcp payload.

    sec-edgar-mcp's ``get_recent_filings`` returns a dict with company
    metadata at the top level and a ``filings`` list keyed by accession.
    Be tolerant of older shapes (the upstream tool surface evolves).
    """
    cik = ""
    company_name = ""
    symbol: str | None = None
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        cik = str(payload.get("cik") or payload.get("CIK") or fallback_cik or "")
        company_name = str(payload.get("company_name") or payload.get("name") or "")
        symbol = _coerce_str(payload.get("ticker") or payload.get("symbol"))
        raw_list = payload.get("filings") or payload.get("results") or []
        if isinstance(raw_list, list):
            for row in raw_list:
                if isinstance(row, dict):
                    rows.append(row)
                    if not cik and (row.get("cik") or row.get("CIK")):
                        cik = str(row.get("cik") or row.get("CIK"))
    elif isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                rows.append(row)

    cik_padded = cik.zfill(10) if cik.isdigit() else cik or (fallback_cik or "")
    filings: list[Filing] = []
    for raw in rows:
        form_type = _coerce_form_type(raw.get("form") or raw.get("form_type"))
        if form_type is None:
            # Skip exotic forms not in our v0.6.0 set.
            continue
        accession = str(raw.get("accession") or raw.get("accession_number") or "")
        if not accession:
            continue
        filed_date = _coerce_date(raw.get("filed_date") or raw.get("filing_date") or raw.get("filed"))
        if filed_date is None:
            continue
        row_cik = str(raw.get("cik") or raw.get("CIK") or cik_padded)
        if row_cik.isdigit():
            row_cik = row_cik.zfill(10)
        url = (
            _coerce_str(raw.get("edgar_url"))
            or _coerce_str(raw.get("url"))
            or _edgar_url(accession, row_cik)
        )
        filings.append(
            Filing(
                accession=accession,
                cik=row_cik,
                company_name=str(raw.get("company_name") or raw.get("issuer_name") or company_name),
                symbol=_coerce_str(raw.get("symbol") or raw.get("ticker") or symbol),
                form_type=form_type,
                filed_date=filed_date,
                period_of_report=_coerce_date(
                    raw.get("period_of_report") or raw.get("report_date") or raw.get("period")
                ),
                edgar_url=url,
            )
        )
    return cik_padded, company_name, symbol, filings


def _sections_from_payload(payload: Any) -> list[FilingSection]:
    """Pull sections out of ``get_filing_sections`` / ``get_filing_content``.

    sec-edgar-mcp 1.x emits sections as a list of dicts (id / title /
    text). Tolerate a bare-text shape for filings the parser cannot
    section (older 8-K filings, exhibits) by wrapping in one synthetic
    section.
    """
    sections: list[FilingSection] = []
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        raw_sections = payload.get("sections")
        if isinstance(raw_sections, list):
            for item in raw_sections:
                if isinstance(item, dict):
                    rows.append(item)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                rows.append(item)
    elif isinstance(payload, str) and payload.strip():
        # Bare-text fallback — wrap in a single "Filing Content" section.
        text = payload.strip()
        return [
            FilingSection(
                id="content",
                title="Filing Content",
                text=text,
                word_count=len(text.split()),
            )
        ]

    for i, raw in enumerate(rows):
        text = str(raw.get("text") or raw.get("body") or raw.get("content") or "")
        title = str(raw.get("title") or raw.get("name") or raw.get("section") or f"Section {i + 1}")
        word_count = int(raw.get("word_count") or len(text.split()))
        sections.append(
            FilingSection(
                id=str(raw.get("id") or raw.get("section_id") or f"sec-{i}"),
                title=title,
                text=text,
                word_count=word_count,
            )
        )
    return sections


# ---------------------------------------------------------------------------
# Insider extraction
# ---------------------------------------------------------------------------


def _direction_from_code(code: str | None) -> InsiderTransactionDirection:
    """Map a Form 4 transaction code to an ``acquired`` / ``disposed`` direction.

    Form 4 codes — P (purchase), A (grant), M (option exercise) are all
    acquisitions; S (sale), D (disposition), F (tax withholding) are
    dispositions. Sec-edgar-mcp also surfaces a ``direction`` string on
    each row when it has it; we use that when present.
    """
    if not code:
        return "acquired"
    code = code.upper().strip()
    if code in {"S", "D", "F", "G", "X"}:
        return "disposed"
    return "acquired"


def _insider_rows_from_payload(payload: Any) -> tuple[str, str, list[InsiderTransaction]]:
    """Pull ``(cik, issuer_name, transactions)`` out of an insider payload."""
    cik = ""
    issuer_name = ""
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        cik = str(payload.get("cik") or payload.get("issuer_cik") or "")
        issuer_name = str(payload.get("issuer_name") or payload.get("company_name") or "")
        raw_list = (
            payload.get("transactions")
            or payload.get("insider_transactions")
            or payload.get("results")
            or []
        )
        if isinstance(raw_list, list):
            for row in raw_list:
                if isinstance(row, dict):
                    rows.append(row)
    elif isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                rows.append(row)

    transactions: list[InsiderTransaction] = []
    for raw in rows:
        form_raw = str(raw.get("form_type") or raw.get("form") or "4").strip()
        form: InsiderFormType
        if form_raw in {"3", "4", "5"}:
            form = form_raw  # type: ignore[assignment]
        else:
            continue
        accession = str(raw.get("accession") or raw.get("accession_number") or "")
        if not accession:
            continue
        txn_date = _coerce_date(raw.get("transaction_date") or raw.get("trade_date"))
        if txn_date is None:
            continue
        direction_str = str(raw.get("direction") or "").strip().lower()
        direction: InsiderTransactionDirection
        if direction_str in {"acquired", "disposed"}:
            direction = direction_str  # type: ignore[assignment]
        else:
            direction = _direction_from_code(raw.get("transaction_code"))
        shares = str(raw.get("shares") or raw.get("transaction_shares") or raw.get("amount") or "0")
        price = _coerce_str(raw.get("price_per_share") or raw.get("price"))
        value = _coerce_str(raw.get("transaction_value") or raw.get("value"))
        issuer_cik_raw = str(raw.get("issuer_cik") or raw.get("cik") or cik)
        issuer_cik = issuer_cik_raw.zfill(10) if issuer_cik_raw.isdigit() else issuer_cik_raw
        reporter_cik_raw = str(raw.get("reporter_cik") or raw.get("owner_cik") or "")
        reporter_cik = (
            reporter_cik_raw.zfill(10) if reporter_cik_raw.isdigit() else reporter_cik_raw
        )
        transactions.append(
            InsiderTransaction(
                accession=accession,
                reporter_name=str(raw.get("reporter_name") or raw.get("owner_name") or ""),
                reporter_cik=reporter_cik,
                issuer_cik=issuer_cik,
                issuer_name=str(raw.get("issuer_name") or issuer_name),
                issuer_symbol=_coerce_str(raw.get("issuer_symbol") or raw.get("ticker")),
                form_type=form,
                transaction_date=txn_date,
                direction=direction,
                shares=shares,
                price_per_share=price,
                transaction_value=value,
                transaction_code=str(raw.get("transaction_code") or raw.get("code") or ""),
                reporter_title=_coerce_str(raw.get("reporter_title") or raw.get("title")),
            )
        )
    cik_padded = cik.zfill(10) if cik.isdigit() else cik
    return cik_padded, issuer_name, transactions


# ---------------------------------------------------------------------------
# Public surface — consumed by sidecar/routers/sec_filings.py
# ---------------------------------------------------------------------------


async def list_filings(
    cik_or_symbol: str,
    form_type: FilingFormType | None = None,
    limit: int = 40,
) -> FilingsListResponse:
    """Return the filings index for a company.

    Args:
        cik_or_symbol: CIK (numeric) or ticker symbol. sec-edgar-mcp
            accepts both.
        form_type: optional filter — restrict to one of the v0.6.0
            supported form types.
        limit: maximum filings to return (upstream caps at 40 by default).
    """
    identifier = _normalize_identifier(cik_or_symbol)
    cache_key = f"sec:filings:{identifier}:{form_type or 'all'}:{limit}"
    cached = await data_cache.get(cache_key, _FILINGS_INDEX_TTL)
    if cached is not None:
        return FilingsListResponse.model_validate(cached)

    args: dict[str, Any] = {"identifier": identifier, "limit": int(limit)}
    if form_type is not None:
        args["form_type"] = form_type
    payload = await _call_tool("get_recent_filings", args)
    cik, company_name, symbol, filings = _filings_from_payload(payload, fallback_cik=identifier)
    response = FilingsListResponse(
        cik=cik or identifier,
        company_name=company_name,
        symbol=symbol,
        filings=filings,
    )
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


async def get_filing(
    accession: str,
    *,
    cik_or_symbol: str | None = None,
) -> FilingDetail:
    """Return the parsed filing detail for one accession.

    ``cik_or_symbol`` is required by sec-edgar-mcp's
    ``get_filing_content`` upstream tool; the panel always passes the
    same identifier it used to fetch the list.
    """
    if not accession:
        raise ProviderError("accession is required")
    identifier = _normalize_identifier(cik_or_symbol or "")
    cache_key = f"sec:filing:{accession}"
    cached = await data_cache.get(cache_key, _FILING_CONTENT_TTL)
    if cached is not None:
        return FilingDetail.model_validate(cached)

    sections_payload = await _call_tool(
        "get_filing_sections",
        {"identifier": identifier, "accession_number": accession, "form_type": "10-K"},
    )
    sections = _sections_from_payload(sections_payload)

    # Pull a minimal filing metadata row by hitting the filings list and
    # filtering by accession — keeps the FilingDetail payload self-contained.
    list_payload = await _call_tool(
        "get_recent_filings",
        {"identifier": identifier, "limit": 40},
    )
    _, _, _, filings = _filings_from_payload(list_payload, fallback_cik=identifier)
    match = next((f for f in filings if f.accession == accession), None)
    if match is None:
        # Sec-edgar-mcp returned sections but the listing page no
        # longer surfaces the accession — synthesise a minimal Filing
        # so the panel can still render.
        match = Filing(
            accession=accession,
            cik=identifier.zfill(10) if identifier.isdigit() else identifier,
            company_name="",
            symbol=None if not identifier.isalpha() else identifier,
            form_type="10-K",
            filed_date=datetime.now(tz=UTC).date(),
            period_of_report=None,
            edgar_url=_edgar_url(
                accession, identifier.zfill(10) if identifier.isdigit() else identifier
            ),
        )

    total_chars = sum(len(s.text) for s in sections)
    detail = FilingDetail(filing=match, sections=sections, total_chars=total_chars)
    await data_cache.set(cache_key, detail.model_dump(mode="json"))
    return detail


async def get_filing_sections(
    accession: str,
    *,
    cik_or_symbol: str | None = None,
) -> list[FilingSection]:
    """Return just the sections list for an accession.

    Thin wrapper over :func:`get_filing` so the panel's section-only
    navigation rail can hit a cheaper route without re-fetching the
    metadata row.
    """
    detail = await get_filing(accession, cik_or_symbol=cik_or_symbol)
    return list(detail.sections)


async def list_insider_transactions(
    cik_or_symbol: str,
    form_type: InsiderFormType | None = None,
    limit: int = 50,
) -> InsiderTransactionsResponse:
    """Return the recent insider transactions for an issuer.

    Args:
        cik_or_symbol: CIK or ticker — same convention as
            :func:`list_filings`.
        form_type: restrict to one of ``"3" | "4" | "5"``. Default is
            all three.
        limit: cap on row count.
    """
    identifier = _normalize_identifier(cik_or_symbol)
    cache_key = f"sec:insider:{identifier}:{form_type or 'all'}:{limit}"
    cached = await data_cache.get(cache_key, _INSIDER_TTL)
    if cached is not None:
        return InsiderTransactionsResponse.model_validate(cached)

    args: dict[str, Any] = {"identifier": identifier, "limit": int(limit)}
    if form_type is not None:
        args["form_types"] = [form_type]
    payload = await _call_tool("get_insider_transactions", args)
    cik, issuer_name, transactions = _insider_rows_from_payload(payload)
    response = InsiderTransactionsResponse(
        cik=cik or identifier,
        issuer_name=issuer_name,
        transactions=transactions,
    )
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


async def search_companies(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search the EDGAR company index — used by the panel's symbol field.

    sec-edgar-mcp exposes a ``search_companies`` tool; pass-through is
    fine because results are advisory only (the panel displays them
    in a dropdown). Returns a list of ``{cik, name, ticker}`` rows.
    """
    if not query or not query.strip():
        return []
    cache_key = f"sec:search:{query.strip().lower()}:{limit}"
    cached = await data_cache.get(cache_key, _FILINGS_INDEX_TTL)
    if isinstance(cached, list):
        return cached  # type: ignore[return-value]
    payload = await _call_tool(
        "search_companies", {"query": query.strip(), "limit": int(limit)}
    )
    rows: list[dict[str, Any]] = []
    raw_list: list[Any] = []
    if isinstance(payload, dict):
        raw_list = payload.get("results") or payload.get("companies") or []  # type: ignore[assignment]
    elif isinstance(payload, list):
        raw_list = payload
    for row in raw_list:
        if not isinstance(row, dict):
            continue
        cik = str(row.get("cik") or row.get("CIK") or "")
        if cik.isdigit():
            cik = cik.zfill(10)
        rows.append(
            {
                "cik": cik,
                "name": str(row.get("name") or row.get("company_name") or ""),
                "ticker": _coerce_str(row.get("ticker") or row.get("symbol")),
            }
        )
    await data_cache.set(cache_key, rows)
    return rows


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _reset_for_tests() -> None:
    """Clear cached availability + last-call state — used only from tests."""
    global _AVAILABLE, _last_tool_call_ok, _last_error
    _AVAILABLE = None
    _last_tool_call_ok = None
    _last_error = None


__all__ = [
    "PROVIDER",
    "get_filing",
    "get_filing_sections",
    "is_available",
    "list_filings",
    "list_insider_transactions",
    "search_companies",
    "status",
]
