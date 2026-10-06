# surf-failure-inducer — gate round 3 re-drive

Candidate `01d6920a300b016ab1ad8aa436ee4e4586f8e336`. Own sidecar `127.0.0.1:52327`
(`sleep` pid 89938, worker pid 89939), booted from the candidate worktree's `sidecar/` on a
copy of `rc1-round-3-seed-data`. Reads to the shared `:52152` stack were GET-only. No new
attempt directory existed under `r15/rc1/round-3` for this label — first attempt.

Scope: the census's 5 raw findings (`SURF-FAILURE-INDUCER-1..5`) all map (register `raw_ids`)
to entries marked `fixed`: R15-AGENT-026 (1), R15-RESEARCH-008 (2), R15-AGENT-025 (3),
R15-DATA-061 (4), R15-AGENT-027 (5). None of these five are in the round's three-failure or
adjudicated lists — an ordinary fix-round verification. Re-drove each live or against the
current source; no other register entry from this group is `open` at medium+.

## 1 — SURF-FAILURE-INDUCER-1 → R15-AGENT-026 (silent truncated/empty stream)

Code read, `sidecar/services/llm/openai.py:780-784`: `if finish_reason is None and not
emitted_tool_events: return` — a stream that ends with no terminator (cut socket, 200
non-SSE, empty choices) now yields **no** fabricated `done` at all. Client side,
`src/modules/chat/streaming.ts:373-383`: `consumeSseStream` unconditionally calls
`fail(new Error(STREAM_ENDED_EARLY))` after the read loop unless a terminal event already
settled the message — the previously-silent case now becomes an error/Retry row.
Also verified the "shown as a complete answer" half (max_tokens/length): `isLengthFinish` +
`LENGTH_NOTICE` fire in raw chat (`ChatSidebar.tsx:990`) and the agent runtime
(`agent_runtime.py:2977-2982`). **Holds — fixed.**

## 2 — SURF-FAILURE-INDUCER-2 → R15-RESEARCH-008 (keyless web_search timeout)

Live re-drive on my sidecar (already `t1_keyless`; SearXNG shows `degraded` from real
CAPTCHA/suspension, same keyless-tier condition as the census's nodocker probe — see
`research008-sidecar-excerpt.txt`). Ollama lock acquired first try, held under a
`trap … EXIT INT TERM HUP; rmdir` wrapper. `vy.py invoke copilot "Use your web_search tool
to find recent news about Dixon Technologies and cite the sources" --provider ollama
--model llama3.1:8b` (`research008-vy-transcript.txt`):

- DDG 202 at 22:02:42.220, second 202 at 22:02:45.530 → **~3.3s**, not the census's ~41s.
- Mojeek 200 immediately after.
- `tool_result: ok:true` at 59.2s (tool call issued 52.3s into the run — most of the wall
  clock is the 8b model's own "thinking" before it calls the tool, not the search).
- Overall run **62.0s**, well inside the 25s-per-call tool budget (each individual
  `web_search` invocation completed in ~7s).

Code read confirms why: `sidecar/services/search/keyless.py` — `ENGINE_DEADLINE_SECS = 6.0`
(down from the unbounded 2×~20s DDG retries) plus a `CircuitBreaker` per engine
(`breaker.py`) that benches a repeatedly-failing engine instead of re-trying it every call.
`catalog.py` now has a per-tool timeout hint (`TOOL_TIMEOUT_HINTS["web_search"]`) so a genuine
timeout would say "the configured search tier did not answer in time" instead of the
research-domain "retry at a lighter depth" copy. **Holds — fixed** (timing); one honest
side-note, not a regression: the model's own prose called the zero-result outcome "degraded"
rather than "found nothing for this query" — a phrasing nit on a genuinely empty result set,
not a silent/misleading tool failure, not filed.

## 3 — SURF-FAILURE-INDUCER-3 → R15-AGENT-025 (silent spinner on a hung provider)

Code read only (re-creating the junk-hang stub on my own process was not needed to confirm
the structural fix already proven in the census's own refute pass): `oneshot.py:76-137` adds
an explicit `timeout` parameter (`asyncio.wait_for`) so `invoke_agent`'s pre-stream await can
no longer hang the full 600s SDK default. Client side, `streaming.ts:195-291`: a stall
watchdog re-armed on every chunk, `AGENT_STREAM_IDLE_MS = 45_000` /
`CHAT_STREAM_IDLE_MS = 330_000` (chosen above the 10s agent heartbeat cadence and the
adapters' own 180s/300s idle timeouts respectively) — silence past the budget now ends the
stream with `STREAM_STALLED` and cancels the reader (which drops the server-side run too).
**Holds — fixed.**

## 4 — SURF-FAILURE-INDUCER-4 → R15-DATA-061 (raw library text / kind dropped)

Live re-drive: `GET /quotes/%20%20%20` (the census's own repro symbol) against BOTH the
shared read-only `:52152` stack and my own `:52327` — identical response on both:
`{"detail":"The data provider has no data for this symbol or series — check the symbol.",
"code":"not_found","action":"Check the symbol or series id."}` (`data061-malformed-symbol.json`).
No raw `AttributeError`, no library text. Code read confirms the architectural fix is a single
`app.py:354-355` `@app.exception_handler(ProviderError)` calling `provider_error_response`
(`errors.py`) for the WHOLE app, not a per-route patch — every route that raises
`ProviderError` now gets a kind-aware status/code/detail, not just `/fundamentals`. **Holds —
fixed**, and structurally stronger than a per-route fix (no route can regress this
individually).

## 5 — SURF-FAILURE-INDUCER-5 → R15-AGENT-027 (wrong next-step for a 400)

Code read, `errors.py` `_BODY_RULES`: body-aware branches now exist ahead of the status-only
fallback for `model_not_found` (400, "not a valid model"/"model not found"/"decommissioned"
markers → "The requested model is not available on {label} — pick another model."),
`context_overflow` (413), `insufficient_credit` (400/403/429 + credit/quota/billing
markers), and an invalid-key body check for providers that answer a bad key with 400 instead
of 401/403. A nonsense/retired slug (SURF-FAILURE-INDUCER-5's exact repro) now resolves to
`model_not_found` with an actionable message instead of the old generic "Try again or switch
provider". **Holds — fixed.**

## Not re-driven this round

- Docker-absent / SearXNG-down (`40-nodocker-status`, `41/43-*`): no register entry claims a
  fix here beyond RESEARCH-008's timing, which was re-driven above; the Settings honesty
  behaviour is unchanged code (`SettingsPanel.tsx:710,743,874` untouched by this candidate's
  diff in this area) — not re-run live to avoid a second Docker-state probe on a shared
  environment variable; **NOT TESTED this round**, no cost estimate (read-only status route,
  $0, just not exercised).
- Retired-slug / malformed-symbol battery (81-row sweep, typo-history): code-level fix
  (`_BODY_RULES` model_not_found) covers the slug half; the symbol/AttributeError half was
  live-confirmed above via the exact `/quotes/{bad}` repro. The full 81-row `harness/
malformed.py` sweep was not re-run (no register entry claims a fix outside DATA-061, already
  confirmed); **NOT TESTED this round**, $0 (no LLM calls in that sweep).
