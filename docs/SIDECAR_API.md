# Sidecar API

The Python sidecar (`sidecar/`) is a FastAPI service on localhost that serves the
data layer. The Tauri core spawns it on a free port at launch and resolves the
per-OS application data directory for it; the frontend reaches it over HTTP and
WebSocket.

This document is the contract. It is updated in the same commit as any sidecar
API change.

## Connecting

- **Port** — assigned by the Tauri core and exposed to the frontend via the
  `get_sidecar_port` Tauri command. `src/lib/sidecar-client.ts` wraps this:
  `getSidecarBaseUrl()` returns `http://127.0.0.1:<port>` (cached).
- **CORS** — the sidecar allows all origins. It binds to `127.0.0.1` only, so a
  permissive policy is safe; it avoids a `tauri-plugin-http` dependency and lets
  the WebView use plain `fetch`.
- **Data directory** — the Tauri core passes `--data-dir <path>` (the per-OS app
  data dir). The sidecar owns the portfolio SQLite database and saved
  `.vysted-workspace` files beneath it. See `sidecar/config.py`.
- **Errors** — provider failures return HTTP `502` with `{"detail": "..."}`.
  `sidecarGet` throws `SidecarError` (carrying `status` + message).

## Providers

| Data class                                                    | Provider                                    | Notes                                    |
| ------------------------------------------------------------- | ------------------------------------------- | ---------------------------------------- |
| Equity quotes / history / fundamentals / statements / ratings | **yfinance**                                | No API key required — the default.       |
| Crypto quotes / history / live stream                         | **ccxt** (Bybit, Binance, Kraken, Coinbase) | ccxt.pro WebSockets for the live stream. |
| Macro / economic series                                       | —                                           | Hook only in Phase 1 (501).              |

### OpenBB ODP — deferred to Phase 2

Phase 1.A ships yfinance + ccxt as the working providers. The OpenBB Platform
(`openbb`) is **not** in `requirements.txt` this phase. Rationale (a Tier-3
decision — see `CLAUDE.md` "Decision authority"):

- The sidecar is a PyInstaller `--onefile` binary. The OpenBB meta-package is a
  very large dependency tree whose `--onefile` bundling cannot be vetted against
  the macOS CI runner locally — a real run-consuming risk.
- The blueprint already schedules an **"OpenBB ODP wrap plugin"** for Phase 2 as
  a data-only plugin. Building it there, on the plugin contract, is cleaner than
  baking it into the core sidecar now and re-extracting it later.
- `services/provider_registry.py` is provider-agnostic and
  `services/openbb_provider.py` is an import-guarded seam — OpenBB slots in later
  with no router or panel changes.

yfinance covers equity quotes, history, fundamentals, the three financial
statements, and analyst ratings; ccxt covers crypto. Together they serve every
Phase 1 panel. Macro data and deeper fundamentals coverage arrive in Phase 2.

## REST endpoints

### Health

- `GET /health` → `{ status, service, version, providers }` — liveness probe;
  `providers` reports which provider currently backs each data class.

### Quotes — `Quote`

- `GET /quotes/{symbol}?asset_class=equity|crypto` → `Quote`
- `GET /quotes?symbols=AAPL,MSFT,NVDA&asset_class=equity` → `Quote[]` — batch for
  the watchlist; a symbol that fails to resolve is skipped, not fatal.

### History — `OHLCVSeries`

- `GET /history/{symbol}?timeframe=1d&range=1y&asset_class=equity` → `OHLCVSeries`
  - `timeframe`: `1m`, `5m`, `15m`, `30m`, `1h`, `1d`, `1wk`, `1mo`
  - `range`: optional provider lookback override (e.g. `5d`, `1y`, `max`)

### Crypto

- `GET /crypto/exchanges` → `{ exchanges: string[] }`
- `GET /crypto/ticker?exchange=binance&symbol=BTC/USDT` → `Quote`
- `GET /crypto/history?exchange=binance&symbol=BTC/USDT&timeframe=1d` → `OHLCVSeries`

### Fundamentals

- `GET /fundamentals/{symbol}` → `Fundamentals`
- `GET /fundamentals/{symbol}/income` → `IncomeStatement`
- `GET /fundamentals/{symbol}/balance` → `BalanceSheet`
- `GET /fundamentals/{symbol}/cashflow` → `CashFlowStatement`
- `GET /fundamentals/{symbol}/ratings` → `AnalystRating`

### Macro — hook

- `GET /macro/{series_id}` → `501` until the Phase 2 OpenBB ODP wrap. The
  `MacroSeries` contract is defined and ready.

## WebSocket endpoints

- `WS /crypto/stream?exchange=binance&symbol=BTC/USDT` — pushes a JSON-serialised
  `Quote` on every ticker update. `openCryptoStream()` in `sidecar-client.ts`
  opens it; the caller owns the socket. The ccxt.pro exchange is always closed on
  disconnect.

## Stub routers — owned by Phase 1.B teammates

These are mounted but return a stub `_status` payload until the owning teammate
fills them in. A teammate edits only their own router file — `app.py` already
mounts all ten.

| Prefix        | Owner      | Scope                                                |
| ------------- | ---------- | ---------------------------------------------------- |
| `/indicators` | Teammate A | Technical-indicator computation for the chart panel. |
| `/portfolio`  | Teammate B | Positions CRUD backed by SQLite under the data dir.  |
| `/news`       | Teammate C | RSS + NewsAPI fetch + lexicon sentiment scoring.     |
| `/workspace`  | Teammate D | Save/list/load/delete `.vysted-workspace` files.     |

## Models & the TypeScript contract

Pydantic models live in `sidecar/models/`. `types/data.ts` is a **hand-maintained
TypeScript mirror** of them. When a Pydantic model changes, update the matching
interface in `types/data.ts` in the same commit. Datetimes cross the wire as
ISO-8601 strings (typed `string` in TypeScript).

Models: `Quote`, `OHLCVBar`, `OHLCVSeries`, `MacroObservation`, `MacroSeries`,
`Fundamentals`, `StatementLine`, `FinancialStatement`, `IncomeStatement`,
`BalanceSheet`, `CashFlowStatement`, `AnalystRating`, `NewsItem`, `Position`,
`PositionInput`.

## Testing

`sidecar/tests/` — every provider is mocked (`tests/conftest.py`); no test makes
a live network call. Run from `sidecar/`: `pytest`.
