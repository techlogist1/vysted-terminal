"""IMF macro provider — the IMF Data SDMX 3.0 REST API, keyless.

The IMF retired the SDMX 2.1 ``IFS`` dataflow (``api.imf.org`` answers 204/404
for every ``IFS/...`` key); its statistics now live in per-topic SDMX 3.0
dataflows (``CPI``, ``QNEA``, ``WEO``, ...) under
``https://api.imf.org/external/sdmx/3.0/``. Series ids are
``<dataflow>/<dotted key>``, e.g. ``CPI/USA.CPI._T.IX.M`` (CPI, all items,
index, monthly, United States); the last key dimension is the frequency.

Public surface (matches every other macro provider in this package):

  - :func:`get_series(series_id) -> MacroSeriesExtended`
  - :func:`search(query, limit) -> list[MacroSearchResult]`
  - :func:`catalog(limit) -> MacroCatalog`
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from models.macro_extended import (
    MacroCatalog,
    MacroCatalogEntry,
    MacroSearchResult,
    MacroSeriesExtended,
)
from models.market import MacroObservation
from services.errors import ProviderError

PROVIDER = "imf"

_log = logging.getLogger(__name__)

_DATA_URL = "https://api.imf.org/external/sdmx/3.0/data/dataflow/*/{dataflow}/+/{key}"
_ACCEPT = "application/vnd.sdmx.data+json;version=2.0.0"
_TIMEOUT_S = 20.0


def _entry(
    series_id: str, title: str, category: str, frequency: str, units: str
) -> MacroCatalogEntry:
    return MacroCatalogEntry(
        provider=PROVIDER,
        series_id=series_id,
        title=title,
        category=category,
        frequency=frequency,
        units=units,
    )


_NA = "National Accounts"
_GROWTH = "Percent change"

# Curated featured catalog. Every id was probed live (keyless, HTTP 200 with a
# populated series) against the SDMX 3.0 API on 2026-09-24. WEO annual rows
# run into the IMF's projection years.
_FEATURED: list[MacroCatalogEntry] = [
    _entry("WEO/USA.NGDP_RPCH.A", "Real GDP growth, annual, United States", _NA, "annual", _GROWTH),
    _entry(
        "QNEA/USA.B1GQ.Q.SA.XDC.Q",
        "Real GDP, quarterly, seasonally adjusted, United States",
        _NA,
        "quarterly",
        "National currency, constant prices",
    ),
    _entry(
        "CPI/USA.CPI._T.IX.M",
        "Consumer Price Index, monthly, United States",
        "Prices",
        "monthly",
        "Index",
    ),
    _entry("WEO/USA.NGDPD.A", "Nominal GDP in USD, annual, United States", _NA, "annual", "USD"),
    _entry("WEO/G163.NGDP_RPCH.A", "Real GDP growth, annual, Euro area", _NA, "annual", _GROWTH),
    _entry("WEO/JPN.NGDP_RPCH.A", "Real GDP growth, annual, Japan", _NA, "annual", _GROWTH),
    _entry("WEO/CHN.NGDP_RPCH.A", "Real GDP growth, annual, China", _NA, "annual", _GROWTH),
    _entry("WEO/IND.NGDP_RPCH.A", "Real GDP growth, annual, India", _NA, "annual", _GROWTH),
    _entry(
        "CPI/IND.CPI._T.IX.M", "Consumer Price Index, monthly, India", "Prices", "monthly", "Index"
    ),
    _entry(
        "WEO/IND.PCPIPCH.A",
        "Inflation, average consumer prices, annual, India",
        "Prices",
        "annual",
        _GROWTH,
    ),
]


def _fetch(dataflow: str, key: str) -> dict[str, Any]:
    """GET one SDMX-JSON 2.0 data message. Isolated for test mockability."""
    resp = httpx.get(
        _DATA_URL.format(dataflow=dataflow, key=key),
        headers={"Accept": _ACCEPT},
        timeout=_TIMEOUT_S,
    )
    resp.raise_for_status()
    return resp.json()


def _parse_key(series_id: str) -> tuple[str, str]:
    """Split a series_id of shape ``<dataflow>/<key>`` into its two parts.

    Accepts:
      - ``CPI/USA.CPI._T.IX.M`` — explicit dataflow + dotted key
      - ``CPI.USA.CPI._T.IX.M`` — first dot is the dataflow boundary (legacy)
    """
    if "/" in series_id:
        head, tail = series_id.split("/", 1)
        return head.strip().upper(), tail.strip()
    # Legacy form: first dot is dataflow boundary
    if "." in series_id:
        head, tail = series_id.split(".", 1)
        return head.strip().upper(), tail.strip()
    raise ProviderError(
        f"IMF series_id {series_id!r} must be ``<dataflow>/<key>`` (e.g. ``CPI/USA.CPI._T.IX.M``)"
    )


def _parse_period(period: str) -> datetime | None:
    """IMF SDMX 3.0 periods: ``2026``, ``2026-M06``, ``2026-Q2``, ``2026-06``."""
    p = period.strip().upper()
    try:
        if len(p) == 4:
            return datetime(int(p), 1, 1, tzinfo=UTC)
        year, rest = p.split("-", 1)
        if rest.startswith("Q"):
            return datetime(int(year), 3 * int(rest[1:]) - 2, 1, tzinfo=UTC)
        if rest.startswith("M"):
            return datetime(int(year), int(rest[1:]), 1, tzinfo=UTC)
        return datetime.fromisoformat(p).replace(tzinfo=UTC)
    except ValueError:
        return None


def _parse_observations(message: dict[str, Any]) -> list[MacroObservation]:
    """Flatten the first series of an SDMX-JSON 2.0 message (a fully specified
    key returns exactly one). An unknown key answers 200 with no series."""
    data = message.get("data") or {}
    datasets = data.get("dataSets") or []
    structures = data.get("structures") or []
    series = (datasets[0].get("series") or {}) if datasets else {}
    if not series or not structures:
        return []
    time_dims = structures[0].get("dimensions", {}).get("observation") or []
    periods = [v.get("value") or v.get("id") for v in time_dims[0].get("values", [])]
    first = next(iter(series.values()))
    observations: list[MacroObservation] = []
    for idx, obs in sorted((first.get("observations") or {}).items(), key=lambda kv: int(kv[0])):
        i = int(idx)
        date = _parse_period(str(periods[i])) if i < len(periods) else None
        if date is None:
            continue
        try:
            value: float | None = float(obs[0]) if obs and obs[0] is not None else None
        except (TypeError, ValueError):
            value = None
        if value is not None and value != value:
            value = None
        observations.append(MacroObservation(date=date, value=value))
    return observations


def _imf_frequency(key_tail: str) -> str | None:
    """Derive frequency from the key's last dimension (A / Q / M / D)."""
    last = key_tail.rsplit(".", 1)[-1].upper() if key_tail else ""
    return {"A": "annual", "Q": "quarterly", "M": "monthly", "D": "daily"}.get(last)


