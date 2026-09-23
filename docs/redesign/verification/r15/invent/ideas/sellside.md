# R15 Stage 4: ideation seat `sellside`

**Seat:** sell-side equity research analyst at a boutique Indian brokerage covering small and mid caps.
Writes initiation reports and results updates, models management guidance against delivery quarter
over quarter, competes for corporate access and channel checks, and knows exactly what a buy-side
client pays a report for and what is filler.
**Model:** `claude-opus-5-5[1m]` · **Date:** 2026-09-23 · **Mode:** read-only thinking. Nothing is built.

## Evidence conventions and honest limits

- Every code claim carries a `file:line` I opened this session on `004-r4-experience-rebuild`.
- **WebSearch was unavailable** (session budget exhausted). World claims are one of three kinds:
  (a) carried from `census/world/*.md` with its URL; (b) **verified by a direct fetch this session**
  (the probe below); (c) marked **[seat knowledge, unverified this session]**. Mechanics never
  depend on category (c).
- Scenes use real listed companies. **Events in a scene are hypothetical unless they are quoted
  from the probe.** A scene is not a claim about that company.
- I read the other seats (bloomberg, forensic, quant, retail, hn-sceptic, journalist) before writing.
  Overlaps are named per idea so the judge can merge rather than double-count. This seat's unique
  contribution is the **model**: the forecast object a sell-side analyst lives in. Other seats
  watch filings. I want filings to *move numbers the user owns*.

### The live probe I ran (it moves three ideas from "blocked" to "one step away")

I made three polite `AnnSubCategoryGetData` pulls through the repo's own curl_cffi lane
(impersonate=chrome, `Referer: https://www.bseindia.com/`, 3 s spacing, six-month window
2026-03-01 → 2026-09-22) for Fusion Finance (543652), Apollo Micro Systems (540879) and Hero
MotoCorp (500182). I also made eight attachment GETs, which I read with the repo's own
`extract_pdf_text` (`sidecar/services/search/extract.py:436`). Scratch script and raw output:
`$SCRATCH/sellside/probe.py`, `probe_out.json` (scratch only, not in the repo).

1. **Earnings-call transcripts are already on the wire.** BSE tags them as
   `SUBCATNAME = "Earnings Call Transcript"` (2 for Fusion, 3 for Apollo, 2 for Hero in six months).
   `_bse_row_to_announcement` keeps `CATEGORYNAME` ("Company Update") and drops the subcategory
   whenever a category exists (`sidecar/services/corporate_disclosures.py:166`). The model has no
   slot for it (`sidecar/models/announcements.py:28-41`), so the app has the transcript in hand
   and cannot tell it from a newspaper notice. Two shapes exist in the wild:
   - **Full transcript attached.** Apollo, 8 Aug 2026 call: 22 pages and 57,734 chars extracted.
     Hero, 7 Aug 2026 call: 19 pages and 56,091 chars. Speaker turns are labelled
     ("Binay Singh: …", "Harshavardhan Chitale: …") and the moderator names each analyst's firm.
   - **Cover letter only.** Fusion, filed 17 Aug 2026: one page. It says the transcript "is
     available on the Company's website" and gives a link that the PDF text **wraps across two
     lines** (`https://fusionfin.com/wp-content/uploads/2026/08/Transcript-of-Q1-FY-2026-27-of-` /
     `earning-conference-call_10.08.2026.pdf`). A one-hop fetch has to de-wrap it.
   This partly corrects `WLD-T-6` ("no transcript capability"). The capability is still absent,
   but the data is not. For BSE filers who attach the transcript, it arrives in the feed the app
   already calls.
2. **Corporate access is a filed, dated feed.** The `Analyst / Investor Meet` subcategory holds
   10 filings (intimations + outcomes) for Fusion, 14 for Apollo and 14 for Hero in six months. Apollo's 14 Sep 2026
   intimation names the event: *"22nd Sep 2026, Tuesday · Physical · Anand Rathi Annual Flagship
   Conference G-200 Summit 2026 · Mumbai"*. Fusion's 17 Sep names only *"Group of Investors ·
   One-to-One & Group Meetings · In-person, Mumbai"* (29 Sep 2026). Apollo also files an
   `Investor Presentation` roughly every roadshow day (20 in six months). That is the deck they
   actually showed.
3. **Between-the-prints data is filed monthly.** Hero's 1 Sep 2026 press release opens with a
   machine-readable table: `Particulars AUG'26 AUG'25 YTD FY'27 YTD FY'26 / Motorcycles 493,851
   501,523 … / Total 568,398 553,727 2,779,127 2,370,552`. Apollo files a `Business Update` or
   `General Update` roughly every two to three weeks (7 in six months). The 16 Sep one reads
   *"awarded the Transfer of Technology (ToT) for the Semi Active Laser Homing System (SALHS)"*.
4. **Use-of-proceeds reports are filed quarterly.** Both Fusion (10 Aug and 15 May) and Apollo
   (14 Aug and 15 May) file a `Monitoring Agency Report` plus a `Reg. 32 (1), (3) - Statement of
   Deviation & Variation`. Fusion's Aug report is 12 pages and 20,746 chars, all extractable text.

