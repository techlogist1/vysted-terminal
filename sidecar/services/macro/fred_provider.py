"""FRED macro provider — in-process via ``fredapi==0.5.2``.

The v0.6.0 Phase-6 plan originally called for FRED via a subprocess MCP
server, but ``fred-mcp-server`` turned out to be a Node.js package, not
a Python one. FRED is now consumed in-process via the mature
``fredapi`` Python client (Mortada). Decision rationale + reasoning chain
in :file:`BLOCKERS-M.md` T3-M-1.

Public surface (matches every other macro provider in this package):

  - :func:`get_series(series_id) -> MacroSeriesExtended`
  - :func:`search(query, limit) -> list[MacroSearchResult]`
  - :func:`catalog(limit) -> MacroCatalog`

Authentication
~~~~~~~~~~~~~~

FRED requires a free API key (https://fred.stlouisfed.org/docs/api/api_key.html).
The provider reads it from the ``FRED_API_KEY`` environment variable. When
the key is missing every call raises :class:`ProviderError` which the router
translates to a 502 — matching every other BYOK upstream's degradation
behaviour.

Search + catalog
~~~~~~~~~~~~~~~~

FRED's "search/series" REST endpoint backs :func:`search`; the curated
catalog returns the most-popular FRED series (DGS10, GDP, UNRATE,
FEDFUNDS, etc.) when no upstream catalog cheap-call is available.
"""

from __future__ import annotations

import logging
import os
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

PROVIDER = "fred"

_log = logging.getLogger(__name__)

_API_KEY_ENV = "FRED_API_KEY"

# Curated "featured" catalog — the FRED series the macro panel offers when the
# user clicks the "Featured" tab without typing a query. Hand-picked from the
# FRED most-popular list (https://fred.stlouisfed.org/tags/series?ob=pv) so it
# is useful without making the picker depend on an extra upstream call.
_FEATURED: list[MacroCatalogEntry] = [
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="DGS10",
        title="10-Year Treasury Constant Maturity Rate",
        category="Interest Rates",
        frequency="daily",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="DGS2",
        title="2-Year Treasury Constant Maturity Rate",
        category="Interest Rates",
        frequency="daily",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="FEDFUNDS",
        title="Federal Funds Effective Rate",
        category="Interest Rates",
        frequency="monthly",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="CPIAUCSL",
        title="Consumer Price Index for All Urban Consumers: All Items",
        category="Prices",
        frequency="monthly",
        units="Index 1982-1984=100",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="UNRATE",
        title="Unemployment Rate",
        category="Labor",
        frequency="monthly",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="GDP",
        title="Gross Domestic Product",
        category="National Accounts",
        frequency="quarterly",
        units="Billions of Dollars",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="GDPC1",
        title="Real Gross Domestic Product",
        category="National Accounts",
        frequency="quarterly",
        units="Billions of Chained 2017 Dollars",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="M2SL",
        title="M2 Money Stock",
        category="Money Supply",
        frequency="monthly",
        units="Billions of Dollars",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="PAYEMS",
        title="All Employees, Total Nonfarm",
        category="Labor",
        frequency="monthly",
        units="Thousands of Persons",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="T10Y2Y",
        title="10-Year Treasury Minus 2-Year Treasury Yield Spread",
        category="Interest Rates",
        frequency="daily",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="VIXCLS",
        title="CBOE Volatility Index (VIX)",
        category="Markets",
        frequency="daily",
        units="Index",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="DEXUSEU",
        title="U.S. / Euro Foreign Exchange Rate",
        category="Exchange Rates",
        frequency="daily",
        units="U.S. Dollars to One Euro",
    ),
]

# FRED's REST API uses lowercase frequency codes; map them to the macro
# contract's :data:`MacroFrequency` literal.
_FREQ_MAP: dict[str, str] = {
    "d": "daily",
    "w": "weekly",
    "bw": "weekly",
    "m": "monthly",
    "q": "quarterly",
    "sa": "quarterly",
    "a": "annual",
}


def _api_key() -> str:
    """Return the configured FRED API key, or raise :class:`ProviderError`."""
    key = os.environ.get(_API_KEY_ENV)
    if not key:
        raise ProviderError(
            f"FRED provider requires the {_API_KEY_ENV} environment variable. "
            "Sign up for a free key at https://fred.stlouisfed.org/docs/api/api_key.html."
        )
    return key


def _make_client() -> Any:
    """Construct a ``fredapi.Fred`` client. Isolated for test mockability.

    Checks the env var BEFORE importing fredapi so a missing key surfaces
    the canonical "set FRED_API_KEY" error even on a build without the
    library installed (e.g. CI / unit tests).
    """
    key = _api_key()
    try:
        from fredapi import Fred  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover — exercised via test
        raise ProviderError(f"fredapi is not installed: {exc}") from exc
    return Fred(api_key=key)


