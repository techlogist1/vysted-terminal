# rc1 gate round 4 — adversarial sample verifier, shard 2 (rc1-vshard-2)

Candidate sha: `68d5573aff9a579af084dcbb124843f2aecff6e8` (read-only worktree `rc1-round-4-1006c6d-fix-int`, HEAD checked).
Live probes ran against this shard's own sidecar on `:52602` (booted from the worktree source, a scratch copy of the seed data dir). Frontend probes ran with vitest on a read-only rsync copy of the worktree `src/`. In-process probes ran from the worktree `sidecar/` with `PYTHONDONTWRITEBYTECODE=1`, so nothing was written into it. The shared stack was not touched. No Ollama calls were made.

Upstream condition: throughout the run Yahoo v7 quote/getcrumb returned 429 (shared IP). No verdict below depends on a Yahoo 5xx or on a lock timeout.

Raw output for each id is in `verifier/shard-2-raw/<ID>.txt`. Findings are in `findings/rc1-vshard-2.json`.

**Tally: 14 hold, 6 refuted.** Five of the six fail certification because a fix_shape clause is unfixed; LEAD-014 is refuted outright. Three adjacent low defects are listed at the end.

| id | verdict | own repro | fresh variant | basis |
|---|---|---|---|---|
| R15-DATA-063 | **refuted (not certified)** | fixed: `/indicators/HDFC.NS` returns 200 with provider `none` (it used to 502) | — | fix_shape "carry the typed freshness/reason" is unfixed. The IndicatorResponse keys are `symbol, timeframe, provider, indicators, volume_profile` with no freshness field, while `/history/TCS` carries `freshness: eod`. |
| R15-DATA-015 | **refuted (not certified)** | fixed: ELCIDIN is flagged on both bounds against the NSE+BSE range, and AMAL is flagged | JNPR (listed 2026-08-06, 36 bars) serves hi 282 / lo 232.11 with status **ok** and label null | fix_shape "history shorter than 52 weeks → label since <date>" is unfixed. The BSE API outside check was blocked (Akamai), so the verdict rests on the served history span. |
| R15-DATA-037 | holds | 1d range 1mo/1y/5y → 30/365/1826 bars (BTC, ETH, SOL) | 1h → 720/8760/10000 | adjacent: the 1h/5y 10,000-bar clamp is served with `partial=false` |
| R15-RESEARCH-014 | holds | a stub `length` finish adds SYNTHESIS_TRUNCATED_NOTE | the Gemini enum `FinishReason.MAX_TOKENS` is also flagged; `STOP` is not | |
| R15-AGENT-025 | holds | pins in `test_b5_runtime_liveness.py` plus code: 180 s client idle timeout, 10 s heartbeat, `provider_idle` frame, 20 s planner timeout, STREAM_STALLED watchdog in `streaming.ts` | real-socket stub through OpenAIProvider: a keep-alive comment trickle (bytes flow, so no httpx timeout) and a mid-stream stall **both** end with `provider_idle` at the idle budget after heartbeats | planner timeout is 20 s, not the 15 s in fix_shape; it is bounded either way |
| R15-AGENT-048 | holds | a hanging repair oneshot is bounded: 2 repairs, 60.2 s, 5/5 sentinels | a replying repair meters usage `[(100,7),(100,7)]` into done | |
| R15-CODE-PLATFORM-019 | holds | C and D started at 0.1–0.3 s while A ran to 4.0 s (no wave barrier) | a hung node with `timeout_seconds: 1.5` errors "node timed out after 1.5s"; its dependant fails as upstream-failed | |
| R15-CODE-PLATFORM-005 | holds | live: 450 concurrent mixed BS/greeks/binomial pricings, all stable | in-process: 2 threads (euro BS 2026 ×1500, american binomial 2030 ×300), both stable | |
| R15-CODE-AGENT-012 | holds | live MCP tools/list (40 tools): invoke_agent schema is `{agent_id, prompt}` | no tool has a secret-shaped parameter | |
| R15-CODE-DATA-006 | holds | superseded run A's late result leaves run B's state untouched | — | adjacent: a formula pre-flight rejection is overwritten by A's late result |
| R15-LIFECYCLE-017 | holds | a ValueError from get_fundamentals logs 7 WARNINGs and progress (7,7) | — | adjacent: an `upsert_info` error escapes the per-symbol try |
| R15-LIFECYCLE-020 | **refuted (not certified)** | fixed: no boot sweep; warming starts lazily on the region default (nifty50) | live: after POST /screener/run nifty50, a warm cycle hit 429 and the shared yahoo circuit throttles went 236→238 | fix_shape clause "keep background warming from opening the circuit user requests share" is unfixed (`yahoo_batch_provider.py:322` records into `provider_health.YAHOO`) |
| R15-DATA-017 | holds | JNPR, DHOOTTRANS, SUMAX: all 9 disclosures routes return 200; `/quotes/SUMAX` returns 200; legal-name autocomplete returns the right entity (SUMAX → SUMAX-SM.NS) | AXIOMGAS (SM) and AGASTYAEN appear only in the runtime-refreshed master (2026-09-26), not in the bundled one; both work for quotes, announcements and autocomplete | |
| R15-LEAD-014 | **refuted** | full, fenced and properties-only schema echoes are rejected (0 accepted) | a placeholder echo `{prop: "<type-name>"}` is **accepted for 20 of 54 tools** (e.g. fundamentals `{"symbol":"string"}`) | the fix_shape itself names this placeholder form as an echo |
| R15-AGENT-051 | holds | 3 charts with the third focused → "Focused chart: INFY.NS" | equity-overview focused → "Chart: SPY", "Focused panel", deixis on RELIANCE.NS | |
| R15-CODE-FRONTEND-015 | **refuted (not certified)** | — | Earnings Calendar publishes under `earnings`, but its dockview id is `earnings-calendar`; Screener publishes under `screener` with id `screener-panel` | the "single key convention" clause is unfixed; a focused Earnings Calendar resolves to the chart symbol |
| R15-UI-021 | **refuted** | — | two charts, each with a selected drawing; click a non-focusable spot; one Backspace on `document.body` → **both** charts lose their drawing | the `document.body` exemption (4c9f7516) leaves the global delete scope; selection persists |
| R15-RESEARCH-016 | holds | pin `test_ultra_cites_the_preseeded_filings_floor` plus the guard split at `iter.py:379-393` | ULTRA with 3 angles gives the same sources as DEEP, the floor row appears once, no duplicates | |
| R15-CODE-RESEARCH-002 | holds | sync-raise, async-raise and hanging gates/fetchers are each dropped with an error step | all 3 legs returned | |
| R15-RESEARCH-017 | holds | an injected resolve_target KeyError gives an honest `ok:false` at ultra (heavy) and deep (iter) | — | the fix_shape's single-pass fallback was superseded by R15-CODE-RESEARCH-003 (9703eee7) |

## Adjacent defects (new, low)
1. **near R15-DATA-037.** `ccxt_provider._since_ms` clamps a 1h/5y range to `_MAX_BARS=10_000`, so it starts 2025-08-06, but the response says `partial=false, coverage_start=null`. The chart claims 5y coverage when it has about 14 months.
2. **near R15-CODE-DATA-006.** In `src/store/screener.ts:383-391` the formula pre-flight returns before `_runAbortController?.abort()`. An in-flight run A therefore stays current, and its late `finish()` overwrites the formula error with `status: ready` and the OLD criteria's result.
3. **near R15-LIFECYCLE-017.** `await fundamentals_store.upsert_info(key, rich)` (`screener.py:1094`) sits outside the per-symbol try. A store error escapes `_enrich_survivors` and aborts phase E instead of being logged per symbol.
