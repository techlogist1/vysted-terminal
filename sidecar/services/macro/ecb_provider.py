"""ECB macro provider — in-process via ``ecbdata==0.1.1``.

``ecbdata`` is a small client over the ECB's Statistical Data Warehouse
(SDMX 2.1 REST endpoint at ``data-api.ecb.europa.eu``). Each ECB series
is identified by a dotted key like ``FM.D.U2.EUR.4F.KR.MRR_FR.LEV``
(Main Refinancing Rate, daily, EUR). No API key required.

Public surface (matches every other macro provider in this package):

  - :func:`get_series(series_id) -> MacroSeriesExtended`
  - :func:`search(query, limit) -> list[MacroSearchResult]`
  - :func:`catalog(limit) -> MacroCatalog`
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from models.macro_extended import (
    MacroCatalog,
    MacroCatalogEntry,
    MacroSearchResult,
    MacroSeriesExtended,
)
from models.market import MacroObservation
from services.errors import ProviderError

PROVIDER = "ecb"

_log = logging.getLogger(__name__)

# Hand-curated featured catalog — the headline ECB series the macro panel
# offers on the "Featured" tab. ECB's full keyfamily browsing is rich enough
# to deserve a Phase-7 dedicated browse UI; for v0.6.0 a curated list
# covers the canonical "monetary policy + ICP + ECB BSI" surface.
_FEATURED: list[MacroCatalogEntry] = [
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="FM.D.U2.EUR.4F.KR.MRR_FR.LEV",
        title="Main Refinancing Operations Rate (MRO) — daily",
        category="Monetary Policy",
        frequency="daily",
        units="Percent per annum",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="FM.D.U2.EUR.4F.KR.DFR.LEV",
        title="Deposit Facility Rate — daily",
        category="Monetary Policy",
        frequency="daily",
        units="Percent per annum",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="FM.D.U2.EUR.4F.KR.MLFR.LEV",
        title="Marginal Lending Facility Rate — daily",
        category="Monetary Policy",
        frequency="daily",
        units="Percent per annum",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="ICP.M.U2.N.000000.4.ANR",
        title="HICP - Overall index, annual rate of change, Euro area",
        category="Prices",
        frequency="monthly",
        units="Percentage change",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="ICP.M.U2.N.XEF000.4.ANR",
        title="HICP - Core (excl. energy & food), Euro area",
        category="Prices",
        frequency="monthly",
        units="Percentage change",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="BSI.M.U2.Y.V.M30.X.1.U2.2300.Z01.E",
        title="M3 Money Stock — Euro area",
        category="Money Supply",
        frequency="monthly",
        units="EUR (millions)",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="LFSI.M.I9.S.UNEHRT.TOTAL0.15_74.T",
        title="Unemployment Rate, Euro area, total, 15-74",
        category="Labour",
        frequency="monthly",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="EXR.D.USD.EUR.SP00.A",
        title="EUR/USD spot exchange rate (daily)",
        category="Exchange Rates",
        frequency="daily",
        units="USD per 1 EUR",
    ),
]


def _make_client() -> Any:
    """Construct an ``ecbdata`` client. Isolated for test mockability."""
    try:
        from ecbdata import ecbdata  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ProviderError(f"ecbdata is not installed: {exc}") from exc
    return ecbdata


def _parse_observations(df: Any) -> list[MacroObservation]:
    """Parse the DataFrame returned by ``ecbdata.get_series``."""
    observations: list[MacroObservation] = []
    if df is None:
        return observations
    # ecbdata returns a DataFrame with columns including TIME_PERIOD and OBS_VALUE.
    try:
        rows = df.to_dict(orient="records")
    except AttributeError:
        return observations
    for row in rows:
        raw_date = row.get("TIME_PERIOD") or row.get("time") or row.get("TIME")
        if raw_date is None:
            continue
        try:
            date = datetime.fromisoformat(str(raw_date))
        except ValueError:
            # ECB sometimes returns YYYY-MM or YYYY for monthly/annual series.
            txt = str(raw_date)
            if len(txt) == 7:  # YYYY-MM
                try:
                    date = datetime.fromisoformat(f"{txt}-01")
                except ValueError:
                    continue
            elif len(txt) == 4:  # YYYY
                try:
                    date = datetime.fromisoformat(f"{txt}-01-01")
                except ValueError:
                    continue
            else:
                continue
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        raw_value = row.get("OBS_VALUE") or row.get("value")
        value: float | None
        try:
            float_v = float(raw_value) if raw_value is not None else None
            value = (
                None if float_v is None or float_v != float_v else float_v  # NaN check
            )
        except (TypeError, ValueError):
            value = None
        observations.append(MacroObservation(date=date, value=value))
    return observations


def _ecb_frequency(series_id: str) -> str | None:
    """Derive frequency from the ECB key's second token (D / M / Q / A)."""
    parts = series_id.split(".")
    if len(parts) < 2:
        return None
    code = parts[1].upper()
    return {"D": "daily", "W": "weekly", "M": "monthly", "Q": "quarterly", "A": "annual"}.get(code)


def get_series(series_id: str) -> MacroSeriesExtended:
    """Fetch an ECB time series by its dotted SDMX key."""
    if not series_id:
        raise ProviderError("ECB get_series requires a non-empty series_id")
    client = _make_client()
    try:
        df = client.get_series(series_id)
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"ECB upstream error for {series_id!r}: {exc}") from exc

    observations = _parse_observations(df)

    # Try to pull a title from the DataFrame's first row metadata; ecbdata
    # returns title-ish columns sporadically depending on the series. Fall
    # back to the series_id when no usable title is found.
    title = series_id
    try:
        first_row = df.iloc[0].to_dict() if hasattr(df, "iloc") and len(df) > 0 else {}
        for candidate in ("TITLE", "TITLE_COMPL", "title"):
            value = first_row.get(candidate)
            if isinstance(value, str) and value:
                title = value
                break
    except (AttributeError, KeyError, IndexError):
        pass

    return MacroSeriesExtended(
        series_id=series_id,
        title=title,
        units=None,
        observations=observations,
        provider=PROVIDER,
        frequency=_ecb_frequency(series_id),
        last_updated=None,
        seasonal_adjustment=None,
        source_url=f"https://data.ecb.europa.eu/data/datasets/{series_id}",
        notes=None,
    )


def search(query: str, limit: int = 25) -> list[MacroSearchResult]:
    """Best-effort search over the featured ECB catalog by substring match.

    The ECB SDH endpoint does not expose a cheap free-text search; full
    keyfamily browsing is a Phase-7 candidate. v0.6.0 ranks by title
    substring against the curated featured set, which covers Use Case 5's
    headline series.
    """
    if not query:
        return []
    q = query.lower()
    matches: list[MacroSearchResult] = []
    for entry in _FEATURED:
        title_l = entry.title.lower()
        if q in title_l or q in entry.series_id.lower():
            score = 1.0 if q == title_l else 0.5 if title_l.startswith(q) else 0.25
            matches.append(
                MacroSearchResult(
                    provider=PROVIDER,
                    series_id=entry.series_id,
                    title=entry.title,
                    frequency=entry.frequency,
                    units=entry.units,
                    score=score,
                )
            )
    matches.sort(key=lambda r: r.score, reverse=True)
    return matches[:limit]


def catalog(limit: int = 25) -> MacroCatalog:
    """Return the curated ECB catalog."""
    return MacroCatalog(provider=PROVIDER, entries=list(_FEATURED[:limit]))


__all__ = ["PROVIDER", "catalog", "get_series", "search"]
