# rc1-drive-failure-inducer — working log

Role: OWNER-DRIVE failure-inducer regression re-drive against candidate `4097dac4`.
Full scored table + deltas: `../drives/failure-inducer.md`. This file is the terse
chronological record.

1. Checked for a prior rc1 attempt at this role: none found (`rc1/findings`, `rc1/drives`,
   `surface/failure-inducer/rc1/` all had entries from other roles but nothing under
   `failure-inducer` — fresh start, not a continuation).
2. Read `PROMPT_surface_s2.md` OWNER-DRIVE + failure-inducer section, `COMMON.md`, census
   `surface/failure-inducer/EVIDENCE.md` (full scorecard, 01-53 + malformed-symbol sweep) and
   `COVERAGE.json`. Cross-referenced the register (`vysted-r15-register.json`): all 5
   SURF-FAILURE-INDUCER-{1..5} raw findings roll up into R15-AGENT-025/026/027,
   R15-DATA-061, R15-RESEARCH-008 — every one `status: fixed`. That set the scope: verify
   each fix holds on the candidate (regression check), not a fresh sweep.
3. Booted own sidecar `:52327` from `rc1-cand` source, own data dir (`cp -R` of
   `rc1-seed-data`), shared read-only MCP pair `:52153`/`:52154`. `/health` ok.
4. Confirmed git fix commits exist on candidate for all 5: `dcea43e3` (R15-AGENT-026),
   `9b678194` (R15-AGENT-025), `42087077` (R15-AGENT-027), `22bdc72b`/`e9762f78`/`3a9aa93d`/
   `e340574e` (R15-DATA-061), `0e67f366`/`cf186ad5` (R15-RESEARCH-008).
5. Copied census's `harness/junk_provider.py` verbatim, ran it on `:52341` (loopback stub,
   stdlib, $0). Restarted my sidecar with `OPENAI_BASE_URL=http://127.0.0.1:52341/v1` (the
   openai-python SDK reads that env var itself when `base_url` isn't explicitly passed —
   confirmed via `services/llm/openai.py:346`).
6. `vy.py invoke copilot ... --provider openai --model junk-truncated --bad-key`: got an
   explicit `error{code:"truncated"}` frame, not a silent "done". Same for
   `junk-emptychoices` (`code:"empty_response"`) and `junk-html` (also `empty_response` —
   less specific than census's ideal "unreadable response" but no longer silent/misleading,
   so the regression check holds). R15-AGENT-026 CONFIRMED FIXED.
7. Ran the pinned test `sidecar/tests/test_b5_runtime_liveness.py` for R15-AGENT-025 instead
   of a live 150-600s wait (over the 120s per-call cap either way): 4/4 pass. Read the
   watchdog code directly (`agent_runtime.py:1002-1056`): 10s heartbeat, 180s/300s
   (cloud/local) idle -> `provider_idle` error frame. CONFIRMED FIXED by code + test.
8. `zzz-nonsense/not-a-model-9000:free` via real OpenRouter free lane (no key needed for a
   400 rejection, $0): got `code:"model_not_found"`, "pick another model" — body-matched
   classification (`services/errors.py:272`), not the old status-only "unknown/try again".
   R15-AGENT-027 CONFIRMED FIXED.
9. Restarted sidecar with a loopback-only proxy block (`ALL_PROXY=127.0.0.1:9` etc, my
   process only, per the induction boundary rule) for R15-DATA-061: `/history/AAPL` ->
   honest `code:"network"` error (was silently `bars:[]` -> "No price data"); `/news` -> 502
   `code:"provider_error"` (was a bare "all sources failed" or raw text depending on route);
   `/quotes/%20%20%20` and `/quotes/%24%24%24` (whitespace/`$$$`, single-symbol route) -> clean
   404 `code:"not_found"`, no yfinance `AttributeError` leak. CONFIRMED FIXED across every
   sub-case I could reach.
