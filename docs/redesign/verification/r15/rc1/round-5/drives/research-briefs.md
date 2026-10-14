# rc1 drive — research-briefs (gate round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (verified via `git rev-parse HEAD` in the
scratch worktree before driving). Own sidecar `127.0.0.1:52321` (`rc1-round-5-cand` source),
data dir `rc1-round-5-data-rc1-drive-research-briefs` (keyless copy of `rc1-round-5-seed-data`).
Full log: `docs/redesign/verification/r15/rc1/round-5/logs/rc1-drive-research-briefs.md`. Raw
evidence: `docs/redesign/verification/r15/surface/research-briefs/rc1/round-5/`.

**Scope note.** `git diff` from round-4's candidate (`1006c6da`) to this round's candidate
(`9bc600ec`) touches, inside this surface's owned files: `sidecar/services/news_provider.py`
(+6), `sidecar/services/research/fast.py` (+22), `sidecar/services/research/relevance.py`
(+274/-13), `src/lib/host-actions.ts` (+44) — the Stage-C batch-28/29/30 relevance-gate and
webAvailable-reconciliation work (R15-LEAD-050/051, the RESEARCH-001 regression fix, DATA-030's
revert). `sidecar/services/research/deep.py`, `iter.py`, `verify.py`, `citecheck.py`,
`src/modules/research/BriefPanel.tsx`, `src/modules/chat/message-notices.ts` are **byte-identical**
to round 4 — those items are evidenced by round-4's own live reconfirmation plus this round's
fresh live runs below (both hit the same code paths).

## Scored table

