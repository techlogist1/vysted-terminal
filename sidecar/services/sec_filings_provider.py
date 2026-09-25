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
import re
from datetime import date
from typing import Any

import httpx

from models.sec import (
    Filing,
    FilingDetail,
    FilingFormType,
    FilingSection,
    FilingsListResponse,
    InsiderFormType,
    InsiderTransaction,
    InsiderTransactionDirection,
    InsiderTransactionsResponse,
)
from services import data_cache, mcp_client
from services.errors import ProviderError

PROVIDER = "sec-edgar-mcp"

_log = logging.getLogger(__name__)

# Env vars the Tauri core sets when ``src-tauri/src/sec_edgar_mcp.rs``
# spawned the subprocess successfully.
_PORT_ENV = "VYSTED_SEC_EDGAR_MCP_PORT"
_HOST_ENV = "VYSTED_SEC_EDGAR_MCP_HOST"

# Shared discovery/status/health-tracked-call shape (R15-CODE-AGENT-024);
# mirrors openbb_mcp_provider's own ``_subprocess`` for plugin-manager parity.
_subprocess = mcp_client.LocalMcpSubprocess("sec-edgar-mcp", port_env=_PORT_ENV, host_env=_HOST_ENV)

# Cache TTLs.
_FILINGS_INDEX_TTL = 3600.0  # 1h
_FILING_CONTENT_TTL = 86400.0  # 24h
_INSIDER_TTL = 3600.0  # 1h

# R15-UI-032: sec-edgar-mcp 1.0.8's ``search_companies`` tool swallows every
# ``edgar.search()`` exception into an empty list (core/client.py), so the
# panel's symbol field never finds a company by name. SEC EDGAR itself
# publishes a full ticker/CIK/name index; reading that directly is a working
# local path that doesn't depend on the MCP subprocess at all.
_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
_COMPANY_TICKERS_CACHE_KEY = "sec:company_tickers"
_COMPANY_TICKERS_TTL = 86400.0  # 24h — SEC ships this file roughly daily.
# SEC fair-access guidance wants a contact UA (mirrors services.sec_ownership).
_SEC_USER_AGENT = "Vysted Terminal (contact: support@vysted.com)"

# ---------------------------------------------------------------------------
# Port + availability discovery
# ---------------------------------------------------------------------------


def is_available() -> bool:
    """Return whether the sec-edgar-mcp subprocess is reachable."""
    return _subprocess.is_available()


async def status() -> dict[str, Any]:
    """Status payload for ``GET /sec/status`` (consumed by plugin manager)."""
    return await _subprocess.status(PROVIDER)


# ---------------------------------------------------------------------------
# Client + tool dispatch
# ---------------------------------------------------------------------------


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
    decoded: Any = None
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            try:
                decoded = json.loads(text)
            except (TypeError, ValueError):
                # Some tools (e.g. filing-content) return long-form prose;
                # surface as the raw text body.
                return text
            break
    else:
        # Fallback: structured content (FastMCP 3.x with output_schema).
        decoded = result.get("structuredContent")
        if not isinstance(decoded, dict):
            raise ProviderError(f"sec-edgar-mcp tool {tool_name!r} returned no content")
    # sec-edgar-mcp reports its own failures in-band as ``{"success": false,
    # "error": ...}``; parsed as data they became a cached empty (R15-DATA-038).
    if isinstance(decoded, dict) and decoded.get("success") is False:
        raise ProviderError(
            f"sec-edgar-mcp tool {tool_name!r} failed: {decoded.get('error') or 'unknown error'}"
        )
    return decoded


async def _call_tool(name: str, arguments: dict[str, Any]) -> Any:
    """Invoke a sec-edgar-mcp tool and return the decoded body."""
    return await _subprocess.call_tool_json(name, arguments, decode=_decode_tool_result)


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


