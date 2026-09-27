# surf-onboarding-stranger — OWNER-DRIVE, gate round 4 (rc1/round-4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (worktree
`.../scratchpad/rc1-round-4-cand`, confirmed via `git rev-parse HEAD` before driving).
Own sidecar booted from the candidate's `sidecar/` source on **:52326**, data dir
`<scratchpad>/vysted-iso/data-onboarding-stranger-r4` — created EMPTY, only
`dev-keystore.json = {"secrets": {}, "migrated": true}` seeded (chmod 600), MCP env
pointed at the shared read-only openbb-mcp `:52153` / sec-edgar-mcp `:52154` (never
restarted). Boot: `sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port
52326 --data-dir …` per `ISO_STACK.md` (stdin-EOF watchdog gotcha: kill the inner
`sleep` pid, not the `sh -c` wrapper's pid, to close the pipe — the wrapper's pid alone
leaves the sleep/python still connected). Stopped cleanly at the end (`sleep` pid
killed, `/health` refused, worker pid gone).

This continues past the census (`SURFACE/onboarding-stranger/EVIDENCE.md`,
`COVERAGE.json`) and reads the panel/store code first (`OnboardingFlow.tsx`,
`OnboardingBanner.tsx`, `DisclaimerFlow.tsx`, `store/safety.ts`, `store/symbols.ts`,
`lib/region.ts`, `ChatSidebar.tsx`) before driving. Per the round-4 lead note, prior
gate rounds' evidence (rc1/round-3, etc.) is read for context only, never cited as this
round's evidence — every row below has its own fresh raw file in this directory
(`docs/redesign/verification/r15/surface/onboarding-stranger/rc1/round-4/`).

## Scored table

