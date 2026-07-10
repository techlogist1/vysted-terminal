"""Corporate-disclosure Pydantic models (R7 Component 3).

Typed shapes for the India corporate-disclosure feeds served by
:mod:`services.corporate_disclosures` and ``routers/disclosures.py``:

* :class:`Announcement` — one exchange announcement (NSE corporate-announcements
  feed / BSE ``AnnSubCategoryGetData`` feed), merged + deduped by the service.
* :class:`ResultsEvent` — one results-calendar / board-meeting event (the NSE
  ``event-calendar`` feed).
* :class:`ShareholdingPattern` — one quarterly shareholding-pattern row. The
  NSE shareholding MASTER carries the promoter(+group), public, and
  employee-trust percentages; the FII/DII split lives only in the linked XBRL
  filing, so ``fii_percent``/``dii_percent`` are honest ``None`` unless a
  source actually supplies them — never fabricated (``xbrl_url`` points at the
  filing that carries the full split).

Mirrored by hand in ``types/data.ts`` — keep in sync (see CLAUDE.md Gotchas).
"""

from __future__ import annotations

import datetime as _dt
from datetime import date, datetime

from pydantic import BaseModel


class Announcement(BaseModel):
    """One corporate announcement from an Indian exchange feed."""

    symbol: str
    #: The exchange that disseminated this item: ``"NSE"`` or ``"BSE"``.
    exchange: str
    headline: str
    #: Exchange category label (e.g. "Updates", "Company Update"); None when absent.
    category: str | None = None
    #: Direct URL of the filed attachment (usually a PDF); None when none filed.
    attachment_url: str | None = None
    #: Dissemination timestamp (IST-aware); None when the feed row had no
    #: parseable timestamp (kept rather than dropped — the text still informs).
    ts: datetime | None = None


class AnnouncementsResponse(BaseModel):
    """``GET /disclosures/announcements`` — the merged, deduped feed."""

    symbol: str
    #: The single-exchange filter applied, or None for the merged NSE+BSE feed.
    exchange: str | None = None
    count: int
    announcements: list[Announcement] = []
    #: Exchanges that actually served this response (e.g. ["NSE","BSE"]).
    sources: list[str] = []
    #: Exchanges that were attempted but failed, with the honest reason — a
    #: partial merge is served rather than failing the whole feed.
    errors: dict[str, str] = {}


class ResultsEvent(BaseModel):
    """One results-calendar / board-meeting event (NSE event-calendar feed)."""

    symbol: str
    company: str | None = None
    #: Event purpose, e.g. "Financial Results", "Dividend", "Demerger".
    purpose: str
    #: The board-meeting description text accompanying the event.
    description: str | None = None
    #: Meeting/event date; None when the feed row carried no parseable date.
    #: (Annotated via the module alias — the field NAME shadows ``date`` when
    #: Pydantic evaluates this class's deferred annotations.)
    date: _dt.date | None = None


class ResultsCalendarResponse(BaseModel):
    """``GET /disclosures/results`` — results/board-meeting events, newest first."""

    symbol: str
    count: int
    events: list[ResultsEvent] = []


class ShareholdingPattern(BaseModel):
    """One quarterly shareholding-pattern row for a listed company.

    Percentages are 0-100 (as the exchanges publish them). ``fii_percent`` /
    ``dii_percent`` are ``None`` when the source feed does not carry the split
    (the NSE master does not — the linked XBRL filing does); they are never
    fabricated.
    """

    symbol: str
    #: The quarter-end date this pattern reports (e.g. 2026-03-31).
    quarter_end: date
    #: Promoter + promoter-group holding, percent of equity.
    promoter_percent: float | None = None
    fii_percent: float | None = None
    dii_percent: float | None = None
    #: Total institutional holding (FII + DII), percent of equity. The NSE
    #: quarterly master does not carry it (the split lives in the XBRL), so it
    #: is ``None`` on that lane; the BSE lane parses it from the SEBI XBRL and
    #: populates it (with ``fii``/``dii`` when the foreign/domestic split is
    #: present). Never fabricated.
    institutions_percent: float | None = None
    public_percent: float | None = None
    employee_trusts_percent: float | None = None
    #: Date the pattern was filed with the exchange.
    submission_date: date | None = None
    #: The XBRL filing URL carrying the full category-level split (FII/DII detail).
    xbrl_url: str | None = None
    #: The exchange lane that served this pattern — ``"NSE"`` (quarterly master)
    #: or ``"BSE"`` (SEBI XBRL). Lets a consumer state the provenance and the
    #: as-of quarter of an exchange figure verbatim.
    source: str | None = None


class ShareholdingResponse(BaseModel):
    """``GET /disclosures/shareholding`` — quarterly patterns, newest first."""

    symbol: str
    count: int
    patterns: list[ShareholdingPattern] = []