def _coerce_form_type(value: Any) -> str | None:
    """Normalise the upstream form-type string; ``None`` only when absent.

    EDGAR's form space is open (20-F, 6-K, 10-K/A, SC 13D, 424B4, ...), so any
    form is kept as filed; only the undashed spellings of the common forms are
    mapped (R15-DATA-039).
    """
    if value is None:
        return None
    raw = str(value).strip().upper()
    mapping = {"10K": "10-K", "10Q": "10-Q", "8K": "8-K", "DEF14A": "DEF 14A"}
    return mapping.get(raw, raw) or None


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
            continue
        accession = str(raw.get("accession") or raw.get("accession_number") or "")
        if not accession:
            continue
        filed_date = _coerce_date(
            raw.get("filed_date") or raw.get("filing_date") or raw.get("filed")
        )
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


_SECTION_TITLES = {
    "business": "Business",
    "risk_factors": "Risk Factors",
    "mda": "Management's Discussion and Analysis",
}


def _parse_error(tool_name: str, detail: str) -> ProviderError:
    """A success payload the parser could not read: logged, raised, never cached."""
    _log.warning("sec-edgar-mcp %s payload not parsed: %s", tool_name, detail)
    return ProviderError(f"sec-edgar-mcp {tool_name} returned a payload Vysted could not parse")


def _sections_from_payload(payload: Any) -> list[FilingSection]:
    """Pull sections out of ``get_filing_sections`` / ``get_filing_content``.

    sec-edgar-mcp 1.0.8 emits ``sections`` as a dict of ``name -> text``
    (plus non-text flags such as ``has_financials``); a list of dicts
    (id / title / text) is also accepted. A bare-text shape for filings the
    parser cannot section (older 8-K filings, exhibits) is wrapped in one
    synthetic section. An empty ``sections`` is a real empty (the upstream
    sections only 10-K/10-Q); any other shape raises, uncached.
    """
    sections: list[FilingSection] = []
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict) and isinstance(payload.get("sections"), dict):
        for key, text in payload["sections"].items():
            if isinstance(text, str) and text.strip():
                title = _SECTION_TITLES.get(key) or key.replace("_", " ").title()
                rows.append({"id": key, "title": title, "text": text})
    elif isinstance(payload, dict) and isinstance(payload.get("sections"), list):
        for item in payload["sections"]:
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
    else:
        raise _parse_error("get_filing_sections", f"unrecognised shape {type(payload).__name__}")

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
    """Pull ``(cik, issuer_name, transactions)`` out of an insider payload.

    sec-edgar-mcp 1.0.8 returns FILING-level rows (``filing_date``,
    ``form_type``, ``accession_number``, ``company_name``, ``cik``, optional
    ``owner_name``/``owner_title``) under a top-level issuer ``name``, with no
    per-trade date, code, direction or share count. Such a row is kept with its
    filing date and a null direction/shares; per-trade rows keep their detail.
    An unrecognised shape, or rows that all fail to parse, raises.
    """
    cik = ""
    issuer_name = ""
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        cik = str(payload.get("cik") or payload.get("issuer_cik") or "")
        issuer_name = str(
            payload.get("issuer_name") or payload.get("company_name") or payload.get("name") or ""
        )
        raw_list = next(
            (
                payload[key]
                for key in ("transactions", "insider_transactions", "results")
                if isinstance(payload.get(key), list)
            ),
            None,
        )
        if raw_list is None:
            raise _parse_error("get_insider_transactions", f"no rows list in {sorted(payload)}")
        for row in raw_list:
            if isinstance(row, dict):
                rows.append(row)
    elif isinstance(payload, list):
        for row in payload:
            if isinstance(row, dict):
                rows.append(row)
    else:
        raise _parse_error(
            "get_insider_transactions", f"unrecognised shape {type(payload).__name__}"
        )

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
        txn_date = _coerce_date(
            raw.get("transaction_date") or raw.get("trade_date") or raw.get("filing_date")
        )
        if txn_date is None:
            continue
        direction_str = str(raw.get("direction") or "").strip().lower()
        direction: InsiderTransactionDirection | None
        if direction_str in {"acquired", "disposed"}:
            direction = direction_str  # type: ignore[assignment]
        elif raw.get("transaction_code"):
            direction = _direction_from_code(raw.get("transaction_code"))
        else:
            direction = None  # a filing-level row carries no trade to classify
        shares = _coerce_str(
            raw.get("shares") or raw.get("transaction_shares") or raw.get("amount")
        )
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
                issuer_name=str(raw.get("issuer_name") or raw.get("company_name") or issuer_name),
                issuer_symbol=_coerce_str(raw.get("issuer_symbol") or raw.get("ticker")),
                form_type=form,
                transaction_date=txn_date,
                direction=direction,
                shares=shares,
                price_per_share=price,
                transaction_value=value,
                transaction_code=str(raw.get("transaction_code") or raw.get("code") or ""),
                reporter_title=_coerce_str(
                    raw.get("reporter_title") or raw.get("owner_title") or raw.get("title")
                ),
            )
        )
    if rows and not transactions:
        raise _parse_error("get_insider_transactions", f"{len(rows)} rows, none parsed")
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


