"""Bundled instrument masters for the symbol resolver (Pass B / B1).

``us_instruments.json`` (SEC ``company_tickers.json`` snapshot — ticker + name),
``nse_instruments.json`` (NSE ``EQUITY_L`` + ETF list — symbol, name, type), and
``bse_instruments.json`` (BSE scrip list — scrip-code, symbol, name, group, ISIN;
the micro-cap tail in groups B/X/XT/T/Z) are read at runtime via
:mod:`importlib.resources`. Bundled (not fetched live) so resolution is
deterministic, offline-first, and test-stable; PyInstaller ships them via an
``--add-data`` entry in ``scripts/ensure-sidecar.mjs`` (mirroring
``services.screener_universes``). The BSE master is a representative seed —
``regenerate_bse_master.py`` refreshes the full snapshot from the live BSE
endpoint, mirroring how the NSE master is produced.
"""
