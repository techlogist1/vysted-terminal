# Phase 8 — Performance Baseline

**Captured:** 2026-05-18 against the v0.7.0+housekeeping tip `005a8d0` plus
the Phase 8 lead-foundation commits. Operator's Windows 11 machine; Tauri
dev mode (not release); main sidecar `vysted-sidecar.exe` 99 MB
PyInstaller `--onefile` binary built 2026-05-17.

**Purpose:** Phase 9 (operator manual Mac test) + Phase 10 (launch ops) can
re-run these measurements identically to detect regressions. Methodology
captured so any future operator can reproduce.

---

## Methodology

- Hardware: operator's primary Windows 11 dev machine. CPU/RAM/GPU class
  not enumerated here (Phase 9 should add hardware fingerprint).
- Tauri dev mode via `pnpm tauri dev` (NOT `pnpm tauri build` + run
  release bundle — release will be faster).
- 5-panel + AI Assistant cockpit was the active workspace.
- Sidecar bound to a fresh `mkdtemp` data-dir (cold DB).
- Each measurement: 1–100 samples per the section below; median + min +
  max + p95 + p99 reported where multi-sample.
- Tools: `curl -w "%{time_total}\n"` for HTTP round-trips; PowerShell
  `Get-Process` / `Get-NetTCPConnection` for process state; `time` for
  one-shot wall-clock.

---

## Cold-start to first interactive panel

**Source:** `tauri-dev.log` lines 1-220.

| Phase                                       | Wall-time         |
| ------------------------------------------- | ----------------- |
| `node scripts/ensure-all-sidecars.mjs`      | ~3 s              |
| `pnpm dev` → Next.js Ready                  | **0.4 s** (Turbopack) |
| Cargo download crates                       | ~6 s (8 crates, 610 KiB) |
| Cargo compile (Rust core, dev profile)      | **~1 min 25 s**   |
| Tauri shell launch + sidecar spawn          | ~2 s              |
| Sidecar boot + Uvicorn ready                | ~3 s              |
| First `/health` 200 from frontend           | ~1 s              |
| **Total cold-start**                        | **~95 s**         |

**Warm-start (cargo cache hot):** roughly 8–10 s (Rust deps cached, only
the local `vysted-terminal` crate recompiles if source-changed). Specific
warm-start sampling deferred (this run was cold; subsequent same-session
restarts would warm).

**Subprocess spawn:**
- `[openbb-mcp] subprocess spawned on 127.0.0.1:54109` — reported but
  subprocess does NOT actually listen on that port (see BUG_CATALOG
  finding UC1-openbb-mcp-not-listening).
- `[sec-edgar-mcp] subprocess spawned on 127.0.0.1:54111` — same
  port-binding gap.

---

## Sidecar `/health` round-trip latency (100 samples)

**Command:**
```bash
for i in $(seq 1 100); do
  curl -sS -o /dev/null -w "%{time_total}\n" http://127.0.0.1:54108/health
done | sort -n
```

| Stat | Value      |
| ---- | ---------- |
| min  | **1.5 ms** |
| p50  | **5.3 ms** |
| p95  | **228 ms** |
| p99  | **486 ms** |
| max  | 527 ms     |
| mean | 40 ms      |