### Side observations for the lead (not ideas; these may deserve raw findings)

- **`attachment_url` rots after a few weeks.** The app always builds
  `…/corpfiling/AttachLive/<name>` (`corporate_disclosures.py:84`). Filings from 10 Aug and
  17 Aug 2026 returned **HTTP 404 (8,406 bytes) on `AttachLive` and 200 PDF on `AttachHis`**,
  while 1 Sep and 16 Sep filings were 200 on `AttachLive`. The module docstring checked only
  the opposite case, a *current* filing that 404s on `AttachHis` (`corporate_disclosures.py:21-23`).
  So every results PDF, transcript and presentation older than a few weeks probably reaches the
  research PDF lane as a dead link. Smallest fix: on a 404, retry once against `AttachHis`.
  Checked against `census/raw/*.json`: no finding names this (the nearest is the
  AttachLive-retry item in `intent-deferred-84.json`, which is about intermittent serving, not
  migration).
- **The BSE announcements window has a ceiling.** `strPrevDate=20250901` (about 12.7 months)
  returned `{"Table":[]}` for all three scrips. `20260301` (about 6.7 months) returned 92, 103 and
  97 rows. Any catch-up or history sweep has to page in windows of six months or less. The app
  today asks for 30 days, page 1 only (`corporate_disclosures.py:88,138,140`).

---

## What "Jarvis" means from this seat

A buy-side PM does not pay my desk for the company history, the industry primer or the
"key risks: competition, regulation, macro" page. That is 70% of every initiation by page count and
0% of why the client votes for us in the broker poll. They pay for four things:

1. **A model they can interrogate:** my numbers, my drivers, and why I moved them.
2. **Speed on the print:** a correct first take within the hour, with the variance explained.
3. **Access:** what management said, what they would not say, and who else was in the room.
4. **A variant view:** what the price already assumes, and where I disagree with that.

A chatbot with panels gives none of these. It answers the question you asked. Jarvis from my seat
is **the junior analyst who keeps my model alive**: they read every filing on my names the day it
lands, and they walk in with *"Apollo's Business Update this morning adds ₹X cr to order inflow.
That puts H1 book-to-bill at 1.4×, and your FY27 revenue line now needs only 62% execution of the
opening book instead of 71%. Want me to move it? Here is the page."* The axes, in the order my desk
weighs them: **memory** (of my estimates and why they moved), **receipts** (page-level, or it
did not happen), **watching** (filings, meets, monthly numbers), **initiative** (proposes a change
to *my* numbers through a gate I control, never silently).

### Shared substrate (described once; ideas 1, 2, 3, 5, 6, 7 and 9 ride it)

**The Covered-Name Feed.** This is a narrowing, not a new tape. Forensic's *Tape*, Bloomberg-1 and
HN-6 already specify a per-symbol-cursor sweep of exchange announcements for held and watched names.
I need that sweep plus three things it does not yet promise:

- **Subcategory as a first-class field.** Add `subcategory` to `Announcement`
  (`models/announcements.py:28-41`, not Tier-1; mirror it in `types/data.ts`) and stop collapsing
  it (`corporate_disclosures.py:166`). Every idea below routes on `SUBCATNAME`: `Financial Results`,
  `Earnings Call Transcript`, `Analyst / Investor Meet`, `Investor Presentation`,
  `Monitoring Agency Report`, `Reg. 32 … Deviation`, `Press Release`, `General`.
- **The AttachHis fallback** from the side observation above. Without it, a model fed from filings
  starves after a few weeks.
- **Six-month paging** for back-fill when a name is first covered, so the model starts with eight
  quarters of transcripts and results, not 30 days.

**The Model Store.** New `sidecar/services/model_store.py`: SQLite in the data dir, following the
pattern of `portfolio_db.py:23-35` (one file, `CREATE TABLE IF NOT EXISTS`, sync sqlite3).
It has three tables:
- `lines`: symbol, line_id, label, unit, formula or null.
- `cells`: symbol, line_id, period, value, kind ∈ {actual, estimate, guidance}, source_ref.
- `revisions`: append-only; symbol, line_id, period, old, new, reason, trigger_filing, at.

