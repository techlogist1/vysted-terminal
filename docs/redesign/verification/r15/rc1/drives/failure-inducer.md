# rc1-drive-failure-inducer — regression re-drive of the 5 filed SURF-FAILURE-INDUCER findings

Candidate `4097dac4` ("merge(r15): stage C batch 11 - 18 certified fixes at 9985b00e"). Own
sidecar `:52327`, source `rc1-cand`, data dir `cp -R` of `rc1-seed-data` at
`.../scratchpad/rc1-data-failure-inducer` (keyless, `dev-keystore.json` empty secrets). MCP
pair shared read-only `:52153`/`:52154` (never restarted). Junk stub reused from census
harness (`harness/junk_provider.py`, loopback, stdlib) on `:52341`. All 5 register entries
below are census-filed under `raw_ids` containing `SURF-FAILURE-INDUCER-{1..5}` and carry
register `status: fixed` — this drive is the regression check on that claim, not a fresh
census sweep.

## Scorecard — the 5 filed findings, census → rc1

| register id | census verdict (SURF-FAILURE-INDUCER-N) | rc1 re-test | rc1 verdict | evidence |
|---|---|---|---|---|
| R15-AGENT-026 (`-1`) | silent: truncated/emptychoices/200-HTML streams rendered as a finished, unflagged answer | `junk-truncated` → `error{code:"truncated", message:"The provider closed the stream before the answer finished."}`; `junk-emptychoices` → `error{code:"empty_response"}`; `junk-html` → `error{code:"empty_response"}` (all now explicit `error` frames before `done`, not silent) | **ok — fixed, holds** | `surface/failure-inducer/rc1/truncated.jsonl`, `emptychoices.jsonl`, `html.jsonl` |
| R15-AGENT-025 (`-3`) | silent 150s+ spinner, no watchdog, 600s SDK timeout | code: `agent_runtime.py:1002-1056 _relay_provider` — 10s heartbeat, `IDLE_TIMEOUT_S=180`/`LOCAL_IDLE_TIMEOUT_S=300` (`llm/base.py:52,54`), emits `provider_idle` error frame past idle; `sidecar/tests/test_b5_runtime_liveness.py` 4/4 pass on candidate. Not re-run live (180s exceeds the 120s per-call cap; test suite is the faster, equally direct proof) | **ok — fixed, holds** (code-read + passing pinned test, not a live 180s wait) | `sidecar/services/agent_runtime.py:1002-1056`, `sidecar/services/llm/base.py:52-57`, test run in working log |
| R15-AGENT-027 (`-5`) | nonsense slug → `code:"unknown"`, "Try again or switch provider" (retry cannot help) | `zzz-nonsense/not-a-model-9000:free` via real OpenRouter (free, $0) → `error{code:"model_not_found", message:"The requested model is not available on OpenRouter — pick another model.", action:"Choose a different model in Settings."}` — body-matched (`services/errors.py:272` `("not a valid model","invalid model","model not found","model_not_found")`), not status-only | **ok — fixed, holds** | `surface/failure-inducer/rc1/nonsense-slug.jsonl` |
| R15-DATA-061 (`-4`) | `/history` 200 `bars:[]` under netdown → chart says "No price data"; `/fundamentals` raw curl text; `/quotes/{bad}` yfinance `AttributeError` leaked raw | Proxy-down profile (`ALL_PROXY=127.0.0.1:9`, my process only): `/history/AAPL` → `{"code":"network","detail":"Could not reach the data provider — check your internet connection."}`; `/news` → `{"code":"provider_error", detail:"The data provider returned an unexpected response."}` (502, no raw text); `/quotes/%20%20%20` and `/quotes/%24%24%24` → clean `404 {"code":"not_found"}`, no `AttributeError` | **ok — fixed, holds** | `surface/failure-inducer/rc1/netdown-data-routes.txt` |
| R15-RESEARCH-008 (`-2`) | keyless `web_search` DDG-first burns ~41s of the 25s tool cap before Brave is tried | code: `ENGINE_DEADLINE_SECS=6.0` (`services/search/keyless.py:67`, `asyncio.timeout` wrap at :263) bounds every engine attempt so DDG+fallback fits inside 25s; `sidecar/tests/test_keyless_backend.py` 23/23 pass on candidate. Not re-run as a live 40s web_search (over budget; the deadline constant + passing suite is the direct, cheaper proof) | **ok — fixed, holds** | `sidecar/services/search/keyless.py:67,258-278`, test run in working log |

