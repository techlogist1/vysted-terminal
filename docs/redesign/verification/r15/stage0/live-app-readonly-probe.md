# Read-only probe of the operator's live dev stack (up since 13 Sep 20:01) — 2026-09-19 06:24 IST

## GET /health
```json
{
    "status": "ok",
    "service": "vysted-sidecar",
    "version": "0.8.0",
    "providers": {
        "analyst_rating": "openbb-mcp (yfinance fallback)",
        "balance_sheet": "openbb-mcp (yfinance fallback)",
        "cash_flow": "openbb-mcp (yfinance fallback)",
        "fundamentals": "openbb-mcp (yfinance fallback)",
        "income_statement": "openbb-mcp (yfinance fallback)",
        "macro_series": "openbb-mcp",
        "ohlcv": "ccxt (nse_direct, nse, bse, yfinance fallback)",
        "quote": "ccxt (nse_direct, nse, bse, yfinance fallback)",
        "openbb-mcp": "available"
    }
}
```
## GET /search/status
```json
{
    "tier": "t1_keyless",
    "available": true,
    "engines": [
        {
            "id": "ddg",
            "label": "DuckDuckGo",
            "state": "closed",
            "cooldown_remaining_s": 0.0,
            "min_interval_s": 3.0,
            "detail": "DuckDuckGo available"
        },
        {
            "id": "brave",
            "label": "Brave",
            "state": "closed",
            "cooldown_remaining_s": 0.0,
            "min_interval_s": 2.0,
            "detail": "Brave available"
        },
        {
            "id": "mojeek",
            "label": "Mojeek",
            "state": "closed",
            "cooldown_remaining_s": 0.0,
            "min_interval_s": 2.0,
            "detail": "Mojeek available"
        }
    ]
}
```
## GET /search/searxng/status
```json
{
    "state": "not_installed_docker",
    "detail": "docker CLI found but the daemon is not running \u2014 start Docker/OrbStack",
    "reason": null,
    "port": null,
    "url": null,
    "container": null,
    "container_name": "vysted-searxng",
    "image": "searxng/searxng",
    "docker": {
        "cli_present": true,
        "daemon_running": false,
        "runtime": null
    }
}
```
## GET /mcp/status
```json
{
    "ready": true,
    "toolCount": 36,
    "endpoint": "/mcp",
    "protocolVersion": "2025-06-18"
}
```
## GET /openbb-mcp/status
```json
{
    "available": true,
    "provider": "openbb-mcp",
    "endpoint": "http://127.0.0.1:52053/mcp",
    "lastToolCallOk": false,
    "lastError": "ClosedResourceError: "
}
```
## GET /sec/status
```json
{
    "available": true,
    "provider": "sec-edgar-mcp",
    "endpoint": "http://127.0.0.1:52054/mcp",
    "lastToolCallOk": true,
    "lastError": null
}
```
## GET /system/provider-health
```json
{
    "yahoo": {
        "open": false,
        "cooldown_remaining": 0.0,
        "consecutive_throttles": 0.0,
        "consecutive_opens": 0,
        "opens_total": 954,
        "throttles_total": 28382.0
    }
}
```
## GET /system/ollama/status
```json
{
    "running": false,
    "endpoint": "http://127.0.0.1:11434",
    "models": []
}
```
