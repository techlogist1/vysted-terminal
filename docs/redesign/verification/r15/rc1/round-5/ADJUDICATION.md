# rc1 gate round 5 — adjudication

Adjudicator pass under gate rule change 1. Worktree `worktree-agent-rc1-r5-adjudicate`,
base `origin/004-r4-experience-rebuild` @ e5877962. Inputs: round-5 verifier findings
(`docs/redesign/verification/r15/rc1/round-5/verifier/`), `rc1-vshard-triage.json`,
`failure-counts.json`. Output: `vysted-r15-register.json`/`.md` edited append-only
(status flips on the 4 regressions only; every other edit is a note append; 57 new
entries appended, ids R15-LEAD-059..115).

## THE BAR — round-5 reading

1. **Deterministic chain green** — holds; round-5 carried no deterministic-chain failure
   into this adjudication (nothing in the round-5 verifier/triage inputs reopens it).
2. **Gate 8 holds** — holds; no round-5 finding touches Gate 8's own repro.
3. **Every `fixed` register entry still passes its OWN stated repro** — 4 do not
   (see Regressions below) and reopen to `open`. The remaining 20 `refuted`-verdict
   non-holds entries from `rc1-vshard-triage.json` all HOLD their own stated repro —
   what the vshard triage found was a *different* claim, so per the bar those stay
   `fixed` and the new claim is filed separately (Class-refuted below), never reopening
   the original.
4. **Open critical+high == 0** — was true entering round 5; round 5 files one new high
   (R15-LEAD-059) inside the gate's one bounded fix round for new criticals/highs.
   **Open critical/high after filing: 1 (R15-LEAD-059).** This does not
   satisfy item 4 as stated — R15-LEAD-059 is the round's bounded fix-round item, per
   gate rule change 1 ("new criticals/highs get one bounded fix round inside the gate").
   No entry reached the three-failure rule this round; R15-LIFECYCLE-020 stays at 2
   (see its class-refuted note).

## 1. Regressions (4) — reopened to `open`

Own stated repro reproduced on the verifier's round-5 re-run. Per the bar this is the
only path back to `open`; nothing else in this adjudication reopens an entry.

| id | own-repro re-run | certification failures |
|---|---|---|
| R15-CODE-PLATFORM-072 | docs/redesign/verification/r15/rc1/round-5/verifier/refutations/cp072.out.txt (reproduced) | 1 |
| R15-LIFECYCLE-024 | docs/redesign/verification/r15/rc1/round-5/verifier/refutations/l024.out.txt (reproduced) | 1 |
| R15-RESEARCH-022 | docs/redesign/verification/r15/rc1/round-5/verifier/refutations/r022.out.txt (reproduced) | 2 |
| R15-AGENT-027 | docs/redesign/verification/r15/rc1/round-5/verifier/refutations/a027.out.txt (reproduced) | 2 |

Disposition under gate rule change 1: none of the 4 qualifies as a NEW critical/high (all
were already-registered highs/mediums reopening on their own repro, not new findings), so
none is in the round's bounded fix round — they stay `open`, first 0.9.1 batch.

## 2. New entries (57) — R15-LEAD-059 through R15-LEAD-115

Source: `rc1-verifier.json` `new_defect`/`chain` rows (36, keys `rc1-verifier:5`..`:40`,
row 24 is the one `chain`-kind row, `CROSS-PLATFORM-002`) + `vshard-triage.json`
`adjacent[]` items (42) minus 21 dedup pairs (20 verifier/adjacent overlaps + 1
adjacent-internal DATA-068/LEAD-039 merge folded into R15-LEAD-109) = 57 filed. One high
(R15-LEAD-059, filed first per the DO list), then mediums ascending, then lows ascending.
No exact duplicate found against any of the 679 pre-existing entries (checked by near-id
title comparison), so all 57 are filed as new — none reopens an existing entry.

