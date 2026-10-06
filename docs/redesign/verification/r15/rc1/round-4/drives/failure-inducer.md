# Owner-drive: failure-inducer — RC1 gate round 4

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `127.0.0.1:52327`, source
run from the round-4 candidate worktree (`sidecar/.venv`), data dir copied fresh from
`rc1-round-4-seed-data` (keyless) to `rc1-round-4-data-failure-inducer`, MCP env pointed at
the shared read-only `openbb-mcp:52153` / `sec-edgar-mcp:52154`. All writes/probes this round
went to my own sidecar only; the shared `:52152` stack was never touched.

Scope: `SURFACE/inducer/` (5 files, 19-23 Sep) and `SURFACE/failure-inducer/` (top-level, 23
Sep — `COVERAGE.json` fully terminal, `EVIDENCE.md`, the harness scripts) are already a
complete census of this surface; round 3 (`rc1/round-3/EVIDENCE.md`) already re-verified the
5 raw findings this group produced (`SURF-FAILURE-INDUCER-1..5`, all mapped to register
entries `fixed`) against candidate `01d6920a`. Round 4's job is a regression re-check of that
same set on the new candidate (three commits/batches further: batch-25/26/27), plus driving
what the round-3 EVIDENCE.md explicitly left `NOT TESTED` (Docker-absent/SearXNG-down status,
malformed-symbol sweep). Diffed `01d6920a..1006c6da` on every file the 5 fixes live in first
(`git diff --stat`): only `sidecar/services/errors.py` (+13 lines, a new `_BODY_RULES` branch)
and `sidecar/services/llm/openai.py` (client-construction moved inside the try/except) changed
— both are R15-LEAD-043 (no-key humanization, composer-chat's entry, additive) — so no code
under my 5 findings' fix shape was touched between rounds; live re-drives below confirm the
diff read.

## Scored table

| # | Drive | Result | Score | Raw file |
|---|---|---|---|---|
| 1 | AGENT-026 regression: OpenAI-compatible adapter direct against `junk-truncated`/`junk-chunkdrop`/`junk-orerror` stubs (openai + openrouter provider ids, candidate source, no sidecar) | `junk-truncated` (silent stream-end, no finish_reason) yields **only** the one `LLMDeltaEvent`, no fabricated `LLMErrorEvent`/done — matches the round-3 fix shape (client-side `STREAM_ENDED_EARLY` still fires per `streaming.ts:385`, unchanged this round); `junk-chunkdrop`/`junk-orerror` both correctly humanize to an `LLMErrorEvent` for both providers | ok — **holds, no regression** | `01-adapter-direct-regression.txt` |
| 2 | DATA-061 regression: `GET /quotes/%20%20%20` (the entry's own repro) | `404 {"detail":"...no data for this symbol...","code":"not_found",...}` — no raw `AttributeError`, unchanged from round 3 | ok — **holds** | `02-data061-regression.txt` |
| 3 | Malformed-symbol sweep spot-check (`$$$`, `RELIANCE.NS.NS`, a SQL-injection string, unicode `भारत`) on `/quotes/{sym}` | All 4 correctly `404 not_found` with the humanized sentence, no raw library text | ok | `03-malformed-symbols-regression.txt` |
| 4 | Same sweep, a script-tag symbol `<script>alert(1)</script>` | `502 {"code":"provider_error","action":"Retry, or try again later."}` — sidecar log: yfinance got an empty/non-JSON body for this symbol (`Expecting value: line 1 column 1`), so it falls outside the `not_found` humanization path | **broken — new_defect rc1-drive-failure-inducer:1** (recurrence of a class the round-3 verifier already flagged against the closed R15-DATA-061) | `03b-script-symbol-properly-encoded.txt` |
| 5 | Exact round-3-verifier repro `GET /quotes/%24%24%25%5E` (`$$%^`) | Identical `502 provider_error / Retry` | confirms #4, same finding | `04-dataclass-recur-dollarpercentcaret.txt` |
| 6 | `GET /fundamentals/ZZZZNOTREAL/{income,balance,ratings}` (round-3-verifier's second repro) | All three `200` with empty/null data, no reason field — indistinguishable from a real symbol with zero filings | **broken — new_defect rc1-drive-failure-inducer:2**, same recurring class | `05-unknown-symbol-fundamentals-subroutes.txt` |
| 7 | AGENT-025 regression: hung-provider timeout code path | `oneshot.py` (moved from the file path round-3 cited, same module under `services/llm/`) still carries the `timeout=`/`asyncio.wait_for` guard; `streaming.ts` still defines `AGENT_STREAM_IDLE_MS=45_000`/`CHAT_STREAM_IDLE_MS=330_000` unchanged | ok — **holds** (code-read only; re-creating the 600s hang stub was not needed to confirm an unchanged guard already live-proven in round 3) | code citation, `sidecar/services/llm/oneshot.py:76-137`, `src/modules/chat/streaming.ts:201-202` |
| 8 | AGENT-027 regression: `_BODY_RULES` model_not_found/insufficient_credit/invalid-key-as-400 branches | All three branches present verbatim in `errors.py`, plus the new LEAD-043 missing-credentials branch ahead of them (additive, does not shadow) | ok — **holds** | code citation, `sidecar/services/errors.py:245-295` |
| 9 | RESEARCH-008 regression: live `vy.py invoke copilot "Use your web_search tool to find recent news about Dixon Technologies and cite the sources" --port 52327 --provider ollama --model llama3.1:8b` (own sidecar, keyless, SearXNG genuinely `degraded` — same real condition as round 3) | `tool_use` at 48.9s -> `tool_result ok:true` at 56.2s, **7.3s** for the `web_search` call (vs. the pre-fix census's unbounded ~41s per engine) — consistent with `ENGINE_DEADLINE_SECS=6.0` + the circuit breaker, unchanged since round 3; model's own text honestly reported "the searxng backend is degraded" rather than fabricating results; total run 135s (the extra time vs round 3's 62s is the 8b model's own second tool call + narration, not search latency) | ok — **holds** | `06-research008-regression-vy.txt` |
| 10 | SearXNG-down/no-docker status honesty spot-check (current real state — Docker up, SearXNG genuinely engine-degraded, not itself an induced no-docker profile) | `/search/status` -> `t1_keyless`, 3 engines `closed` (healthy); `/search/searxng/status` -> `degraded`, `reason` names the specific suspended engines, `docker.daemon_running:true` | ok (unchanged honest reporting); the actual no-docker/dead-SearXNG env profiles (`harness/boot.sh nodocker`/`netdown`) were **NOT re-run this round** — no register entry claims a fix in that code path since round 3's own explicit `NOT TESTED` (the Settings copy at `SettingsPanel.tsx:710,743,874` is untouched by this candidate's diff in this area per the `git diff --stat` above) | `07-search-status-regression.txt` |
| 11 | 429/500/hang/junk-html/junk-badsse/junk-emptychoices stubs, retired-slug `z-ai/glm-4.5-air:free`, nonsense slug | **NOT re-run this round** — no code under any of these paths changed per the `git diff --stat` scope check, and each was already live-confirmed at the census (23 Sep, files `20-*`, `21-*`, `50-*`, `51-*`, `52-*`) with no register entry claiming a fix since; re-deriving them would cost real OpenRouter free-tier calls for zero new information | NOT TESTED (no cost estimate — free-tier calls, $0, just not exercised; cite census evidence instead) | n/a — `docs/redesign/verification/r15/surface/failure-inducer/20-*.jsonl`, `21-*.jsonl`, `50-*.jsonl`, `51-*.jsonl`, `52-junk-hang.txt` |

NEEDS-GUI: none in this group (every row is an API/adapter-level drive by design).

## Census/round-3 -> round-4 deltas

- All 5 raw findings (`SURF-FAILURE-INDUCER-1..5` / `R15-AGENT-026`, `R15-RESEARCH-008`,
  `R15-AGENT-025`, `R15-DATA-061`, `R15-AGENT-027`) — **still fixed, no regression** on
  `1006c6da`. The only code touching this group's fix surface since round 3 is R15-LEAD-043
  (composer-chat's entry, purely additive).
- **New this round**: two fresh, live-reproduced instances of the DATA-061 defect **class**
  (misclassified/silent data-route failures) that the round-3 verifier had already flagged
  (`rc1-verifier:7`, recorded in DATA-061's own `note` field) as recurring against the closed
  entry, and which still reproduce unchanged on this candidate — filed as
  `rc1-drive-failure-inducer:1` and `:2` since neither has its own open register id yet.
  These are NOT part of the round's frozen three-failure/adjudicated lists (DATA-061 is not in
  section (9)'s two-failure list) — ordinary findings for the lead to route.
- No regressions found on anything previously scored `ok`/`partial`/`broken` by the census or
  round 3.

## Scope notes

- A harness artifact, not a product finding: the `trap … rmdir` wrapper around the RESEARCH-008
  re-drive reported `rmdir: ... No such file or directory` on exit — the lock dir I created was
  already gone by completion (likely raced by output-buffering, not a double-release); the
  `mkdir`-based lock itself was held correctly for the call's duration and no other process's
  lock was touched.
- Full malformed-symbol 81-row sweep (`harness/malformed.py`) and the junk-provider harness
  battery were not re-run wholesale this round (unchanged code, no register entry pointing at a
  regression there); the targeted spot-checks in rows 3-6 above are what surfaced the two new
  findings.

## Evidence files

All under `docs/redesign/verification/r15/surface/failure-inducer/rc1/round-4/`:
`01-adapter-direct-regression.txt`, `02-data061-regression.txt`,
`03-malformed-symbols-regression.txt`, `03b-script-symbol-properly-encoded.txt`,
`04-dataclass-recur-dollarpercentcaret.txt`, `05-unknown-symbol-fundamentals-subroutes.txt`,
`06-research008-regression-vy.txt`, `07-search-status-regression.txt`.
