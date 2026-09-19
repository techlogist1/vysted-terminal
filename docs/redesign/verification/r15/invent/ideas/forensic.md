# R15 Stage 4 — ideation seat `forensic`

**Seat:** micro-cap forensic investor, ValuePickr school. Reads every annual report, related-party
note, auditor change, pledge filing and credit-rating rationale. Burned by governance blow-ups.
Trusts filings, not aggregators.
**Model:** `claude-fable-5-1` · **Date:** 2026-09-19 · **Mode:** read-only thinking, nothing built.

## Evidence conventions and honest limits

- Every code claim carries `file:line`, opened this session on `004-r4-experience-rebuild`.
- **WebSearch was unavailable** (session budget exhausted, 200/200). World claims are therefore one
  of: (a) carried from `census/world/*.md` with its URL, (b) verified by a direct fetch this
  session, or (c) marked **[seat knowledge — unverified this session]**. Category (c) must be
  verified before anything is built on it. Nothing in (c) is load-bearing for mechanics.
- **Scenes use real small-caps from `battery/manifest.json` as the stage. The events in a scene are
  hypothetical unless a manifest fact is quoted.** No scene is a claim about that company.
- `census/world/investor-asks-forums.md` is an empty shell (32 lines, PART A unpopulated) and
  `census/OPPORTUNITY_LEDGER.md` does not exist yet, so the demand side here is my seat, plus
  `fey-tijori-trendlyne.md` §10 and `perplexity-screener.md`.

### The one live probe I ran (it reframes three ideas)