#: ``get_filing``'s metadata-lookup windows, smallest first (R15-LEAD-010).
#: sec-edgar-mcp 1.0.8 reads each row's ``period_of_report``, which fetches that
#: filing's SGML from EDGAR, so a window's cost grows per row: 200+ rows time
#: out or fail ("cannot unpack non-iterable NoneType") and 400 hangs past the
#: client timeout. The lookup opens with base's 40-row request and widens once.
_FILING_WINDOWS = (40, 100)

#: Periodic-report forms tried, form-filtered at the smallest window only, when
#: no explicit ``form_type`` hint locates the accession in the unfiltered
#: windows above (R15-LEAD-010) — the annual/quarterly forms a heavy
#: Form-4/144 filer's recency stream pushes past row 100.
# ponytail: bounded to these 3 extra 40-row calls; an unhinted filing of a
# rarer form still outside all of the above (e.g. an 8-K) is not_found — the
# caller's form hint is how that one resolves.
_PERIODIC_FORMS = ("10-K", "10-Q", "20-F")


async def get_filing(
    accession: str,
    *,
    cik_or_symbol: str | None = None,
    form_type: str | None = None,
) -> FilingDetail:
    """Return the parsed filing detail for one accession.

    ``cik_or_symbol`` is required by sec-edgar-mcp's
    ``get_filing_content`` upstream tool; the panel always passes the
    same identifier it used to fetch the list.

    R15-DATA-007: metadata is resolved FIRST, against the issuer's recent
    filings list. A miss raises ``ProviderError(kind="not_found")`` — never
    a synthesised ``Filing`` — so an accession outside the list window (or
    one sec-edgar-mcp doesn't recognise) surfaces as an honest 404, not a
    filing that reads "10-K filed today" with no company name.

    R15-LEAD-010: ``form_type`` is the listed row's form — the lookup runs over
    that form-filtered list first (what the panel showed), then, with no hint
    or on a miss, over the unfiltered list. Each pass opens with a 40-row
    window and widens to 100 only when a full window misses. A failed hinted
    lookup falls back to the unfiltered list. With no hint, once the unfiltered
    list also misses, the lookup tries each periodic-report form's own
    40-row list (``_PERIODIC_FORMS``) before raising — a heavy Form-4/144
    filer's 10-K/10-Q can sit well past row 100 of the raw recency stream.
    """
    if not accession:
        raise ProviderError("accession is required")
    identifier = _normalize_identifier(cik_or_symbol or "")
    cache_key = f"sec:filing:{accession}"
    cached = await data_cache.get(cache_key, _FILING_CONTENT_TTL)
    if cached is not None:
        return FilingDetail.model_validate(cached)

    # Metadata FIRST — the sectioning call below needs the filing's REAL
    # form_type (a 10-Q sectioned as "10-K" mis-parses its headings), and a
    # miss here must raise, not synthesise a filing (§6 D-B2, R15-DATA-007).
    passes: list[tuple[dict[str, str], tuple[int, ...]]] = (
        ([({"form_type": form_type}, _FILING_WINDOWS)] if form_type else [])
        + [({}, _FILING_WINDOWS)]
        + ([] if form_type else [({"form_type": f}, _FILING_WINDOWS[:1]) for f in _PERIODIC_FORMS])
    )
    match = None
    for form_filter, windows in passes:
        for limit in windows:
            try:
                list_payload = await _call_tool(
                    "get_recent_filings",
                    {"identifier": identifier, "limit": limit, **form_filter},
                )
            except ProviderError:
                if not form_filter:
                    raise
                break  # this filtered list failed: fall through to the next pass
            _, _, _, filings = _filings_from_payload(list_payload, fallback_cik=identifier)
            match = next((f for f in filings if f.accession == accession), None)
            if match is not None or len(filings) < limit:
                break  # found, or the list is exhausted: a wider window adds nothing
        if match is not None:
            break
    if match is None:
        raise ProviderError(f"filing metadata unavailable for {accession!r}", kind="not_found")

    sections_payload = await _call_tool(
        "get_filing_sections",
        {"identifier": identifier, "accession_number": accession, "form_type": match.form_type},
    )
    sections = _sections_from_payload(sections_payload)

    total_chars = sum(len(s.text) for s in sections)
    detail = FilingDetail(filing=match, sections=sections, total_chars=total_chars)
    await data_cache.set(cache_key, detail.model_dump(mode="json"))
    return detail