Formulas use the existing no-eval grammar (`services/screener_formula.py:1-16`, which has no `eval`
or `exec` anywhere on the path, with `FUNCTIONS = {abs,min,max}` at `:117`). The only extension is
cell references. Agent-proposed changes to user-owned cells are host actions that stage in the
proposed-changes gate (`src/store/proposed-changes.ts:1-10`: "NOTHING lands before acceptance …
There is no auto-apply path"). This is the user's research data, not an order. It never touches the
order-safety surface, and trading is out of the product anyway.

---

## 1. The First-Hour Note: the results update, drafted before the call starts (FLOOR-adjacent: results-day signal + receipts)

**User moment.** It is 4:40 pm on a Thursday in November. Apollo Micro Systems posts Q2 FY27
results to BSE (hypothetical event). I cover it. My client desk wants my take before the 6 pm call,
and a better-read colleague at a bigger house will send one out at 5:15. The probe gives the
Q1 baseline, taken from the 8 Aug 2026 transcript: standalone revenue ₹156 cr, PAT ₹28 cr, EBITDA
and PAT margins of 31% and 18% ("Page 4 of 21"). By 4:52 Vysted shows me the Q2 variance table
against Q1, against Q2 FY26 and against **my own model's Q2 estimate**. Every actual carries its
PDF page. There are three lines of prose, and every number in them has survived verification.

**Mechanics.**
- *Trigger:* the Covered-Name Feed sees `SUBCATNAME = "Financial Results"` for a covered symbol.
  With the laptop open, it rides the existing warm-loop cadence (`services/fundamentals_warm.py:403`,
  started in the lifespan at `app.py:130`). On wake, the sweep catches up, and on open the note is
  the first thing the agent says (terminal preamble, `services/agent_runtime.py:376`).
- *Extraction is deterministic:* SEBI's results format prints a fixed comparative grid (current
  quarter, preceding quarter, same quarter last year, YTD, previous YTD, previous full year)
  [seat knowledge, unverified this session: exact column order varies by filer]. The PDF lane
  already reads these files (`extract.py:436`, 60-page cap at `:65`). A table locator finds the P&L
  grid page, and a row matcher maps "Revenue from operations / Other income / Total expenses /
  Finance costs / Depreciation / PBT / Tax / PAT / EPS" to model line ids. The LLM is not in this
  path.
- *Unit witness, mandatory:* results PDFs declare "₹ in lakhs" or "₹ in crores" in the grid header.
  Misreading that header is exactly the "Perplexity misread a small-cap filing by 1000×" failure.
  No unit header means no note: the card says "unit header not found on p.N, not extracted" and
  never guesses. It pairs with OPP-2's ₹ scale witness and uses the market-cap witness
  (`services/market_cap_witness.py:140`) as a sanity bound on implied EPS × shares.
- *Standalone vs consolidated:* both are usually filed. The note uses the basis the user's model
  declares and labels it. A missing basis is stated, never substituted.
- *Prose:* one LLM call over the verified grid. Its output passes the same number gate the overview
  narrative already uses (`services/company_narrative.py:209` `_verify_text` redacts any number that
  matches no source value). It publishes as a brief (`publish_brief`, `catalog.py:1177`) whose typed
  blocks already render metric cards and tables (`src/modules/research/brief-blocks.tsx:443,549`).
- *New:* table locator + row matcher + unit-header parser with a fixture per filer shape;
  `results_flash` read handler registered in the catalog; variance block type.

**Why Jarvis.** Watching (it saw the print), receipts (every cell carries a page), memory (the
comparison is against *my* estimate, not a consensus that does not exist for a ₹3,000 cr name).

**60-second demo.** Point it at a filed results PDF in the fixture set, then hit "simulate new
filing". The note appears with a variance table and a page badge per cell. Click a badge and the
PDF opens at that page. Change the model's Q2 revenue estimate and the variance column updates live.

**Lifecycle cost.** Filers change grid layouts. SME filers under Reg 33 print half-yearly, not
quarterly. Scanned PDFs exist (`extract.py:398` already writes the honest scanned-pages note). It
needs a growing fixture corpus: one per new layout seen, each a two-minute test to add. Expect about
a day a quarter of fixture upkeep across a 30-name coverage list.

**Biggest risk.** A row-matcher miss that maps "Total income" (which includes other income) onto
"Revenue from operations" on a lender or holding company. **Mitigation:** the line map is per
sector archetype, and a matched row whose label is not an exact dictionary hit is flagged amber
("matched by similarity"), never shown as clean.

**Size:** M (S if the Covered-Name Feed exists first).

---

## 2. The Living Model: your forecast, kept alive by filings, with a revision trail (NOT floor)