The app already downloads the SEBI shareholding-pattern XBRL per quarter
(`sidecar/services/bse_provider.py:672-691`) and reads **one concept** out of it
(`_SHP_PCT_CONCEPT`, `:594`), for six summary categories (`:596-603`), explicitly skipping every
multi-member context (`if len(members) != 1: continue`, `:744`). I fetched the exact file the
fixture index names (`tests/fixtures/bse/shp_quarters_509470.json` → `509470_872026152119_SHP.xml`,
one polite GET via the repo's own curl_cffi lane): HTTP 200, 126,455 bytes, **83 distinct
`in-bse-shp:` concepts**. Among the ones the app throws away:

- `NameOfTheShareholder` (12 rows) — every named promoter entity and every public holder above 1%.
- `NameOfSignificantBeneficialOwners` + `NameOfRegisteredOwner` (5 rows) — the human behind the LLP.
- `WhetherAnySharesHeldByPromotersAreEncumberedUnderPledged`, `…UnderNonDisposalUndertaking`,
  `…OtherThanByWayOfPledgeOrNDU` — the three-way encumbrance declaration, not just "pledge".
- `WhetherTheListedEntityHasIssuedAnyWarrants…ForPublicShareholder`,
  `WhetherTheListedEntityHasAnySharesInLockedIn…`, `WhetherCompanyIsSME`.

This filer declares no encumbrance, so the numeric pledged-share concept names were not observed;
they need one probe against a pledged name before build. The point stands: **the regulator's own
cap table is already on the user's disk path and 82 of 83 concepts are discarded.**

Same shape on announcements. A BSE row carries `SUBCATNAME`, `News_submission_dt`, `DissemDT`,
`TimeDiff`, `CRITICALNEWS`, `ANNOUNCEMENT_TYPE`, `FILESTATUS`, `Fld_Attachsize`
(`tests/fixtures/bse/ann_sub_category_get_data.json`, row 0). `_bse_row_to_announcement` keeps
headline, one of category-or-subcategory, attachment and one timestamp
(`sidecar/services/corporate_disclosures.py:161-178`; subcategory is dropped whenever a category
exists, `:166`; submission-vs-dissemination collapses to the first key present, `:180-195`). The
model has no slot for the rest (`sidecar/models/announcements.py:28-41`). The window is 30 days,
page 1 only (`corporate_disclosures.py:88`, `:138-140`). A forensic reader lives in exactly the
fields being dropped.

---

## What "Jarvis" means from this seat

A chatbot answers "is the pledge rising?". Jarvis is the colleague who walks in and says "the
auditor of your third-largest holding resigned at 9:40 pm on Friday, the letter cites *inability to
obtain sufficient audit evidence on inventory*, that is the second gatekeeper exit in five months,
you wrote in March that you would sell on an auditor change, here is page 2 of the letter." Four
properties, in order of how much they matter to me:

1. **Receipts** — a number without the filing page is a rumour. I have been burned by aggregators.
2. **Watching** — governance events are rare, undated in advance, and filed when nobody is looking.
3. **Memory** — of what I said I would do, what I accepted as a known risk, what the document said
   on the day I read it.
4. **Initiative** — only after 1–3. Initiative without receipts is a push-notification casino.

### Shared substrate (described once; ideas 1, 2, 4, 6, 9 ride it)

**The Tape** — a local append-only store of exchange events for the names the user actually owns or
watches (tens, not 5,000).

- **Store:** new `sidecar/services/filings_tape.py`, SQLite in the data dir, modelled on
  `runs_store.py` (own db file, `CREATE TABLE IF NOT EXISTS` at `:55`, additive-column migration
  precedent `_ensure_options_column` at `:94`). Tables: `events` (symbol, exchange, news_id,
  ts_submitted, ts_disseminated, category, subcategory, headline, attachment_url, attachment_bytes,
  klass, first_seen_at), `cursor` (symbol, last_swept_at), `signals` (rule_id, symbol, fired_at,
  evidence_json, state `new|seen|suppressed`, suppress_reason, suppress_level).
- **Sweep:** a fourth loop beside the three in `fundamentals_warm.start_warm_fundamentals`
  (`sidecar/services/fundamentals_warm.py:403-430`, registered in the lifespan at
  `sidecar/app.py:127-130`, stopped in the `finally` at `:142`), region-gated the same way
  (`_REGION_RECHECK_SECONDS`, `:54`). **Sleeping-laptop semantics fall out of the cursor:** on each
  tick, sweep any symbol whose `last_swept_at` is stale, with the BSE window set to
  `max(30d, now − last_swept_at)` instead of the fixed constant (`corporate_disclosures.py:88,140`).
  A lid closed for nine days is one wider request per symbol on wake. No daemon, no hosted relay.
- **Scope:** portfolio positions are already sidecar-side (`portfolio_db`); the watchlist rides the
  workspace blob, so the frontend posts the scope on change (the `page.tsx` store-subscription
  pattern CLAUDE.md documents for `autosaveLayout`).
- **No LLM in the sweep.** Classification is a versioned lookup table over `SUBCATNAME` + headline
  regex. BYOK tokens are spent only when the user opens a signal. This is what makes a free,
  every-15-minutes evaluation honest on a laptop, and it is why a hallucination can never *create*
  an alert.
- **Surfacing:** the OS-notification bridge exists but only drains workflow intents
  (`src/lib/desktop-notification.ts:1-25,56`; emitter `workflow_nodes/builtin.py:325`); it needs a
  second intent source. Unseen signals also get one line in the terminal preamble
  (`sidecar/services/agent_runtime.py:376`), so the agent *opens* with them — that line is the
  difference between a panel and a colleague.

---

## forensic-1 · Gatekeeper Exit Tape — "who is leaving the building" · NOT on the floor

**User moment.** Monday 8:50 am, lid opens after a long weekend. Notification: *"VERTEX — 2
gatekeeper exits in 143 days."* (Stage: Vertex Securities, BSE 531950, a 48.4 cr cap whose promoter
holding already "collapsed 73.41% -> 36.44%" per `battery/manifest.json`; the exits are
hypothetical.) The card shows a timeline: Company Secretary resigned in May, statutory auditor
resigned Friday 21:40. One click: the agent reads the resignation letter and quotes the stated
reason with the page number. No summary, the sentence.

