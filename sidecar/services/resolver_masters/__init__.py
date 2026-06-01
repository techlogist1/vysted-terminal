"""Bundled instrument masters for the symbol resolver (Pass B / B1).

``us_instruments.json`` (SEC ``company_tickers.json`` snapshot — ticker + name)
and ``nse_instruments.json`` (NSE ``EQUITY_L`` + ETF list — symbol, name, type)
are read at runtime via :mod:`importlib.resources`. Bundled (not fetched live)
so resolution is deterministic, offline-first, and test-stable; PyInstaller
ships them via an ``--add-data`` entry in ``scripts/ensure-sidecar.mjs``
(mirroring ``services.screener_universes``).
"""
