# R7 Track D — integration notes for the lead

Append-only notes from the data track (worktree-agent-r7-data). Each entry
states what the lead must wire (or verify needs no wiring) when merging.

## Component 2 — NSE exchange-direct provider (`services/nse_provider.py`)

- **No router registration needed.** The provider self-registers through the
  `provider_registry._PROVIDERS` declaration table (`nse_direct`, rank 15, IN
  equity, quote + ohlcv). `/health` picks it up automatically via
  `active_providers()` — expect `quote`/`ohlcv` to now read
  `ccxt (nse_direct, nse, bse, yfinance fallback)`.
- **No `app.py` / `services/config.py` change.** Nothing in this component
  touches another track's files.
- **IN preference order is now** `nse_direct (15) → nse/jugaad (20) → bse (25)
→ yfinance (50)`. Any block/throttle/circuit-open on the direct lane falls
  through to jugaad transparently; yfinance stays the gated last resort for IN
  and the US spine.
- **`types/data.ts` unchanged** — the provider emits the existing
  `Quote`/`OHLCVSeries` models; no new model was added in this component.
- **Component 3 consumers:** `get_corporate_announcements` /
  `get_results_calendar` / `get_shareholding_master` return the RAW observed
  list shapes (fixtures under `sidecar/tests/fixtures/nse/`) for
  `services/corporate_disclosures.py` to model.
- **Deliberate deviation from the brief's `AsyncSession`:** the registry's
  quote/ohlcv seam is synchronous (every provider it drives is sync; callers
  wrap in `asyncio.to_thread`), so the cookie-dance session uses curl_cffi's
  sync `Session(impersonate="chrome")` guarded by a module lock — identical
  anti-bot surface, no event-loop friction in worker threads (Tier-2,
  spec-derivable from the registry contract).
- **Live caveat (observed 2026-06-10):** `api/quote-equity` is Akamai
  path-ACL'd from at least some vantages while every other API path serves on
  the same session. `get_quote` handles this: blocked → rotate → per-path
  breaker → EOD quote derived from `historicalOR` (worked live). Do not treat
  a quote-equity 403 in logs as a provider bug.
- `scripts/smoke-test-sidecars.mjs` gained `_probeNseDirectNoSla()` (warn-only,
  never fails the run) — it shells to the sidecar venv python because Node's
  fetch has the wrong TLS fingerprint for NSE's edge.