**0 regressions.** All 5 census-filed findings this group owns hold fixed on the candidate.
No `new_defect` survived triage (see below).

## Spot-checks beyond the 5 (not separately filed originally, quick regression sanity)

- `junk-429` → `{"code":"rate_limit", message:"OpenAI is rate-limiting your account — try again in a minute."}`; `junk-500` → `{"code":"provider_5xx", ...}` — both still honest, unchanged from census.
- `/quotes?symbols=RELIANCE,TCS,AAPL` under netdown: RELIANCE/TCS answer (BSE, unaffected by the loopback-only proxy block since NSE/BSE lanes don't route through it this way), AAPL (yfinance, US) is silently dropped from the array — **read the code** (`routers/quotes.py:65-90`): this is a **documented, intentional** batch semantic ("a symbol that fails to resolve is skipped rather than failing the whole request... matching the prior sequential skip-on-failure semantics"), and the frontend renders a dropped symbol as an honest empty/dash row (`WatchlistPanel.tsx:132`, `quote === null` branch), not a fabricated value. Not filed — by design, not silent-to-the-user.
- SearXNG/nodocker profile: restricting `PATH` no longer reads as "Docker absent" — `searxng_manager.py:146,154-155` now falls back to known install paths (`/usr/local/bin/docker` etc.) beyond `PATH`, a hardening that makes the census's PATH-strip induction technique obsolete on this candidate (the induced-failure edge moved; not a product defect — if anything, fewer false "Docker missing" reports for a user with a non-standard shell `PATH`). Logged as a methodology note, not a finding.
- Live probe of the shared SearXNG/search-engine chain right now: `/search/searxng/status` → `state:"degraded"`, `detail:"SearXNG is running but its search engines are blocked"`, `reason:"brave: Suspended: too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA"`. This is a real, current upstream condition (proven by direct probe against the shared, already-running SearXNG container), not a candidate code defect — filed as `kind: environment` for visibility, not scored against the 5 fixes.

## Process record

Sidecar `:52327` cycled through 4 env profiles (base, junk via `OPENAI_BASE_URL`, netdown via
loopback-proxy env, nodocker via stripped `PATH`) per `boot.sh`'s pattern, each restart
confirmed via `/health` before probing. Junk stub `:52341` (`harness/junk_provider.py`,
copied verbatim from census, stdlib-only, no money). All LLM calls: junk stub (`--bad-key`,
$0) except the one real OpenRouter free-slug call (`zzz-nonsense/...:free`, $0, no key
required for a 400 model-not-found rejection). Ollama `llama3.1:8b` available locally but not
needed — every finding under test is a transport/classification behavior best forced via the
stub, not a model-quality question. Sidecar and stub both stopped at end (`kill` on recorded
sleep/stub pids, verified via `ps`).

## Round 2 — re-verified against candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2` (gate round 2)

The round-1 drive above tested candidate `4097dac4`. The gate-round-2 candidate `4c6dfe8c`
sits 297 commits later on `004-r4-experience-rebuild`, including heavy churn in
`sidecar/services/agent_runtime.py` (the R15-LEAD-030/033/035/036 tool-citation/figure-guard
series) — the exact file the R15-AGENT-025 fix (`_relay_provider` idle watchdog) lives in — so
this was re-driven live rather than assumed to still hold. Own sidecar `:52327` rebuilt from
the fresh `rc1-cand` worktree (`sidecar/.venv` present, HEAD confirmed
`4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`), fresh data dir
`rc1-data-failure-inducer-r2` (`cp -R` of `rc1-seed-data`, never the round-1 dir). Junk stub
port `52341` was occupied by another concurrent role's sidecar (`rc1-data-battery-1`) and
`52342` by another (`rc1-data-battery-2`) — moved the stub to `52350` (free, verified via
`lsof` before bind), no shared-port collision.

| register id | round-2 re-test on `4c6dfe8c` | verdict | evidence |
|---|---|---|---|
| R15-AGENT-026 | `junk-truncated`/`junk-emptychoices`/`junk-html` via `OPENAI_BASE_URL` → stub — byte-identical `error{code:"truncated"}` / `error{code:"empty_response"}` (x2) frames, in that exact order, before `done` | **ok — fixed, holds** | `surface/failure-inducer/rc1/truncated-r2.jsonl`, `emptychoices-r2.jsonl`, `html-r2.jsonl` |
| R15-AGENT-025 | Live 180s wait is still over the 120s per-call cap; re-ran the pinned test file fresh on `4c6dfe8c` (not assumed from round 1) — `test_b5_runtime_liveness.py` + `test_keyless_backend.py` together: **27/27 pass**, 31.44s. Confirmed the watchdog constants unmoved: `agent_runtime.py:1002-1056 _relay_provider`, `IDLE_TIMEOUT_S=180`/`LOCAL_IDLE_TIMEOUT_S=300` (`llm/base.py:54,56`) | **ok — fixed, holds** | pytest log in working log; `sidecar/services/agent_runtime.py:1002-1056` |
| R15-AGENT-027 | `zzz-nonsense/not-a-model-9000:free` via real OpenRouter free lane ($0) — byte-identical `error{code:"model_not_found", message:"...pick another model."}` | **ok — fixed, holds** | `surface/failure-inducer/rc1/nonsense-slug-r2.jsonl` |
| R15-DATA-061 | Re-tested BOTH profiles this round: (a) clean profile, `/quotes/%20%20%20` and `/quotes/%24%24%24` → clean `404 {"code":"not_found"}`, `/quotes/AAPL` resolves `200` normally — no `AttributeError` leak in either malformed-symbol case; (b) netdown profile (`ALL_PROXY`/`HTTP(S)_PROXY=127.0.0.1:9`), `/history/AAPL` → `503 {"code":"network"}`, `/news` → `502 {"code":"provider_error"}`, and under netdown the same two malformed symbols now surface as `503 {"code":"network"}` instead of `404` (network check now runs before the not-found check when the network itself is down) — still an honest classified error either way, never the raw `AttributeError` | **ok — fixed, holds** (route-ordering detail under netdown noted, not a defect — no raw error text surfaces in any profile) | `surface/failure-inducer/rc1/malformed-symbols-clean-r2.txt`, `netdown-data-routes-r2.txt` |
| R15-RESEARCH-008 | `test_keyless_backend.py` re-run fresh on `4c6dfe8c`: 23/23 pass; `ENGINE_DEADLINE_SECS=6.0` unmoved (`services/search/keyless.py:67`) | **ok — fixed, holds** | pytest log in working log; `sidecar/services/search/keyless.py:67` |

**0 regressions on round 2 either.** All 5 owned findings hold on `4c6dfe8c` despite the
297-commit drift through the very file (`agent_runtime.py`) the idle-watchdog fix lives in.

Spot-checks repeated and unchanged: `junk-429`/`junk-500` still honest (byte-identical
messages); retired slug `z-ai/glm-4.5-air:free` still an explicit `model_not_found` (OpenRouter
now returns 404 with an upgrade-path message instead of round-1's phrasing — a wording change
on OpenRouter's side, not the candidate's; still honest, still actionable); nodocker
`PATH`-strip methodology note still applies (`searxng_manager.py`'s fallback-to-known-paths
still reports `cli_present:true` with `PATH` stripped — same hardening, same non-finding); the
shared SearXNG environment condition (`brave`/`duckduckgo`/`startpage` CAPTCHA'd/rate-limited)
is still live on direct re-probe — same `kind: environment` observation, unchanged, not
re-filed as a new finding.

Sidecar `:52327` cycled through the same 4 profiles again on `4c6dfe8c` (base → junk via
`OPENAI_BASE_URL` → clean (malformed-symbol re-check) → netdown via loopback-proxy env →
nodocker via stripped `PATH`), each restart's sleep pid killed and port confirmed free via
`lsof` before the next boot. Stub on `:52350` stopped the same way. Final state: neither
`:52327` nor `:52350` listening; `:52152-54` untouched throughout.