**Anomaly:** p95 = 45× p50, p99 = 92× p50. This tail latency on a route
that just reads memory state (`active_providers()` returns a dict that
doesn't touch the DB) suggests **GIL contention** with the polling load
from the Tauri webview (which polls `/quotes`, `/crypto/ticker`,
`/openbb-mcp/status`, `/tradesa-v2/status`, `/agents`, `/portfolio/positions`,
`/llm/providers` etc. concurrently).

Flagged in BUG_CATALOG cross-cutting if confirmed by Phase 9 re-test. If
p95 stays >100 ms when polling load is lower, this is S3 polish (would
matter for v1.x scale, not v1.0). Phase 6 added a lot of in-process
endpoints; the cumulative GIL pressure may need profiling for v1.1.

---

## Quote single-symbol round-trip (cold)

**Command:**
```bash
time (curl -sS http://127.0.0.1:54108/quotes/AAPL?asset_class=equity > /dev/null)
```

**Result:** 219 ms (single request, cold). Includes yfinance fetch (since
the cache was fresh).

**Steady-state caching** would be much lower — Phase 6 introduced
`data_cache.py` TTL cache. Re-running the same request after the cache
warms should be sub-millisecond.

---

## 1-year daily history round-trip (cold)

**Command:**
```bash
time (curl -sS "http://127.0.0.1:54108/history/AAPL?timeframe=1d&range=1y" > /tmp/aapl-1y.json)
```

**Result:** **903 ms** (single request, cold). Response: 41181 bytes, 250
bars (year of trading days). Includes yfinance fetch + JSON serialisation.

Chart panel render time on top of this: the canvas redraw is fast (<50 ms
typically) — the bottleneck is the fetch.

---

## Agent first-token latency

**Not measured this session.** Requires BYOK provider key (Anthropic /
OpenAI / etc.) in the OS keychain, which is unreachable from the Chrome
F7 fallback path. **Deferred to Phase 9 operator manual test** where the
Tauri shell with real keychain access can exercise each provider.

Future-Phase-9 procedure:
1. In Tauri shell, open AI Assistant.
2. `/key set anthropic <key>` for each provider that has a key.
3. Send `Summarise AAPL fundamentals` via `/ask`.
4. Measure send-click → first character streamed using browser
   performance API.
5. Per-provider median over 5 send-recv cycles.

---

## Backtest workflow execution time

**Not measured this session.** Backtest engine depends on the workflow
templates + (in many cases) fundamentals data from openbb-mcp. The
openbb-mcp subprocess port-binding gap (UC1-openbb-mcp-not-listening)
makes any backtest workflow that needs fundamentals fail upstream. **Deferred
to Phase 9 / re-measure after F1 fix loop** unblocks openbb-mcp.

Methodology for Phase 9 / F1 verification:
1. Open Backtest panel via Ctrl+K → "Open Backtest".
2. Select the bundled "SPY mean-reversion 30d" template.
3. Submit. Measure submit → run-complete event time.
4. Strategy Critic comment render time (separate from the run itself).

---

## Workflow engine throughput (5-node)

**Not measured this session.** Requires Node Editor (canvas-interactive
surface — requires Playwright real-event injection, not chrome-devtools
MCP). **Deferred to Phase 9** or to the Playwright real-event suite when
it lands (BLOCKERS.md v0.5.1+ carry-forward).

---

## Sidecar memory + CPU under polling load

**Not measured this session.** Lightweight observation from `Get-Process`:

| Process                          | Approx. mem  | Comment                       |
| -------------------------------- | ------------ | ----------------------------- |
| vysted-sidecar (PID 64784)       | _(not captured)_ | Main FastAPI sidecar      |
| vysted-openbb-mcp-sidecar (2 PIDs) | _(not captured)_ | Bootloader + worker child |
| vysted-sec-edgar-mcp-sidecar (2 PIDs) | _(not captured)_ | Same shape             |
| vysted-terminal (PID 69468)      | _(not captured)_ | Tauri Rust shell + WebView2 |

Phase 9 should capture `Get-Process | Where ProcessName -like 'vysted-*'`
output 30 s after boot and again 5 min after sustained polling, comparing
WorkingSet to baseline.

---

## Summary

| Metric                          | Result        | Notes                       |
| ------------------------------- | ------------- | --------------------------- |
| Cold-start (Rust uncached)      | ~95 s         | One-time cargo download + compile |
| Warm-start (Rust cached)        | ~8–10 s (est) | Sample needed in Phase 9    |
| /health p50                     | 5.3 ms        | Acceptable                  |
| /health p95                     | 228 ms        | **Anomalous** — GIL? S3 polish |
| /health p99                     | 486 ms        | **Anomalous** — same        |
| /quotes/AAPL cold               | 219 ms        | yfinance fetch dominates    |
| /history/AAPL 1y daily cold     | 903 ms        | yfinance fetch dominates    |
| Agent first-token latency       | deferred      | Phase 9 with keychain       |
| Backtest workflow               | deferred      | After F1 fix loop           |
| 5-node workflow                 | deferred      | Playwright real-event needed |
| Memory under polling load       | deferred      | Phase 9                     |

**Headline:** main sidecar is fast at its happy path (p50 5.3 ms) but has
a heavy tail (p95 228 ms) under realistic polling load. The cold-start
~95 s is dominated by cargo download+compile; Tauri release-build would
shrink that to a single binary launch.

---

*Re-run identically in Phase 9 / 10 / v1.x to detect regression.*