async def get_filing_sections(
    accession: str,
    *,
    cik_or_symbol: str | None = None,
    form_type: str | None = None,
) -> list[FilingSection]:
    """Return just the sections list for an accession.

    Thin wrapper over :func:`get_filing` so the panel's section-only
    navigation rail can hit a cheaper route without re-fetching the
    metadata row. ``form_type`` (R15-LEAD-010) is the same lookup hint
    ``get_filing`` takes — forward it when the caller has it.
    """
    detail = await get_filing(accession, cik_or_symbol=cik_or_symbol, form_type=form_type)
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


async def _load_company_tickers() -> dict[str, dict[str, Any]]:
    """The SEC's full ticker/CIK/name index, cached 24h.

    ``company_tickers.json`` is a ``{"0": {"cik_str": ..., "ticker": ...,
    "title": ...}, "1": {...}, ...}`` map, refreshed by SEC roughly daily and
    reachable without the sec-edgar-mcp subprocess.
    """
    cached = await data_cache.get(_COMPANY_TICKERS_CACHE_KEY, _COMPANY_TICKERS_TTL)
    if isinstance(cached, dict) and cached:
        return cached
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": _SEC_USER_AGENT}, timeout=30.0, follow_redirects=True
        ) as client:
            resp = await client.get(_COMPANY_TICKERS_URL)
        resp.raise_for_status()
        payload = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError(f"sec company_tickers.json fetch failed: {exc}") from exc
    if not isinstance(payload, dict) or not payload:
        raise ProviderError("sec company_tickers.json returned an unexpected shape")
    await data_cache.set(_COMPANY_TICKERS_CACHE_KEY, payload)
    return payload


def _company_ticker_row(raw: dict[str, Any]) -> dict[str, Any]:
    cik = str(raw.get("cik_str") or raw.get("cik") or "")
    if cik.isdigit():
        cik = cik.zfill(10)
    ticker = _coerce_str(raw.get("ticker"))
    return {"cik": cik, "name": str(raw.get("title") or ""), "ticker": ticker}


async def search_companies(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search the EDGAR company index — used by the panel's symbol field.

    R15-UI-032: sec-edgar-mcp 1.0.8's ``search_companies`` tool swallows
    every ``edgar.search()`` exception into ``[]`` (its ``core/client.py``),
    so it never actually finds a company. This reads SEC's own
    ``company_tickers.json`` index instead — a working local path that needs
    no MCP round-trip. Matching is a case-insensitive substring over both the
    ticker and the company name; an exact ticker match is returned first.
    Returns a list of ``{cik, name, ticker}`` rows, capped at ``limit``.
    """
    q = query.strip().lower()
    if not q:
        return []
    tickers = await _load_company_tickers()
    exact: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    for raw in tickers.values():
        if not isinstance(raw, dict):
            continue
        ticker = str(raw.get("ticker") or "").lower()
        title = str(raw.get("title") or "").lower()
        if not ticker and not title:
            continue
        if ticker == q:
            exact.append(_company_ticker_row(raw))
        elif q in ticker or q in title:
            partial.append(_company_ticker_row(raw))
        if len(exact) >= limit:
            break
    return (exact + partial)[:limit]


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _reset_for_tests() -> None:
    """Clear cached availability + last-call state — used only from tests."""
    _subprocess.reset_for_tests()


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
