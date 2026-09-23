# L6-longsession — does a sidecar stay stable over an hours-long session?

Worker: claude-opus-5-5 (L6 finisher). Status: **FIRST-WINDOW EVIDENCE ONLY** — this file covers
the first ~15 minutes of a detached 3 h 20 min soak that is still running. The ≥3 h verdict is
Stage C's job; section 7 says exactly how to take it. No product code was changed.

Method: a detached stdlib soak (`soak.py`, written by the previous L6 worker) drives realistic
traffic at an isolated sidecar on `127.0.0.1:52229` and samples the process every 60 s. This
finisher read the soak's own logs, the sidecar/MCP logs and the code they point at, and took five
passive `ps` readings of the main worker's CPU time (the same `ps` the soak runs every minute). It
did not send a request to `:52229`, did not attach a profiler, and did not stop or restart anything.

## 1. What the soak runs

| Item | Value |
|---|---|
| Stack | `seat-l6-longsession/boot.sh`: main sidecar from **source** (`sidecar/.venv/bin/python3 main.py --port 52229 --data-dir …/seat-l6-longsession/data`) + the built `vysted-openbb-mcp-sidecar` (`:53229`) and `vysted-sec-edgar-mcp-sidecar` (`:53239`), each with its stdin held by a `sleep 86400` pipe. Stack booted 12:26:21 IST (`pids-life-l6-longsession.json`). |
| Data | a copy of the operator's backup data dir (`vysted-iso/data` → `seat-l6-longsession/data`); keystore is `{"secrets": {}, "migrated": true}` (40 B, keyless); region IN |
| Soak process | `python3 soak.py` (system Python 3.9, pid **64697**), started 12:29:42 IST under `nohup`, `DURATION_S=12000` (3 h 20 min) → ends ≈ **15:49:42 IST**, then kills the three `sleep` pids, which stops its own stack |
| Cycle (every 60 s) | `/health`, `/quotes?symbols=RELIANCE.NS,TCS.NS,INFY.NS,HDFCBANK.NS,SPY,QQQ,NVDA,AAPL`, `/quotes/{s}`, `/fundamentals/{s}`, `/history/{s}?timeframe=1d`, `/portfolio/positions`, `/openbb-mcp/status`, `/system/provider-health` — `{s}` rotates through 12 symbols (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, ITC, SBIN `.NS`; AAPL, MSFT, NVDA; TATAMOTORS.NS; BHARTIARTL.NS) |
| Every 5th cycle | `/news?limit=20`, `/agents`, `/runs`, `/workspace`, `/search/status`, `/resolve?q=<s>` |
| Every 10th cycle (c%10==5) | portfolio CRUD: `POST` → `PUT` → `DELETE /portfolio/positions/{id}` (tracked portfolio, not trading) |
| Every 15th cycle (c%15==1) | one copilot invoke through `scripts/r15/vy.py` on OpenRouter `nvidia/nemotron-3-super-120b-a12b:free`, rotating three prompts (quote / P/E and market cap / append a note). About 13 over the run. |
| Sampler (every 60 s) | `ps` (rss, vsz, %cpu, etime), `ps -M` thread count, `lsof` line count / TCP / ESTABLISHED / CLOSE_WAIT, `footprint -p` (MB), `vm_stat`, file sizes of every data-dir file plus `sidecar.log` / `openbb-mcp.log`. Taken for the main worker and both MCP workers. |