| # | Item | Score | Evidence |
|---|---|---|---|
| 1 | Clean-profile boot / `/health` | ok | `01-health.txt` |
| 2 | Fake OpenRouter key validate (`POST /llm/keys/validate`) | ok (fix holds) | `02-fake-openrouter-key.txt` → `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` |
| 3 | Same fake key + trailing space | ok (fix holds) | `03-fake-openrouter-key-trailing-space.txt` → identical clean `invalid` response, server-side trim holds |
| 4 | First-launch TOS content | ok (fix holds) | `05-tos-body-coderead.txt` (`DisclaimerFlow.tsx:28-33`) — no trading/broker/kill-switch language; carries "no brokerage connection", data-may-be-wrong, AI-can-be-wrong, PolyForm Strict/commercial licence text. (`/safety/disclaimer-status` is not a sidecar route — `04-disclaimer-status.txt` 404 — this flow is keychain-only, `store/safety.ts`, confirmed by code read, not a regression) |
| 5 | Keychain-denied dead end (T5, no try/catch around `getSecret`/`setSecret`) | unchanged, blocked_tier4 (adjudicated, not re-driven for a fix) | `store/safety.ts:20-27` code read this session — no try/catch present |
| 6 | Onboarding-banner copy + keyless-readiness gating (no longer shown after a working local-model setup) | ok (fix holds) | `OnboardingBanner.tsx:17-49` code read — `defaultLaneNotReady` derives from `useKeylessReadiness`, cites R15-UI-019 |
| 7 | Hardware-fit `fits` / `does-not-fit` | ok, unchanged | `14-system-hardware.txt` (3 installed models green), `15-local-model-recommendation.txt`; `marginal` still NOT TESTED (unreachable on this 16 GB M1 Pro) |
| 8 | Resolve "zomato" (lower) | ok (fix holds) | `06-resolve-zomato-lower.txt` → ETERNAL LIMITED + `rename{renamed_from:ZOMATO,renamed_to:ETERNAL}` |
| 9 | Resolve "ZOMATO" (upper) | ok (fix holds) | `07-resolve-ZOMATO-upper.txt` → same clean resolution |
| 10 | Autocomplete "ZOMATO" | ok (fix holds) | `08-autocomplete-ZOMATO.txt` → ETERNAL candidate with rename block |
| 11 | `/quotes/ZOMATO.NS` (retired symbol) | ok (fix holds) | `09-quotes-ZOMATO-NS-retired.txt` → clean `404 not_found`, no yfinance internals leaked |
| 12 | Resolve "eternal" (current symbol) | ok, unchanged | `10-resolve-eternal.txt` |
| 13 | Ollama `model_not_pulled` routing | ok (fix holds) | `12-ollama-model-not-pulled.txt` → `{"ok":false,"reason":"model_not_pulled",...}`; code read `ChatSidebar.tsx:831-836` opens the real local-setup step with this reason string (R15-AGENT-028) |
| 14 | Ollama model present/pulled validate | ok | `13-ollama-model-pulled-ok.txt` → `{"ok":true}` |
| 15 | Default watchlist/chart vs India-first region | still open, no regression (R15-UI-076, low, out of this round's fix scope) | `11-default-symbols-coderead.txt` — `DEFAULT_SYMBOLS` still SPY/QQQ/BTC/ETH/NVDA/AAPL, `DEFAULT_REGION = "IN"` |
| 16 | Keyless first-panel data (default watchlist quotes, IN news) | ok, unchanged | `18-quotes-default-watchlist.txt`, `19-news-region-in.txt` |
| 17 | Onboarding wizard escape-prevention / skip marker | ok, unchanged | `17-escape-skip-coderead.txt` (`onEscapeKeyDown`/`onPointerDownOutside`/`onInteractOutside` all `preventDefault`; skip durable via `app-meta:onboarding-complete` keychain marker) |
| 18 | Keyless first composer turn, live local lane (`llama3.1:8b`, full turn) | partial (honest, not a regression) | `16-keyless-first-message-zomato.jsonl` / `.log` — full 238 s transcript below |

### Row 18 detail — live keyless first message

Prompt: *"hi, I just installed this. what can you do, and how is Zomato stock doing
today?"* via `vy.py invoke copilot ... --provider ollama --model llama3.1:8b --port
52326` (local-model lock held for the duration, released on exit via the required
`trap ... rmdir` wrapper).

The model called `market_overview()` (2.2 s, ok) then `price_data(symbol="ZOMATO.NS")`
(1.4 s, real `tool_result` — not fabricated — `ok:false, error:"provider error:
correctness gate: empty series for 'ZOMATO.NS' from 'yfinance'"`), then answered
honestly: *"No news found for Zomato... We couldn't retrieve the current price for
Zomato stock. Our provider is currently missing this information for Zomato
(ZOMATO.NS)."* Total wall time 238 s (in line with census's 182–463 s local-lane
timings), `finish_reason: stop`, real (non-fabricated) tool_result this run — no
recurrence of the earlier-round fabricated-tool-call pattern. The model did not call
`resolve_symbol` and so never surfaced the Zomato→Eternal rename to the user in this
run, even though the resolver itself is fixed and reachable (rows 8–11 above); this is
local-model tool-choice variance (documented gotcha class: "qwen/llama tool-use
inconsistency"), not a new defect — no fabrication, no silent failure, the honest-gap
disclosure holds. Not filed.

Investigated and ruled a non-issue: a burst of `services.provider_registry: provider
openbb-mcp returned an incomplete fundamentals; trying next for richer data` lines in
the sidecar log during this call's wall-clock window was traced to the sidecar's own
background **India fundamentals warm-cache task** (`services.fundamentals_warm`,
logged from boot: `"fundamentals warm: seeded 5891 india rows"` etc., R15-LEAD-034
area) running independently of the chat request on the same process — confirmed by
timeline correlation (the chat call's own two tool calls total 3.6 s of the 238 s;
the warm-cache churn spans the whole boot-to-shutdown window). Not related to this
drive's request, not a regression.

## Census → round-4 deltas

No regressions. Every previously-certified fix (R15-UI-008 fake-key validate,
R15-UI-052 welcome/banner copy, R15-UI-019 banner keyless-readiness, R15-DATA-018
Zomato/Eternal resolver, the clean 404 on the retired symbol, R15-AGENT-028
model-not-pulled routing) re-confirmed live on the round-4 candidate. R15-UI-076
(default symbols vs region) and R15-UI-044 (keychain-denied dead end) remain open at
their existing adjudicated/low status, unchanged, out of this round's fix scope. No
new defects found.

## Findings

None. `findings/rc1-drive-onboarding-stranger.json` is `[]`.
