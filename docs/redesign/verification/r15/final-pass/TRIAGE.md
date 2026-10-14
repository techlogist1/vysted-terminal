# Final-pass triage at d38b5d1a

Fresh context, claude-opus-5-5 (effort high), label final-triage. This agent neither found nor will fix these findings. Rubric applied in order: R4, R5, R3 (against `git show d38b5d1a:docs/redesign/verification/vysted-r15-register.json`, snapshot `register-at-d38b5d1.json`, plus this pass's own entries R15-LEAD-125..135 already in the working register), then R1 and R2.

**Register not edited.** `git diff --quiet d38b5d1a -- docs/redesign/verification/vysted-r15-register.json` fails: the lead's working copy adds LEAD-125..135 and moves LIFECYCLE-001 and LEAD-123 to fixed. The 38 new entries (R15-FINAL-001..038) are in `REGISTER_ADDITIONS.json` for the lead to merge. register_edited = false.

**Re-runs.** I re-ran repros on my own sidecar :52880 (final-cand source, seed copy). Commands: `raw/final-triage/rr.sh`. Output: `raw/final-triage/rr.out`. All of these reproduced:
- AMAL.NS market_cap null vs AMAL.BO 8.69e9
- SUNRAJDI pe_ratio 155.5 beside eps 0.23
- SIFY revenue_currency INR on 191.7M
- GSTL NSE+BSE rows both INE632W01016/540654, with results from GlobalSpace (BSE)
- YASHOPTICS 404 'check the symbol'
- autocomplete 'Zeal Aqua' returns []
- RELIANCE.BO history latest 2025-12-31 vs .NS 2026-06-30
- 2 of 60 /news titles carry &amp;

In-process Brave: 429 in 0.7 s, while curl in the same minute got 200 (`raw/final-triage/brave.out`). I stopped the sidecar by killing its sleep pid 28950.

**R7.** No admitted id is at 3 or more certification failures, so nothing is stopped and no DECISIONS item is drafted. Prior failures: R15-AGENT-027 2, R15-RESEARCH-022 2, R15-CODE-PLATFORM-072 1, R15-LIFECYCLE-024 1. All others are 0, and new entries are 0. One more not_certified verdict on AGENT-027 or RESEARCH-022 stops it.

**Gate list notes:**
- **R15-LEAD-123** (open in the register at the sha) is not admitted. Its fix IS the sha: d38b5d1a is the merge of 45e3da32, certified by a fresh Opus verifier, and the working register already reads fixed. LS-1 passed at the sha.
- **R15-UI-084** stays needs_gui (R5 list). Its rig steps were appended to NEEDS_GUI.md.
- The other 30 open critical/high/medium entries are carried as admitted existing entries.

## Admitted new entries

| id | sev | area | keys | title | note |
|---|---|---|---|---|---|
| R15-FINAL-001 | critical | ui-panels, agent-chat | maintainer:2 | A bare-ticker portfolio lot is re-priced against a different listing when the session region changes: INFY 20 @ Rs1,500 shows -$29,779.20 (-99.26%) under region US, and the CSV export carries it | Class sibling of R15-DATA-002 (blocked_tier4, DECISIONS 4.15) on a surface no DATA-002 attempt touched (portfolio); filed separately per the lead's precedent in DECISIONS 4.15 (sibling note, LEAD-127). R2: a fabricated money P&L shown as true = critical (finder said high). |
| R15-FINAL-002 | high | data-smallcaps, research-search | investor:5 | NSE SME GSTL (Globesecure Technologies) is stamped with BSE GSTL Globalspace Technologies' ISIN INE632W01016 / scrip 540654, so its results calendar, announcements, corporate actions and shareholding split merge a different company's BSE filings | regression of R15-LEAD-059 (class of R15-CODE-DATA-001): the FOCUS repro holds, a fresh case of the same class does not. Re-run by final-triage on own :52880: /resolve?q=GSTL NSE+BSE rows both INE632W01016/540654; /disclosures/results?symbol=GSTL -> 10 events company GlobalSpace Technologies Limited |
| R15-FINAL-003 | high | data-smallcaps, agent-chat | investor:3, investor:9 | After the exchange-filed overlay replaces EPS, P/E stays on the provider EPS the payload says is not served (SUNRAJDI P/E 155.5 beside served EPS 0.23 at 12.44; true ~54), the flag reason quotes a third implied P/E 141.1, and the copilot tells the user the 155.5 'is indeed right' | regression of R15-DATA-013. investor:9 (gpt-4o-mini, hosted lane, AC-1) is the chain of the same mechanism: one item, both keys. Re-run by final-triage on own :52880: /fundamentals/SUNRAJDI eps 0.23, pe_ratio 155.5. |
| R15-FINAL-004 | high | research-search, data-smallcaps | investor:12 | Deep brief for FOCUS (Focus Lighting and Fixtures) states unrelated common-word headlines (Flydubai pilot podcast 'Focus on flying', European shares 'focus on inflation data') as the company's own sentiment and strategy | regression of R15-RESEARCH-001 (off-entity evidence in DEEP briefs); overlaps open R15-LEAD-056 (non-IN DOW alias) but the IN gate path is distinct. Code verified at the sha: sidecar/services/research/relevance.py:650-700, :735-752. |
| R15-FINAL-005 | high | data-smallcaps, ui-panels | investor:2 | Every NSE Emerge (SME) listing has no fundamentals: /fundamentals 404s telling the user to check the symbol, and income/balance return empty 200s with no reason (YASHOPTICS, SUMAX, QUALIANCE, GANESHIN, VOLERCAR) | New (sibling of fixed R15-DATA-017 / R15-LEAD-034, whose repros hold). Re-run by final-triage on own :52880: /fundamentals/YASHOPTICS -> 404 not_found 'check the symbol'. |
| R15-FINAL-006 | high | ui-panels | drive-portfolio-notes:1 | Portfolio quote fan-out wedges the sidecar: per-symbol /quotes GETs abort at the 30 s client budget, the in-flight guard releases on the abort while the server keeps working, and each tick re-requests every symbol (0/100 resolved over 210 s; RELIANCE quote >40 s on the same sidecar) | New: the rc1 fix (dcb09674, rc1-drive-portfolio-notes:1) was never a register entry; R15-LIFECYCLE-027's default budget (f1182138) defeats it. |
| R15-FINAL-007 | high | agent-chat | drive-portfolio-notes:2 | With the Portfolio panel closed, get_portfolio stamps every non-crypto holding with the session region's currency, so a USD AAPL lot is served to the agent as currency INR and the copilot states 'AAPL - 2 shares, cost basis Rs190' | regression of R15-AGENT-091 (the field exists; the store fallback asserts the wrong value). Not R4: the wrong currency is in the product's tool result. |
| R15-FINAL-008 | high | lifecycle | FI-FINAL-CORRUPT-CACHE-BRICKS-BOOT, maintainer:5 | A corrupt SQLite store is never quarantined: a corrupt data_cache.db (pure cache) fails sidecar startup on every launch, and a corrupt custom_agents.db / delegate_runs.db / plugins.db 500s every route of that store until the file is deleted by hand | Same mechanism found twice in this pass (failure-inducer per-db matrix surface/failure-inducer/final/83-corrupt-each-db-boot.txt and maintainer LS-2): one item, both keys. Class sibling of fixed R15-DATA-090 (workspace JSON only). |
| R15-FINAL-009 | medium | data-smallcaps, ui-panels | investor:1 | AMAL (NSE, the default IN bind) serves market_cap and shares_outstanding unavailable while the same ISIN on BSE (AMAL.BO) serves both in the same sidecar | regression of R15-DATA-048. Re-run by final-triage on own :52880: /fundamentals/AMAL market_cap null; /fundamentals/AMAL.BO market_cap 8690951168. |
| R15-FINAL-010 | medium | data-smallcaps | investor:4 | SIFY analyst revenue estimate (USD-sized 191.7M) is labelled revenue_currency INR, a ~64x understatement against Sify's quarterly revenue INR 12,352 M, and the Earnings estimate grid renders it | regression of R15-DATA-113. Re-run by final-triage on own :52880: /earnings/SIFY/estimates revenue_estimate_mean 191700000.0 revenue_currency INR. |
| R15-FINAL-011 | medium | data-smallcaps, ui-panels | investor:6 | Symbol autocomplete never offers the BSE company of a same-ticker collision: 'Zeal Aqua', 'Sanathnagar Enterprises', ZEAL.BO and SEL.BO return only the NSE namesake or nothing, though /resolve binds the BSE company | New: distinct mechanism from R15-LEAD-130 (former name / scrip code). Re-run by final-triage on own :52880: autocomplete 'Zeal Aqua' -> []; ZEAL.BO -> only NSE Zeal Global Services. |
| R15-FINAL-012 | medium | data-smallcaps | investor:7 | RELIANCE.BO earnings history is two quarters stale against the NSE listing of the same company (latest 2025-12-31 vs 2026-06-30) and its analyst consensus differs (36 vs 26 analysts), with no staleness or listing-basis note | New. Re-run by final-triage on own :52880: /earnings/RELIANCE.BO/history latest 2025-12-31; /earnings/RELIANCE.NS/history latest 2026-06-30. |
| R15-FINAL-013 | medium | agent-chat | investor:10 | 'Should I buy Amal Ltd?' on gpt-4o-mini gets a buy lean justified by an industry P/E comparison no tool fetched | Hosted lane, outside the R4 class; judged under R1 as a product gap in the copilot prompt (an advice posture), not mere model prose. |
| R15-FINAL-014 | medium | agent-chat | maintainer:1, battery3-agent022-local-text-toolcall | Ollama lane: a tool call leaked as a Python-literal dict (None/True/False) is not rescued; the raw call blob is shown as the assistant reply | regression of R15-AGENT-018 (class gap). battery3 (AGENT-022 Sumax prompt, cost_basis: None) is the same mechanism: one item. Safety held in every sample (nothing staged or applied). |
| R15-FINAL-015 | medium | release | maintainer:7 | THIRD_PARTY_NOTICES.md lists the wrong version for 56 of 121 main-sidecar Python components because transitive deps are unpinned and the bundle ships what pip resolved at build time | New. No package missing and no licence family changed in the drifted set. |
| R15-FINAL-016 | medium | agent-chat, ui-panels | drive-panels-layouts:nd-1 | arrange_layout custom reports success ('Arranged sec_filings_list' / 'Arranged your panels') when no panel token resolves and the layout is unchanged | New. |
| R15-FINAL-017 | medium | ui-panels | drive-portfolio-notes:3 | A holding whose symbol answers 404 raises the transport-failure banner 'Couldn't refresh live quotes' with a Retry that can never succeed, and the 404 is re-requested every 5 s | New: converse of fixed R15-UI-004. |
| R15-FINAL-018 | medium | research-search | drive-research-briefs:3 | With the ULTRA slider one user turn fans out into N sequential full ULTRA heavy runs (4 research calls -> ~19 min, ~$1.25, each brief replacing the last) | New. |
| R15-FINAL-019 | medium | research-search, ui-panels | drive-settings-plugins:searxng-daemon-down-install-copy | Settings SearXNG card tells a user whose Docker/OrbStack is installed but stopped that Docker 'isn't available' and to install it, ignoring docker.cli_present/daemon_running and the sidecar's 'start Docker/OrbStack' detail | New: distinct from fixed R15-LIFECYCLE-007 (PATH resolution). |
| R15-FINAL-020 | medium | research-search | battery2-brave-impersonated-fetch-429 | Keyless web search: the Brave engine (impersonated fetch) gets HTTP 429 while a plain-UA curl from the same host gets 200 in the same minute, so keyless web_search returns zero rows on this network | Re-run by final-triage 18:2x IST: in-process BraveSearchBackend.search -> SearchError HTTP 429 in 0.7 s; curl -A Mozilla/5.0 -> 200 (raw/final-triage/brave.out). Not a regression of R15-RESEARCH-008. |
| R15-FINAL-021 | medium | docs | F-DOCS-001 | docs/SIDECAR_API.md ('the contract') documents 20 of 111 live routes and states an allow-all-origins CORS posture, a 501 macro hook and stub routers that the running sidecar contradicts | New. Verified at the sha: SIDECAR_API.md:16 'the sidecar allows all origins'. |
| R15-FINAL-022 | medium | docs | F-DOCS-002 | R12_HAND_TESTING_GUIDE.md, the only hand-testing guide, walks an order-placement 'safety showcase', a brokers plugin and a paper portfolio removed by D81 | New. Verified at the sha: R12_HAND_TESTING_GUIDE.md:37. Document only; no product order surface (D81 holds). |
| R15-FINAL-023 | medium | release | F-DOCS-004 | RELEASE_RUNBOOK.md step 1 tells the operator to merge the superseded worktree-agent-r15-version-0.9.0 branch although the 0.9.0 bump is already in the sha | New. Verified: git merge-base --is-ancestor 517da226 d38b5d1a -> 1; RELEASE_RUNBOOK.md:14-15. |
| R15-FINAL-024 | low | data-smallcaps | investor:8 | Ownership witness flags a near-agreeing institutions figure with a false reason: Yahoo 0.00% vs filed 0.03% (AMAL) is flagged 'disagrees ... beyond 3pp' | New. |
| R15-FINAL-025 | low | research-search | investor:11 | DEEP research overran its 180 s wall budget by 79 s (259 s) on the local lane: the final synthesis call is not boxed by the remaining wall | New. Runtime budget, not the R4 figure class. |
| R15-FINAL-026 | low | ui-panels | maintainer:3 | Screener freshness line prints unrounded float seconds ('quotes 41.64699196815491s ago') | New. Verified at the sha. |
| R15-FINAL-027 | low | ui-panels, research-search | maintainer:4 | News titles keep raw HTML entities: the News Feed shows 'F&amp;O Talk: ...' literally (and the agent news tool gets the same) | New. Re-run by final-triage on own :52880: 2 of 60 /news titles carry &amp;. |
| R15-FINAL-028 | low | lifecycle | maintainer:6 | A bundle sidecar that cannot bind its port dies with SIGABRT (exit 134, Fatal Python error _enter_buffered_busy on the stdin watchdog) instead of a clean non-zero exit | New. |
| R15-FINAL-029 | low | platform | maintainer:8 | transform.code size caps are bypassed by sum(list, start): a 25-character expression builds an uncapped list (8.3 GB peak RSS) and keeps running after the 5 s timeout | regression of R15-CODE-PLATFORM-066 (class gap; its own repros hold). |
| R15-FINAL-030 | low | agent-chat | drive-composer-chat:nd-1 | write_note files a note under the literal company name ('COCHIN SHIPYARD') instead of the ticker, so the symbol's note view (COCHINSHIP) stays empty | New; class sibling of fixed R15-CODE-FRONTEND-014 (scope 'global'). |
| R15-FINAL-031 | low | lifecycle | drive-panels-layouts:nd-2 | delete_workspace leaves <name>.vysted-workspace.bak behind, so a later corrupt-file recovery of a same-named workspace resurrects the deleted workspace's content | New. |
| R15-FINAL-032 | low | ui-panels | drive-panels-layouts:reg-1 | A local-model narrative written with markdown-bold headers (**TAKE** / **BULL** ...) collapses to a flat summary + insights; the five typed fields come back empty | regression of R15-UI-094 (one sample; model formatting varies). |
| R15-FINAL-033 | low | ui-panels | drive-portfolio-notes:4 | A whitespace-only Avg cost saves the holding at cost basis 0, and a hex quantity '0x10' saves as 16 | regression of R15-UI-078. Verified at the sha. |
| R15-FINAL-034 | low | ui-panels, research-search | drive-research-briefs:2 | Brief header reads 'web + structured data' directly above the 'Structured data only - no web sources found' banner on a filings-only brief | Residual of R15-RESEARCH-041 named in its refuter note. |
| R15-FINAL-035 | low | docs | F-DOCS-003 | MCP_INTEGRATION.md names 25 tools; the live MCP surface lists 39 | New. |
| R15-FINAL-036 | low | docs | F-DOCS-005 | CURRENT_STATE.md cites a missing build report, the deleted monte_carlo.py and an absent ConnectCard.tsx, and reports 0.8.0 and 619 vitest / 942 pytest | New. |
| R15-FINAL-037 | low | release | F-DOCS-006 | RELEASE_RUNBOOK.md's 'verbatim' ci-local block differs from package.json ci-local | New. |
| R15-FINAL-038 | low | platform | F-DOCS-008 | MCP discovery file advertises protocol 2025-06-18 while /mcp/status reports 2025-11-25; the Rust sync comment points at a constant that does not exist | Sibling of fixed R15-CODE-AGENT-022 (which fixed /mcp/status only). Verified at the sha. |

**Severity changes vs the finders (R2):**
- R15-FINAL-001 is raised from high to critical. It shows a fabricated money P&L (-99.26%) as true, in the panel and in the CSV export.
- R15-FINAL-003 merges investor:3 (finder: medium) and investor:9 (finder: high) at high. This is the class grade of R15-DATA-013.
- R15-FINAL-008 merges FI-FINAL (finder: high) and maintainer:5 (finder: medium) at high.
- Every other entry keeps the finder's severity.

**maintainer:2 vs R15-DATA-002.** DATA-002's root-cause text is generic. However, every DATA-002 attempt touched only the watchlist, EO, chart, palette and agent-add. The lead's own ruling in DECISIONS 4.15 (sibling note) files untouched surfaces separately; that is how LEAD-127 was filed. I therefore filed this as its own entry, not as an attachment.

## Duplicates (one item, every key kept)

- investor:9 -> R15-FINAL-003
- maintainer:5 -> R15-FINAL-008
- battery3-agent022-local-text-toolcall -> R15-FINAL-014
- drive-research-briefs:1 -> R15-LEAD-134
- F-DOCS-007 -> R15-LEAD-129

Why:
- **investor:9** is the copilot chain of investor:3's P/E mechanism.
- **maintainer:5** is a different store with the same unhandled `sqlite3.DatabaseError`.
- **battery3** is the same Python-literal `cost_basis: None` leak; its battery lane filed it as known_limitation against AGENT-022, but AGENT-022 is not a class entry and the leak is not a figure.
- **drive-research-briefs:1** is LEAD-134's mechanism: fast.py `_NO_WEB_NOTE` is used for unreachable/timeout reasons. I recommend re-grading LEAD-134 to medium.
- **F-DOCS-007** is the README provider list from LEAD-129. Its stale test counts belong in the same README pass.

## Attached (ATTACHED.json)

- maintainer:att-ls1-coldboot -> R15-LEAD-123
- maintainer:att-ac5-origin -> R15-CODE-AGENT-001
- investor:att-ds1-bareamal -> R15-DATA-002
- maintainer:att-ui3-foreign -> R15-UI-090
- investor:att-rs4-decisions41 -> DECISIONS 4.1 (rc1-battery-4:1, FR-070 FAST budget)
- maintainer:att-ls3-openbbkill -> R15-DATA-061
- drive-research-briefs:att-lead060 -> R15-LEAD-060
- drive-research-briefs:att-research043 -> R15-RESEARCH-043
- drive-research-briefs:att-lead128 -> R15-LEAD-128
- drive-research-briefs:att-agent027 -> R15-AGENT-027
- drive-screener:att-1 -> R15-LEAD-069
- drive-screener:att-2 -> R15-LEAD-076
- drive-panels-layouts:att-news-reliance -> R15-DATA-030
- drive-panels-layouts:att-sec-in-502 -> R15-DATA-061
- drive-settings-plugins:import-fontsize-only-toast -> R15-LEAD-089
- drive-settings-plugins:privacy-copy-overpromise -> R15-LEAD-068
- drive-onboarding-stranger:att-keychain-denied -> R15-UI-044
- drive-onboarding-stranger:att-ollama-unreachable-start-copy -> R15-LEAD-133
- drive-failure-inducer:att-agent027-groq413 -> R15-AGENT-027
- drive-failure-inducer:att-lead071-outage-cached-empty -> R15-LEAD-071
- FI-FINAL-HANG-NETWORK-COPY -> R15-AGENT-027
- F-DOCS-009 -> R15-DOCS-003
- drive-research-briefs:4 -> DECISIONS 4.1 (rc1-battery-4:1, FR-070 FAST budget)

Attachments added by triage:
- **FI-FINAL-HANG-NETWORK-COPY -> R15-AGENT-027.** The errors.py class heuristic gives a hosted timeout the network copy. AGENT-027's note names the same heuristic for Ollama.
- **F-DOCS-009 -> R15-DOCS-003.** README is in its files.
- **drive-research-briefs:4 -> DECISIONS 4.1.** That item covers FAST dropping the first-brief fundamentals leg. The price half was already attached to LEAD-128.

The lanes' own attachments were checked against the register by id and found consistent.

## Known limitation (R4, local lane llama3.1:8b, figure for a subject with no ok tool call)

- investor:kl-1 -> R15-LEAD-037
- drive-composer-chat:kl-1 -> R15-LEAD-037
- drive-composer-chat:kl-2 -> R15-LEAD-030
- drive-research-briefs:kl-1 -> R15-LEAD-030
- drive-screener:kl-1 -> R15-LEAD-030
- battery1-known-limitation-agent033-bdl-figures -> R15-LEAD-030
- maintainer:kl-1 -> R15-LEAD-038

KNOWN_LIMITATION_INSTANCES.json now carries a `triage` field on each row. The battery-1 AGENT-033 instance was added to it.

## Needs GUI (R5, NEEDS_GUI.md, DEFERRED)

- drive-composer-chat:gui-1: arrange_layout compare apply needs a mounted dockview; jsdom half honest (NEEDS_GUI.md)
- drive-composer-chat:gui-2: composer collapse ladder paint at real dock widths (NEEDS_GUI.md)
- drive-research-briefs:ng-1: BriefPanel favicon onError / export paint need the rig (NEEDS_GUI.md)
- drive-onboarding-stranger:gui-links-pull-keychain: external links, live model download and keychain denial need a real window/native dialog (NEEDS_GUI.md)
- R15-UI-084: R5 operator-attended list; maximize paint needs a real window (1 prior gui-round not_certified)

## Refuted

- investor:env-1: Environment, not a product defect (R1b): OpenRouter free-pool 404/429 and DeepSeek 402 (unfunded) were each answered with humanized provider errors; probes recorded in scenarios/AC-1.md:20-23. (evidence docs/redesign/verification/r15/final-pass/scenarios/AC-1.md)
- investor:kl-2: Local-model prose claim ('brief contains news') with no figure: outside the R4 figure class, and under R1b model prose not rendered as data; the structured card is correct. (evidence docs/redesign/verification/r15/final-pass/raw/investor/rs1-ollama-normal.jsonl)
- investor:kl-3: Local-model invented ambiguity question with no figure: outside the R4 class; R1b model prose, the resolve result (KPITTECH) is correct and nothing renders it as data. (evidence docs/redesign/verification/r15/final-pass/raw/investor/kpit-ollama.log)
- investor:kl-4: Local-model misreading of an ok tool result in prose, no figure: outside the R4 class; R1b model prose, not rendered as data. (evidence docs/redesign/verification/r15/final-pass/raw/investor/ac1/ac1-ollama-p4-conflict.log)

## Not mine, noted

This pass's xadv lanes were triaged separately (XADV_TRIAGE.md). Its entries are in the working register:
- LEAD-127 (fixed)
- LEAD-128..134
- LEAD-135 (medium, open)
- LEAD-125/126 (from the GUI round)

They are not re-ruled here. R15-FINAL-011 is distinct from LEAD-130, and R15-FINAL-005 is distinct from DATA-017/LEAD-034, whose repros hold.

## Gate-3 load

Critical/high items for the closure round:

- R15-FINAL-001 (critical, new), prior_failures 0
- R15-FINAL-002 (high, new), prior_failures 0
- R15-FINAL-003 (high, new), prior_failures 0
- R15-FINAL-004 (high, new), prior_failures 0
- R15-FINAL-005 (high, new), prior_failures 0
- R15-FINAL-006 (high, new), prior_failures 0
- R15-FINAL-007 (high, new), prior_failures 0
- R15-FINAL-008 (high, new), prior_failures 0

- **Mediums:** 45 admitted in total, new and existing. Under the operator's bar they are filed for 0.9.1 unless writers have room.
- **New lows:** 15. These are listed, not gated.