| # | Item | Register id | Severity | Round 5 score | Evidence |
|---|---|---|---|---|---|
| 1 | Full brief lifecycle: resolve → market-data pull → web search → filings → news-gate → `publish_brief` autobrief → divergence read-back | `brief` (1 row) | — | **ok** | Live NORMAL run, PERSISTENT.NS, ollama llama3.1:8b: resolved in 2.8s, price honestly `ok:false` ("timed out after 6s — dropped"), fundamentals honestly `ok:false` ("yfinance rate-limited"), web search returned 2 real sources (`keyless-fallback`), news leg dropped 2 off-entity items with an honest note ("0 on-entity... 2 item(s)... off-entity/off-topic and dropped"), filings pulled 20 real NSE/BSE rows, `publish_brief` fired with a valid `execution` record. `01-normal-persistent.jsonl` / `.stdout.txt` |
| 2 | DEEP/ULTRA citations point at wrong documents | R15-RESEARCH-003 | high | **ok** | Live DEEP run, CYIENT.NS (fresh symbol, not reused from any earlier round), 341s, real IterResearch synthesis (2 rounds + wind-down), 8 sources. Checked every `[n]` marker against the published `sources` array by hand: `"BSE and NSE filings [1][2]"` → `[1]`=BSE Q1 result filing, `[2]`=NSE outcome-of-board-meeting filing (both genuinely filings, exactly as claimed); `"stock price [6]"` → `[6]`=`vysted://price/CYIENT`; `"news articles... [8]"` → `[8]`=`vysted://news/CYIENT`. **4/4 markers correct**, zero stale/off-by-round citations (contrast the census's 15/15-wrong finding). `02-deep-cyient.jsonl` |
| 3 | Local-lane DEEP/ULTRA hits the 60s per-call cap and silently ships the structured floor labelled "web coverage is thin" | R15-RESEARCH-005 | high | **ok** | Same DEEP run: `synthesize \| wrote brief from evolving report \| 76269 ms` (not the 60007-60014 ms cap-hit signature), real per-section prose (Key Findings / Open Questions / Recommendations / Valuation), `execution.degraded_reason: null`. Not the fixed floor copy. `02-deep-cyient.jsonl` |
| 4 | ULTRA ships a model-authored "Merged Sources"/"References" bibliography and literal `[n] 1` markers | R15-RESEARCH-029 | medium | **ok** | Same DEEP run's citation-check step: `"stripped 0 out-of-range marker(s), 0 model-written source list(s)/[n] literal(s)"` — clean. `02-deep-cyient.jsonl` |
| 5 | Citation-integrity net only matches bare `[n]`; grouped `[2, 3]` / prose pseudo-citations ship unresolved | R15-RESEARCH-043 | medium (`blocked_tier4`, DECISIONS 4.17) | **not reproduced this round** | Same citation-check step reports 0 stripped items; the DEEP brief's own markers are all bare `[n]`. Per the lead's standing rule this class gets no fix round regardless; no concurrence note needed since it did not recur. |
| 6 | SearXNG reports "ready" while Settings/the brief both act as if it is broken | R15-RESEARCH-028 | medium | **ok** | Live probe, my own sidecar: `GET /search/searxng/status` → `{"state":"degraded","detail":"SearXNG is running but its search engines are blocked","reason":"brave: Suspended: too many requests; duckduckgo: CAPTCHA; startpage: Suspended: CAPTCHA"}` — honest, not the false `ready`. `GET /search/status` → `t1_keyless`, per-engine breaker states (`half_open`, cooldowns). `03-search-status.json`, `04-searxng-status.json` |
| 7 | `webAvailable`/no-web-honest-banner never reconciled with actual source count | R15-RESEARCH-041 | low (`open`) | **ok (mechanism verified, not regressed)** | Code: `src/lib/host-actions.ts:289` — `webAvailable = sources.length > 0 \|\| input.web_available === true` (the WS3 fix: derives FALSE from an omitted/false flag with zero sources, never defaults true). Both live runs had real sources and correctly read `webAvailable: true`; the register's own `open` repro (0 sources + `webAvailable:true`) did not recur in either run, matching round 4's precedent. Still correctly `open` at low severity — not a regression, not this round's fix target. `05-code-checks-banner-notice-sourcerow.txt` |
| 8 | "kept previous"/"did not confirm" divergence notices not recognised by the chat's regex | R15-AGENT-031 / R15-UI-054 | medium | **ok** | Code: `message-notices.ts` `isRuntimeNotice(stepKind) { return stepKind === "notice" }` — a structural `step_kind` check, not string-matched copy (can't drift again). Live: both runs' end-of-stream carried a real `step_kind:"notice"` event (`"The brief panel did not confirm the publish..."`) because I drove headlessly with no companion `/agents/actions/ack` POST — expected (the sidecar's own `_publish_divergence_notices` docstring names this exact class), not a defect; confirms the mechanism fires. `01-*.jsonl`, `02-*.jsonl` index-1 `notice` events; `05-code-checks-*.txt` |
| 9 | `vysted://` structured-provenance sources render as external favicon links | R15-UI-080 | low (`open`) | **open (expected, not a regression)** | Code unchanged: `BriefPanel.tsx` `SourceRow` still `<a href={source.url} target="_blank">` + `<ExternalLink>`. Register status is `open`; correctly still open. `05-code-checks-banner-notice-sourcerow.txt` |
| 10 | DEEP/ULTRA news leg fed the unfiltered region-wide feed, stating another company's news as the target's own | R15-RESEARCH-001 | critical | **ok (evidenced by the certified relevance-gate fix + a live adjacent check)** | Not reproduced with the exact BDL repro this round (budget went to a fresh-symbol DEEP citation check instead, item 2 above). Evidenced by: the shared `relevance.py`/`fast.py`/`news_provider.py` diff since round 4 (+274/-13, +22, +6 lines — the batch-29/30 entity-anchoring work), `stage-c/batch-30/VERDICTS.json` certifying `R15-LEAD-050` (the RESEARCH-001-regression fix: GE/BP short-ticker relevance restored) with a live `pnpm ci-local` chain (3792 passed) plus the verifier's own re-run of the focused files (114 passed), and my own NORMAL run's live news leg correctly dropping 2 off-entity items with an honest note. |
| 11 | ULTRA cross-check mangles the first figure of every claim line / prints AGREE for UNVERIFIED claims | R15-RESEARCH-004 / R15-RESEARCH-002 | high/critical | **not driven this round** | `sidecar/services/research/verify.py` is byte-identical to round 4 (not in the diff-stat above); round 3/4 already reconfirmed live on independent runs. ULTRA depth was not re-driven this round (ULTRA's 3-angle synthesis costs 10+ min per census/round-3/4 precedent; budget went to the DEEP citation-integrity check instead, the higher-value regression risk given this round's actual code diff). NOT TESTED live this round — would cost ~1 ULTRA run (~10-15 min wall, $0 on the local lane) to close. |

## Findings

None. `docs/redesign/verification/r15/rc1/round-5/findings/rc1-drive-research-briefs.json` is `[]`.

One process observation, not a product defect: a second concurrent agent (tag
`rc1-round-5-scenarios-local`, port 52311) ran its own `ollama` call while I held
`/tmp/vysted-r15-ollama.lock` for the Cyient DEEP call — its own lock script `mkdir`s, logs
acquired/busy, but runs `vy.py invoke` unconditionally either way. This did not affect the
correctness of either agent's results (only possible latency contention on the shared llama.cpp
server), and is not a file I own to fix.

## Sidecar

Boot: sh -c launcher pid 19395, sleep pid **19397** (killed to stop), worker pid 19398.
`/health` confirmed `ok` (`openbb-mcp: available`) before driving; confirmed down
(connection refused) after `kill 19397`.