| id | sev | source | title | files |
|---|---|---|---|---|
| R15-LEAD-059 | high | rc1-verifier:5 | FOCUS announcements merge the BSE feed of a different company (BSE scrip 543312) with Focus Lighting and Fixtures NSE items under one symbol | sidecar/services/corporate_disclosures.py; sidecar/services/symbol_resolver.py |
| R15-LEAD-060 | medium | rc1-verifier:6 | Verifier verdict text wrapped in underscore emphasis (_UNVERIFIED_ / __UNVERIFIED__) parses as AGREE | sidecar/services/research/verify.py:130 (_parse_verdict: \bWORD\b defeated by underscore) |
| R15-LEAD-061 | medium | rc1-verifier:7 | strip_model_bibliography misses common bibliography heading variants, so a model-written source list survives beside the verified one | sidecar/services/research/citecheck.py:75,94 |
| R15-LEAD-062 | medium | rc1-verifier:8 + rc1-vshard-7 adjacent | A Gemini free-tier per-minute 429 (RESOURCE_EXHAUSTED ... retry in Ns) is shown as "out of credit or quota. Add credit or check your plan" | sidecar/services/errors.py (humanize rules) |
| R15-LEAD-063 | medium | rc1-verifier:9 | historyForSend drops the oldest turns once the thread passes 60k chars with no notice to the user or the model | src/store/chat-history.ts:296 |
| R15-LEAD-064 | medium | rc1-verifier:10 | 20-F ownership lane returns not_applicable with 0 holders for ADRs whose 20-F has a holders table (IBN, HDB) | sidecar/services (20-F ownership parser) |
| R15-LEAD-065 | medium | rc1-verifier:11 | FAST research web-only branch (no instrument resolves) awaits _web_round without a time box; only the resolved branch uses asyncio.wait_for | sidecar/services/research/fast.py:597 |
| R15-LEAD-066 | medium | rc1-verifier:12 + rc1-vshard-0 adjacent | write_screener_filters with only the documented OR/nested group tree is rejected: schema requires criteria | sidecar/services/agent_tools/catalog.py (write_screener_filters schema) |
| R15-LEAD-067 | medium | rc1-verifier:13 + rc1-vshard-3 adjacent | Macro search failure renders as an empty "No matching series": the store catches every error and stores []; keyless FRED search is a 502 with an actionable message | src/store/macro.ts:120 |
| R15-LEAD-068 | medium | rc1-verifier:14 + rc1-vshard-4 adjacent | Settings privacy copy over-promises: "Nothing leaves this machine except calls you make to providers you configure" while keyless lanes (Yahoo, NSE/BSE, DDG) call out without configuration | src/components/SettingsPanel.tsx:122; src/components/SettingsPanel.tsx:1324 |
| R15-LEAD-069 | medium | rc1-verifier:15 + rc1-vshard-5 adjacent | Screener formula validate accepts a boolean operand in a comparison ("roe > (pe_ratio < 15)", "(pe_ratio > 3) > 0.5") and coerces it | sidecar/services/screener_formula.py |
| R15-LEAD-070 | medium | rc1-verifier:16 + rc1-vshard-4 adjacent | Analyst ratings swallow a Yahoo rate-limit into an empty 200 list that reads as no coverage | sidecar/services/analyst_ratings_extended.py:189-203 |
| R15-LEAD-071 | medium | rc1-verifier:17 + rc1-vshard-2 adjacent | A Yahoo rate-limit on earnings history is swallowed as an empty history and cached for 24 h | sidecar/services/earnings_provider.py:225-275; sidecar/routers/earnings.py |
| R15-LEAD-072 | medium | rc1-verifier:18 + rc1-vshard-1 adjacent | Heavy/ULTRA brief stopped by its spend ceiling publishes note=None, and the cross-check keeps spending after the breach | sidecar/services/research/iter.py; sidecar/services/agent_tools/deep_research.py |
| R15-LEAD-073 | medium | rc1-verifier:19 + rc1-vshard-1 adjacent | The latest round's tool results are never elided by _fit_to_window, so a multi-result round leaves the answer below the 1/8 reserve | sidecar/services/agent_runtime.py |
| R15-LEAD-074 | medium | rc1-verifier:20 + rc1-vshard-1 adjacent | Scheduled and MCP-run workflows run with no event sink: action.notify_desktop reports notified:true but nothing is shown | sidecar/services/workflow_scheduler.py:136; sidecar/services/mcp_server.py:277-301 |
| R15-LEAD-075 | medium | rc1-verifier:21 + rc1-vshard-1 adjacent | Editing a custom agent silently clears its default_model on save (customSpecToSummary sets defaultModel: null) | src/store/agents.ts:128; src/modules/agent-builder/AgentBuilderPanel.tsx |
| R15-LEAD-076 | medium | rc1-verifier:22 + rc1-vshard-2 adjacent | A partially throttled screen shows "No rows matched - loosen a threshold / Reset filters" although most symbols were never evaluated | src/modules/screener/ScreenerResultsTable.tsx |
| R15-LEAD-077 | medium | rc1-verifier:23 + rc1-vshard-2 adjacent | A focused SEC Filings panel publishes identifier, not symbol, so the agent context names the wrong symbol | src/modules/sec/SecFilingsPanel.tsx:164; src/modules/chat/context-provider.ts |
| R15-LEAD-078 | medium | rc1-verifier:24 + rc1-vshard-4 adjacent | Flaky test_research_fast::test_fast_web_round_runs_alongside_a_time_boxed_fan_out: an unstubbed earnings-quality leg makes it timing-dependent | sidecar/tests/test_research_fast.py |
| R15-LEAD-079 | medium | rc1-verifier:25 + rc1-vshard-4 adjacent | ReasoningSplitter releases a held reasoning echo in full when an answer follows it (provisional, shard evidence only) | sidecar/services/llm/reasoning_split.py |
| R15-LEAD-080 | medium | rc1-verifier:26 + rc1-vshard-5 adjacent | Agent/MCP compute_greeks and price_option return QuantLib-unit vega/theta/rho unlabelled; the model restated them as per-unit values | sidecar/services/agent_tools/quant_tools.py; sidecar/services/agent_tools/catalog.py |
| R15-LEAD-081 | medium | rc1-verifier:27 + rc1-vshard-6 adjacent | sp500 screen serves S&P 500 member PTC as PTC India Limited (INR) from a fundamentals row written before the LEAD-044 fix; no migration purges it | sidecar/services/fundamentals_store.py; sidecar/services/screener.py; sidecar/services/fundamentals_warm.py |
| R15-LEAD-082 | medium | rc1-verifier:28 + rc1-vshard-7 adjacent | Screener top-K round-robin gives currency-less rows their own group slot, so a null-market-cap row displaces a real one | sidecar/services/screener.py |
| R15-LEAD-083 | medium | rc1-verifier:29 + rc1-vshard-7 adjacent | Earnings drill-down As-of chip shows the client fetch clock and ignores the envelope server as_of | src/store/earnings.ts; src/modules/earnings/EarningsCalendarPanel.tsx |
| R15-LEAD-084 | low | rc1-verifier:30 | NSE holiday table ends 2026-12-25; 2027-01-26 (Republic Day) is treated as an IN trading day (D-B9-4 covers the test horizon, not the data) | sidecar/services (NSE holiday table) |
| R15-LEAD-085 | low | rc1-verifier:31 | Suffixed unknown symbols (QQZZFAKE.NS, XYZNOTATICKER.BO) still return 200, 0 bars, reason null | sidecar/routers/history |
| R15-LEAD-086 | low | rc1-verifier:32 | The sibling [failed: ...] trailer still rides verbatim assistant history to the provider (_without_step_trailers strips only [tool steps:]) | sidecar/services/agent_runtime.py:660; src/store/chat-history.ts |
| R15-LEAD-087 | low | rc1-verifier:33 | Ratio guard still replaces a correct ADS-ratio sentence dated 26-Jun-2026 / Jun-26-2026 with "not available" | sidecar/services (ratio guard) |
| R15-LEAD-088 | low | rc1-verifier:34 + rc1-vshard-3 adjacent | Resolver suggestions for MAZAGONDOCK / RELIANCEIND variants | sidecar/services/symbol_resolver.py |
| R15-LEAD-089 | low | rc1-verifier:35 | Import toast says "Imported settings." for {settings:{fontSize}} when nothing applied | src/components/SettingsPanel.tsx:2044-2081; src/components/SettingsPanel.test.tsx:394-404 |
| R15-LEAD-090 | low | rc1-verifier:36 | Cross-check extract still slow before the wall timeout (verdict leg boxed) | sidecar/services/research |
| R15-LEAD-091 | low | rc1-verifier:37 | Type-first JSON tool-call text can leak into the visible answer | sidecar/services/agent_runtime.py |
| R15-LEAD-092 | low | rc1-verifier:38 | _row_value has a twin implementation that can drift | sidecar/services/screener.py |
| R15-LEAD-093 | low | rc1-verifier:39 | One doc line still says "the 18" host actions while the others and the catalog say 19 | docs/ |
| R15-LEAD-094 | low | rc1-verifier:40 | sidecar/agents/copilot.json system prompt example reply "Built you a brief on NVDA - it's at the top of the cockpit" teaches an applied-tense claim that conflicts with review mode (local rb1/rb4 overclaim) | sidecar/agents/copilot.json |
| R15-LEAD-095 | low | rc1-vshard-0 adjacent | Bond pricer display currency fixed at mount; region switch while open keeps USD | src/modules/quant/BondPricerPanel.tsx:127 |
| R15-LEAD-096 | low | rc1-vshard-0 adjacent | leading_token reads a negated COMPLETE sentence as complete | sidecar/services/research/deep.py |
| R15-LEAD-097 | low | rc1-vshard-1 adjacent | A scrip with one trade inside 52 weeks keeps a forward-fill-derived provider 52w low unflagged when it is within the 10% tolerance | sidecar/services/yfinance_provider.py; sidecar/services/disclosures/range_check.py |
| R15-LEAD-098 | low | rc1-vshard-1 adjacent | The announcements cache key includes limit and the raw symbol form, so callers that differ in limit or .NS suffix refetch the full history | sidecar/services/corporate_disclosures.py; sidecar/services/agent_tools/disclosure_tools.py; sidecar/routers/disclosures.py |
| R15-LEAD-099 | low | rc1-vshard-2 adjacent | save_screen overwrites the user's live screener draft without disclosing it; Undo does not restore the draft | src/lib/host-actions.ts; src/store/screener.ts; src/lib/host-actions.test.ts |
| R15-LEAD-100 | low | rc1-vshard-2 adjacent | _us_isin caches a definite ISIN miss for the life of the process | sidecar/services/symbol_resolver.py:672 |
| R15-LEAD-101 | low | rc1-vshard-2 adjacent | CONTRIBUTING.md says 'Python 3.13+' but the build requires exactly 3.13 | CONTRIBUTING.md:26; scripts/build-python.mjs (WANT='3.13') |
| R15-LEAD-102 | low | rc1-vshard-3 adjacent | Ollama adapter catch-all humanizes internal exceptions as an Ollama error | sidecar/services/llm/ollama.py:206-210; sidecar/services/llm/ollama.py:279-283 |
| R15-LEAD-103 | low | rc1-vshard-3 adjacent | Onboarding local-model recommendation collapses any sidecar failure to 'Couldn't reach the local engine' | src/lib/hardware-fit.ts:63-74; src/components/OnboardingFlow.tsx:646 |
| R15-LEAD-104 | low | rc1-vshard-3 adjacent | Perplexity/Sonar ResearchSource builders drop published_at | sidecar/services/research/perplexity.py:180; sidecar/services/research/sonar.py:201 |
| R15-LEAD-105 | low | rc1-vshard-4 adjacent | OpenRouter chat URL literal in research lanes | sidecar/services/research/sonar.py:42; sidecar/services/agent_tools/deep_research.py:795 |
| R15-LEAD-106 | low | rc1-vshard-5 adjacent | SEC company search is a raw substring match | src/modules/sec/SecFilingsPanel.tsx; src/store/sec.ts; sidecar/services/sec_filings_provider.py |
| R15-LEAD-107 | low | rc1-vshard-5 adjacent | add_chart_drawing: a non-empty bogus panelId bypasses the open-chart fallback | src/lib/host-actions.ts; sidecar/services/agent_tools/catalog.py |
| R15-LEAD-108 | low | rc1-vshard-5 adjacent | BLUEPRINT says 12 AI agents; 13 first-party agents ship | docs/BLUEPRINT.md:20; docs/BLUEPRINT.md:615 |
| R15-LEAD-109 | low | rc1-vshard-7/9 adjacent (merged) | /earnings/{sym}/estimates maps a yfinance 429 to 502 provider_error 'unexpected response', while /fundamentals/{sym}/ratings maps the same throttle to 429 rate_limited | sidecar/services/earnings_provider.py:239-240 |
| R15-LEAD-110 | low | rc1-vshard-7 adjacent | A listed 1994 JPM 10-K opens as 502 'unexpected response' (sec-edgar-mcp get_filing_sections NoneType) instead of degrading to the raw filing text | sidecar/services/sec_filings_provider.py |
| R15-LEAD-111 | low | rc1-vshard-9 adjacent | clearSearch does not bump searchGeneration; late 501 paints error under emptied SEC search field | src/store/sec.ts (clearSearch) |
| R15-LEAD-112 | low | rc1-vshard-9 adjacent | 200 F&O bhavcopy with truncated PK zip raises BadZipFile out of fetch_latest_fo, no walk-back | sidecar/services/option_chain.py |
| R15-LEAD-113 | low | rc1-vshard-9 adjacent | Stale 'client-side mathjs' comments in node-registry.ts:185-190 and code-node-run.ts header | src/modules/node-editor/node-registry.ts:185-190; src/modules/node-editor/code-node-run.ts |
| R15-LEAD-114 | low | rc1-vshard-10 adjacent | nse_bhavcopy.py:36-40 docstring says the NSE master is '~2,675 symbols' and that SME (SM/ST) rows are 'outside the master'; the master is now 3506 rows including 571 SM | sidecar/services/nse_bhavcopy.py:36-40 |
| R15-LEAD-115 | low | rc1-vshard-10 adjacent | The quarterly-gap TTM reason always says 'a quarter of the trailing year' is unfiled, which understates the gap for fresh listings with only one or two quarters ever filed | sidecar/services/exchange_financials/correctness_gate.py:586-590 |

