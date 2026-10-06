# R15 Stage C batch 13: verifier verdicts

- **Merge target:** `worktree-agent-batch-13-int@e02073bd` (base `ba951d23`).
- **Stack:** the main sidecar ran from the source of a scratch worktree at e02073bd on `127.0.0.1:52310`, with a copy of the vysted-iso data dir. The MCP subprocesses were on :52153/:52154. `/health` returned ok.
- **Chain:** integrator `pnpm ci-local` passed with CI_EXIT=0 at 69fa149e (pytest 3200 passed, 1 skipped). The smoke test passed with SMOKE_EXIT=0. After the reviewer's follow-up e02073bd, the focused re-run shows 124 passed.
- **Verdict: approve.** Two entries certify and none is a regression. AGENT-090 improves the product, but its class pin is incomplete. CODE-AGENT-033 did not ship.

| id | verdict |
|---|---|
| R15-RESEARCH-007 | certified |
| R15-DOCS-017 | certified |
| R15-AGENT-090 | not certified (class gap) |
| R15-CODE-AGENT-033 | not certified (no fix landed) |

## R15-RESEARCH-007: certified

**Original repro.** Run `domain_tier` from the worktree source:

| URL | tier before | tier now |
|---|---|---|
| `medium.com/investor-diary/...` | 1 | 3 |
| `someblog.wordpress.com/ir/...` | 1 | 3 |
| `www.investors.com/news/...` | 1 | 3 |
| `reuters.com/markets/x` | 2 | 2 |

**Batch-12 fresh cases.** All of these now return 3: `ir.firebaseapp.com`, `investors.web.app`, `ir.herokuapp.com`, `www.investors.co.uk`, `ir.co.in` and `investors.com.au`.

**New fresh cases, not in any test.** All of these return 3:
`ir.repl.co`, `investors.co.nz`, `ir.vercel.app`, `investors.pages.dev`, `ir.github.io`, `ir.gitlab.io`, `investors.ne.jp`, `ir.com.br`, `ir.blogspot.co.uk`, `investors.substack.com`, `ir.s3.amazonaws.com`, `ir.appspot.com` and `investors.bitbucket.io`.

**Real company IR hosts under a ccSLD, not in any test.** All of these stay at 1:
`ir.tata.co.in`, `investors.xero.co.nz`, `ir.sony.co.jp` and `investor.vale.com.br`.

**Controls.** `ir.nvidia.com`, `investors.infosys.com` and `ir.tesla.com` stay at 1.

**Ranking.**
- `rank_sources([ir.herokuapp, investors.co.uk, ir.repl.co, Reuters])` returns `['Reuters', 'Heroku', 'CoUK', 'ReplCo']`.
- `priority_note` names only `tier-1 press: [1]`. It gives no primary record.

**Bundling.** The PSL ships inside the built binary. `pyi-archive_viewer -l` on the integrator's 12:11 `vysted-sidecar` lists `services/research/psl/public_suffix_list.dat`. `MAIN_ADD_DATA` carries the `psl` directory.

## R15-DOCS-017: certified

**Counts from the loader** (`load_india_universe`):

| universe | count |
|---|---|
| `nse-all` | 3506 |
| `bse-all` | 5042 |
| `india-all` | 5891 |

The NSE row types break down as EQ 2584, SM 571 and ETF 351.

**Live route.** `GET /screener/universe?id=` on the running sidecar returns the same numbers: nse-all 3506, bse-all 5042, india-all 5891 and sp500 503.

**The doc.** `CURRENT_STATE.md` section 3.3 quotes exactly these counts: 3,506 (EQ 2,584 + ETF 351 + SM 571), 5,042, 5,891 and 503. The stale 2,675 figure is gone. The module docstring and `models/screener.py:34` now name row types instead of counts.

## R15-AGENT-090: not certified

**Live repro, 5 trials.** Each trial ran `vy.py invoke copilot "How many ordinary shares does one SIFY ADR represent, and what is SIFY's TTM revenue in USD?"` with llama3.1:8b on ollama, autonomy ask, on :52310.