def get_series(series_id: str) -> MacroSeriesExtended:
    """Fetch an IMF time series by SDMX key (e.g. ``CPI/USA.CPI._T.IX.M``)."""
    if not series_id:
        raise ProviderError("IMF get_series requires a non-empty series_id")
    dataflow, key = _parse_key(series_id)
    try:
        message = _fetch(dataflow, key)
    except httpx.HTTPStatusError as exc:
        kind = "not_found" if exc.response.status_code in (204, 404) else None
        raise ProviderError(f"IMF upstream error for {series_id!r}: {exc}", kind=kind) from exc
    except httpx.TransportError as exc:
        raise ProviderError(f"IMF upstream error for {series_id!r}: {exc}", kind="network") from exc
    except ValueError as exc:  # a non-JSON body
        raise ProviderError(f"IMF upstream error for {series_id!r}: {exc}") from exc

    observations = _parse_observations(message)
    if not observations:
        raise ProviderError(f"IMF has no data for {series_id!r}", kind="not_found")

    featured = next((e for e in _FEATURED if e.series_id == series_id), None)
    return MacroSeriesExtended(
        series_id=series_id,
        title=featured.title if featured else series_id,
        units=featured.units if featured else None,
        observations=observations,
        provider=PROVIDER,
        frequency=_imf_frequency(key),
        last_updated=None,
        seasonal_adjustment=None,
        source_url="https://data.imf.org/",
        notes=f"Dataflow={dataflow}, key={key}",
    )


def search(query: str, limit: int = 25) -> list[MacroSearchResult]:
    """Substring search over the curated IMF featured catalog.

    A full agency-wide SDMX search is too expensive for a synchronous UI call
    (every dataflow's structure has to be fetched), so search covers the
    curated featured set.
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
    """Return the curated IMF catalog."""
    return MacroCatalog(provider=PROVIDER, entries=list(_FEATURED[:limit]))


__all__ = ["PROVIDER", "catalog", "get_series", "search"]
