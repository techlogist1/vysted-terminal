"""Data-provider services for the Vysted Terminal sidecar.

Routers call :mod:`services.provider_registry`, which dispatches to the concrete
providers (:mod:`services.yfinance_provider`, :mod:`services.ccxt_provider`, and
the import-guarded :mod:`services.openbb_provider`).
"""