| run | outcome |
|---|---|
| 1 | Guard fired. The first delta is the fixed sentence "The ADR-to-ordinary-share ratio is not available from this session's sources." The model then says it cannot convert ₹ to USD. |
| 2 | No ratio stated. The model asked a confused clarifying question. |
| 3 | Guard fired. The fixed sentence, then "The TTM revenue for SIFY in USD is ₹4,488 crores." |
| 4 | Guard fired. The fixed sentence, then an "unavailable" statement. |
| 5 | "The terminal cannot determine the TTM revenue of SIFY." |

The bar is met: 0 of 5 runs state an untraced ratio. Batch 12 saw 3 of 5 fabricated at the same rate that the guard now fires.

**The class check fails on fresh phrasings.** `_guard_ratio_claims(text, [fundamentals result with shares_outstanding and no depositary term])`:

| claim | result |
|---|---|
| "Each SIFY ADR is equivalent to 2 ordinary shares." | replaced |
| "One ADS = 10 ordinary shares." | replaced |
| "The ADS ratio is 1:6 according to fundamentals." | replaced |
| "SIFY American Depositary Shares each represent six underlying equity shares." | **kept** |
| "Each ADR is equivalent to 2 shares of common stock." | **kept** |
| "The ADR-to-share ratio is 1 ADR : 6 shares." | **kept** |
| price range "traded from 5.20 to 7.10" | kept (correct) |
| "$6.12, up 3%" | kept (correct) |

**Why these escape.** `_CLAIM_NUMBERS` only matches a number directly followed by one of `ordinary|equity|underlying|common` and then `shares`, or a bare `N:M` / `N to M` / `N-for-M`. A two-word qualifier escapes, "shares of common stock" escapes, and "N ADR : M shares" escapes. These are ordinary 20-F and model phrasings of the same claim. As with RESEARCH-007 in batch 12, the acceptance cases pass but the class does not.

**Side effect, not a defect of the entry.** Replacement is whole-sentence. When the model puts the ratio and the revenue in one sentence, the revenue is dropped with it. In run 1, the follow-up about "this value" in ₹ refers to a figure the user never saw.

**INR half (batch-12 item 3, folded here): concur that it is outside the ratio guard.**
- The live `/fundamentals/SIFY` returns `currency: USD` and `financial_currency: INR`, so the data carries the reporting currency.
- Runs 1 and 3 keep the ₹ label rather than presenting INR as USD. Run 3's "in USD is ₹4,488 crores" is still clumsy model prose.
- No fabricated USD value appeared.

## R15-CODE-AGENT-033: not certified (no fix landed)

- **Nothing changed.** The integration diff touches none of `models/llm.py`, `services/llm/base.py`, `types/ai.ts`, `src/modules/chat/streaming.ts` or `scripts/agent_eval/grader.py`. `worktree-agent-batch-13-W1` holds only `b24a0860` (AGENT-090).
- **The live stream has no tool_result kind.** The event kinds in all 5 live trials are heartbeat, tool_use, delta and done.
- **The repro still reproduces.** `grade({'expect':{}}, [tool_use option_chain {expiry:'nearest'}, tool_result ok:false '422 invalid expiry', delta, done])` returns `[]`, which grades as a pass.

## Issues found (outside the entries' diffs)

1. `sidecar/services/screener_universe_india.py:95`: the `_nse_lookup` docstring still says "once per `india-all` symbol (~5,156)". The loader returns 5,891. This is the same count-in-comment drift DOCS-017 removed from the module docstring, and it is out of that entry's scope.
2. AGENT-090: whole-sentence replacement drops co-located facts. A clause-level replacement, or a guard that splits on `;`/` and `, would keep the revenue half.
3. llama3.1:8b run 4 claims "After retrying, I was able to fetch the required information" when no retry happened, and says TTM revenue is unavailable although `fundamentals` carries `revenue_ttm`. Run 2 invents a "Route Mobile" ambiguity. This is a model-quality issue, not a runtime one.
