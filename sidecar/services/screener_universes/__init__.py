"""Bundled universe snapshots for the v0.6.0 screener.

Each ``<universe>.json`` file is loaded at request time via
:mod:`importlib.resources` from :func:`services.screener.resolve_universe`.
``sp500.json`` and ``nifty50.json`` ship curated snapshots; ``crypto_top50.json``
is the offline seed for the cache-backed top-50 list.
"""

from __future__ import annotations

__all__: list[str] = []
