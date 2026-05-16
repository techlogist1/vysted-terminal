"""Macro data providers — Phase 6 (Teammate M).

Four provider modules, each exposing the same three-call public surface so the
router dispatch is a flat lookup:

  - :func:`get_series(series_id) -> MacroSeriesExtended`
  - :func:`search(query, limit) -> list[MacroSearchResult]`
  - :func:`catalog(limit) -> MacroCatalog`

The providers are kept independent (no shared base class) because each
upstream's SDK is shaped differently — `fredapi` is sync, `ecbdata` is sync,
`sdmx1` is sync over `requests`, `wbgapi` is sync over `requests`. Wrapping
each in `asyncio.to_thread` at the router seam keeps the FastAPI event loop
free without imposing a contract the SDKs do not natively support.

The router (:mod:`services.macro.macro_router`) is the only public entry
point — it dispatches on the :data:`MacroProvider` literal and threads the
``data_cache`` reads-on-write seam through.
"""

from __future__ import annotations

from services.macro.macro_router import (
    get_catalog,
    get_series,
    search,
)

__all__ = ["get_catalog", "get_series", "search"]
