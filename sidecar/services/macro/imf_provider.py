"""IMF macro provider — in-process via ``sdmx1==2.26.0``.

The IMF publishes its statistics through an SDMX 2.1 REST endpoint
(https://sdmxcentral.imf.org/sdmxws/rest/) which the generic ``sdmx1``
client wraps under the ``IMF_DATA`` source id. IMF series ids are
slash-delimited SDMX keys like ``IFS/A.US.NGDP_R_K_IX`` (International
Financial Statistics, annual, US, Real GDP index).

Public surface (matches every other macro provider in this package):

  - :func:`get_series(series_id) -> MacroSeriesExtended`
  - :func:`search(query, limit) -> list[MacroSearchResult]`
  - :func:`catalog(limit) -> MacroCatalog`
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

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

# Default SDMX source. ``IMF_DATA`` is the newer SDMX 2.1 endpoint exposed by
# the IMF (Data API); ``IMF`` is the legacy v1 path which sdmx1 also supports.
_DEFAULT_SOURCE = "IMF_DATA"

# Curated featured catalog — the IFS / WEO / BOP series that cover Use Case 5's
# headline macro story (US GDP, inflation, current account, fiscal balance).
_FEATURED: list[MacroCatalogEntry] = [
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/A.US.NGDP_R_K_IX",
        title="Real GDP index, annual, United States",
        category="National Accounts",
        frequency="annual",
        units="Index 2010=100",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/Q.US.NGDP_R_K_IX",
        title="Real GDP index, quarterly, United States",
        category="National Accounts",
        frequency="quarterly",
        units="Index 2010=100",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/M.US.PCPI_IX",
        title="Consumer Price Index, monthly, United States",
        category="Prices",
        frequency="monthly",
        units="Index",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/A.US.NGDP_USD",
        title="Nominal GDP in USD, annual, United States",
        category="National Accounts",
        frequency="annual",
        units="USD (billions)",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/A.EU.NGDP_R_K_IX",
        title="Real GDP index, annual, Euro area",
        category="National Accounts",
        frequency="annual",
        units="Index 2010=100",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/A.JP.NGDP_R_K_IX",
        title="Real GDP index, annual, Japan",
        category="National Accounts",
        frequency="annual",
        units="Index 2010=100",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/A.CN.NGDP_R_K_IX",
        title="Real GDP index, annual, China",
        category="National Accounts",
        frequency="annual",
        units="Index 2010=100",
    ),
    MacroCatalogEntry(
        provider=PROVIDER,
        series_id="IFS/A.IN.NGDP_R_K_IX",
        title="Real GDP index, annual, India",
        category="National Accounts",
        frequency="annual",
        units="Index 2010=100",
    ),
]


def _make_client(source: str = _DEFAULT_SOURCE) -> Any:
    """Construct an ``sdmx1`` client. Isolated for test mockability."""
    try:
        import sdmx  # type: ignore[import-not-found]  # sdmx1 imports as ``sdmx``
    except ImportError as exc:  # pragma: no cover
        raise ProviderError(f"sdmx1 is not installed: {exc}") from exc
    return sdmx.Client(source)


def _parse_key(series_id: str) -> tuple[str, str]:
    """Split a series_id of shape ``<dataflow>/<key>`` into its two parts.

    Accepts:
      - ``IFS/A.US.NGDP_R_K_IX`` — explicit dataflow + dotted key
      - ``IFS.A.US.NGDP_R_K_IX`` — first dot is the dataflow boundary (legacy)
    """
    if "/" in series_id:
        head, tail = series_id.split("/", 1)
        return head.strip().upper(), tail.strip()
    # Legacy form: first dot is dataflow boundary
    if "." in series_id:
        head, tail = series_id.split(".", 1)
        return head.strip().upper(), tail.strip()
    raise ProviderError(
        f"IMF series_id {series_id!r} must be ``<dataflow>/<key>`` (e.g. ``IFS/A.US.NGDP_R_K_IX``)"
    )


def _parse_observations_from_sdmx(message: Any) -> list[MacroObservation]:
    """Walk an sdmx1 DataMessage and emit ``MacroObservation`` entries.

    The DataMessage carries one or more DataSets; each DataSet has Series;
    each Series has Observations. v0.6.0 flattens the first series found
    into the contract — IMF queries with a fully-specified key return
    exactly one series.
    """
    observations: list[MacroObservation] = []
    if message is None:
        return observations
    datasets = getattr(message, "data", []) or []
    if not datasets:
        return observations
    series_list = []
    for ds in datasets:
        # sdmx1 exposes .series as a dict or list depending on shape.
        try:
            ds_series = list(ds.series.values()) if hasattr(ds.series, "values") else list(ds.series)
        except (AttributeError, TypeError):
            ds_series = []
        series_list.extend(ds_series)
    if not series_list:
        return observations
    # Take the first series — for fully-specified keys this is the only one.
    first = series_list[0]
    obs_iter = getattr(first, "obs", None)
    if obs_iter is None:
        return observations
    try:
        items = list(obs_iter)
    except TypeError:
        return observations
    for obs in items:
        # sdmx1 Observation has .dimension (time period) and .value
        period = getattr(obs, "dim", None) or getattr(obs, "dimension", None)
        raw_value = getattr(obs, "value", None)
        if period is None:
            continue
        try:
            period_str = str(period)
            # Common IMF formats: YYYY, YYYY-MM, YYYY-Q1 / YYYY-Qn
            if "Q" in period_str.upper() and "-" in period_str:
                head, q = period_str.upper().split("-Q", 1)
                month = {"1": "01", "2": "04", "3": "07", "4": "10"}.get(q.strip(), "01")
                date = datetime.fromisoformat(f"{head}-{month}-01")
            elif len(period_str) == 4:
                date = datetime.fromisoformat(f"{period_str}-01-01")
            elif len(period_str) == 7:
                date = datetime.fromisoformat(f"{period_str}-01")
            else:
                date = datetime.fromisoformat(period_str)
        except ValueError:
            continue
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        value: float | None
        try:
            float_v = float(raw_value) if raw_value is not None else None
            value = None if float_v is None or float_v != float_v else float_v
        except (TypeError, ValueError):
            value = None
        observations.append(MacroObservation(date=date, value=value))
    return observations


def _imf_frequency(key_tail: str) -> str | None:
    """Derive frequency from the IMF key's first dimension (A / Q / M)."""
    first = key_tail.split(".", 1)[0].upper() if key_tail else ""
    return {"A": "annual", "Q": "quarterly", "M": "monthly", "D": "daily"}.get(first)


def get_series(series_id: str) -> MacroSeriesExtended:
    """Fetch an IMF time series by SDMX key (e.g. ``IFS/A.US.NGDP_R_K_IX``)."""
    if not series_id:
        raise ProviderError("IMF get_series requires a non-empty series_id")
    dataflow, key = _parse_key(series_id)
    client = _make_client()
    try:
        message = client.data(dataflow, key=key)
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"IMF upstream error for {series_id!r}: {exc}") from exc

    observations = _parse_observations_from_sdmx(message)

    return MacroSeriesExtended(
        series_id=series_id,
        title=series_id,
        units=None,
        observations=observations,
        provider=PROVIDER,
        frequency=_imf_frequency(key),
        last_updated=None,
        seasonal_adjustment=None,
        source_url="https://data.imf.org/",
        notes=f"Dataflow={dataflow}, key={key}",
    )


def search(query: str, limit: int = 25) -> list[MacroSearchResult]:
    """Best-effort search over the curated IMF featured catalog.

    Full SDMX agency-wide search via sdmx1 is too expensive for a synchronous
    UI call (every dataflow's keyfamily has to be fetched). v0.6.0 ships
    substring search over the curated featured set; a Phase-7 dataflow
    browse UI is the long-term path.
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