**Mechanics.** Sweep → classify `klass ∈ {auditor_exit, cfo_exit, cs_exit, id_exit, auditor_appt,
rating_action, …}` from `SUBCATNAME` + headline (both present in the BSE payload, both dropped today
at `corporate_disclosures.py:161-178`). Rules, all deterministic: any mid-term `auditor_exit`; ≥2
gatekeeper exits in 180 days; an independent-director exit citing anything other than "personal
reasons/pre-occupation" (checked only on open, by the LLM, quoted verbatim); an incoming auditor
that is new to the Tape entirely. On open, the PDF lane reads the letter
(`sidecar/services/search/extract.py:436`; resignation letters are 1–3 pages, far inside the
60-page cap at `:65`). SEBI circular CIR/CFD/CMD1/114/2019 (18 Oct 2019), "Resignation of statutory
auditors from listed entities and their material subsidiaries"
(`https://www.sebi.gov.in/legal/circulars/oct-2019/resignation-of-statutory-auditors-from-listed-entities-and-their-material-subsidiaries_44703.html`
— title, number and date confirmed by fetch; the body did not render, so the detailed-reasons
requirement is **[seat knowledge — unverified this session]**).
*New:* the Tape; the classifier table; the window parameter; `subcategory`/`ts_submitted`/
`ts_disseminated` on `Announcement` (`models/announcements.py:28-41` — not Tier-1); a timeline card.

**Why Jarvis.** Watching + initiative + receipts. The cluster is the signal and no human holds a
180-day window across 30 names in their head.

**60-second demo.** Seed the Tape from a fixture with two exits. Launch. Notification fires before
any chat. Open card → timeline → "read the letter" → quoted reason, page 2, exchange URL.

**Lifecycle cost.** `SUBCATNAME` vocabulary drifts; BSE API shape drifts (the module docstring
already dates its observation, `corporate_disclosures.py:15-23`). Keep an `unclassified` bucket that
is *visible*, and a fixture-pinned classifier test. NSE `desc` is coarser ("Updates") so BSE is the
primary lane; an NSE-only SME name gets a weaker tape and must say so.

**Biggest risk.** Alert fatigue from routine board churn. Mitigation: only cluster/mid-term rules
notify; single routine exits land silently on the timeline.

**Size.** S–M (Tape M once; this idea S on top).

---

## forensic-2 · The Filing Clock — delay is data · NOT on the floor

**User moment.** Results season. I open Jumbo Bag (BSE 516078) and the header carries a small clock
chip: *"Results: 31 → 38 → 44 → 45 days after quarter-end. Last two filed after 21:00 on a Friday.
One board meeting rescheduled. One corrigendum to results."* (Pattern hypothetical.) Nobody told me
to look. Every forensic investor knows bad numbers are filed late, at night, before a holiday; no
tool measures it.

**Mechanics.** Pure arithmetic over timestamps the app already fetches and mostly discards:
quarter-end → results-outcome `ts` (results headline regex already exists,
`sidecar/services/research/disclosures.py:45-48`); time-of-day and weekday in IST (`_ist()`,
`corporate_disclosures.py:99`); board-meeting intimation date vs actual outcome (results calendar,
`corporate_disclosures.py:335`, `ResultsEvent` at `models/announcements.py:59-71`);
`News_submission_dt` vs `DissemDT` gap (dropped at `:180-195`); headline match on
`corrigendum|revised|clarification`; shareholding `submission_date` lateness
(`models/announcements.py:122`, BSE index `filing_date_time`, `bse_provider.py:572`). Output is a
`BriefDerivedValue`-shaped metric with `formula` and `basis` (`types/brief.ts:72-89`), so it renders
in the existing metric-card grid and rides the conflict/label discipline already there.
*New:* the derivation module (~150 lines), one chip, Tape history depth (needs the window param).

**Why Jarvis.** Watching. It notices the *behaviour of the filer*, which no aggregator field
contains, and it needs no model at all.

**60-second demo.** Two names side by side: a steady 28-day filer and a drifting one. Hover the chip
→ the four filings with their exchange timestamps and links.

**Lifecycle cost.** Near zero: timestamps are the most stable fields in the payload. Statutory
deadlines (45/60 days) change rarely; keep them in one constants block with a source comment.

**Biggest risk.** Over-reading noise — a single late filing means nothing. Show the series, colour
only a monotonic 3+ quarter drift, never a score.

**Size.** S.

---

## forensic-3 · Cap-Table X-ray — names, beneficial owners, encumbrance, from the XBRL already downloaded · pledge is on the floor; the rest is not

