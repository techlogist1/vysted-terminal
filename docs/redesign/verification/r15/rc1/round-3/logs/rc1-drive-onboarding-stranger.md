# rc1-drive-onboarding-stranger — working log, gate round 3

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`, confirmed via `git rev-parse HEAD` on the
scratch worktree before starting.

1. Checked for prior round-3 work under this label — none existed (this surface group's
   `rc1/round-3/` subdir did not exist yet; created it). Read the census
   (`surface/onboarding-stranger/EVIDENCE.md`, `COVERAGE.json`,
   `census/raw/surf-onboarding-stranger.json`) and mapped its 6 raw findings to register entries
   (all resolved: 4 fixed, 1 not_a_defect, 1 open-low). Also found 3 more register entries in this
   surface's territory not in the original raw file (R15-UI-019, R15-UI-049, R15-UI-057).
2. Seeded a clean data dir (`dev-keystore.json` only) and booted my own main sidecar on `:52326`
   from the candidate worktree's `sidecar/` source, MCP env pointed at the shared read-only
   openbb-mcp/sec-edgar-mcp (`:52153`/`:52154`) — never restarted those.
3. **Spawn gotcha**: first two boot attempts (`nohup ... &`, then a plain foreground run) both
   exited cleanly (code 0) right after the tool-registration log lines, before Uvicorn ever bound
   the port — `main.py`'s `_exit_when_parent_closes_stdin` watchdog saw EOF on a closed/`/dev/null`
   stdin and `os._exit(0)`'d. Fixed by following `ISO_STACK.md`'s exact pattern: pipe `sleep 86400`
   into the python process's stdin so the fd stays open; `/health` came back `ok` within 10s.
4. Re-drove the group's own findings live against the candidate:
   - `POST /llm/keys/validate` with a fake OpenRouter key (with and without a trailing space) —
     both now correctly `ok:false reason:invalid` (was `ok:true` in census; R15-UI-008 confirmed
     fixed, R15-UI-057 trim confirmed fixed).
   - `GET /resolve`, `/resolve/autocomplete`, `/quotes/ZOMATO.NS` for the Zomato→Eternal rename —
     all now resolve to ETERNAL with rename metadata, and the retired-symbol quote is a clean
     404-shaped error instead of a 502 leaking a yfinance internal attribute name (R15-DATA-018
     confirmed fixed).
   - Sanity: `/quotes` (SPY/QQQ/NVDA/AAPL), `/news?region=IN`, `/system/hardware`, `/resolve?q=eternal`
     — all unchanged and ok.
5. Code-read the frontend claims and logic the backend can't exercise (no GUI available):
   `DisclaimerFlow.tsx` (TOS body rewritten, matches R15-UI-041's `not_a_defect` status),
   `OnboardingFlow.tsx` (welcome-screen "web research" claim now correctly gated behind a model,
   privacy claim reworded — R15-UI-052 confirmed), `OnboardingBanner.tsx` (banner now hides for a
   ready keyless default lane, comment cites R15-UI-019 by id), `store/llm-providers.ts` +
   `llm-providers.test.ts` (`promoteKeyedProvider`, R15-UI-049, has its own pinned regression test).
   `store/symbols.ts` `DEFAULT_SYMBOLS` confirmed unchanged (R15-UI-076 correctly stays open/low).
6. Did not re-drive: the keychain-denied dead end (R15-UI-044, `blocked_tier4`, adjudicated, no fix
   round, and a real OS keychain denial isn't reachable from a headless API-only re-drive); the
   Ollama daemon-down / model-not-pulled onboarding states (shared Ollama daemon on this machine,
   never stopped per the LOCAL-MODEL LOCK rule's spirit — those states were NOT TESTED in the
   census for the same reason and remain NOT TESTED here). Did not re-run a full local-model agent
   turn (A1/A2/A4) — the wrong-Zomato-answer root cause (the resolver) is directly re-verified
   above and is what A1 exercised; a fresh 3-7 minute Ollama turn adds no new signal for a
   regression-focused round and the local-model lane is a shared, contended resource.
7. Stopped my sidecar cleanly by killing the `sleep` pid holding its stdin pipe open (confirmed
   `/health` refused and the worker pid gone afterward).

No new defects found. No regressions found. Wrote the scored table + deltas to
`SURFACE/onboarding-stranger/rc1/round-3/RC1-R3-ONBOARDING-STRANGER.md` and an empty findings
array (nothing qualified) to `findings/rc1-drive-onboarding-stranger.json`.
