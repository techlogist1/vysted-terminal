# surf-onboarding-stranger — gate round 3 (rc1/round-3) re-drive

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `127.0.0.1:52326`, clean data dir
`rc1-round-3-data-onboarding-stranger` (only `dev-keystore.json` seeded), MCP env pointed at the
shared read-only openbb-mcp `:52153` / sec-edgar-mcp `:52154`, never restarted. Re-drove against
the census (`SURFACE/onboarding-stranger/EVIDENCE.md`, `COVERAGE.json`) and the register entries
this group's raw findings map to.

Sidecar spawn gotcha hit and worked around: `main.py` runs a stdin-EOF watchdog
(`_exit_when_parent_closes_stdin`) that `os._exit(0)`s the instant stdin gets EOF — a bare
`nohup ... &` under the Bash tool gives it a closed/`/dev/null` stdin and it exits before Uvicorn
even logs. Fix: the `ISO_STACK.md` pattern, `nohup sh -c 'sleep 86400 | ./.venv/bin/python3 main.py ...'
&`, keeps stdin open on the sleep's pipe; killing the sleep pid closes the pipe and the sidecar exits
via the same watchdog (clean, no SIGKILL). Confirmed the sidecar stopped this way at the end of the
drive (`/health` refused, worker pid gone).

## Register map for this group

| raw_id | register id | status @ candidate | this round |
|---|---|---|---|
| SURF-ONBOARDING-STRANGER-1 | R15-UI-008 | fixed | **confirmed live** |
| SURF-ONBOARDING-STRANGER-2, -3 | R15-UI-052 | fixed | **confirmed live** (code-read) |
| SURF-ONBOARDING-STRANGER-4 | R15-UI-041 | not_a_defect | **confirmed current** (TOS rewritten) |
| SURF-ONBOARDING-STRANGER-5 | R15-DATA-018 | fixed | **confirmed live** |
| SURF-ONBOARDING-STRANGER-6 | R15-UI-076 | open (low) | **confirmed unchanged** (expected — low stays open) |
| (banner/local-model contradiction) | R15-UI-019 | fixed | **confirmed** (code-read) |
| (Settings key trim) | R15-UI-057 | fixed | **confirmed live** |
| (promote key over keyless default) | R15-UI-049 | fixed | **confirmed present** (pinned test `llm-providers.test.ts`) |
| (keychain-denied dead end, T5) | R15-UI-044 | blocked_tier4 | not re-driven (adjudicated, no fix round; a real keychain-deny requires OS-level denial, out of scope for an API-only re-drive) |

## Scored table

| # | Item | Census score | RC1 round-3 score | Evidence |
|---|---|---|---|---|
| 1 | First-launch TOS content | broken (described trading) | **ok** — TOS_BODY now reads "data and analysis tool... no brokerage connection... data may be delayed/wrong... AI-generated analysis can be wrong... PolyForm Strict 1.0.0" | `src/modules/safety/DisclaimerFlow.tsx:29-33` (read direct) |
| 2 | Fake OpenRouter key validates | broken (`ok:true`) | **ok** — `POST /llm/keys/validate {provider:openrouter, api_key:<fake>}` → `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` | live curl, this session |
| 3 | Key with trailing space (K08) | broken-ish (garbled "transport error") | **ok** — same fake key + trailing space → identical clean `invalid` response (server-side trim holds) | live curl, this session |
| 4 | Welcome-screen keyless "web research" claim | broken (claimed keyless) | **ok** — now "Pick a path below to turn on the AI agent (and its web research)" — gated correctly behind a model | `src/components/OnboardingFlow.tsx:240-242` |
| 5 | "Nothing leaves this machine" / "fully private... offline" privacy claims | broken (false) | **ok** — reworded: "Your keys, notes and portfolio stay on this machine — market data and web searches go to public providers"; local path: "it still reaches out for market data and web searches, but the model itself is yours" | `OnboardingFlow.tsx:231-233,260`, `OnboardingBanner.tsx:67-69` |
| 6 | Banner still shown after local-model setup | broken (COD-frontend-panels-agent-shell-11) | **ok** — `defaultLaneNotReady` now checks `useKeylessReadiness` for a keyless default lane; comment cites R15-UI-019 by id | `OnboardingBanner.tsx:17-20,44-49` |
| 7 | Zomato→Eternal rename resolve/autocomplete | broken ("No instrument matched") | **ok** — `GET /resolve?q=zomato` and `q=ZOMATO` and `/resolve/autocomplete?q=ZOMATO` all return `ETERNAL LIMITED` with a `rename{renamed_from:ZOMATO,renamed_to:ETERNAL,...}` block | live curl, this session |
| 8 | `/quotes/ZOMATO.NS` (retired symbol) | broken (502, leaked yfinance internal attribute error) | **ok** — clean `{"detail":"The data provider has no data for this symbol or series...","code":"not_found"}`, no library internals leaked | live curl, this session |
| 9 | "eternal" resolve (current symbol) | ok | **ok**, unchanged | live curl |
| 10 | Adding a key after skip promotes the default provider | not in census skeleton (found later) | **ok** — `promoteKeyedProvider` exists with a pinned regression test citing R15-UI-049 | `src/store/llm-providers.ts:80`, `src/store/llm-providers.test.ts:10` |
| 11 | Default watchlist/chart vs India-first region | wrong (SPY/QQQ/NVDA/AAPL vs region=IN) | **wrong, unchanged** (expected — R15-UI-076 stays `open`, severity `low`, not in gate scope) | `src/store/symbols.ts:40-46` (DEFAULT_SYMBOLS unchanged) |
| 12 | Keyless first-panel data (quotes/news/hardware-fit/resolve) | ok | **ok**, unchanged | live curl: `/quotes`, `/news`, `/system/hardware`, `/resolve` |
| 13 | Keychain-denied dead end (T5) | broken (COD-safety-audit-12 / R15-UI-044) | NOT TESTED this round — `blocked_tier4`, adjudicated, no fix round; would require simulating an OS keychain permission denial, out of scope for a headless API re-drive | n/a |
| 14 | Ollama daemon-down / model-not-pulled onboarding states | NOT TESTED (shared daemon never stopped) | NOT TESTED again, same constraint (shared Ollama lane, never stopped) | n/a |

## Census → RC1 deltas

- **5 fixes hold live/code-confirmed with no regression**: R15-UI-008, R15-UI-052, R15-UI-019,
  R15-DATA-018, R15-UI-057 (plus R15-UI-049 confirmed present with its own pinned test).
- **1 adjudicated-current, not re-opened**: R15-UI-041 (`not_a_defect`) — the TOS body is in fact
  now correct (rewritten in the D81 trading-removal batch), consistent with that status.
- **1 stays open by design**: R15-UI-076 (low) — default symbols/chart still don't follow the
  IN region default; unchanged from census, correctly left open at low severity, not in this
  round's fix scope.
- **No new defects found.** No regression found. Nothing scored ok-in-census-now-broken.
- Bonus: the old `/quotes/ZOMATO.NS` 502 that leaked a yfinance internal attribute name
  (`'PriceHistory' object has no attribute '_dividends'`) is now a clean honest 404-shaped error —
  a side benefit of the DATA-018 resolver fix's error path, not separately filed (not a new defect,
  a strict improvement already covered by the same fix).

## Findings this round

None. `findings/rc1-drive-onboarding-stranger.json` is `[]`.
