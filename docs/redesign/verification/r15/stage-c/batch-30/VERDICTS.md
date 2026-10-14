# R15 Stage C: batch-30 verdicts

- **Verifier:** Opus 5.5 with a fresh context, 27 Sep 2026.
- **Merge target:** `worktree-agent-batch-30-int@67c56430`.
- **Setup:** a scratch worktree at that SHA ran its own main sidecar from source on `127.0.0.1:52310`, with MCP on :52153/:52154 and the data dir copied from `vysted-iso/data`. A second scratch worktree at base `19a70e80` was used only for in-process base-versus-head comparisons.
- **Chain:** the integrator's `pnpm ci-local` exited 0 on run 2 at `67c56430` (3792 passed, 1 skipped), and smoke exited 0. The verifier re-ran `test_news`, `test_research_relevance`, `test_b7_exchange_financials` and `test_news_tool`: 114 passed.
- **Outside world:** real headlines came from Google News RSS, 100 per query, with the publisher suffix stripped. Real BSE and NSE filings came through the live `exchange_financials` lane.

| Entry | Verdict |
|---|---|
| R15-LEAD-050 | **certified** |
| R15-LEAD-051 | **certified** |
| R15-DATA-030 | **not_certified**: the over-match is fixed, but on-entity tagging regressed for word tickers the press writes by ticker (fresh class case) |
| R15-LEAD-052 | **not_certified**: the ALL-CAPS case is fixed, but mixed-case upper-case mentions of 3+ character word tickers are now dropped, against the fix_shape |

## R15-LEAD-050 (medium): certified

The relevance gate was checked with `row_relevant` on real Google News titles, non-IN, base against head:

| Target | Titles | Relevant at base | Relevant at head | Lost |
|---|---|---|---|---|
| GE (GE Aerospace) | 100 | 50 | **95** | 0 |
| BP (BP p.l.c.) | 100 | 8 | **98** | 0 |
| GM | 100 | 58 | 58 | 0 |
| SM Energy | 100 | 100 | 100 | 0 |

Cases run in-process:
- **Literal repro:** "GE beats estimates on jet engine demand" went from False to **True**.
- **Held-back case:** SM + "SM beats on Permian output" went from False to **True**.
- **Fresh cases the fix was not written against:** CF Industries + "CF beats on nitrogen prices" and MP Materials + "MP beats estimates on rare earth output" both went from False to **True**.
- **Still irrelevant, as the fix_shape requires:** "AI stocks slide on rate fears" for AI, "IT spending to rise 8%" for IT, "MARKETS ON EDGE AHEAD OF CPI PRINT" for ON, and "Lockheed wins contract on hypersonic program" for ON.
- **Unchanged controls:** "ON Semiconductor beats estimates", "C3.ai shares jump", "AMD beats estimates" and "Allstate catastrophe losses mount" all stay True.

## R15-LEAD-051 (medium): certified

`FiledPeriods.cadence()`, base against head:

| Shape | Base | Head |
|---|---|---|
| IPO: Jan-Mar 26 + Apr-Jun 26 (literal) | half-yearly | **quarterly-gap** |
| Single quarter, Jul-Sep 26 (fresh) | half-yearly | **quarterly-gap** |
| Former-SME migrant: Oct-Mar half + Apr-Jun + Jul-Sep (held back) | half-yearly | **quarterly** |
| Pure half-yearly, newest period ending September (held back) | half-yearly | half-yearly |
| Pure half-yearly, newest period ending March | half-yearly | half-yearly |
| Complete 4 quarters | quarterly | quarterly |

`_ttm_basis(None, cadence)` contains no "half-yearly" on any quarter-filer shape.

**Live fresh case, from real BSE filings:** JONJUA.BO has only three quarters ever filed (Oct-25, Jan-26 and Apr-26 starts), the real-world instance of this entry. Its cadence is now `quarterly-gap`, and live `/fundamentals/JONJUA` reads "the exchange filings leave a quarter of the trailing year unfiled or unparsed; kept, flagged". In batch-29 it read "(a half-yearly filer)". The writer updated the JONJUA test assertion to the new label. That update is justified: the live lane shows quarters only, which makes JONJUA the entry's own class.

**Unchanged:**
- NDTV live: `quarterly-gap`, same reason as batch-29.
- TCS.NS live: `quarterly`, with no reason.

## R15-DATA-030 (high): not certified

**Over-match is fixed.** Everything below holds live or in-process:
- **Literal repros:** "Reliance Industries Q2…" tags RELIANCE.NS, "TCS wins $1bn deal" tags TCS.NS, HDFC Bank, SBI and Bajaj Finance tag, and the A, T and F articles tag nothing.
- **Round-4 acceptance:** IT "it's too late", AI "AI-exposed college majors", "Reliance Power", "LT Foods" and "ITC Hotels" all return `[]`.
- **Held-back cases:** "all-time high" for ALL, "Meta Critical Minerals", "Maruti Infrastructure", and "onsemi (NASDAQ: ON)" tags ON.
- **Live US region:** `/news?symbols=AI`, `IT` and `ON` each return 20 items, all `via_symbol_feed`, with 0 alias-tagged region items. The MarketWatch "AI-exposed" and "it's too late" items are present in the feed and untagged.
- **`META,RELIANCE.NS,UBER`:** 39 items, including TheStreet's "Bank of America backs Meta stock…".

