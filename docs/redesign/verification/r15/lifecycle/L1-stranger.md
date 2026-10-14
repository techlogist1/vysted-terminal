# L1-stranger — a stranger's first five minutes (keyless, no Docker, clean profile)

Worker: claude-opus-5-5[1m], life-S2A item `l1-stranger`, 2026-09-23 09:56-10:25 IST. Status:
COMPLETE (sidecar stopped at the end).

Method: induced test + code-read. My own sidecar from source on **:52225**, data dir
`<scratchpad>/vysted-iso/seat-l1-stranger/data` created EMPTY (only `dev-keystore.json` =
`{"secrets": {}, "migrated": true}`, 0600 — no operator data), own MCP pair on :53225 / :53235.
Every process of mine ran with **`PATH=/usr/bin:/bin:/usr/sbin:/sbin`**: the stranger with no
Docker, and also exactly the PATH macOS launchd gives an app opened from Finder/Dock
(`launchctl print gui/501` shows no PATH in the GUI domain environment). Evidence lives in
`lifecycle/L1-stranger/`:

| File | What |
|---|---|
| `http-log.jsonl` | every request I made (tags D/Q/E/P/R), status, time, response head |
| `idle-boot-sampler.jsonl` | 13 samples over 6.5 min of the first boot: RSS, CPU, log counters, `/system/provider-health`, data-dir files (`harness/sampler.py`) |
| `sidecar-log-nonrequest.txt` | every non-request log line the clean boot produced |
| `rename-gate-proof.txt` | `harness/rename_gate.py` — the rename-lane retry gate, driven with an `httpx.MockTransport` |

Continues `SURFACE/seat-stranger/transcript.md` (19 Sep, status GETs + resolve sweep) and
`SURFACE/onboarding-stranger/EVIDENCE.md` (today, 09:24-09:50: onboarding screens, keyless first
message, key paths, first panels — Docker was UP there). This item does not re-run those; it adds the
no-Docker boot, what the app does on its own in the first minutes, and the lifecycle state a first
day leaves behind. The one keyless chat probe the census allows was not spent: onboarding-stranger's
`A1` (qwen2.5:7b, 182 s, wrong "not covered" answer) and `A4` (qwen3:8b research, 463 s) already
record the keyless composer on this machine, and the failure-inducer's `41`/`43` record the
no-Docker web_search.

## 1. Minute 0-1: boot, with nobody touching anything

| t (s) | Observed | Source |
|---|---|---|
| 4.2 | `/health` 200, `openbb-mcp: available`, version 0.8.0 | boot poll |
| ~5 | `nse_symbol_change: request failed ()` then `no file and no recent cache — rename lane is a no-op` | `sidecar-log-nonrequest.txt` |
| ~6-10 | `nse_bhavcopy: request failed for 2026-09-23 ()`, same for 2026-09-22 | same |
| 27 | Yahoo circuit **OPEN** (`opens_total 1`, `throttles_total 16`) — zero user data requests made yet | sampler row 1 |
| 57 | throttles 52 | sampler |
| 87 | circuit re-opened, cooldown 144 s (`opens_total 2`, throttles 83) | sampler |
| ~90 | `screener warm: rate-limited … backing off 64s`; `fundamentals warm: rate-limited (streak=1); backing off 687s` | log |
| 357 | third warm retry: CPU 41 %, RSS 393 MB, circuit open again (`opens_total 4`) | sampler |
| ~660 | `opens_total 6`, throttles 149 | `P04` |

RSS 369 MB at 27 s, settling to 150-200 MB idle, back to ~390 MB on each warm cycle. Data dir after
6.5 min: 2.79 MB (a 2.47 MB `fundamentals_cache.db` seed + a small `data_cache.db`).

What runs at boot (code): `app.py:127` `screener_service.start_warm_precompute()` — the warm loop
over `_WARM_UNIVERSES = ("sp500",)` (`screener.py:148`) every 40 s (`screener.py:147`), whatever the
region; `app.py:130` the India fundamentals warm; `app.py:134` the NSE rename-master refresh. None of
this is visible anywhere in the UI; the only trace is the log.