Start command (from the soak's own header; the worker used `nohup`, output in `soak.nohup.out`, 0 B):
`cd <scratch>/vysted-iso/soak && nohup python3 soak.py > soak.nohup.out 2>&1 &` (pid written to
`soak.pid` by `soak.py:main`).

**Note on the notes coverage.** L6's spec asks for notes GETs. The cycle has no `/notes` route. Notes
are exercised only by invoke prompt #3 (an agent-driven append), about every 45 min.

## 2. The aborted first launch (`soak/aborted-first-launch/`)

The first start (pid 64582, 12:29:01) ran for 21 s: one cycle, one invoke, one memory sample.
Then it was replaced by the current launch (12:29:42). Why it was aborted is **inferred**: its MEM line has no
`fp=` field and the current `soak.py` (mtime 12:29) samples `footprint`, so the worker most likely
restarted it to add the footprint metric.

| Evidence | Value |
|---|---|
| start sample | main rss 58.4 MB, threads 13, lsof lines 206, TCP 20 (12 ESTABLISHED, **7 CLOSE_WAIT**), %cpu 61.4; openbb rss 42 MB |
| seed | `/portfolio/positions` was empty (2 B) → 5 positions POSTed (201, 1–3 ms). The relaunch found them present and did not re-seed. |
| cycle 1 | all 200. `/quotes` batch **8.8 s**, `/history/TCS.NS` 5.2 s |
| invoke #1 | `rc=0 4417ms`, events `{'thinking': 18, 'tool_use': 1, 'error': 1, 'done': …}`: an **error event inside an "ok" run**. The assistant text was empty. The full transcript is lost because the relaunch's invoke #1 overwrote `invoke-01.jsonl` (see §6). |

Takeaway: the aborted launch is a warm-start baseline only. Its one useful fact is that a stream can
carry an `error` event and still count as `rc=0`, so the Stage C verifier must read events, not rc.

## 3. Resource trend — first 845 s of the current launch (main worker pid 64164)

`fp` = `footprint -p` (physical footprint incl. compressed). `lsof` = `lsof -p` line count, which
includes mem-mapped files and is not a pure fd count. `cw` = CLOSE_WAIT sockets.

| t (s) | fp MB | rss MB | thr | lsof | tcp | cw | %cpu | openbb fp | sec fp | data_cache.db | -wal | fundamentals_cache.db | sidecar.log B |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 359 | 189 | 16 | 232 | 26 | 4 | 61.5 | 223 | 124 | 6,266,880 | 0 | 2,691,072 | 37,202 |
| 60 | 361 | 86 | 16 | 238 | 27 | 3 | 61.5 | 223 | 124 | = | 0 | = | 38,131 |
| 120 | 363 | 114 | 16 | 238 | 28 | 4 | 65.3 | 223 | 124 | = | 0 | = | 38,861 |
| 181 | 365 | 127 | 16 | 238 | 26 | 1 | 66.0 | 223 | 124 | = | 0 | = | 41,307 |
| 241 | 365 | 116 | 16 | 240 | 28 | 5 | 62.7 | 223 | 124 | = | 0 | = | 42,057 |
| 301 | 366 | 128 | 16 | 217 | 21 | 6 | 30.2 | 223 | 124 | = | 0 | = | 43,387 |
| 362 | 367 | 116 | 16 | 240 | 28 | 6 | 61.0 | 223 | 124 | = | 0 | = | 44,117 |
| 422 | 386 | 99 | 16 | 248 | 30 | 3 | 61.5 | 223 | 124 | = | 0 | = | 45,024 |
| 483 | 387 | 94 | 16 | 251 | 31 | 5 | 44.5 | 223 | 124 | = | 0 | = | 45,628 |
| 543 | 387 | 110 | 16 | 251 | 31 | 9 | 57.7 | 223 | 124 | = | 0 | = | 46,232 |
| 603 | 388 | 114 | 16 | 257 | 33 | 7 | 60.2 | 223 | 124 | = | 0 | = | 49,161 |
| 664 | 388 | 105 | 16 | 248 | 30 | 7 | 62.2 | 223 | 124 | = | 0 | = | 49,915 |
| 724 | 378 | 119 | 16 | 253 | 31 | 8 | 61.3 | 223 | 124 | = | 0 | = | 50,784 |
| 784 | 378 | 114 | 16 | 256 | 32 | 7 | 61.0 | 223 | 124 | = | 0 | = | 51,510 |
| 845 | 378 | — | 16 | 257 | 33 | 5 | — | 223 | 124 | = | 0 | = | 52,552 |

Readings, first window only (not a verdict):

- **Memory:** footprint went 359 → 388 → 378 MB. Most of the rise is one +19 MB step at t≈422 s,
  when the first US `/history` (AAPL, 41 KB of bars) landed; it then gave back 10 MB. There is no
  slope yet. **RSS is not usable here**: it swings 86–189 MB while footprint is flat, because the
  host is under heavy memory pressure (`vm_stat`: ~4–11 k free 16 KB pages, 1.6 M pages held in
  the compressor, swapouts climbing 3.347 M → 3.390 M). Judge memory by `footprint_mb` only.
- **Threads:** a flat 16 on the main worker. The MCP workers hold 5 and 4 threads and their
  footprints (223 / 124 MB) have not moved.
- **lsof lines / TCP:** 232 → 257 (+25) and TCP 26 → 33 (+7) in 14 min. CLOSE_WAIT bounces between
  1 and 9 and does not accumulate. The first US-symbol cycles loaded new shared libraries, which
  inflate the lsof line count. **This is the metric to watch at ≥3 h**: a real socket leak shows
  as TCP and CLOSE_WAIT still climbing after t≈1 h.
- **WAL / data files:** `data_cache.db` (6,266,880 B), its `-wal` (0 B), `fundamentals_cache.db`
  (2,691,072 B) and `portfolio.db` (12,288 B) are unchanged the whole window. Portfolio CRUD
  commits in place, and none of the cycle's routes writes the data cache. So this workload cannot
  grow the WAL. It also means NSE daily history is **not cached**: `/history/TCS.NS` took 4,706 ms
  at c1 and 5,108 ms at c13, and `/history/RELIANCE.NS` took 4,866 ms at c12.
- **Logs:** `sidecar.log` grows ~18 B/s (≈65 KB/h ≈ 1.5 MB/day of access lines plus fall-through
  warnings). `openbb-mcp.log` grows ~5 B/s: two 404 lines per IN `/fundamentals`, because the MCP
  mangles `TCS.NS` → `TCS-NS` (known: COD-mcp-servers-9).
- **CPU — the one defect already visible** (section 5 / LIFE-L6-LONGSESSION-1): the main worker
  burns ~0.6 of a core continuously, almost entirely on its main (event-loop) thread.

## 4. Requests and errors so far

129 soak rows through c14 (12:43). All are 2xx except the TATAMOTORS pair below.

| Route | n | p50 ms | max ms | Note |
|---|---|---|---|---|
| `/health` | 14 | 4 | 8 | the loop stays responsive between cycles |
| `/quotes` (8-symbol batch) | 14 | ~3,900 | **31,577** (c3) | one 31.6 s outlier while the Yahoo circuit was open. Every other batch took 3.5–9.3 s. |
| `/quotes/{s}` | 14 | ~1,050 | 3,491 | .NS ~0.75–1.4 s (nse_direct gets `curl: (35) Connection reset`, then the jugaad `nse` lane answers); US 0.1–0.4 s |
| `/fundamentals/{s}` | 14 | ~2,000 | 2,838 | every IN call first wastes an openbb-mcp round trip ("returned no rows", then falls through) |
| `/history/{s}?timeframe=1d` | 14 | ~4,700 | 5,319 | .NS 4.5–5.3 s, uncached; US 0.14–0.39 s |
| portfolio GET / POST / PUT / DELETE | 15 / 1 / 1 / 1 | 2 | 8 | 200/201/200/204; CRUD read-back clean |
| `/news`, `/agents`, `/runs`, `/workspace`, `/search/status`, `/resolve` | 2 each | ≤1,331 | | all 200; `/workspace` is 16 B (no saved workspace in the copy) |
| INVOKE #1 (12:29:53) | 1 | 8,535 | | `ok`, one `fundamentals` tool call, answer "P/E 15.36 / ₹7.57 lakh crore" cited to yfinance. `{thinking 142, tool_use 1, delta 15, done 1}` |

**TATAMOTORS.NS (c10, recurs every 12th cycle).** Tata Motors was renamed in Oct 2025, so this
ticker is retired. Three routes gave three different answers within 7 s:
`/quotes` → **502** `yfinance quote failed for 'TATAMOTORS.NS': 'PriceHistory' object has no attribute '_dividends'`
(raw library text); `/fundamentals` → **404** "No instrument matches 'TATAMOTORS.NS' — check the symbol.";
`/history` → **200** with an empty series (111 B), which `routers/history.py:27` tags
`reason: "in_eod_only"`. The chart then renders "No EOD data for this symbol. BSE/NSE serve
end-of-day only — intraday/realtime needs a BYOK broker (Kite/Upstox/Dhan)."
(`src/modules/chart/ChartPanel.tsx:387-389`). That reason is false for a daily chart of a renamed
symbol, and it points at a broker lane the 23 Sep decision removes. `/resolve?q=tatamotors` → 200.
**Not re-filed.** The mechanisms are already in the register: raw-text leak SURF-COMPOSER-CHAT-3
and INT-spec-135-137, false region-based empty reason SURF-PANELS-LAYOUTS-3, renamed ticker not
resolvable SURF-ONBOARDING-STRANGER-5. What this soak adds is the long-session angle: a portfolio
or watchlist that holds a retired ticker hits all three at once, every refresh, all session. The
broker copy in the empty-state string belongs to the trading-removal batch.

**Pre-soak 500s are a harness artifact, not a product finding.** `sidecar.log` holds two
`GET /fundamentals/{RELIANCE.NS,AAPL} 500` (CancelledError via cancel scope, then "Task
exception was never retrieved") from the previous worker's warm-up probes at ~12:26. The cause:
`boot.sh` starts the main sidecar in parallel with the MCP children, so it dialled openbb-mcp
before the child had bound. The shipped app does not do this: `src-tauri/src/lib.rs:470-490`
joins both MCP spawn threads, and each one blocks in `wait_for_port_with_retries`
(`openbb_mcp.rs:149`), before `start_main_sidecar` runs. The underlying mechanism (MCP transport
failure escapes as an unhandled 500) is SURF-RESEARCH-BRIEFS-13 / COD-mcp-servers-2. Once the
child was up, every later `/fundamentals` returned 200, so no dead session got cached.

## 5. Steady CPU burn on the event-loop thread (LIFE-L6-LONGSESSION-1)

Passive readings of the main worker (`ps -o etime,utime,time`, `ps -M`):

| wall time | etime | CPU time (user+sys) | user | lifetime avg |
|---|---|---|---|---|
| ≈12:40 | 13:41 | 8:10.43 | | 59.7 % |
| 12:41:27 | 15:21 | 9:10.00 | | 59.7 % |
| ≈12:42 | 15:45 | 9:24.71 | 8:39.39 | 59.7 % |
| 12:43:05 | 16:59 | 10:09.33 | | 59.8 % |
| 12:44:19 | 18:13 | 10:53.62 | 10:01.97 | 59.8 % |

- Over the 272 s from 13:41 to 18:13 the process used 163.2 s of CPU (**60 % of a core**), and 92 %
  of that is user time. This is Python work, not page-fault decompression from the memory pressure.
- `ps -M` puts **10:49.65 of the 10:53.62 on the first (main) thread**, which is where uvicorn runs
  the asyncio event loop. The 15 other threads together hold under 5 s.
- The load is not request-driven. Those 272 s spanned about 4.5 cycles, and each cycle's
  requests take about 12–15 s of wall time, so about 60 s in total. Even if all of that were pure
  CPU on one thread, at least 100 s of the 163 s CPU fell between cycles. The decaying `%cpu` shows
  the same thing: it read 61.5 % at t=422 and 44.5 % at t=483, after all-US cycles whose requests
  finished in under 6 s and 55 s before the sample.
- Contrast: L1-stranger's clean, keyless sidecar idled at **0.0–0.8 %** CPU for 6.5 min
  (`lifecycle/L1-stranger/idle-boot-sampler.jsonl`), with one 41 % spike on a warm retry.
- **Root cause: not attributed** (no profiler was attached, by rule). Candidates from the code:
  the IN-region warm workers started in the lifespan (`app.py:127-134`;
  `fundamentals_warm.py` sweep / crawl / bhavcopy loops at `:199`, `:373`, `:301`), the
  `nse_symbol_change` refresh, or post-response work left on the loop by the IN quote/history
  lanes. The warm workers are the weakest candidates: `fundamentals_cache.db` and `data_cache.db`
  were not written once in the window, so they did not complete a cycle. Stage C should attribute it (§7).

## 6. Soak-harness caveats (for the reader; not product findings)

1. `lsof` line count is not a pure fd count (it includes mapped files). Judge by `tcp` / `close_wait` and
   by the slope after the first hour.
2. RSS is distorted by host memory pressure. Use `footprint_mb`.
3. INVOKE `status` is `vy.py`'s exit code (0 iff the run's status was `ok`, `scripts/r15/vy.py:264`).
   An `error` event inside an ok run still reads rc=0 (aborted launch #1), so read the
   `invoke-NN.jsonl` event counts.
4. `invoke-NN.jsonl` is keyed by per-launch invoke count, so a relaunch overwrites the earlier
   launch's file. The aborted launch's invoke #1 transcript is gone.
5. The main sidecar runs from source, not the PyInstaller binary. The MCP children are the built
   binaries. Frozen-binary footprint will differ.
6. Other isolated sidecars shared this IP during the window, so the Yahoo circuit opened repeatedly
   (`provider health: yahoo circuit OPEN …` in `sidecar.log`). That confounds absolute latency
   (the 31.6 s batch) but not the resource slopes.
7. `soak-summary.json`'s `non_2xx` will include about 17 × 2 TATAMOTORS rows (every 12th cycle
   over ~200 cycles). Subtract them before reading it as an error rate.

## 7. How to read the rest

**Files** (all under `<scratch>/vysted-iso/soak/`, where `<scratch>` =
`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad`):

| File | Cadence | Content |
|---|---|---|
| `soak-status.json` | rewritten each cycle | `{pid, started, elapsed_s, duration_s, cycle, invokes, last, base}`. A stale `last` (> 3 min old) with the pid alive means a hung cycle; with the pid dead before `duration_s`, the soak crashed. |
| `soak.log` | ~9–16 lines/min + 1 MEM line/min | human-readable |
| `soak-requests.jsonl` | one row per request / invoke | `ts, t, cycle, method, path, status, ms, bytes, err` |
| `soak-mem.jsonl` | one row per 60 s | `main` / `openbb` / `sec` proc stats, `vm`, `sizes` |
| `invoke-NN.jsonl` | ~every 15 min | full SSE event stream of invoke NN |
| `soak-summary.json` | once, at the end | `{cycles, invokes, requests, non_2xx, ended}`. It exists only if the soak completed. |
| `../seat-l6-longsession/sidecar.log`, `openbb-mcp.log` | continuous | tracebacks and fall-through warnings |

Expected cadence: 1 cycle/60 s (≈200 cycles total), 1 MEM sample/60 s (≈200 rows), ≈13 invokes.
The soak ends ≈15:49:42 IST and then **kills its own stack**. Any live-process measurement (CPU
attribution) must happen before that time.

**Liveness check (no request to the sidecar):**
`ps -p $(cat <scratch>/vysted-iso/soak/soak.pid) -o pid,etime; cat <scratch>/vysted-iso/soak/soak-status.json; tail -3 <scratch>/vysted-iso/soak/soak.log`

**The ≥3 h verdict command** (run once `soak-status.json` `elapsed_s ≥ 10800`, or after `soak-summary.json` appears):

```bash
cd <scratch>/vysted-iso/soak && python3 - <<'EOF'
import json, statistics as st
mem=[json.loads(l) for l in open("soak-mem.jsonl")]
req=[json.loads(l) for l in open("soak-requests.jsonl")]
def win(a,b): return [r for r in mem if a<=r["t"]<b and r["main"].get("alive")]
def med(rows,f): v=[f(r) for r in rows if f(r) is not None]; return st.median(v) if v else None
early, late = win(1800,3600), win(max(r["t"] for r in mem)-1800, 10**9)
for name,f in [("fp_mb",lambda r:r["main"]["footprint_mb"]),("threads",lambda r:r["main"]["threads"]),
               ("lsof",lambda r:r["main"]["fds"]),("tcp",lambda r:r["main"]["tcp"]),("close_wait",lambda r:r["main"]["close_wait"]),
               ("openbb_fp",lambda r:r["openbb"].get("footprint_mb")),("sec_fp",lambda r:r["sec"].get("footprint_mb")),
               ("wal_B",lambda r:r["sizes"].get("data_cache.db-wal")),("log_B",lambda r:r["sizes"]["sidecar.log"])]:
    print(f"{name:11} 30-60min={med(early,f)}  last30min={med(late,f)}")
bad=[r for r in req if r["method"]!="INVOKE" and not(r["status"] and 200<=r["status"]<300) and "TATAMOTORS" not in r["path"]]
inv=[r for r in req if r["method"]=="INVOKE"]
h=sorted(r["ms"] for r in req if r["path"]=="/health")
print("cycles",max(r["cycle"] for r in req),"non2xx(excl TATAMOTORS)",len(bad),[(r["cycle"],r["path"],r["status"]) for r in bad][:20])
print("invokes",len(inv),"rc!=0",[(r["path"],r["status"]) for r in inv if r["status"]!=0])
print("health p50/p99 ms",h[len(h)//2],h[int(len(h)*.99)-1])
EOF
for f in invoke-*.jsonl; do python3 -c "import json,sys,collections;c=collections.Counter(json.loads(l)['kind'] for l in open('$f'));print('$f',dict(c))"; done
ps -p 64164 -o etime=,utime=,time=   # CPU: only while the stack is still up (before ~15:49:42 IST)
```

**What a pass looks like** (each line independent; the late window is compared to the 30–60 min window,
so warm-up is excluded):

- `fp_mb` rises by at most ~10 % (≲ +40 MB) with no steady climb across the last three hours.
  `openbb_fp` / `sec_fp` are flat.
- `threads` stays at 16. `tcp` and `close_wait` stay flat (close_wait < ~15, not trending up);
  `lsof` is flat once the first hour's library loads are done.
- The data_cache `-wal` stays at 0 or a bounded few MB (checkpointed). `sidecar.log` grows linearly
  at ~65 KB/h with no traceback bursts (`grep -c "Exception in ASGI application" sidecar.log` stays at the pre-soak 2; `grep -c Traceback` at 14).
- 0 non-2xx outside TATAMOTORS. Every invoke has rc 0 **and** a `done` event with **no** `error`
  event. `/health` p99 < 100 ms. Both MCP workers are still alive in the last MEM row.
- CPU: the lifetime average per `ps -o time` should fall toward the L1 idle baseline (~0–5 %) between
  cycles. If it stays ~60 %, LIFE-L6-LONGSESSION-1 stands. Attribute it before 15:49:42 with
  `sample 64164 10 -file <scratch>/vysted-iso/soak/cpu-sample.txt` (a read-only stack sample; it
  briefly suspends the process, so only the Stage C verifier should run it) or with
  `py-spy dump --pid 64164` if installed. The frame at the top of the main thread names the loop that spins.

A **fail** is any of: a steady footprint slope (≥ ~15 MB/h sustained), a TCP / CLOSE_WAIT climb, a
thread-count climb, an MCP worker dying, a growing WAL, non-TATAMOTORS 5xx, an invoke with an
`error` event, or the soak pid dying before `duration_s` (check `soak.log` for `CYCLE ERROR`).

## 8. Root-cause read-back (recorded, nothing fixed)

- LIFE-L6-LONGSESSION-1: the main-thread CPU burn is real and measured, but its source is not
  attributed. Fix shape: profile the event-loop thread, then move the hot code off the loop or
  stop the spinning loop. Details in the raw finding.
- Retired-symbol triple answer: already covered by SURF-COMPOSER-CHAT-3, SURF-PANELS-LAYOUTS-3,
  SURF-ONBOARDING-STRANGER-5 and INT-spec-135-137. Not re-filed.
- Boot-order 500s: a harness artifact (§4). The mechanism is SURF-RESEARCH-BRIEFS-13.
- NSE daily history uncached (≈5 s per open, repeatable) and wasted openbb-mcp round trips for IN
  fundamentals (COD-mcp-servers-9) are latency facts carried for Stage C. They do not threaten
  stability.