Real Google News titles, tagged at base against head:

| Query | Target | Tagged at base | Tagged at head | Reading |
|---|---|---|---|---|
| Reliance Power | RELIANCE.NS | 97 | 7 | fixed; the 7 left are "Reliance Infra", "Reliance Group" and similar abbreviations |
| LT Foods | LT.NS | 88 | 0 | fixed |
| ITC share | ITC.NS | 100 | 94 | the 6 lost are all ITC Hotels, fixed |
| Reliance Industries / HDFC Bank / SBI / Maruti / Meta / Apple | own | 97 / 92 / 40 / 89 / 99 / 97 | identical | no on-entity loss |
| **KeyCorp KEY** | KEY | 61 | **9** | regression: "KeyCorp (KEY) Stock Could Be 47% Undervalued Despite Its 117% Run" |
| **Lowe's LOW** | LOW | 82 | **15** | regression: "Lowe's (LOW) Stock Looks Reasonable…", "LOW Stock In Focus As Lowe's Launches Drone Delivery…", "Lowe's begins testing drone delivery (LOW:NYSE)" |
| **Coinbase COIN** | COIN | 27 | **11** | regression: "Why Coinbase (COIN) Stock Is Trading Up Today", "COIN Stock Hits 4-Month High…" |
| **Intercontinental Exchange ICE** | ICE | 100 | **85** | regression: "ICE Launches Private Credit Reference Data Service", "(ICE:NYSE)" |
| Welltower WELL | WELL | 98 | 96 | "WELL Upgraded by JP Morgan" |
| Gartner stock | IT | 98 | 97 | "IT Stock Rises As RBC Lifts Price Target" |

**Why this is not certified.** The fresh class case shows that a common-word ticker the press writes AS a ticker loses on-entity tags that base had. This is the same failure mode batch-29 was rejected for: the fix removes the alias for every headline to stop a few. Three things drive it:
- The stoplist includes companies routinely written by their ticker (ICE, KEY, LOW, COIN, DOW). That contradicts the plan's own exclusion rule.
- `anchored_ticker` does not accept the case-sensitive `Name (TICKER)` form, an upper-case `TICKER Stock` token, or the reversed `(TICKER:EXCH)` form. For non-acronym word tickers these forms are unambiguous, and the audit fix_shape's case-sensitive upper-case ticker match would have kept them.

**Live product today.** `/news?symbols=COIN|KEY|LOW` stays non-empty through per-symbol feed provenance. The loss hits region-feed and news-tool items written as "Name (TICKER)", and the US region feed does carry that style (Insider Monkey: "Lockheed Martin (LMT)…").

## R15-LEAD-052 (low): not certified

What holds:
- **Literal repro:** "ALL EYES ON THE FED AS RATE DECISION LOOMS" for ALL went from True to **False**.
- **Fresh ALL-CAPS case:** "ALL IN ON AI: WHY INVESTORS KEEP BUYING" went from True to **False**.
- **Anchored forms kept:** "NYSE: ALL jumps 4%" and "Allstate (NYSE: ALL) climb…" stay True.

What fails is the fix_shape: "require an anchored common-word ticker match to sit in an otherwise-mixed-case headline". The shipped rule instead drops every non-anchored mention of a stoplisted ticker, including mixed-case headlines. Real Google News titles through `row_relevant`, base against head:

| Target | Relevant at base | Relevant at head | Example of what is lost |
|---|---|---|---|
| ICE | 99 | **84** | "ICE Launches Private Credit Reference Data Service", "ICE Invests in OKX at $25 Billion to Launch Tokenized NYSE Stocks" |
| KEY | 95 | **90** | "KEY Q2 Earnings Beat as NII & Fee Income Grow Y/Y" |
| LOW | 100 | **98** | "3 Reasons to Avoid LOW and 1 Stock to Buy Instead" |

These losses are a regression of on-entity evidence for DEEP and FAST research.

## Issues noticed (outside the entries' diffs; for the register adjudicator)

1. **The stoplist is bypassed through the name alias.** When the stripped master name IS the word, the name alias still over-matches. DOW's name alias "dow" tags "Dow Jones falls 300 points" at both base and head, and NICE behaves the same way. This is the plan's own "on semiconductor" residual, in the same class.
2. **Name aliases carry master-name artefacts.** AMZN's alias is "amazon com" and KEY's is "keycorp /new/", so "Amazon unveils new drones" and "KeyCorp raises dividend" never tag. This is pre-existing and identical at base.
3. **The collision rule only knows full listed names.** Abbreviated forms still tag RELIANCE.NS: "Reliance Power, Reliance Infra shares in focus", and "Reliance ADA Group" / "Reliance Anil Ambani Group" (which are not listed).
4. **2-letter tickers with no brand token never pass the relevance gate on a bare mention.** Examples are "GM beats estimates", "GS tops estimates" and "HP rig count rises". The cause is `_entity_signals`' `len(symbol) >= 3`. This is pre-existing and identical at base 19a70e80.
5. **Empty live IN results today are an outside-world gap, not tagging.** Live IN `/news?symbols=RELIANCE.NS|HDFCBANK|ITC` returned `[]` because Yahoo's per-symbol RSS served 0 items for those `.NS` symbols (checked directly) and the Saturday IN region feeds mention none of them. SBIN had 8 items.
