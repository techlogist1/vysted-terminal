"""SEC EDGAR filing Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/sec.ts``.

XBRL-precise numeric fields are typed as ``str`` here to mirror the TS side's
``string`` typing — preserves precision past JavaScript's
``Number.MAX_SAFE_INTEGER`` (AAPL's total-assets cent value, for example,
overflows). The sidecar's sec-edgar-mcp client wraps the upstream's
arbitrary-precision XBRL values without coercing to ``float`` along the way.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Filing identity
# ---------------------------------------------------------------------------

FilingFormType = Literal["10-K", "10-Q", "8-K", "DEF 14A", "3", "4", "5"]


class Filing(BaseModel):
    """Top-level filing metadata — one row in the filings list."""

    model_config = ConfigDict(extra="forbid")

    accession: str
    cik: str
    company_name: str
    symbol: str | None = None
    form_type: FilingFormType
    filed_date: date
    period_of_report: date | None = None
    edgar_url: str


# ---------------------------------------------------------------------------
# Filing content
# ---------------------------------------------------------------------------


class FilingSection(BaseModel):
    """One parsed section of a filing — e.g. ``"Item 1A. Risk Factors"``."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    text: str
    word_count: int


class FilingDetail(BaseModel):
    """Filing detail payload — what the FilingViewer panel renders."""

    model_config = ConfigDict(extra="forbid")

    filing: Filing
    sections: list[FilingSection]
    total_chars: int


# ---------------------------------------------------------------------------
# XBRL facts
# ---------------------------------------------------------------------------


class XbrlFact(BaseModel):
    """One XBRL-precise financial fact pulled from a filing."""

    model_config = ConfigDict(extra="forbid")

    concept: str
    value: str
    units: str
    period_end: date
    period_start: date | None = None
    accession: str


XbrlCategory = Literal["balance-sheet", "income-statement", "cash-flow"]


class FinancialFacts(BaseModel):
    """The set of XBRL facts for one statement category at a symbol."""

    model_config = ConfigDict(extra="forbid")

    cik: str
    symbol: str | None = None
    category: XbrlCategory
    facts: list[XbrlFact]


# ---------------------------------------------------------------------------
# Insider transactions (Forms 3, 4, 5)
# ---------------------------------------------------------------------------

InsiderTransactionDirection = Literal["acquired", "disposed"]
InsiderFormType = Literal["3", "4", "5"]


class InsiderTransaction(BaseModel):
    """One insider transaction row from a Form 3 / 4 / 5 filing."""

    model_config = ConfigDict(extra="forbid")

    accession: str
    reporter_name: str
    reporter_cik: str
    issuer_cik: str
    issuer_name: str
    issuer_symbol: str | None = None
    form_type: InsiderFormType
    transaction_date: date
    direction: InsiderTransactionDirection
    shares: str
    price_per_share: str | None = None
    transaction_value: str | None = None
    transaction_code: str
    reporter_title: str | None = None


class InsiderTransactionsResponse(BaseModel):
    """Insider-transactions payload returned by ``/sec/insider/{cik}``."""

    model_config = ConfigDict(extra="forbid")

    cik: str
    issuer_name: str
    transactions: list[InsiderTransaction]


# ---------------------------------------------------------------------------
# Filings list
# ---------------------------------------------------------------------------


class FilingsListResponse(BaseModel):
    """Filings-list payload returned by ``/sec/filings``."""

    model_config = ConfigDict(extra="forbid")

    cik: str
    company_name: str
    symbol: str | None = None
    filings: list[Filing]