### Dedup decisions (one line each)

- Every `rc1-verifier:N` key that also had a same-defect `vshard-N adjacent` item merged
  into one filed entry (see the `source` column above, e.g. R15-LEAD-062, R15-LEAD-066..083,
  R15-LEAD-088) — verifier's title/repro/files won over the adjacent item's shorter note
  where both existed.
- R15-LEAD-109 additionally merges the `rc1-vshard-9` DATA-068-adjacent item into the
  `rc1-vshard-7` earnings-provider item — both describe the same throttle-to-error-code
  mapping divergence between `/earnings/estimates` and `/fundamentals/ratings`, filed once.
- The remaining verifier-only rows (R15-LEAD-059/060/061/064/065/084/085/086/087/089/090/
  091/092/093/094) had no adjacent counterpart — filed straight from `rc1-verifier.json`.
- The remaining adjacent-only rows (R15-LEAD-095..115 except 109) had no verifier
  counterpart — filed straight from `vshard-triage.json`'s `adjacent[]`, files backed by
  an explicit file:line in the evidence text where present, else the nearest existing
  register entry's own `files` array (8 entries: R15-LEAD-090/093/096/098/106/107/114 area).

### Not filed (1)

- `rc1-verifier.json` row 41 (`kind: "environment"`): 3 uncommitted lines in
  `spend-ledger.jsonl` at checkout time — a run-hygiene observation about the verification
  harness itself, not a product defect. Not filed; no register entry.

