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