**Confound, stated honestly:** three other isolated sidecars (:52152, :52221, :52226) were running
their own warm loops from the same IP at the same time, so how fast Yahoo throttled is not a clean
single-user number. The throttle counters are this process's own, though, and so is the fact that
the loop starts pulling ~500 US symbols the moment the app opens.

## 2. Minute 1-2: TOS, onboarding, key banner

Rendered order and copy were measured by onboarding-stranger (`20-onboarding-replay.json`), not
re-run. Their verdicts for the first-run screens, as the lifecycle view of a first run:

| Screen | Explains / blocks | Registered as |
|---|---|---|
| TOS dialog | describes a trading product that no longer exists; no "AI output can be wrong" disclosure | SURF-ONBOARDING-STRANGER-4 |
| Welcome | "It already works — no key … web research run right now" — no web research without a model | SURF-ONBOARDING-STRANGER-2 |
| Privacy lines | "Nothing leaves this computer except the model calls you authorize" — false; section 1 adds that the app sends ~500 US tickers to Yahoo and fetches NSE archives before the user clicks anything | SURF-ONBOARDING-STRANGER-3 (supporting evidence only, not re-filed) |
| Path A, cloud key | any string is "connected" | SURF-ONBOARDING-STRANGER-1 |
| Path B, local model, Ollama absent | install guidance + "brew install ollama" + re-check (`OnboardingFlow.tsx:566-590`); on a machine too small for any model: "tight on memory … use the cloud key" (`OnboardingFlow.tsx:531-540`); hardware probe failed: "Couldn't reach the local engine … the terminal is usable keyless meanwhile" (`OnboardingFlow.tsx:636-640`) | honest (code-read; the machine's Ollama is shared and was never stopped) |

## 3. Minute 2-3: the composer without a key

Three strangers, three code paths (`src/modules/chat/ChatSidebar.tsx`):

| Stranger | What the composer does | Verdict |
|---|---|---|
| Has Ollama and a model (this machine) | default lane `ollama/qwen2.5:7b` answers; first token ~60 s, 182 s total | works, slow (onboarding-stranger `A1`) |
| No Ollama, no key | `validateProvider("ollama")` false → "No AI model is set up yet — opening setup. (Quotes, charts, news and web research already work without one.)" and onboarding reopens (`:794-805`) | honest, except the "web research" clause (SURF-ONBOARDING-STRANGER-2) |
| Picked a cloud provider, no key | "No API key for <label>. Add one in Settings → AI Providers" (`:789-795`) | honest |

## 4. Minute 3: search without Docker

| Probe | Result |
|---|---|
| `D01 /search/status` | `tier t1_keyless`, DuckDuckGo / Brave / Mojeek all "available" |
| `D02 /search/searxng/status` | `not_installed_docker`, detail "docker CLI not found — install Docker Desktop or OrbStack", `cli_present:false` |
| Settings → Research (code) | chip "Docker not found" (`SettingsPanel.tsx:743-744`); "SearXNG runs in a local Docker container, and Docker isn't available on this machine. Install Docker first — docs.docker.com/…" (`SettingsPanel.tsx:874-884`) |

For a stranger who really has no Docker, that is honest. **This machine has Docker**: OrbStack is
installed and running (`/usr/local/bin/docker -> /Applications/OrbStack.app/…/xbin/docker`, the
shared `vysted-searxng` container is serving on :8888). The sidecar still said "docker CLI not
found — install Docker", because `_run_docker` runs a bare `"docker"` through `PATH`
(`searxng_manager.py:137-144`, `FileNotFoundError` → 127 → `cli_present=False`
`searxng_manager.py:362`) and my process's PATH is the launchd default. Nothing in the Tauri core
or the sidecar adds `/usr/local/bin`, `/opt/homebrew/bin` or `~/.orbstack/bin` (no PATH handling in
`src-tauri/src/*.rs`; the sidecar is spawned at `lib.rs:206-213` with args only, so it inherits the
app's environment; no PATH code under `sidecar/` outside `.venv`). The operator and every drive so far
launched from a terminal, which is why nobody has seen this. → **LIFE-L1-STRANGER-1.** Final
confirmation on a packaged `.app` opened from Finder is NEEDS-GUI; the sidecar-side behaviour
above is measured.

Downstream: without SearXNG the chat's `web_search` runs the keyless chain and times out at its 25 s
cap (SURF-FAILURE-INDUCER-2); `/search/status` has no frontend consumer, so nothing tells the user
that research is running on the degraded tier (failure-inducer continuation addendum).

## 5. Minute 3-5: first data panels on an empty profile

| Req | Status / time | Observation |
|---|---|---|
| `Q02` quotes SPY,QQQ,NVDA,AAPL (default watchlist) | 200, 0.73 s | yfinance live — fine even with the Yahoo circuit open |
| `Q03` quotes RELIANCE,TCS,HDFCBANK,INFY .NS | 200, **23.7 s** | nse_direct `freshness:"eod"`, timestamp 2026-09-22, `market_state:"REGULAR"` at 10:00 IST on a trading day (T+1 EOD for India is INT-spec-135-139; the latency is SURF-PANELS-LAYOUTS-7) |
| `Q04` fundamentals RELIANCE.NS | 200, 4.5 s | populated |
| `Q05` history RELIANCE.NS 1d | 200, 5.5 s | 1 y of bars |
| `E16` news IN | 200, 0.6 s | 10 items |
| `E01`-`E08` agents, custom-agents, runs, backtest runs/strategies, plugins, workflows, audit log | 200, all < 10 ms | honest empty shapes (`[]`, `{"runs":[]}`, 13 agents, 5 strategies) |
| `E09` earnings upcoming | 200, 5.6 s, `events: []` | default universe is ten US mega-caps (WLD-T-7) |
| `P01` screener nifty50 PE<30, **cold** (India default universe, `screener.py:107-110`) | 200, **44.8 s** | 49 evaluated, 25 results |
| `P02` screener sp500 PE<30 at T+11 min | 200, 17.4 s | **0 evaluated, 506 skipped `rate_limited`, 0 results** — the universe the warm loop has been pre-warming since boot |
| `P03` nifty50 again | 0.01 s | warm now |

The S&P 500 screen at T+11 min evaluated nothing: after 11 minutes of warm cycles the loop had not
landed one (three throttled cycles, backoff 64 → 110 → 227 s), and it had spent the process's Yahoo
budget and opened the shared circuit six times on the way. The India default universe the user
actually starts with is not in the warm set and took 44.8 s cold. How the panel then renders a
0-evaluated run ("No rows matched the criteria — loosen a threshold") is already
SURF-SCREENER-1. → **LIFE-L1-STRANGER-3** (the boot warm policy, not the rendering).

## 6. What the first day leaves behind: the rename lane is off until midnight IST

The boot-time rename-master fetch failed once (`request failed ()` — the exception text is empty,
the class isn't logged, so even the log can't say whether it was a timeout, TLS or DNS). A direct
`httpx.get` of the same URL with the same headers and the same PATH a minute later answered
200 / 68,818 B in 1.35 s, so this was a transient blip, not a dead endpoint.

Its consequence is not transient:

| Probe (same minute) | Stranger :52225 (fetch failed at boot) | Isolated :52152 (fetch succeeded) |
|---|---|---|
| `/resolve?q=GUJGASLTD` | `GUJGASLTD` "Gujarat Gas Limited", `former_name null`, no rename note (`R01`) | `GUJENERGY` "GUJARAT ENERGY LIMITED", `former_name GUJGASLTD`, note "renamed … effective 2026-07-01" |
| `/resolve?q=GUJENERGY` (the current symbol) | `needs_disambiguation`, led by **US "UR-ENERGY INC"** (`R02`) | resolves |
| log after 3 later `/resolve` calls | still exactly 2 `nse_symbol_change` lines — no second attempt | — |

Mechanism: `_refresh_guarded` stamps `_refreshed_on = _ist_today()` in a `finally`
(`nse_symbol_change.py:430-437`), so a failed fetch counts as today's refresh, and
`schedule_refresh` — called on every `/resolve` (`routers/resolve.py:91,140`) — returns at once
while `_refreshed_on == today` (`:450-451`). `rename-gate-proof.txt`: first fetch raises
`ConnectTimeout("")` → attempts=1, map empty; three more `schedule_refresh()` → still attempts=1;
only a day rollover retries and gets `GUJGASLTD → GUJENERGY`. A clean profile has no cached master to
fall back to (`fetch_latest` stale-cache loop `:417-424` finds nothing), so for the rest of install
day every renamed Indian scrip answers with its dead identity and its current ticker can't be found
at all, and nothing in `/resolve`, `/health` or the UI says the rename lane is off. The module calls
this an "honest no-op" (`symbol_resolver.py:793-795`, also `:669`); to the user it is silent. →
**LIFE-L1-STRANGER-2.** (The ZOMATO→ETERNAL miss is a different mechanism, SURF-ONBOARDING-STRANGER-5;
COD-resolver-1 covers the lane's ticker-string join.)

## 7. Dead ends and unexplained failures, first five minutes

1. Settings tells a user who has Docker/OrbStack to install Docker (when the app is opened from
   Finder/Dock) — LIFE-L1-STRANGER-1.
2. Renamed Indian scrips resolve to the old identity, and the current ticker can't be found, for the
   whole install day after one boot blip, silently — LIFE-L1-STRANGER-2.
3. The app starts pulling the US S&P 500 from Yahoo the moment it opens, trips its own circuit, and
   at T+11 min the S&P 500 screen evaluates 0/506 while the India default runs cold in 45 s —
   LIFE-L1-STRANGER-3.
4. Already registered, seen again here: onboarding copy (SURF-ONBOARDING-STRANGER-1..4), Indian
   watchlist latency (SURF-PANELS-LAYOUTS-7), empty-run rendering (SURF-SCREENER-1), keyless
   web_search timeouts (SURF-FAILURE-INDUCER-2), no frontend consumer of `/search/status`.

## Root cause read-back (recorded only, nothing fixed)

- **Docker lookup:** `searxng_manager._run_docker` execs bare `"docker"`; the app never extends PATH
  for a GUI launch. Smallest fix shape: probe the well-known install paths (`/usr/local/bin`,
  `/opt/homebrew/bin`, `~/.orbstack/bin`, `/Applications/Docker.app/Contents/Resources/bin`) when
  `docker` isn't on PATH, or have the Tauri core pass a login-shell PATH to the sidecar.
- **Rename gate:** set `_refreshed_on` only on success (or on a successful stale-cache hydrate); a
  failure should retry with backoff; log `type(exc).__name__`; surface
  `rename_lane: unavailable` on `/resolve` or `/health` while the map is empty.
- **Warm policy:** `_WARM_UNIVERSES` is a US-only constant started unconditionally at boot. Gate it
  on region (warm `nifty50` for IN), delay the first cycle until the UI has had its first requests,
  and don't let background warming open the circuit that user requests share.

## Not tested

- A packaged `.app` launched from Finder (NEEDS-GUI) — the sidecar-side PATH behaviour was
  reproduced exactly; the PATH launchd hands a GUI app was read from `launchctl print`, not observed
  inside the packaged app.
- A really Ollama-free machine: the machine's Ollama is shared and was never stopped;
  `/system/ollama/status` hardcodes `127.0.0.1:11434` (`routers/system.py:27`), so it can't be pointed
  away per-process. The LocalStep states were code-read.
- A single-sidecar, uncontended IP for the section 1 throttle numbers (every other lane on this
  machine shares the IP). Cost to settle: $0, ~15 min on a machine with no other sidecar running.
- The keyless chat probe (skipped as already recorded, see the header). $0 either way.