**User moment.** Vertex Securities: the manifest records that the promoter holding "collapsed
73.41% -> 36.44%". The aggregator shows two percentages. I want the question a forensic investor
asks next: *who holds the 37 points now?* The X-ray shows a quarter-on-quarter name diff: which
named holders appeared, which vanished, whether a new >1% body corporate has a Significant
Beneficial Owner row, whether the encumbrance flags flipped — each line linked to that quarter's
XBRL. Then the memory line: *"Two of these entities also appear above 1% in names in your research
spaces."* (Hypothetical; this is exactly how operator networks get spotted on ValuePickr — by hand.)

**Mechanics.** Extend `parse_shp_xbrl` (`bse_provider.py:694-759`) to stop skipping multi-member
contexts (`:744`) and harvest named-holder rows, SBO rows, the three encumbrance flags and the
warrant/lock-in flags verified above. The summary cache stores parsed JSON, not raw XML
(`bse_provider.py:823-850`), so bump the cache schema once; filings are immutable, the re-parse is
bounded by `_MAX_SHP_XBRL_PARSES = 8` (`:592`). Extend `ShareholdingPattern`
(`models/announcements.py:82-138`) and its TS mirror additively. Pledge *derivative*
(4-quarter direction, the practitioner rule carried in `fey-tijori-trendlyne.md` O-7) becomes one
derived series once the numeric concept is confirmed. The cross-company index is a local table
`holder_name → [(symbol, quarter, pct)]` filled only from names the user has touched — it is the
user's own research trail, not a market-wide scrape.
*New:* parser extension, a name-normaliser (LLP/Pvt Ltd/HUF suffixes, PAN is not disclosed so
matching is fuzzy and **must be shown as fuzzy**), a diff table block in `BriefBody`
(`src/modules/research/brief-blocks.tsx`), the co-occurrence table.

**Why Jarvis.** Memory + receipts. It remembers a name I saw four months ago in another company.

**60-second demo.** "Who owns Vertex now?" → diff table, two new names highlighted, SBO row
expanded, each cell opening the regulator XBRL for that quarter. Then the co-occurrence line.

**Lifecycle cost.** SEBI revises the SHP taxonomy every couple of years; the existing code already
absorbs one silent schema change (fraction vs percent, `bse_provider.py:703-716`). Pin fixtures per
taxonomy version; unknown concepts degrade to "not parsed", never guessed. BSE-only lane: NSE-only
names keep today's summary.

**Biggest risk.** False identity — two different "Shree Ganesh Traders". Never assert sameness; say
"same name string", show both filings, let the human judge.

**Size.** M.

---

## forensic-4 · Cheap-Paper Calendar — who got the discounted shares and when can they sell · NOT on the floor

**User moment.** I hold a 400 cr name. Eight months ago it allotted warrants and preferential shares
to a list of non-promoter entities at a steep discount; I read it then and forgot. Today:
*"14% of the free float allotted at ₹42 comes out of lock-in on 14 Nov. CMP ₹310. Allottee list and
lock-in dates: page 3 of the allotment intimation."* (Hypothetical.) This is the micro-cap
supply-overhang event; it is the pump-and-exit pattern's exit door, and it has a *date*.

**Mechanics.** Tape classes `pref_issue_notice`, `allotment`, `warrant_conversion`,
`trading_approval`. On first sight of one, a durable Delegate run (`run_manager.launch_run`,
`sidecar/services/run_manager.py:237`, budget-bounded by `BudgetGuard`) reads the PDF and extracts
`{allottee, category, shares, price, allotment_date, lock_in_until}` as a **proposed** calendar
entry: the user accepts it through the existing diff gate (`src/store/proposed-changes.ts:64,92`),
with the source page open beside it. Accepted entries are plain rows with dates; the sweep raises
them T-30 / T-7 with no LLM. Cross-check for free: the SHP XBRL's
`WhetherTheListedEntityHasAnySharesInLockedIn…` and warrant flags (verified above) must agree with
an open calendar entry, or the entry is flagged stale. Lock-in tenures under SEBI ICDR are
**[seat knowledge — unverified this session]**; the design does not depend on them because the
date is read from the filing, never computed from a rule.
*New:* extraction prompt + schema, a `calendar` table on the Tape, one proposed-change kind, a
"supply events" strip on the portfolio panel.

