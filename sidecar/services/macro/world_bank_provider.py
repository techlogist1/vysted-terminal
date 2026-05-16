"""World Bank macro provider — in-process via ``wbgapi==1.0.14``.

``wbgapi`` is the World Bank Group's official Python client over their
Indicators API. Indicators are addressed by code like ``NY.GDP.PCAP.CD``
(GDP per capita, current USD). Per-country queries identify a country by
its ISO-3 code.

Series id format used by this provider:

  - ``NY.GDP.PCAP.CD`` — defaults to ``USA``.
  - ``NY.GDP.PCAP.CD:DEU`` — explicit country code (legacy colon form).
  - ``WB:NY.GDP.PCAP.CD:DEU`` — fully-qualified per spec; the leading
    ``WB:`` is stripped.

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

PROVIDER = "world-bank"

_log = logging.getLogger(__name__)

_DEFAULT_COUNTRY = "USA"

# Curated featured catalog — the World Bank WDI indicators that cover Use
# Case 5's headline national-development surface. The full WB catalog has
# 16,000+ indicators; full browsing is a Phase-7 candidate.
_FEATURED: list[MacroCatalogEntry] = [
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="NY.GDP.PCAP.CD",
        title="GDP per capita (current USD)",
        category="National Accounts",
        frequency="annual",
        units="USD",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="NY.GDP.MKTP.CD",
        title="GDP (current USD)",
        category="National Accounts",
        frequency="annual",
        units="USD",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="NY.GDP.MKTP.KD.ZG",
        title="GDP growth (annual %)",
        category="National Accounts",
        frequency="annual",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="FP.CPI.TOTL.ZG",
        title="Inflation, consumer prices (annual %)",
        category="Prices",
        frequency="annual",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="SL.UEM.TOTL.ZS",
        title="Unemployment, total (% of labour force)",
        category="Labour",
        frequency="annual",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="SP.POP.TOTL",
        title="Population, total",
        category="Demographics",
        frequency="annual",
        units="People",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="NE.EXP.GNFS.ZS",
        title="Exports of goods and services (% of GDP)",
        category="Trade",
        frequency="annual",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="GC.DOD.TOTL.GD.ZS",
        title="Central government debt, total (% of GDP)",
        category="Fiscal",
        frequency="annual",
        units="Percent",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="EN.ATM.CO2E.PC",
        title="CO2 emissions (metric tons per capita)",
        category="Environment",
        frequency="annual",
        units="Tons per capita",
    ),
]


def _make_client() -> Any:
    """Construct the ``wbgapi`` module. Isolated for test mockability."""
    try:
        import wbgapi  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise ProviderError(f"wbgapi is not installed: {exc}") from exc
    return wbgapi


def _parse_series_id(series_id: str) -> tuple[str, str]:
    """Return (indicator, country) from one of the supported series_id forms."""
    raw = series_id.strip()
    if raw.upper().startswith("WB:"):
        raw = raw[3:]
    if ":" in raw:
        head, country = raw.split(":", 1)
        return head.strip(), country.strip().upper() or _DEFAULT_COUNTRY
    return raw, _DEFAULT_COUNTRY


def get_series(series_id: str) -> MacroSeriesExtended:
    """Fetch a World Bank indicator series for one country.

    ``series_id`` accepts ``<indicator>``, ``<indicator>:<ISO3>`` or
    ``WB:<indicator>:<ISO3>``. Defaults to ``USA``.
    """
    if not series_id:
        raise ProviderError("World Bank get_series requires a non-empty series_id")
    indicator, country = _parse_series_id(series_id)
    client = _make_client()
    try:
        # wbgapi.data.fetch yields per-year observation rows.
        rows = list(client.data.fetch(indicator, country))
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(
            f"World Bank upstream error for {indicator!r}/{country!r}: {exc}"
        ) from exc

    observations: list[MacroObservation] = []
    for row in rows:
        # row shape: ``{'economy': ..., 'series': ..., 'time': 'YR2023', 'value': ...}``
        if isinstance(row, dict):
            time_raw = row.get("time")
            value_raw = row.get("value")
        else:
            time_raw = getattr(row, "time", None)
            value_raw = getattr(row, "value", None)
        if time_raw is None:
            continue
        time_str = str(time_raw)
        if time_str.startswith("YR"):
            time_str = time_str[2:]
        try:
            date = datetime.fromisoformat(f"{time_str}-01-01")
        except ValueError:
            continue
        if date.tzinfo is None:
            date = date.replace(tzinfo=UTC)
        value: float | None
        try:
            float_v = float(value_raw) if value_raw is not None else None
            value = None if float_v is None or float_v != float_v else float_v
        except (TypeError, ValueError):
            value = None
        observations.append(MacroObservation(date=date, value=value))

    # Sort by date — wbgapi may return newest-first; the chart wants
    # chronological order.
    observations.sort(key=lambda o: o.date)

    title = indicator
    try:
        # series.info returns an InfoStream; .table() / .items() may be available.
        info = client.series.info(indicator)
        if hasattr(info, "items") and callable(info.items):
            items = list(info.items)
            if items:
                first = items[0]
                # InfoRow shape: (id, name, ...). Prefer name when populated.
                title = getattr(first, "value", indicator) or indicator
    except Exception as exc:  # noqa: BLE001 — title fallback is benign
        _log.debug("wbgapi.series.info failed for %s: %s", indicator, exc)

    return MacroSeriesExtended(
        series_id=series_id,
        title=f"{title} — {country}",
        units=None,
        observations=observations,
        provider=PROVIDER,
        frequency="annual",
        last_updated=None,
        seasonal_adjustment=None,
        source_url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}",
        notes=f"Indicator={indicator}, country={country}",
    )


def search(query: str, limit: int = 25) -> list[MacroSearchResult]:
    """Best-effort indicator search via wbgapi + curated featured set.

    ``wbgapi.series.list(q=query)`` returns matching indicators; we map them
    through the contract. When the upstream call fails (network, etc.) we
    fall back to substring-search over the curated featured catalog.
    """
    if not query:
        return []
    try:
        client = _make_client()
        rows = list(client.series.list(q=query))
    except Exception as exc:  # noqa: BLE001 — fall back, not fatal
        _log.debug("wbgapi.series.list fall back to curated set: %s", exc)
        rows = []

    matches: list[MacroSearchResult] = []
    seen: set[str] = set()
    for row in rows[:limit]:
        sid = row.get("id") if isinstance(row, dict) else getattr(row, "id", None)
        title = row.get("value") if isinstance(row, dict) else getattr(row, "value", None)
        if not sid or sid in seen:
            continue
        seen.add(sid)
        matches.append(
            MacroSearchResult(
                provider=PROVIDER,
                series_id=str(sid),
                title=str(title or sid),
                frequency="annual",
                units=None,
                score=0.75,
            )
        )

    if not matches:
        q = query.lower()
        for entry in _FEATURED:
            title_l = entry.title.lower()
            if q in title_l or q in entry.series_id.lower():
                matches.append(
                    MacroSearchResult(
                        provider=PROVIDER,
                        series_id=entry.series_id,
                        title=entry.title,
                        frequency=entry.frequency,
                        units=entry.units,
                        score=0.5,
                    )
                )

    return matches[:limit]


def catalog(limit: int = 25) -> MacroCatalog:
    """Return the curated World Bank catalog."""
    return MacroCatalog(provider=PROVIDER, entries=list(_FEATURED[:limit]))


__all__ = ["PROVIDER", "catalog", "get_series", "search"]