def _coerce_freq(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    return _FREQ_MAP.get(raw.lower())


def _coerce_seasonal(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    if raw.lower() in {"sa", "seasonally adjusted", "seasonally_adjusted"}:
        return "seasonally-adjusted"
    if raw.lower() in {"nsa", "not seasonally adjusted", "not_seasonally_adjusted"}:
        return "not-adjusted"
    return None


def _parse_observations(series: Any) -> list[MacroObservation]:
    """Turn a fredapi series (``pandas.Series`` of float / NaN) into observations."""
    observations: list[MacroObservation] = []
    if series is None:
        return observations
    try:
        items = list(series.items())  # type: ignore[union-attr]
    except AttributeError:
        return observations
    for raw_date, raw_value in items:
        # fredapi returns pandas.Timestamp; coerce to UTC datetime.
        if hasattr(raw_date, "to_pydatetime"):
            date = raw_date.to_pydatetime()
        elif isinstance(raw_date, datetime):
            date = raw_date
        else:
            try:
                date = datetime.fromisoformat(str(raw_date))
            except ValueError:
                continue
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        value: float | None
        try:
            float_v = float(raw_value)
            value = None if float_v != float_v else float_v  # NaN check
        except (TypeError, ValueError):
            value = None
        observations.append(MacroObservation(date=date, value=value))
    return observations


def get_series(series_id: str) -> MacroSeriesExtended:
    """Fetch a FRED time series and its metadata.

    Raises :class:`ProviderError` on missing API key, missing series, or
    upstream error.
    """
    if not series_id:
        raise ProviderError("FRED get_series requires a non-empty series_id")
    client = _make_client()
    try:
        series = client.get_series(series_id)
        info = client.get_series_info(series_id)
    except Exception as exc:  # noqa: BLE001 — bubble up as ProviderError
        raise ProviderError(f"FRED upstream error for {series_id!r}: {exc}") from exc

    observations = _parse_observations(series)
    # ``info`` is a pandas Series indexed by metadata field name.
    info_dict: dict[str, Any] = {}
    try:
        info_dict = dict(info.items())  # type: ignore[union-attr]
    except AttributeError:
        pass

    last_updated_raw = info_dict.get("last_updated")
    last_updated: datetime | None = None
    if last_updated_raw is not None:
        try:
            last_updated = datetime.fromisoformat(str(last_updated_raw).replace(" ", "T"))
            if last_updated.tzinfo is None:
                last_updated = last_updated.replace(tzinfo=UTC)
        except ValueError:
            last_updated = None

    return MacroSeriesExtended(
        series_id=series_id,
        title=str(info_dict.get("title") or series_id),
        units=str(info_dict.get("units")) if info_dict.get("units") else None,
        observations=observations,
        provider=PROVIDER,
        frequency=_coerce_freq(info_dict.get("frequency_short")),
        last_updated=last_updated,
        seasonal_adjustment=_coerce_seasonal(info_dict.get("seasonal_adjustment_short")),
        source_url=f"https://fred.stlouisfed.org/series/{series_id}",
        notes=str(info_dict.get("notes")) if info_dict.get("notes") else None,
    )


def search(query: str, limit: int = 25) -> list[MacroSearchResult]:
    """Search the FRED series catalog by free-text query.

    Returns up to ``limit`` matches; results are pre-ranked by FRED's own
    popularity score normalised to the 0–1 range.
    """
    if not query:
        return []
    client = _make_client()
    try:
        df = client.search(query, limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"FRED search failed for {query!r}: {exc}") from exc
    if df is None:
        return []

    results: list[MacroSearchResult] = []
    try:
        rows = df.to_dict(orient="records")
    except AttributeError:
        rows = []
    # FRED's popularity is 0–100 — normalise to 0–1.
    for row in rows:
        sid = row.get("id") or row.get("series_id")
        if not sid:
            continue
        try:
            score = float(row.get("popularity") or 0.0) / 100.0
        except (TypeError, ValueError):
            score = 0.0
        results.append(
            MacroSearchResult(
                provider=PROVIDER,
                series_id=str(sid),
                title=str(row.get("title") or sid),
                frequency=_coerce_freq(row.get("frequency_short")),
                units=str(row.get("units")) if row.get("units") else None,
                score=max(0.0, min(1.0, score)),
            )
        )
    return results


def catalog(limit: int = 25) -> MacroCatalog:
    """Return the FRED "featured" catalog (curated popular series)."""
    return MacroCatalog(provider=PROVIDER, entries=list(_FEATURED[:limit]))


__all__ = ["PROVIDER", "catalog", "get_series", "search"]
