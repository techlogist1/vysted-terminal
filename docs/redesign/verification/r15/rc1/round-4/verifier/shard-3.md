# rc1 gate round 4 — adversarial sample verifier, shard 3 (rc1-vshard-3)

Candidate: `68d5573aff9a579af084dcbb124843f2aecff6e8` (read-only worktree `scratchpad/rc1-round-4-1006c6d-fix-int`).
Own sidecar: `:52603` from worktree source, data dir `scratchpad/rc1-round-4-data-rc1-vshard-3`; shared `:52153/:52154` MCPs read-only.
Scratch harness: vitest config `scratchpad/vs3/vt/vitest.config.mts` (root = worktree, include = scratch tests only); Python checks run `cd $W/sidecar && ./.venv/bin/python3 <scratch script>`.
Model: Opus (claude-opus-5-5[1m]). Findings: `findings/rc1-vshard-3.json`. Log: `logs/rc1-vshard-3.md`.

## Verdicts

| Entry | Verdict | Evidence (literal + fresh variant) |
|---|---|---|
| R15-CODE-FRONTEND-012 | holds | `/portfolio` router is GET-only; fresh: update lot h-2 + delete h-1 through the gate -> only `/agents/actions/ack` fetched, zero `/portfolio` URLs (vs3/a.out) |
| R15-DATA-089 | holds | same run: no sync / sidecarPositionId path remains; apply cases are local-store only |
| R15-CODE-PLATFORM-022 | holds | PUT/DELETE portfolio routes gone; router.routes GET-only. Adjacent: `purchased_at` still advertised in portfolio_add/update schemas (finding 9) |
| R15-LEAD-004 | **refuted** | literal (KANORICHEM, TCS) holds, fresh NDTV fails: `curl -s http://127.0.0.1:52603/fundamentals/NDTV` -> revenue_ttm/net_income_ttm reason "TTM basis: the exchange filings do not cover the trailing year in four quarters (a half-yearly filer) — annual, not trailing-4Q; kept, flagged". NSE lane lengths [3,3,3,6,3] (Sep-2025 quarter missing); screener.in shows NDTV files quarterly incl. Sep-2025. In-process `FiledPeriods` of 3-month periods with one hole -> `cadence()=="half-yearly"`. The label is still derived from coverage, not period lengths (fix_shape unmet). Suspected `exchange_financials.FiledPeriods.cadence`, `correctness_gate._ttm_basis` |
| R15-LEAD-015 | holds | live DHANBANK quarterly gaps ['2025-09-30']; fresh `_mark_gaps`: 2 consecutive missing quarters, half-yearly missing half, annual missing year, 3-period one-gap all marked; annual ISO labels on openbb (JONJUA, TCS, MSFT) |
| R15-DATA-050 | holds | JONJUA, ICON, SAFE, BSE 544257, ELCIDIN -> 200 with BSE results; AAPL, ZZZZNOTREAL -> 200 coverage not_applicable + note |
| R15-AGENT-036 | holds | fresh `vs3/runs_fresh.py` via the HTTP router: launch -> ask_user pause -> answer (header key) -> token breach -> resume. Resume request = [ORIGINAL, A1, [ask_user → Q1?], ANSWER ONE, B1, "Continue the task…"] — prompt first, answer in place, no replay |
| R15-AGENT-035 | holds | same run on provider=openrouter model=vendor/model-x: get_provider('openrouter') and model vendor/model-x on all 3 segments, key present each segment, cost 5002 -> 5004 (accumulates), no key bytes in runs.db; Resume control in AgentsRail -> `resumeDelegateRun` with `X-LLM-Api-Key` |
| R15-LIFECYCLE-013 | holds | paused state reached through ask_user (status paused, question "Q1?"), `/runs/{id}/answer` 200 resumed; run row persists provider/model (live ollama llama3.1:8b row below) |
| R15-UI-023 | holds | fresh vitest `vs3/vt/d-chart.test.tsx`: (F1) timeframe 1d->1h with /indicators 503 -> both drawn line series removed; (F2) SAR via chart-command `loadSymbol` with /indicators resolving before /history -> no marker writes until INFY candles commit, then markers against INFY closes. 2/2 pass |
| R15-UI-031 | **refuted** | visible race fixed (fresh `vs3/vt/e-equity.test.tsx`: superseded load settling LAST or rejecting LAST never lands; narrative only for newest; 2/2 pass), but fix_shape "(and abort the prior request)" is unimplemented: no AbortController/signal in `doLoad` (EquityOverviewPanel.tsx:712-747) or `loadEquityOverview(symbol, region)`; superseded loads keep six sidecar requests running. Low severity |
| R15-CODE-FRONTEND-017 | **refuted** | earnings fresh case holds (watchlist-scoped newer load keeps NVDA payload), but SEC slices: late `loadFilingDetail(A-1)` after B-2 ready sets activeAccession back to "A-1"; late AAPL insider 504 after MSFT ready leaves insiderStatus "error"/"EDGAR timeout" on MSFT. Only `loadFilings` has a generation. Per-slice generation fix_shape unmet |
| R15-RESEARCH-038 | holds | fresh Crash(RuntimeError) + Hang(deadline) engines: 1 search -> each breaker 1 failure, closed; 2 searches -> open (one failure per engine turn) |
| R15-RESEARCH-024 | holds | Brave-shaped row keeps domain moneycontrol.com + published_at 2026-08-13T10:00:00Z through `_dispatch` and `deep._record_web` |
| R15-UI-038 | holds | legacy Sonar reuters -> news, bseindia -> filing, vysted:// -> research |
| R15-UI-037 | holds | "Avg cost / share" label, "per share" placeholder, "Avg cost" column. Adjacent: CSV export header still "Cost basis" (finding 8) |
| R15-AGENT-043 | **refuted** | literal (nested sub-group bad leaf) reported; fresh: `{criteria:[{roe gt "15"},{market_cap gt 1000}], group:{and:[pe_ratio lt 20]}}` -> "Wrote 1 screener criterion — review and Run", no drop note; roe leaf silently dropped (`dropped: group ? groupDropped : [...]`). Adjacent: with run:true the flat AND group never runs (finding 6) |
| R15-AGENT-041 | holds | update-undo restores {h-1 INFY 5@1400}, status undone; AUTO-mode portfolio delete stays staged/pending |
| R15-UI-012 | holds | HTML 502 -> "sidecar returned 502"; 422 array -> "prompt: Field required; max_wall_secs: Extra inputs are not permitted" |
| R15-CODE-PLATFORM-011 | holds | live 422 from `:52603/agents/buffett/runs`; delegate launch shows "Could not start: prompt: Field required; max_wall_secs: Extra inputs are not permitted" (workflow.ts raw text already open as R15-CODE-FRONTEND-027) |
| R15-RESEARCH-032 | holds | 422 array -> "SearXNG status unavailable: probe: Input should be a valid boolean"; window focus re-read -> Ready, alert clears; live `/search/searxng/status` probes the container |
| R15-UI-019 | holds | code: banner gated on keyless readiness (Ollama the only keyless provider), dismissal durable via keychain BANNER_ACCOUNT |
| R15-CODE-AGENT-006 | holds | live `/llm/providers` default + known models equal `model_registry.json` for all 8 providers; TS side imports the JSON |
| R15-AGENT-055 | **refuted** | description half fixed (JSON single source), panel sets still differ: single-focus agent=[chart] vs menu technical=[chart,watchlist,news]; compare agent=[chart] vs menu compare-desk=[chart,equity-overview]; research-cockpit agent adds news. fix_shape test "same panel set per template id" fails; menu label "Compare" still collides with agent 'compare' |

