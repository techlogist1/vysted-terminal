# RC1 Findings — merged

Merged from all 18 `docs/redesign/verification/r15/rc1/findings/*.json` files into `FINDINGS.json` (69 findings total), sorted by kind then severity. No new judgement — every row below is copied verbatim from its source file.

| Key | Kind | Severity | Register id | Title | Source file |
|---|---|---|---|---|---|
| rc1-datapack:1 | regression | critical | R15-DATA-008 | SIFY revenue_ttm/net_income_ttm still served as INR-scale numbers under currency:"USD" (partial fix) | rc1-datapack.json |
| rc1-verifier:1 | regression | critical | R15-RESEARCH-002 | verify._parse_verdict still reads a negative verdict as 'agree' unless UNVERIFIED is the first token (re-confirms rc1-vshard-0:1 at 1d6511c8) | rc1-verifier.json |
| rc1-vshard-0:1 | regression | critical | R15-RESEARCH-002 | verify._parse_verdict still reads a negative verdict as 'agree' when the verdict word is not literally first | rc1-vshard-0.json |
| rc1-verifier:11 | regression | high | R15-LEAD-010 | SEC filing viewer still 404s a listed filing on any caller that sends no form hint, and the /sections route ignores form_type; entry is 'fixed' but certified... | rc1-verifier.json |
| rc1-verifier:2 | regression | high | R15-DATA-002 | The Cmd-K live Tickers row loads the chart with the bare symbol and no exchange/region, so picking the US AMAL row in an IN session charts Amal Limited (NSE)... | rc1-verifier.json |
| rc1-verifier:3 | regression | high | R15-AGENT-019 | A question-shaped portfolio write request is classified read-only and the write tools are stripped (re-confirms rc1-vshard-0:3) | rc1-verifier.json |
| rc1-verifier:4 | regression | high | R15-AGENT-003 | On a budget halt the runtime has already yielded the halted round's tool_use events, which it never dispatches; delegate runs lift them into proposed changes... | rc1-verifier.json |
| rc1-verifier:5 | regression | high | R15-RESEARCH-007 | The IR host-prefix rule still ranks non-primary hosts as tier-1 PRIMARY (re-confirms rc1-vshard-1:1) | rc1-verifier.json |
| rc1-verifier:6 | regression | high | R15-UI-090 | Quote freshness still reads 'eod' for an Indian index during NSE hours (re-confirms rc1-vshard-1:2) | rc1-verifier.json |
| rc1-vshard-0:2 | regression | high | R15-DATA-002 | The Cmd-K palette's per-listing ticker row loads the chart without a region, so a US AMAL pick in an IN session charts Amal Ltd (NSE, INR) | rc1-vshard-0.json |
| rc1-vshard-0:3 | regression | high | R15-AGENT-019 | A question-shaped portfolio write request is classified as a read and write tools are stripped | rc1-vshard-0.json |
| rc1-vshard-0:4 | regression | high | R15-AGENT-003 | On a budget halt the runtime yields tool_use events it never dispatches, and delegate runs turn them into proposed changes | rc1-vshard-0.json |
| rc1-vshard-1:1 | regression | high | R15-RESEARCH-007 | The IR host-prefix rule still ranks non-primary sources as PRIMARY. investors.com (Investor's Business Daily, a news site) and ir./investors. subdomains on a... | rc1-vshard-1.json |
| rc1-vshard-1:2 | regression | high | R15-UI-090 | Quote freshness still uses the wrong calendar for any instrument that is not detected as Indian. yfinance-served Indian indices (^NSEI, ^BSESN), bare-symbol ... | rc1-vshard-1.json |
| rc1-datapack:2 | regression | medium | R15-DATA-058 | Sify (ADR) name-search: SIFY now included but still ranked last despite the highest score | rc1-datapack.json |
| rc1-verifier:10 | regression | medium | R15-DATA-059 | US identity still empty on a ticker resolve (re-confirms rc1-vshard-3:1) | rc1-verifier.json |
| rc1-verifier:12 | regression | medium | R15-DOCS-017 | CURRENT_STATE.md s3.3 still says sp500 is 506 symbols (sp500.json has 503) and omits nse-all/bse-all/india-all (re-confirms rc1-vshard-3:3) | rc1-verifier.json |
| rc1-verifier:7 | regression | medium | R15-DATA-043 | A top-K cut over a mixed-currency screen keeps the first currency group and drops the 'ranked within each currency' note (re-confirms rc1-vshard-0:6) | rc1-verifier.json |
| rc1-verifier:8 | regression | medium | R15-AGENT-027 | errors.humanize still gives the wrong next step for common provider errors (re-confirms rc1-vshard-0:5) | rc1-verifier.json |
| rc1-verifier:9 | regression | medium | R15-DATA-068 | GET /fundamentals/{symbol}/ratings still carries no as_of (re-confirms rc1-vshard-2:1) | rc1-verifier.json |
| rc1-vshard-0:5 | regression | medium | R15-AGENT-027 | errors.humanize still gives the wrong next step for common provider errors | rc1-vshard-0.json |
| rc1-vshard-0:6 | regression | medium | R15-DATA-043 | A top-K cut over a mixed-currency screen silently keeps the alphabetically-first currency group and drops the 'ranked within each currency' note | rc1-vshard-0.json |
| rc1-vshard-2:1 | regression | medium | R15-DATA-068 | GET /fundamentals/{symbol}/ratings (analyst consensus, 6h data_cache) still carries no as_of; the route discards the fetch time, so the Equity Overview 'Anal... | rc1-vshard-2.json |
| rc1-vshard-3:1 | regression | medium | R15-DATA-059 | US identity still empty on a ticker resolve: /resolve?q=ONC and ?q=SIFY return isin=null and former_name=null although former_names.json carries BeiGene and ... | rc1-vshard-3.json |
| rc1-vshard-3:2 | regression | medium | R15-LEAD-010 | The windowed get_filing lookup still 404s a listed 10-K on every caller that sends no form hint: GET /sec/filings/{acc}/sections and the data.fetch_sec_filin... | rc1-vshard-3.json |
| rc1-vshard-3:3 | regression | medium | R15-DOCS-017 | CURRENT_STATE.md section 3.3's screener bullet is stale again and still omits nse-all/bse-all/india-all: it says sp500 is 506 symbols dated 2026-06-04 and 'R... | rc1-vshard-3.json |
| rc1-drive-onboarding-stranger:1 | regression | low | R15-LEAD-030 | Reclassification note (not a new finding): a fresh instance of the already-adjudicated, blocked_tier4 R15-LEAD-030 class ('local model narrates a fabricated ... | onboarding-stranger.json |
| rc1-drive-portfolio-notes:2 | regression | low | R15-UI-035 | P4/P4b delete-control harness replay needed a rewrite for a new ConfirmButton arm/confirm gate, not a regression in the fix itself | rc1-drive-portfolio-notes.json |
| rc1-verifier:13 | regression | low | R15-DOCS-018 | CURRENT_STATE.md s3.3 still omits the India provider chain and still calls yfinance the no-key default for equities (re-confirms rc1-vshard-3:4) | rc1-verifier.json |
| rc1-verifier:14 | regression | low | R15-CODE-PLATFORM-013 | Plugin 'on' is still split: the Settings > Modules toggle writes only the module map, the Marketplace writes runtime + plugins.db (re-confirms rc1-vshard-3:5) | rc1-verifier.json |
| rc1-vshard-3:4 | regression | low | R15-DOCS-018 | CURRENT_STATE.md section 3.3 still says nothing about the India provider chain (nse_direct 15 / nse 20 / bse 25 ahead of yfinance 50) and still calls yfinanc... | rc1-vshard-3.json |
| rc1-vshard-3:5 | regression | low | R15-CODE-PLATFORM-013 | Plugin 'on' is still split: the Settings > Modules toggle writes plugin:<id> only in the module map, so the Marketplace shows the plugin enabled and active w... | rc1-vshard-3.json |
| rc1-verifier:21 | gate8 | low |  | GET /plugins still lists a persisted 'tradesa-v2' row (enabled:true, installed:true) and a 'vysted-kite' row from a legacy profile; no code, manifest or cata... | rc1-verifier.json |
| rc1-drive-portfolio-notes:1 | new_defect | high |  | Portfolio quote auto-refresh has no overlap guard or request cancellation, causing an unbounded in-flight backlog once any symbol resolves slowly | rc1-drive-portfolio-notes.json |
| rc1-fix-r1-recheck:1 | new_defect | high |  | rc1-scenarios:5 not closed: the financial_statements tool hands the model raw INR statement sizes with no currency key, so SIFY revenue is still stated as ~$... | rc1-fix-r1-recheck.json |
| rc1-fix-r2-recheck:1 | new_defect | high |  | rc1-scenarios:5 not closed on llama3.1:8b: the SIFY ADR ratio is still fabricated as 1:1 (true 1 ADS = 6 shares); the currency half is fixed | rc1-fix-r2-recheck.json |
| rc1-scenarios:1 | new_defect | high |  | price_data's silent 90-bar cap masquerades as a '52-week' window; the model states an internally-impossible 52-week-low/current-price relationship as fact | rc1-scenarios.json |
| rc1-verifier:16 | new_defect | high |  | rc1-scenarios:5 is not closed at 1d6511c8: llama3.1:8b still fabricates SIFY's ADR ratio (now '1:2'; true 1 ADS = 6 shares) with no tool field behind it; the... | rc1-verifier.json |
| rc1-drive-research-briefs:2 | new_defect | medium |  | Citation-integrity net only recognises a bare '[n]' marker; a bracketed group '[2, 3]' or a prose pseudo-citation '[New findings]' ships as literal, unresolv... | rc1-drive-research-briefs.json |
| rc1-fix-r1-recheck:2 | new_defect | medium |  | rc1-drive-onboarding-stranger:1 not closed: keyless llama3.1:8b still answers the first-run Zomato question with an invented price presented as fetched resul... | rc1-fix-r1-recheck.json |
| rc1-fix-r1-recheck:3 | new_defect | medium |  | rc1-battery-4:1 not closed on the FAST (normal) research depth: a cold Indian name's price and fundamentals legs are still dropped at the 6 s box; the fix on... | rc1-fix-r1-recheck.json |
| rc1-fix-r2-recheck:2 | new_defect | medium |  | rc1-drive-onboarding-stranger:1 not closed: the leaked-call half is fixed, but keyless llama3.1:8b still presents an invented Zomato price as fetched, in pro... | rc1-fix-r2-recheck.json |
| rc1-fix-r2-triage:1 | new_defect | medium |  | Earnings estimates label a foreign reporter's revenue estimate in the trading currency: WIT's next-quarter revenue estimate 244,246,846,490 (INR-sized) is se... | rc1-fix-r2-triage.json |
| rc1-verifier:15 | new_defect | medium | R15-DATA-043 | A row with no fundamentals currency (and a null market cap) ranks FIRST in a market_cap-desc screen: the DATA-043 currency grouping sorts on fundamentals.cur... | rc1-verifier.json |
| rc1-verifier:17 | new_defect | medium |  | rc1-fix-r2-triage:1 still open at 1d6511c8 with no disposition in the fix loop: WIT revenue estimate 244,246,846,490 is labelled USD (it is INR) | rc1-verifier.json |
| rc1-vshard-0:7 | new_defect | medium | R15-DATA-006 | A BSE quote before the open reports change 0.0 for the last session's real move | rc1-vshard-0.json |
| rc1-vshard-2:2 | new_defect | medium |  | After every research call fails (Tier B 401, error steps on the stream), the copilot still replies 'Built you a brief on Infosys - it's at the top of the coc... | rc1-vshard-2.json |
| rc1-fix-r1-triage:1 | new_defect | low |  | nse_provider.get_archive_text and _SessionHolder.ensure wait on the process-wide throttle while holding the module _lock, contra the R15-DATA-066 pace-before... | rc1-fix-r1-triage.json |
| rc1-fix-r2-recheck:3 | new_defect | low |  | Leak hold starts after the marker's first tokens have streamed, so a dangling fragment such as '{"name": "price_data' or '**Tool call:** `price_da' remains i... | rc1-fix-r2-recheck.json |
| rc1-gate8:1 | new_defect | low |  | The review card and the applied label price an agent's portfolio write in the REGION currency, not the listing's: a US holding reads 'Add 10 AAPL @ ₹0 to the... | rc1-gate8.json |
| rc1-gate8:2 | new_defect | low |  | Portfolio CSV export writes Market value, P&L and P&L % as raw binary floats (805.3499999999999, 11.454545454545455) while Weight % is rounded to 2 dp | rc1-gate8.json |
| rc1-gate8:3 | new_defect | low |  | 'Buy 10 shares of AAPL at market' under AUTO: llama3.1:8b emits portfolio_add_position with an invented cost_basis 0 (the runtime accepts it though the tool ... | rc1-gate8.json |
| rc1-vshard-0:10 | new_defect | low | R15-AGENT-021 | Exchange-verbatim corporate_actions / exchange_deals / sec_filings_list text reaches the model unfenced | rc1-vshard-0.json |
| rc1-vshard-0:11 | new_defect | low | R15-UI-001 | An agent write_note that lands inside the 600 ms typing debounce discards the user's unsaved keystrokes | rc1-vshard-0.json |
| rc1-vshard-0:8 | new_defect | low | R15-DATA-006 | The NSE direct quote stamps most_recent_session, which is a latent pre-open misdate | rc1-vshard-0.json |
| rc1-vshard-0:9 | new_defect | low | R15-CODE-FRONTEND-004 | Workspace names differing only by case overwrite each other on case-insensitive filesystems | rc1-vshard-0.json |
| rc1-vshard-1:3 | new_defect | low |  | read_notes and write_note key a note by the exact uppercase scope string, so the same stock split across two forms (DIXON vs DIXON.NS) reads back as 'The use... | rc1-vshard-1.json |
| rc1-vshard-3:6 | new_defect | low | R15-LEAD-013 | The regenerated US seed pack leaves out exactly the constituents LEAD-013 added (BXP, NVR, UDR, plus ECHO and VMRK), so a cold, throttled sp500 screen still ... | rc1-vshard-3.json |
| rc1-vshard-3:7 | new_defect | low | R15-LIFECYCLE-024 | The pre-upgrade backup keys on the app version string while the migrations key on user_version, so the shipped 0.8.0 profile (marker 0.8.0) is migrated 0 -> ... | rc1-vshard-3.json |
| rc1-verifier:18 | chain | high |  | Register criterion not met: 5 c/h/m entries are open (AGENT-017 high; AGENT-049, LEAD-028, RELEASE-007, UI-088 medium) and R15-LEAD-010 (high) is 'fixed' but... | rc1-verifier.json |
| rc1-verifier:19 | chain | high |  | Fixed-name battery has no raw output for 160 of 376 fixed ids (1 critical, 48 high, 109 medium, 2 low); raw set-12 and set-46 are empty, and no findings file... | rc1-verifier.json |
| rc1-verifier:20 | chain | medium |  | Agent-scenario transcripts are incomplete and predate the fix rounds: 11 of 20 OpenRouter runs ended in an upstream provider error ("Upstream error from Nvid... | rc1-verifier.json |
|  | register_note | low |  | New instance of the local-model untraced-claim pattern surfaced via the AGENT-090 ratio guard, on a tool path the batch-16 certification did not exercise | rc1-battery-5.json |
| rc1-battery-3:1 | environment | medium | R15-DATA-056 | BSE shareholding SHP index blocked (403 Akamai) from this dev IP, pre-existing at base | rc1-battery-3.json |
| rc1-datapack:3 | environment | low | R15-DATA-003 | BSE shareholding index returned 403 Forbidden for every BSE-only symbol this run, not just AMAL/SMR | rc1-datapack.json |
| rc1-drive-failure-inducer:1 | environment | low |  | Shared SearXNG's DDG/Brave/Startpage engines are currently CAPTCHA'd/rate-limited (upstream, not candidate code) | rc1-drive-failure-inducer.json |
| rc1-fix-r2-recheck:4 | environment | low |  | OpenRouter nemotron-3-super-120b free lane returned upstream 5xx ('Upstream error from Nvidia: Service temporarily overloaded') on 2 of 3 exact scenarios:5 runs | rc1-fix-r2-recheck.json |
| rc1-verifier:22 | environment | low |  | BSE shareholding is HTTP 403 from this host; the route surfaces it as 502 'The data provider returned an unexpected response. Retry' for every BSE-only name | rc1-verifier.json |
|  | environment | n/a |  | batch-7/W4-research-funnel register/task data mismatch: 12 assigned ids do not exist | rc1-battery-5.json |

## Counts

By kind: regression=32, gate8=1, new_defect=26, chain=3, register_note=1, environment=6


By severity: critical=3, high=18, medium=23, low=24, n/a=1