**User moment.** In March I built a 30-line model for Apollo Micro: order-book-driven revenue,
EBITDA margin, depreciation, interest, tax and share count. That includes warrant conversions,
which the probe shows being allotted in June (*"Allotment Of Equity Shares Upon Conversion Of
Warrants"*, 8, 17 and 23 Jun 2026). In September a PM asks: "Why did you cut FY27 EPS in August?"
Today I dig through a spreadsheet's version history. With Vysted, the model's revision trail answers
it: *"14 Aug: FY27 EBITDA margin 29% → 27%, reason 'mix shift to lower-margin subsystems',
trigger = Q1 transcript p.9 [link]; FY27 share count +2.1% on warrant allotments [3 filings]."*

**Mechanics.**
- *Store:* the Model Store (substrate). A per-archetype template (manufacturer, lender,
  order-book business) seeds lines. The user edits in a grid panel (new module under
  `src/modules/`, a dockview panel like every other). Formulas use the shipped no-eval grammar
  extended with cell references (`screener_formula.py:117`).
- *Actuals auto-fill:* idea 1's extraction writes `kind=actual` cells with `source_ref`
  (URL + page + fetch time). A later filing that *restates* an actual (a regrouping, an Ind AS
  restatement) creates a revision row with trigger = that filing, never a silent overwrite.
- *Estimate changes:* the user edits directly, and the revision row records the reason.
  Agent-proposed edits ("the Q2 print implies your H2 margin is 300 bp too high") go through the
  proposed-changes gate (`src/store/proposed-changes.ts:1-10`) as old→new diffs. The agent can
  propose. It never writes.
- *The agent can read it:* a `model_read` read handler (symbol → lines, cells, last 20 revisions)
  goes into the catalog, so every brief, note and first-hour note compares against *your* number.
  Custom agents get it through the allow-list derivation (`catalog.py` header, lines 1-24). There is
  no hand-edited schema.
- *Export:* `.xlsx` with live formulas through the Rust atomic-write path the repo already uses for
  binary exports (`src/lib/export-artifact.ts:1-12`), **not** the `<a download>` path that
  `WLD-T-2` found dead. This is Screener's real switching cost: "Export data into structured excel
  sheets. Create your own models" (`census/world/perplexity-screener.md:194-195`, WORLD-RES-13).
- *Why a new store rather than Notes:* notes are free-form markdown files
  (`src/modules/notes/notes-persistence.ts:1-10`). A model needs typed cells, units and history.

**Why Jarvis.** Memory above all: the app remembers what I believed, when, and why. Initiative
through the gate. Receipts on every actual.

**60-second demo.** Open Apollo's model and see the actual cells with page badges. Drop in the Q2
results fixture: actuals fill, one estimate cell turns amber ("the print implies a revision"), and
the agent's proposed diff sits in the gate. Accept it and the revision trail gains a row that links
to the page.

**Lifecycle cost.** Templates drift as businesses change shape (a new segment or an acquisition,
like Apollo's *"General Update On Acquisition"* on 21 Aug 2026). Lines must be addable without
breaking history. The schema needs migrations, and the xlsx writer is a dependency to watch (the
openpyxl-class library would be new, and it counts against the sidecar footprint target in
CLAUDE.md).

**Biggest risk.** It becomes a spreadsheet clone that nobody opens because Excel is better at being
Excel. **Mitigation:** do not compete on grid features. Compete on the three things Excel cannot
do: filings fill actuals with receipts, revisions carry reasons and triggers, and the agent reads
the model. Keep the grid deliberately small (30 lines or fewer per template) and export to xlsx for
everything else.

**Size:** M.

---

## 3. Guidance Haircut: a per-management calibration factor, plus horizon drift (FLOOR: guidance vs delivery, new angle)

**User moment.** From the probe, verbatim from Hero's 7 Aug 2026 transcript. The analyst asks:
*"we earlier talked about the 14% to 16% range. Do you think … you will be able to maintain that
range for the year?"* The CFO answers: *"14% to 16% is our guidance for the **midterm** … in the
midterm, we are confident of going back to it, but **not in the short term**."* A sell-side analyst
reads that as guidance being **pushed out a horizon without being cut**. That is the most common way
Indian managements walk back a number. For a small-cap lender like Fusion Finance (hypothetical
event), the same thing happens with credit-cost guidance. Vysted shows a line per guided metric: the
guided range per call, the horizon word per call ("this year" → "H2" → "midterm"), and the delivered
print per quarter. It also shows one number, **the haircut**: over the last N resolved guidances,
this management delivered 0.82× the midpoint. My model uses 1.0×. The card says so.

**Mechanics.**
- *Input:* transcripts via the `Earnings Call Transcript` subcategory (probe finding 1; one-hop fetch
  for cover-letter filers, with the URL de-wrapped and checked by `is_public_http_url`,
  `extract.py:155`). A guidance extractor proposes `{metric, low, high, unit, horizon_phrase,
  speaker, page, verbatim}` rows (LLM, once per transcript). The verbatim span is required, and a
  row whose verbatim does not appear on the cited page is dropped (a deterministic substring check).
  The user accepts rows into the Model Store as `kind=guidance` cells through the gate.
- *Resolution is deterministic:* when idea 1 fills the actual for the horizon's period, the row
  resolves as HIT / MISS / PUSHED (horizon word moved later with the range unchanged) / DROPPED (not
  repeated on the next call; this is HN-7's FADED).
- *The haircut:* delivered ÷ guided midpoint over resolved rows, per metric family (revenue growth,
  margin, credit cost, capex timing). It is shown with n. Below n = 4 it says "insufficient history",
  not a number.
- *Into the model:* an optional "apply haircut" toggle per line. Applying it is a proposed change,
  not a silent edit.
- *New:* the extractor prompt + verbatim check, horizon-phrase lexicon (a small closed list:
  this quarter / H2 / this year / next year / midterm / long term), resolver, and card.

**Overlap.** Bloomberg-4 (pre-print card), HN-7 (promise ledger with FADED) and OPP-4. What is new
here is the **calibration factor feeding a model** and **horizon drift as its own signal**. Those two
turn a tracker into an input.

**Why Jarvis.** Memory (of what they said, each time), receipts (verbatim + page), initiative
(*"your FY27 margin assumes they hit guidance; they have hit 1 of 5"*).

**60-second demo.** Hero's two transcripts in the fixture set. The margin row shows "14-16%, horizon:
this year → midterm" with both verbatim spans, and one click shows each page.

**Lifecycle cost.** Transcript formats vary. Some filers only link to their own website, and those
links rot. That argues for idea 9-style local caching of the fetched PDF, the same
hash-and-keep idea as forensic-7 and HN-2. There is ongoing LLM extraction cost per transcript per
covered name, bounded (30 names × 4 calls a year).

**Biggest risk.** An extraction that invents a range management never gave. **Mitigation:** the
verbatim substring gate and user acceptance. No guidance row reaches the model unaccepted.

**Size:** M.

---

## 4. Priced-In: what the market cap already assumes, beside what management guides and what you model (NOT floor)

**User moment.** Viyash Scientific (the renamed Sequent Scientific; the manifest records a ₹10,998 cr
market cap on 18 Sep 2026) re-rates 30% in a quarter. A PM asks the question I get paid for:
**"what is in the price?"** Vysted answers without an opinion. *"At ₹10,998 cr and a 13% cost of
equity, the price implies ~X% revenue CAGR for 10 years at a Y% steady-state EBIT margin. The
company's own last 5 years: A%. Management guidance: B% (idea 3, 2 calls). Your model: C%."* It
adds a 5×5 sensitivity grid (cost of equity × terminal margin → implied growth). There is no target
price and no buy/sell. (X, Y, A, B and C are placeholders. I did not compute them.)

**Mechanics.**
- *Pure math, no LLM:* a reverse DCF solves for the growth rate that equates discounted FCFF to
  enterprise value. Its inputs are all on the `Fundamentals` contract already: `market_cap`
  (`models/fundamentals.py:65`), `revenue_ttm` (`:91`), `operating_margin` (`:84`),
  `shares_outstanding` (`:94`). History comes from the annual statements the app already serves
  (`services/yfinance_provider.py:418-450`). The ₹ scale is checked against the market-cap witness
  (`market_cap_witness.py:140`) before solving, so a lakh/crore slip cannot yield a 1000× "implied
  growth".
- **No DCF, reverse DCF or cost-of-capital code exists anywhere in the sidecar.** I grepped for
  `dcf|intrinsic|implied_growth|discount_rate|wacc` across `services/ routers/ models/` and got zero
  relevant hits.
- *Every input is visible and editable:* cost of equity (a Settings default with the value
  printed), tax rate, reinvestment rate, terminal growth. It is a `priced_in` read handler
  (catalog-registered, MCP-projected) plus a block type for briefs.
- *Page-one integration:* this is box 2 of idea 8.

**Why Jarvis.** Initiative: it reframes a question the user did not know how to ask. Receipts: every
input shows its source and as-of.

**60-second demo.** Open any Indian name and see the priced-in box with a sensitivity heatmap.
Move the cost-of-equity slider and watch implied growth move. The history, guidance and model
columns sit beside it, with the gap highlighted.

**Lifecycle cost.** Low. It is deterministic math over existing fields. It breaks only if the
fundamentals contract changes. It needs a lender and holding-company archetype that switches to a
P/B-vs-ROE implied-ROE form, because FCFF is meaningless for Fusion, Dhanlaxmi or Naperol. That
switch is a sector rule, not an LLM guess.

**Biggest risk.** False precision, plus a regulatory look. Under the SEBI (Research Analysts)
Regulations, anything that looks like a target price or recommendation to the public is regulated
activity [seat knowledge, unverified this session]. **Mitigation:** never output a price, a rating
or "undervalued". The output is "implied growth at your stated cost of equity" with the grid always
shown, and a single cell is never presented alone.

**Size:** S.

---

## 5. Between the Prints: a quarter-to-date nowcast from monthly filings and order wins (NOT floor)

**User moment.** Hero files August dispatches on 1 Sep 2026 (probe, verbatim table): Total
**568,398** vs **553,727** last August, with YTD FY'27 at **2,779,127** vs **2,370,552**. I cover
**Dhoot Transmission** (listed 17 Aug 2026, per the manifest), whose wiring-harness revenue tracks
two-wheeler OEM volumes [seat knowledge, unverified this session: customer mix to be confirmed
from its DRHP]. By 2 Sep, without me asking, Vysted shows: *"Q2 QTD, two of the three months:
OEM-weighted 2W dispatches +2.7% YoY (Hero) … your Q2 revenue estimate needs +9%. The gap is now
yours to explain."* For an order-book name like Apollo Micro, the same card sums announced inflows
since the last stated book (probe: *"standalone order book stood at INR1,224 crores, while our
consolidated order book stood at INR1,704 crores"* as of 8 Aug 2026, transcript p.4) and shows
book-to-bill against the model's revenue line.

**Mechanics.**
- *Tallies:* a `tallies` table in the Model Store (symbol, metric, period, value, source_ref).
  Sources are Covered-Name Feed rows with `SUBCATNAME ∈ {Press Release, General}` whose headline
  matches the tally's pattern.
- *Extraction is schema-once, deterministic after that:* the first time a filer's monthly release
  is seen, the LLM proposes an extraction spec (which table, which row labels, which unit) and the
  user accepts it through the gate. After that the spec runs deterministically every month with no
  LLM. Hero's table is labelled and regular. When the spec stops matching, the card says "the
  release changed shape on 1 Oct; re-confirm", and never extrapolates.
- *Order wins:* many small caps disclose an order value in the letter body. The ₹ amount is parsed
  with the unit witness (lakh/crore/million). Undisclosed values ("in the ordinary course of
  business", as in the 16 Sep ToT award) count as **events with no value** and are shown as such,
  never imputed.
- *Nowcast math:* QTD vs same-period LY, a run-rate, and "required rate to hit the model's
  estimate". It is arithmetic against Model Store cells.
- *Read-across edge:* the OEM → supplier link comes from idea 6's typed peer set, so it is the
  user's edge, not an inferred one.

**Overlap.** None of the other seats nowcasts. Quant-8 (SUE) works after the print, and this works
before it.

**Why Jarvis.** Watching (monthly filings nobody reads), initiative (it tells me my estimate is now
hard to hit), receipts.

**60-second demo.** A fixture month of Hero dispatches plus Dhoot in the peer set: the QTD card
fills, and the required-rate bar turns red against the model.

**Lifecycle cost.** Per-filer specs break when a PR team redesigns the release. That breakage is
the point of the "re-confirm" state, but it is ongoing curation, perhaps an hour a month across 30
names. Monthly-filing coverage among small caps is patchy. Many file nothing between prints, and the
card must say "no interim data filed" rather than look empty.

**Biggest risk.** A false read-across: an OEM number applied to a supplier whose mix has shifted.
**Mitigation:** the edge weight is the user's, stated on the card, and the card never writes to the
model on its own.

**Size:** M.

---

## 6. Peer Set: a typed value chain you own, with a comps table and read-across on every peer print (NOT floor)

**User moment.** Amal Ltd (BSE 506597; the manifest: bulk sulphuric acid and oleum, an **Atul Ltd
subsidiary**, PE 132). Atul reports first. Today I would notice by luck. With Vysted, a read-across
card lands on Amal the evening Atul files (hypothetical event): *"Parent Atul reported. It mentions
sulphuric-acid realisations on p.7 [verbatim]. Amal sells sulphuric acid and oleum; your Amal
model's realisation line is Z."* The same peer set drives a comps table: EV/EBITDA and P/E on TTM
**and on my model's FY+1**, ROCE, growth, and standalone vs consolidated basis. Every adjustment is
a visible footnote.

**Mechanics.**
- *Peer set object:* stored per covered symbol in the Model Store as typed edges
  {peer, customer, supplier, parent, subsidiary}, with an optional weight and a user note. It is
  seeded from the fundamentals store's `sector` / `industry` / `sector_source` columns
  (`services/fundamentals_store.py:129-131`), which the user then edits. Agent-suggested edges
  (from an annual report's related-party or customer note) arrive as proposed changes with the
  page cited.
- *Comps:* `compare_symbols` is hard-capped at 2-4 instruments (`catalog.py:199-213`: "Compare 2-4
  instruments"). A `peer_comps` handler reads up to ~15 names from the local fundamentals store
  (no fan-out network storm) and joins Model Store FY+1 estimates where the user has them. Footnotes
  are structured: `{adjustment, reason, source_ref}`.
- *Read-across:* any Covered-Name Feed event of kind results, transcript or monthly update on a
  **peer-set node** (which need not be covered) produces a card on each linked covered name. The
  LLM step is narrow: given the peer's filing and the edge type, quote the passage relevant to the
  edge, or say "nothing relevant found". Quotes pass the verbatim gate.

**Why Jarvis.** Watching beyond the user's own names, which is exactly how sell-side analysts get
their best calls. Memory (the value chain persists). Receipts.

**60-second demo.** Amal's peer set shows Atul as parent and two sulphuric-acid peers. Drop in an
Atul results fixture and a read-across card appears on Amal with the quoted page. Open comps and
toggle "on your FY+1".

**Lifecycle cost.** Edges go stale when businesses change (a supplier gets a new customer). There is
an annual "review your peer sets" prompt. Industry taxonomy differs across sources, which is why
edges are user-owned.

**Biggest risk.** Read-across noise, where every peer print pings every name. **Mitigation:** only
typed edges fire (plain "peer" edges fire only on results, not on monthly updates), and a card that
finds nothing relevant is filed silently, not notified.

**Size:** M.

---

## 7. The Dodge Ledger and Who's in the Room: corporate access, remembered (NOT floor)

**User moment.** From the probe, Apollo Micro's 8 Aug 2026 call. An analyst asks whether further
acquisitions are coming, "considering the funds we have right now". Management answers:
*"There are a lot. You will start getting to hear from us, you know, from time to time. **Please keep
a watch on the stock.**"* That is a deflection, and a sell-side analyst notes it for the next meeting.
Apollo's own filing says the next meeting is the **Anand Rathi Annual Flagship Conference G-200
Summit, 22 Sep 2026, Mumbai**. The evening before, Vysted hands me a question bank: open guidance
items from idea 3, unexplained variances from idea 1, and *"asked last call, deflected: acquisition
pipeline and funding (p.N). Deflected 2 calls running."* After the next transcript lands, each
question is marked ANSWERED / DEFLECTED / NOT ASKED.

**Who's in the Room, the second half.** Transcripts name each questioner and their firm. Hero's
7 Aug call has an analyst the moderator introduces as being "with Morgan Stanley". For a small cap,
**the roster of firms asking questions quarter over quarter is an institutional-discovery signal**
that no Indian tool tracks. A call that moves from two local PMS desks to three domestic mutual funds
and a foreign broker is a re-rating precondition. The reverse is abandonment. The intimation feed
adds which conferences and roadshows management attends, from a filed feed of 10-14 meet filings per
name in six months (probe finding 2).

**Mechanics.**
- *Q&A pairing:* speaker-turn parsing of the transcript text. Turns are labelled "Name: …" (probe),
  and the moderator's "next question is from X with Y" gives the firm. This part is deterministic
  regex plus a small list of firm aliases. There is no LLM.
- *Answer labels:* deterministic features decide. Does the answer contain a number, a date, a named
  period, or a direct yes/no on the asked noun? The LLM only proposes the *subject* of the question
  (for grouping across calls). The label is advisory, and the Q&A is always shown verbatim side by
  side.
- *Question bank:* an agent run on the intimation event (`Analyst / Investor Meet` subcategory) or
  on demand. Its output is written to the user's notes through the existing `write_note` host action
  (`catalog.py:1374`), which is already gated.
- *Roster:* a `call_participants` table (symbol, call_date, person, firm, n_questions, page).
  Firm-count per call is charted.
- *New:* turn parser + fixtures (Apollo and Hero transcripts), answer-feature scorer, roster
  table, intimation parser (date, event name, city, meeting type; "Group of Investors" is stored as
  unnamed).

**Why Jarvis.** Memory of what management *would not say*, which no summary product keeps (Trendlyne
ships a summary blob per call, `census/world/fey-tijori-trendlyne.md:462-473`). Initiative (the
question bank appears before the meeting). Receipts (verbatim + page).

**60-second demo.** Load Apollo's transcript fixture and see the Q&A table with the deflection row
highlighted. Then open the roster sparkline over four calls. Then "prepare for 22 Sep" writes the
question bank into Notes.

**Lifecycle cost.** Moderator phrasing varies. Firm aliasing needs a maintained alias list
("MOSL" / "Motilal Oswal"). It costs about one fixture per new transcript format.

**Biggest risk.** Unfairly labelling a legitimate "we don't give guidance on that" as a dodge.
**Mitigation:** the label is DEFLECTED with the rule shown, never "evasive". The pattern across calls
matters more than any single label, and the user can dismiss a label with a reason (that reason is
kept too).

**Size:** M.

---

## 8. Page One: the three boxes a PM pays for, with filler measured and demoted (NOT floor)

**User moment.** The research agent produces a strong brief on Fusion Finance. It is 1,400 words,
and 600 of them are company history, what microfinance is, and "risks include regulatory changes,
competition and macroeconomic conditions". A PM reads the top 150 words and stops. Page One
restructures every brief so the top of the brief is always three boxes. **What changed** since you
last looked (the delta from the last brief on this symbol and the Covered-Name Feed since then).
**What is priced in** (idea 4). **What would change my mind** (one dated, falsifiable statement,
resolvable against a future filing). Everything else folds under "Background". A deterministic
filler score sits on the brief: *"Filler: 38%, meaning sentences with no number, no company-specific
noun and no date."*

**Mechanics.**
- *Box 1:* diff the new brief's structured legs against the previous brief for the same symbol.
  Briefs already carry `structured` (`types/brief.ts:47`, `ResearchBriefData` at `:297`), and the
  store already preserves it across re-publishes (CLAUDE.md, research brief gotcha). New: keep the
  last brief per symbol on disk.
- *Box 3:* the agent must emit one falsifier `{statement, metric, threshold, by_date}`. It resolves
  deterministically when idea 1 fills the metric. This is HN-9's Brier discipline applied to the
  research agent itself rather than to personas.
- *Filler score:* sentence-level heuristic over `parseBodyBlocks` output
  (`brief-blocks.tsx:549`). A sentence counts as substantive if it contains a numeric token, an
  entity from the resolved set, or a date. The score is fed back into the research loop once
  ("rewrite: 38% filler, cut the generic risk paragraph"). It costs one extra LLM round and is off
  in FAST mode.
- *New:* brief-history file, falsifier field on the brief contract (additive in `types/brief.ts`,
  not the Tier-1 plugin contract), filler scorer, three-box renderer.

**Why Jarvis.** It respects the reader's attention the way a good junior does, and box 3 turns every
brief into a forecast that gets checked, which is memory with teeth.

**60-second demo.** The same Fusion brief before and after: 1,400 words becomes three boxes plus a
collapsed background, with the filler meter dropping from 41% to 12% after one rewrite round.

**Lifecycle cost.** The heuristic needs tuning as the research agent's style drifts. Falsifier
resolution depends on idea 1 coverage, so unresolvable falsifiers must expire honestly rather than
linger.

**Biggest risk.** A crude filler metric punishes genuinely useful qualitative context (for example,
management-quality commentary). **Mitigation:** the metric demotes and reports. It never deletes.
Background is one click away.

**Size:** S.

---

## 9. Proceeds Ledger: IPO, QIP and preferential money, where it was promised and where it went (NOT floor)

**User moment.** Every small-cap IPO prospectus has an "Objects of the Issue" table: *₹X cr for the
new plant, ₹Y cr for working capital, ₹Z cr for general corporate purposes*. Sumax Engineering
listed on NSE Emerge on 2 Sep 2026 on an issue announced "to fund new manufacturing capacity"
(manifest source: aninews). A year later, the thing a buy-side client wants from my desk is whether
the plant money went into the plant. The filings answer it quarterly. From the probe, Fusion and
Apollo each file a **Monitoring Agency Report** and a **Reg 32 Statement of Deviation** every quarter
(Fusion's Aug report is 12 pages of extractable text; its 10 Aug statement reads *"No Deviation Or
Variation For The Quarter Ended June 30, 2026"*). Vysted shows a per-issue ledger: object, amount
promised, deployed to date, deviation declared, and the monitoring agency's comments. It flags when
"general corporate purposes" grows, when deployment stalls for two quarters, or when the capex line
lags the commissioning date management guided (idea 3's horizon drift, on a capex object).

**Mechanics.**
- *Input:* the Covered-Name Feed, subcategories `Monitoring Agency Report` and `Reg. 32 (1), (3)`.
  These are SEBI-format tables [seat knowledge, unverified this session: the format prescription
  is the ICDR monitoring-agency schedule]. Extraction is deterministic table parsing via the PDF
  lane (`extract.py:436`), with per-format fixtures.
- *Honest thresholds:* a monitoring agency is mandatory only above an issue-size threshold [seat
  knowledge, unverified this session: ₹100 cr]. Sumax's ₹53.4 cr issue (manifest) would have only
  the Reg 32 statement, and the ledger must say "no monitoring agency required for this issue size"
  rather than look empty.
- *Store:* `proceeds` table in the Model Store (symbol, issue, object, promised, deployed, period,
  deviation_flag, source_ref). Deployed-capex rows link to the model's capex line.
- *Overlap:* forensic-4 (Cheap-Paper Calendar) covers *who got* preferential shares and lock-ins.
  This covers *where the money went*. Together they close the capital-raise loop.

**Why Jarvis.** Watching a filing nobody reads, memory of the promise from the prospectus, receipts
per quarter.

**60-second demo.** Load Fusion's two monitoring-agency fixtures: the ledger fills, with each cell
badged to its page, and a stalled object pulses amber.

**Lifecycle cost.** Few formats, a slow-changing regulation and quarterly cadence make this the
cheapest idea here to keep alive. The initial objects table has to come from the offer document
(one LLM-assisted, user-accepted extraction per issue).

**Biggest risk.** Mis-reading cumulative against quarterly deployment columns. **Mitigation:** a
check that cumulative is monotonic across quarters. A violation blocks the row with the reason
shown.

**Size:** S-M.

---

## How the nine compose (why this seat is one system, not nine features)

```
Covered-Name Feed (subcategory-aware, AttachHis-safe)
   ├─ Financial Results ─────► 1 First-Hour Note ──┐
   ├─ Earnings Call Transcript ► 3 Guidance Haircut ├──► 2 LIVING MODEL ◄── 4 Priced-In reads it
   │                         └► 7 Dodge Ledger     │        ▲
   ├─ Press Release / General ► 5 Between the Prints┘        │ proposed-changes gate (user accepts)
   ├─ Analyst / Investor Meet ► 7 question bank + roster     │
   ├─ Monitoring Agency / Reg32 ► 9 Proceeds Ledger ─────────┘ (capex line)
   └─ peer-node events ──────► 6 Read-across (typed edges)
                                8 Page One renders 1-4 for every brief
```

Build order if the judge takes the cluster: Feed fixes (subcategory, AttachHis, paging) → Model
Store → 1 → 2 → 4 → 3 → 5/6/7/9 in any order → 8.

## Single strongest idea: the Living Model (idea 2), with the First-Hour Note as its engine

Every other seat's strongest idea watches filings and tells the user something. This one **changes a
number the user owns, through a gate, with the filing page attached, and remembers why**. That is the
difference between an alert and an analyst. The buy-side pays sell-side desks for the model and its
revision history more than for anything else we write. No Indian tool keeps one alive. Screener lets
you download data into your own Excel and stops there
(`census/world/perplexity-screener.md:194-195`). Trendlyne summarises calls without touching your
numbers (`fey-tijori-trendlyne.md:462-473`). Perplexity answers and forgets
(`perplexity-screener.md:130`: "retrieves, it does not reason about you").

**Why a rival cannot copy it in a month.** It is not the grid. Any team can ship a grid. It is the
four things under it that Vysted either already has or is one feed-fix away from:
1. page-receipted, unit-witnessed extraction from the long tail of Indian small-cap results PDFs
   (the fixture corpus is the moat, and it compounds with every filer shape seen);
2. a no-eval formula grammar that is already shipped and parity-tested with the TypeScript editor
   (`screener_formula.py:1-16`);
3. a diff-and-accept gate that is already the product's trust spine (`proposed-changes.ts:1-10`);
4. **local-first.** A professional's model is the most confidential file on their laptop. A cloud
   product has to persuade them to upload it, and Vysted never asks. Perplexity, Trendlyne and
   Screener are all hosted. For them this is a policy problem, not an engineering one, and a policy
   problem does not close in a month.