## Adjacent (not refutations)

1. medium — flat AND screener group never runs (`runScreener` sends only `criteria` unless nested/or); label counts the group leaf (near R15-AGENT-043).
2. low — `src/store/quant.ts` slices have no generation guard (near R15-CODE-FRONTEND-017).
3. low — CSV export header "Cost basis" (near R15-UI-037).
4. low — `purchased_at` advertised, never persisted (near R15-CODE-PLATFORM-022).

## Live delegate run (LIFECYCLE-013 literal shape)

Run under the Ollama lock (one call per hold), own sidecar `:52603`, sha 68d5573a:

- `POST /agents/copilot/runs {"provider":"ollama","model":"llama3.1:8b","budget":{"maxTokens":300}}` -> run 51add8e4… -> `error` "token ceiling 300 reached (7582 used)", row provider ollama / model llama3.1:8b, cost 7582 tokens / 1 step; `/api/ps` = ['llama3.1:8b'].
- `POST /runs/51add8e4…/resume` -> 200 `{"resumed":true}` -> `error` "token ceiling 300 reached (7584 used)", row still ollama / llama3.1:8b, cost 15166 tokens / 2 steps (accumulated); `/api/ps` = ['llama3.1:8b'] (no Qwen swap).

Artifacts: `scratchpad/vs3/live013-launch.out`, `live013-resume.out`, `runs_fresh.out`, `d.out`, `e.out`.
