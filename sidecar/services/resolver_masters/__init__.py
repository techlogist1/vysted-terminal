"""Bundled instrument masters for the symbol resolver (Pass B / B1).

``us_instruments.json`` (SEC ``company_tickers.json`` snapshot — ticker + name),
``nse_instruments.json`` (NSE ``EQUITY_L`` + Emerge + ETF lists — symbol, name,
type EQ/SM/ETF; ``regenerate_nse_master.py``), and
``bse_instruments.json`` (BSE scrip list — scrip-code, symbol, name, group, ISIN;
the micro-cap tail in groups B/X/XT/T/Z) are read at runtime via
:mod:`importlib.resources`. Bundled (not fetched live) so resolution is
deterministic, offline-first, and test-stable; PyInstaller ships them via an
``--add-data`` entry in ``scripts/ensure-sidecar.mjs`` (mirroring
``services.screener_universes``). ``regenerate_bse_master.py`` refreshes the BSE
snapshot from the live BSE endpoint. The resolver also refreshes both exchange
masters daily at runtime into the data dir and unions them with these files.

``india_sector_map.json`` (R10, D40) rides the same package: the build-time
India sector / shares_outstanding seed for the screener's fundamentals store
(``regenerate_india_sectors.py`` refreshes it; the header's ``coverage``
block is the honest census of how much of the market it classifies).
"""