**Why Jarvis.** Memory with a deadline. It converts something I read once into something that comes
back on the right day.

**60-second demo.** Feed one allotment PDF. Proposed entry appears with the page beside it → accept
→ time-travel the clock fixture to T-7 → notification with the receipt.

**Lifecycle cost.** Extraction is the only LLM-dependent part, and it is human-accepted once, so
model drift cannot silently corrupt the calendar. Scanned allotment letters hit the existing
honesty note (`extract.py:398-407`) and become "could not read — enter manually".

**Biggest risk.** Multi-tranche allotments and partly-paid warrants make "the" lock-in date plural.
Store per-tranche rows; never collapse.

**Size.** M.

---

## forensic-5 · Accounts Linter with reasoned suppressions · adjacent to the floor (forensic score); the mechanic is not

**User moment.** Jumbo Bag: the manifest records "Profit CAGR 82.2%/5y against sales CAGR 6.81%".
A score would say 4/10 and hide why. The linter says:

```
FA-012  profit-growth-without-sales   PAT CAGR 82.2% vs sales 6.81% (5y)      warn
FA-003  cfo-vs-pat                    [inputs + statement rows + source]       ...
```

I know rule FA-012 is explained by a trading associate (the manifest says "an IOCL polymer-trading
associate"), so I suppress it: *"accepted — mix shift to trading, see AR FY25 segment note"*. That
suppression is stored with the level I accepted. If the gap widens past it, the rule **re-fires and
quotes my own reason back to me.** That is `// eslint-disable-next-line -- reason`, for accounts.

**Mechanics.** The house discipline already exists: flag-never-pick cross-checks with a basis note
(`sidecar/services/earnings_quality.py:1-40`, and siblings `growth_check.py`,
`ownership_check.py`, `research/range_check.py`). Generalise it into rule ids over the statement
seams that already exist (`sidecar/services/provider_registry.py:495-509`). Rule conditions reuse
the no-`eval` expression grammar (`sidecar/services/screener_formula.py:441,563`) with a different
field resolver (the seam is `_field_value`, `:476`). Starter pack, all classic and all computable
from three statements: CFO/PAT, receivable-days and inventory-days drift, other-income share of
PBT, cash-tax vs book-tax, CWIP ageing, capitalised-interest, contingent liabilities vs net worth
(needs idea 8), profit-without-sales. Suppressions live in the Tape's `signals` table.
**Hard dependency, stated plainly:** yfinance statements for BSE-only nano-caps are thin or absent;
a rule with missing inputs reports `no-data`, never `pass`. `perplexity-screener.md` TS-2 already
records that multi-year statements are not agent-reachable; this idea is worth little until that
gap closes, and it should be sequenced behind it.
*New:* rule format + ~10 rules, a lint block in the brief, suppression UI, a `lint_accounts` catalog
capability (`read_handler`, auto-projects per CLAUDE.md).

**Why Jarvis.** Memory of *my* judgment, and the nerve to argue with it later using my own words.

**60-second demo.** Lint a name → three findings with inputs → suppress one with a reason → swap in
next year's fixture → it re-fires: "you accepted 82 vs 7; it is now 140 vs 4."

**Lifecycle cost.** Rules are data and versioned; the corpus is cheap to keep. The data feed under
it is the cost (statement coverage for micro-caps).

**Biggest risk.** `no-data` everywhere on exactly the names this seat cares about. Do not ship it
ahead of statement depth.

**Size.** M (rules) — blocked on data depth.

---

## forensic-6 · Kill-Criteria Compiler — prose exit rules become deterministic tripwires · on the floor (thesis vs filings), with a different mechanism

**User moment.** In Notes, under a holding, I write what every disciplined investor writes and then
ignores: *"Sell if pledge crosses 25%, if the auditor changes, if promoters sell in the open
market, or if results slip past 45 days."* The agent proposes four machine-checkable tripwires as a
diff; I accept three and edit one. From then on they are evaluated by the sweep, with no model in
the loop, against the Tape, the X-ray and the Clock.

**Mechanics.** First, a gap that surprised me: **the agent cannot read the user's notes.** The
catalog has `write_note` (`sidecar/services/agent_tools/catalog.py:1373-1395`, executor
`src/lib/host-actions.ts:1176-1191`) and no read; the terminal snapshot carries only
`notesChars` (`host-actions.ts:999`). The thesis lives in the one surface Jarvis is blind to.
So: add a `read_note` local tool (read-only, scope-keyed like `write_note`; notes shape at
`src/store/notes.ts:8-15`). The compile step is one LLM call producing
`{rule_id, params, source_sentence}` from a closed menu of rule ids (the same rule engine as
forensic-5/9) — it can only *select and parameterise*, never invent a check. The diff gate shows
sentence → tripwire. Evaluation is deterministic. When one fires, the notification quotes the
user's own sentence plus the filing receipt. The existing claims ledger is the precedent for
"remember what was said, reconcile openly" (`src/lib/brief-claims.ts:1-14`, preamble render
`agent_runtime.py:344`), but it is per research-space and numeric-only; tripwires are per-symbol
and durable, so they belong on the Tape, not the workspace blob.
*New:* `read_note`, compile prompt, tripwire rows, a "my rules" section on the symbol note.

**Why Jarvis.** Memory + initiative, and it removes the LLM from the part that must never be wrong.

**60-second demo.** Type three sentences → proposed tripwires → accept → inject a fixture event →
notification: *"You wrote: 'sell if the auditor changes.' It changed on 12 Sep. Letter, page 1."*

**Lifecycle cost.** Low. Sentences the menu cannot express are shown as "not machine-checkable —
kept as a reminder", which is honest and costs nothing.

**Biggest risk.** False comfort: a user believes an uncheckable criterion is armed. The UI must
make armed vs reminder unmistakable.

**Size.** S–M.

---

## forensic-7 · Evidence Locker — content-addressed receipts, and "the document changed under you" · receipts are on the floor; the locker is not

**User moment.** Six months ago a brief quoted a related-party figure from a filing. Today I reopen
it and the chip reads: *"Cited copy: sha256 9f2c…, fetched 14 Mar, page 187. The document at this
URL is now different (revised filing, 3 pages longer)."* Exchanges accept revised uploads; company
IR sites replace PDFs silently; aggregator pages go stale. A forensic investor keeps copies. A
hosted chatbot cannot show me what it read; a local terminal can.

**Mechanics.** Two real gaps in the receipt chain today. (a) Page provenance is computed and then
lost: `extract_pdf_text` returns `pages_used` (`extract.py:506,534`) but `BriefSource` has no page
or hash field (`types/brief.ts:230-248`). (b) **The back of an annual report is invisible:**
`_PDF_MAX_PAGES = 60` (`extract.py:65`) and six kept pages (`:68`), tuned for results filings. The
related-party note, contingent liabilities and the auditor's report of a 250-page AR sit past page
120. Today the agent structurally cannot read the pages this seat reads first.
Build: on any PDF visit, store bytes under `{dataDir}/evidence/<sha256>.pdf` (the exports tree and
atomic-write precedent: `src/lib/export-artifact.ts:1-10`) with `{url, fetched_at, sha256,
page_count, pages_empty}`; add `page?`, `sha256?`, `fetchedAt?` to `BriefSource`; a citation chip
opens the local copy at the page. On re-visit of a known URL, compare hashes; a mismatch is itself
a Tape event (`klass = document_replaced`). Add a targeted deep-read mode that lifts the page cap
for a *named section search* (find "Related Party", read ±4 pages) rather than raising the global
cap, so research latency is unchanged.
*New:* locker store + retention cap, three optional fields on `BriefSource`, section-seek reader,
hash compare.

**Why Jarvis.** Receipts in the coding-agent sense: not "source: bseindia.com" but the exact bytes,
the page, and proof they have not moved.

**60-second demo.** Ask an RPT question → answer with page chip → click → local PDF at page 187 →
swap the fixture URL's bytes → reopen brief → "document changed" banner with a page-count diff.

**Lifecycle cost.** Disk. A heavy user stores a few GB a year; needs an LRU cap and a "pin"
(cited-in-a-saved-brief is never evicted). This lands squarely in lifecycle question L5 (bounds) —
budget it on day one, not after.

**Biggest risk.** Scanned micro-cap ARs: the locker stores them faithfully and the reader still
cannot read them. The existing honesty note (`extract.py:398-407`) must reach the chip: "stored,
not machine-readable".

**Size.** M.

---

## forensic-8 · Annual-Report Redline — `git diff` for the notes to accounts · NOT on the floor

**User moment.** AR season, a name I have held three years. I do not want a summary of 240 pages. I
want what I do by hand with two PDFs and a highlighter: *what changed since last year* in the five
places that matter. The redline shows: a new related party with loans advanced; contingent
liabilities up 3× with a new tax demand; the auditor's report gained an Emphasis of Matter
paragraph; useful life of plant revised upward (profit flattered); a Key Audit Matter on revenue
recognition that was not there last year. Each hunk: last year's page on the left, this year's on
the right. (Hypothetical.)

**Mechanics.** Rides forensic-7 (section-seek reader + locker; both years' ARs are in the BSE
announcements/annual-report lane as `attachment_url`). Pipeline: locate sections by heading regex
(Related Party, Contingent Liabilities, Independent Auditor's Report, Key Audit Matters, CARO
annexure, Significant Accounting Policies) → extract text per section per year → **deterministic
`difflib` hunks first** → the LLM only *labels* each hunk's materiality and must quote both sides
verbatim; the existing citation-integrity pass is the enforcement precedent
(`sidecar/services/research/citecheck.py:216`). Runs as a durable Delegate run
(`run_manager.py:237`) because it is minutes, not seconds, and must survive a closed lid via the
resumable checkpoint. Output is a typed diff block in `BriefBody`.
*New:* section locator, diff block, the run recipe. Scope control for days-not-months: ship three
sections (auditor's report, RPT, contingent liabilities); policies and CARO follow only if the
locator proves reliable.

**Why Jarvis.** This is the coding-agent idea transplanted whole: reviewers trust a diff, not a
summary. It is also the only idea here that turns the AR — the document aggregators structurally
cannot normalise — into the product's home ground.

**60-second demo.** "Redline FY26 vs FY25" → run card ticks through sections → three hunks, one
flagged material, both pages side by side.

**Lifecycle cost.** Heading conventions vary by company and drift slowly; the locator needs a
fallback ("section not found — open PDF at the notes index") rather than a guess. Table-heavy notes
diff badly as text; RPT tables may need the layout-mode retry (`extract.py:_layout_retry`).

**Biggest risk.** Scanned ARs and fused table cells produce garbage hunks that look like findings.
Gate: if `pages_empty` in a section is non-zero, the section is "unreadable", full stop.

**Size.** L as a whole; M if held to three sections on top of forensic-7.

---

## forensic-9 · Red-Flag Rule Packs — detection-as-code for governance (the Sigma/YARA of Indian small-caps) · NOT on the floor

**User moment.** I install a community pack, `governance-sequences`. It is a folder of small rule
files, each one a *sequence* over the Tape with a citation to the regulator order it was distilled
from: *rating downgrade → CFO exit → results delayed*, *warrants to non-promoters → name change to
a fashionable sector → promoter stake falls*, *auditor exit within 45 days of quarter-end*. One of
my holdings lights up: *"3 of 4 steps of rule GS-007 matched in 11 months. Steps matched, with
filings: … Step not matched: … Source of the pattern: [SEBI order link]."* No verdict. A checklist
with receipts. (Historical cases that would seed the first pack — auditor exits days before
results, ratings collapsing from investment grade to default within weeks — are **[seat knowledge —
unverified this session]** and every shipped rule must cite a primary order or filing.)

**Mechanics.** One rule engine, three rule families already motivated above: event-sequence rules
over the Tape (this idea), statement rules (forensic-5), user tripwires (forensic-6). Format:
declarative JSON/YAML — `id`, `title`, `steps[] {klass | expr, within_days}`, `min_match`,
`citations[]`, `severity`. Expressions reuse the no-`eval` grammar
(`screener_formula.py:441`); sequence matching is a small windowed scan over `events`. Rename
detection is already a lane (`sidecar/services/nse_symbol_change.py:245,323`) and becomes a Tape
class for the "renamed into a fad" step. Packs ship as **data plugins** through the existing
contract's `contributesData` capability (`types/plugin.ts:60,75-76` — used as-is, **no contract
change**, which would be Tier-4) and the marketplace install/enable lifecycle
(`src/lib/marketplace.ts`). First-party starter pack of ~12 rules; everything else is community.
*New:* rule schema + validator, sequence matcher, pack loader, a "matched rules" block with
per-step receipts, a contribution guide.

**Why Jarvis.** Watching with institutional memory — not the user's memory, the *market's*. Every
blow-up teaches a pattern; today that knowledge lives in forum post-mortems and nowhere executable.

**60-second demo.** Install pack → Tape replays a fixture history → one rule shows 3/4 with each
step's filing → open the rule file itself in the UI: twenty readable lines and a citation.

**Lifecycle cost.** The corpus is the asset and the liability: rules need review, versioning,
deprecation. Budget a `rules/` lint in CI (schema + citation-URL-present + fixture that fires).
Class vocabulary changes must be additive or packs break.

**Biggest risk.** A rule reads as an accusation. Rules must be phrased as observable sequences,
cite primary documents, output "steps matched", and never name a verdict. First-party pack reviewed
by the operator line by line.

**Size.** M (engine S–M once forensic-1's Tape exists; starter pack is careful writing, not code).

---

## What I deliberately left to other seats

Management guidance vs delivery across quarters (floor; an analyst seat will do it better), the
lakh/crore scale witness (floor; already partly built as the correctness gate), bulk/block-deal
stitching (floor; no data lane exists in the repo yet — `grep` finds none under
`sidecar/services`), and credit-rating-rationale reading. The last one I want badly — rationales
disclose bank-limit utilisation and "issuer not cooperating" status that ARs never state — but it
means scraping six rating-agency sites with no lane today. It enters for free as a Tape class
(`rating_action`) via the exchange intimation; the rationale reader should wait.

## Build order if only some of this happens

`Tape` (substrate) → forensic-2 (S, zero-LLM, instant proof the Tape is worth having) →
forensic-1 → forensic-3 (parser extension, independent of the Tape) → forensic-6 (needs
`read_note`) → forensic-7 → forensic-9 → forensic-4 → forensic-8. forensic-5 waits on statement
depth.

---

## Single strongest idea: forensic-9, Red-Flag Rule Packs (on the Tape)

Every individual signal above can be cloned by a funded rival in a month; signals are arithmetic.
Three things about rule packs cannot be:

1. **A legal asymmetry that is architectural, not a feature.** A hosted platform that displays
   "this company matches a fraud pattern" is *publishing* a statement about a listed company, to
   everyone, from its own servers. Indian promoters litigate. That is why every incumbent ships
   bland scores and "SWOT" and none ships the pattern a forensic investor actually wants
   (`fey-tijori-trendlyne.md` §10: "no mainstream Indian retail platform ships a
   forensic-accounting score"). Vysted publishes nothing: open rules, public filings, evaluated
   privately on the user's own machine against the user's own holdings. A hosted rival cannot copy
   that without ceasing to be hosted.
2. **A corpus takes a community and time, and this community already exists and already does the
   work for free.** ValuePickr-school investors write blow-up post-mortems as a hobby. Nobody has
   given them an executable format. AGPL + the plugin contract + a twenty-line readable rule file
   is that format. A closed rival can copy the engine in a sprint and still have an empty library.
3. **It compounds with private local state rivals cannot hold.** The rules fire against a Tape
   accumulated on this machine, holdings read through the user's own broker session, tripwires
   compiled from the user's own notes, suppressions carrying the user's own reasons, and evidence
   hashed the day it was read. Perplexity's portfolio link does not reach India at all
   (`perplexity-screener.md` §E3), and incumbents charge for evaluation frequency
   (`fey-tijori-trendlyne.md` O-3) — here it is free because it is the user's CPU and no model.

It is also the idea that makes the others one system instead of nine features: the Exit Tape, the
Filing Clock, the X-ray, the Calendar, the Linter and the Kill-Criteria are all just rule families
and event classes over the same store.