10. `/quotes?symbols=RELIANCE,TCS,AAPL` under the same proxy block: AAPL silently absent from
    the response array. Read `routers/quotes.py:65-90` before flagging it — this is an
    explicitly documented, intentional batch semantic ("skip on failure, matching prior
    sequential semantics"), and `WatchlistPanel.tsx:132` renders a missing quote as an
    honest empty/dash row, not a fabricated value. Not filed.
11. Ran the pinned test `sidecar/tests/test_keyless_backend.py` for R15-RESEARCH-008 (23/23
    pass) and read `ENGINE_DEADLINE_SECS=6.0` (`services/search/keyless.py:67`,
    `asyncio.timeout` wrap at :258-278) instead of a live ~40s web_search wait. CONFIRMED
    FIXED by code + test.
12. Nodocker profile (`PATH=/usr/bin:/bin:/usr/sbin:/sbin`, no docker): `/search/searxng/
    status` still reported `docker.cli_present:true` — read `searxng_manager.py:146-155`:
    it now falls back to known install paths beyond `PATH`, so the census's PATH-strip
    technique no longer reaches a "Docker absent" state on this candidate. Logged as a
    methodology note (a hardening, not a defect) in the drive file, not filed as a finding.
13. Same probe surfaced a live fact worth recording: the shared SearXNG container's engines
    (Brave/DDG/Startpage) are currently CAPTCHA'd/rate-limited by the upstream services
    themselves — `kind: environment`, filed for visibility only (not a candidate defect,
    not scored against the 5 fixes).
14. Spot-checked `junk-429`/`junk-500` (still honest, unchanged) for cheap regression
    coverage beyond the 5 primary findings.
15. Stopped my sidecar (`kill` on the recorded sleep pid per profile restart) and the junk
    stub; verified via `ps` that neither `:52327` nor `:52341` is listening. Never touched
    `:52152-54` or any other role's sidecar.

Result: 0 regressions among the 5 owned findings; 1 environment-kind observation filed for
visibility; 1 methodology note (nodocker induction technique needs updating, not a product
bug) recorded in the drive file.

## Round 2 — gate round 2, candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`

1. Re-entered this task fresh (LEAD NOTE gate-round-2, new candidate sha). Found the round-1
   outputs above intact under this same task's files — read them first per the continuation
   rule, then checked whether the candidate had actually moved: `git -C rc1-cand rev-parse
   HEAD` = `4c6dfe8c...`, round-1's drive file says `4097dac4` → confirmed a real, non-trivial
   move (`git log --oneline 4097dac4..4c6dfe8c -- sidecar/services/agent_runtime.py` = 20+
   commits, all R15-LEAD-030/033/035/036 tool-citation work in the exact file the
   R15-AGENT-025 idle-watchdog fix lives in). Decided: re-drive live, not assume-carries-over.
2. Confirmed all 5 register ids still `status: fixed` in `vysted-r15-register.json` at this
   sha (counts: `entries:652, critical:16, high:116, medium:293, low:227`).
3. Booted own sidecar `:52327` fresh from `rc1-cand` (HEAD confirmed), fresh data dir
   `rc1-data-failure-inducer-r2` (never touched the round-1 dir). `/health` ok.
4. Junk stub: `:52341` and `:52342` were both already bound by other concurrent roles'
   sidecars (`rc1-data-battery-1`/`-2`) — checked with `lsof` before binding, moved to `:52350`
   (confirmed free first).
5. Ran `junk-truncated`/`junk-emptychoices`/`junk-html` via `OPENAI_BASE_URL` → stub:
   byte-identical to round 1's frames. R15-AGENT-026 holds.
6. Ran `junk-429`/`junk-500`: byte-identical to round 1, still honest.
7. Restarted clean (unset `OPENAI_BASE_URL`), ran `zzz-nonsense/not-a-model-9000:free` via
   real OpenRouter free lane: byte-identical `model_not_found` frame. R15-AGENT-027 holds.
   Also ran the retired slug `z-ai/glm-4.5-air:free`: still an explicit `model_not_found`
   (OpenRouter's own message text changed to a 404 upgrade-path wording — their side, not
   ours — still honest/actionable, not filed).
8. Restarted with `ALL_PROXY`/`HTTP(S)_PROXY=127.0.0.1:9` (netdown, my process only):
   `/history/AAPL` → `503 network`, `/news` → `502 provider_error`,
   `/quotes?symbols=RELIANCE,TCS,AAPL` → RELIANCE/TCS answer (BSE lane unaffected), AAPL
   silently dropped — re-read `routers/quotes.py` on THIS sha to confirm the documented
   skip-on-failure semantic is still there before not-filing it again. Also re-tested
   `/quotes/%20%20%20`/`/quotes/%24%24%24` under netdown: now `503 network` (was `404` in
   round 1's clean-profile test) — restarted clean afterward specifically to re-run the
   original clean-profile repro and confirm it's a route-ordering difference under netdown,
   not a regression: clean profile still gives `404 not_found` for both, `AAPL` still
   resolves `200` — no `AttributeError` leak in either profile. R15-DATA-061 holds.
9. Ran the two pinned test files together fresh on this sha (not reused from round 1):
   `test_b5_runtime_liveness.py` + `test_keyless_backend.py` → **27/27 pass**, 31.44s. Confirms
   R15-AGENT-025 (watchdog constants unmoved despite the `agent_runtime.py` churn) and
   R15-RESEARCH-008 (`ENGINE_DEADLINE_SECS` unmoved) both hold.
10. Restarted with `PATH=/usr/bin:/bin:/usr/sbin:/sbin` (nodocker profile): `/search/
    searxng/status` still `cli_present:true` — same fallback-to-known-paths hardening as
    round 1, same non-finding methodology note.
11. Direct-probed the shared `:52152`'s `/search/searxng/status` again: still `degraded`,
    same three engines CAPTCHA'd/rate-limited by upstream — same `kind: environment`
    observation, not re-filed as new.
12. Stopped my sidecar and stub each restart (`pkill` on the sleep+worker for `:52327`,
    `kill` on the stub pid for `:52350`), confirmed via `lsof` after each stop and at the
    end. Never touched `:52152-54`, `:52341`, or `:52342` (other roles' ports).

Result: 0 regressions on round 2 (same as round 1, now proven live against the actual
gate-round-2 candidate rather than inherited from a stale round). No new defects. The one
`environment` observation and one methodology note both persist unchanged.