## 3. Class-refuted (20) — stays `fixed`, class claim filed separately

Own stated repro HOLDS on the verifier's round-5 re-run (`docs/redesign/verification/r15/
rc1/round-5/verifier/refutations/*`, cited per-entry in the appended note). The vshard
triage's `refuted` verdict answers a *different* question — a new claim the investigator
found while re-running the repro — so per the bar these stay `fixed` and the new claim is
either filed as a new entry above or dispositioned as already covered.

| id | shard | disposition |
|---|---|---|
| R15-CODE-DATA-001 | 0 | filed as R15-LEAD-059 |
| R15-CODE-DATA-005 | 0 | filed as R15-LEAD-092 |
| R15-RESEARCH-029 | 0 | filed as R15-LEAD-061 |
| R15-RESEARCH-006 | 1 | filed as R15-LEAD-090 |
| R15-AGENT-040 | 2 | filed as R15-LEAD-063 |
| R15-DATA-060 | 3 | filed as R15-LEAD-064 |
| R15-AGENT-044 | 3 | filed as R15-LEAD-088 |
| R15-LEAD-023 | 4 | already covered by decision D-B9-2 (operator decision, DECISIONS_FOR_OPERATOR.md) |
| R15-DATA-073 | 4 | filed as R15-LEAD-084 |
| R15-UI-058 | 4 | filed as R15-LEAD-089 |
| R15-DOCS-016 | 5 | filed as R15-LEAD-093 |
| R15-LEAD-026 | 5 | filed as R15-LEAD-085 |
| R15-RESEARCH-002 | 7 | filed as R15-LEAD-060 |
| R15-CODE-AGENT-033 | 7 | already covered by R15-CODE-AGENT-033 (self) |
| R15-LEAD-031 | 8 | filed as R15-LEAD-091 |
| R15-LEAD-033 | 8 | filed as R15-LEAD-086 |
| R15-AGENT-095 | 9 | filed as R15-LEAD-087 |
| R15-RESEARCH-027 | 9 | filed as R15-LEAD-065 |
| R15-LEAD-044 | 9 | filed as R15-LEAD-081 |
| R15-LIFECYCLE-020 | 10 | already covered by R15-LIFECYCLE-020 (self); certification failures stay at 2 |

R15-UI-058 has no `refutations/` file (its own-repro-holds citation is the `shard-4.md`
reference in `rc1-verifier.json` row 35 instead) — noted in its append rather than a
missing-file citation.

## 4. Inconclusive (5) — no note-worthy status change, live re-proof blocked

Yahoo 429 blocked round-5 live re-proof for all 5; each has a verified battery raw file on
disk from an earlier pass, so this does not count as a failure under the bar.

| id | shard | battery raw |
|---|---|---|
| R15-DATA-048 | 5 | docs/redesign/verification/r15/rc1/round-5/battery/raw/set-41/R15-DATA-048.txt |
| R15-LEAD-039 | 9 | docs/redesign/verification/r15/rc1/round-5/battery/raw/set-72/R15-LEAD-039-RDY.txt (+ SONY, TM in the same set) |
| R15-DATA-113 | 9 | docs/redesign/verification/r15/rc1/round-5/battery/raw/set-75/R15-DATA-113.txt |
| R15-DATA-008 | 9 | docs/redesign/verification/r15/rc1/round-5/battery/raw/set-77/R15-DATA-008.txt |
| R15-DATA-055 | 9 | docs/redesign/verification/r15/rc1/round-5/battery/raw/set-77/R15-DATA-055.txt |

## Final counts

Before: `{'raw': 887, 'entries': 679, 'rejections': 76, 'critical': 16, 'high': 121, 'medium': 305, 'low': 237}`
After: `{'raw': 887, 'entries': 736, 'rejections': 76, 'critical': 16, 'high': 122, 'medium': 329, 'low': 269}`

**open critical/high after filing: 1 (R15-LEAD-059)**

## Uncertain / flagged for the operator

- **R15-LEAD-023 / R15-DATA-073** class-refuted dispositions ("already covered by decision
  D-B9-2" / filed as R15-LEAD-084 citing D-B9-4): the own-repro-holds citation reads as
  still showing the underlying symptom in isolation; I deferred to `R15_GATE_RC1.md`'s
  explicit framing that these are adjudication matters already settled by operator
  decisions D-B9-2/D-B9-4, not fresh certification failures, without re-litigating the raw
  refutation text myself.
- **R15-LEAD-094** (copilot.json applied-tense example reply): filed as a straight analogy
  from row 40's evidence text against `sidecar/agents/copilot.json`'s systemPrompt — no
  vshard-adjacent counterpart to cross-check against, lower confidence than the other
  verifier-sourced rows.

18:16 IST
