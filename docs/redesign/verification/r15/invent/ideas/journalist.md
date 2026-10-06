# R15 Stage 4 ideation — seat: the technology journalist writing the launch review

Worker model id: `claude-fable-5-1`. Date: 2026-09-19. Read-only thinking; nothing built.
Every code claim below was opened and carries `file:line`. World claims cite the census world
files (`docs/redesign/verification/r15/census/world/*.md`), which carry URL + quote.

## What this seat needs, and what I found when I went looking for it

A launch review needs three things: one demo that makes a reader gasp, one honest limitation
paragraph, and one sentence that says why this exists when Perplexity Finance and screener.in
already do. I went through the code looking for each.

**The sentence (draft, to be earned by the ideas below).**
"Perplexity will answer you and Screener will show you the table; Vysted is the only one of the
three that will open the exchange filing on your own machine, show you the page, remember what
you believed last month, and tell you out loud when one of them — or Vysted itself — is wrong."

**The honest limitation paragraph (true of today's code, not the pitch).**
Vysted does not watch anything yet. There is no alert, schedule or trigger anywhere: none of the
50 capabilities in `sidecar/services/agent_tools/catalog.py:146-1444` is an alert, the workflow
node set has no trigger node (`sidecar/services/workflow_nodes/builtin.py:48-400`: fetch, compute,
agent_invoke, branch, compare, log, notify_desktop, json_path, sleep), and a grep of
`sidecar/services` for pledge / bulk-deal / block-deal / SAST returns nothing but a catalog
description string (`catalog.py:659`). Its memory is thin and lives in the wrong process: 50
figures per research space, in the renderer's workspace blob (`types/research-space.ts:83-86`,
`src/lib/brief-claims.ts:1-14`), of which the agent sees the last 12
(`sidecar/services/agent_runtime.py:329-353`) — and only while you are inside that one stock's
research space (`src/modules/chat/context-provider.ts:302-315`). The agent can write your notes
(`catalog.py:1374`) but can never read them: notes are not in the terminal snapshot
(`context-provider.ts:99-121`) and no read tool exists. It keeps exactly one brief per panel,
no archive (`src/store/brief.ts:49-53`). Its receipts stop at the document: the PDF lane knows
which pages it read (`sidecar/services/search/extract.py:506`) and then throws the page
boundaries away at assembly (`extract.py:516-518`), and a brief source has no page field
(`types/brief.ts:230-250`). Scanned results PDFs — the normal Indian small-cap case — are
unreadable: there is no OCR anywhere in `sidecar/services`, only an honest "scanned pages" note
(`extract.py:398`). Its own numeric lie-detector reads dollars, not rupees
(`sidecar/services/company_narrative.py:53-78`: `$`, K/M/B/T and western comma grouping only —
`1,05,130`, "crore" and "lakh" do not parse). And it runs only while the laptop is awake.

**The gasp demo.** Idea 1 (Red Pen), run head-to-head against a rival's answer, on stage.

What is already genuinely unusual, and what every idea below leans on: seven "DISCLOSE, never
substitute" witnesses, each born from a real hostile-battery failure — dividend
(`services/research/semantics.py:255-350`), growth (`services/growth_check.py:1-20`), identity
(`services/identity_crosscheck.py:1-16`), ownership (`services/ownership_check.py:1-20`),
earnings basis (`services/earnings_quality.py:1-21`), 52-week range
(`services/research/range_check.py:1-16`), market cap vs a BSE-derived non-provider share count
(`services/market_cap_witness.py:1-17`) — plus citation integrity
(`services/research/citecheck.py:1-20`). The product already knows how to say "my sources
disagree". It just never says it first, never remembers it, and never points it at anyone else.

Eight ideas. Floor-list ideas are marked FLOOR; six are not on the floor list (idea 5 is half
floor). Scene figures are ILLUSTRATIVE unless attributed to the battery manifest
(`docs/redesign/verification/r15/battery/manifest.json`) or a cited module docstring.

---

## 1. Red Pen — "check this" for anything anyone tells you (NOT floor)

**User moment.** Saturday, a Telegram channel posts: "Naperol Investments — mcap 371 cr sitting
on 888 cr of investments, book 1609 vs price 645, promoters accumulating." The user pastes it
into the composer and types `check this`. Thirty seconds later the same paragraph comes back
marked up, figure by figure: `[OK] 371 cr — BSE close x BSE-master share count, as of Fri`;
`[OK] book 1609 — FY26 balance sheet`; `[BASIS] "888 cr of investments" is market value of
quoted holdings, not the balance-sheet figure — both shown`; `[X] "promoters accumulating" —
promoter % flat for 4 quarters, latest SHP XBRL linked`; `[?] I could not reach a source for
the fifth figure — treat as unverified`. Monday on stage, the journalist does the same with
Perplexity Finance's answer on Restaurant Brands Asia's market cap (the 23% stale-share-count
case in `market_cap_witness.py:6-9`).

**Mechanics.** Rides the numeric-verification pass that already exists for the company
narrative: `_NUMBER_RE` / `_normalise_token` / `_verify_text`
(`sidecar/services/company_narrative.py:64,185,209`) extract every numeric token and match it
against source values within tolerance (`:49-50,80`). Today it is private to one route
(`sidecar/routers/fundamentals.py:154-168`), matches against a bare `list[float]`
(`_source_values`, `:97`) and can only redact to `[unverified]`. New parts: (a) a LABELLED
source map — value → {field, provider, as_of, url} — so every tick carries its receipt; the
provenance already rides every registry result; (b) rupee literacy in the token grammar — `₹`,
`Rs`, crore / lakh / lakh-crore scale words, Indian comma grouping (`1,05,130`) — the single
most important gap, because the benchmark's worst documented failure is a x1000 scale misread
(`census/world/perplexity-screener.md:92-115`); (c) a four-state verdict (`OK / X / BASIS / ?`)
where BASIS is fed directly by the witness conflicts already emitted in the
`field / sources / note` shape (`services/research/semantics.py:255-764`); (d) one new
`check_claims` capability, `kind="read_handler"`, in `catalog.py` — which by the catalog's one
rule (`catalog.py:1469-1474`) also projects to the external MCP surface, so "check this with
Vysted" works from Claude Desktop or Cursor for free; (e) a marked-up-text block in
`src/modules/research/brief-blocks.tsx`. Entity binding reuses `resolve_symbol`
(`catalog.py:170`). The agent also runs its own prose through it before display — it already
does exactly that for the narrative.

**Why it is Jarvis.** Receipts, turned outward. Jarvis is the one in the room who says "sir,
that figure is wrong" — about anyone's figure, including his own.

**60-second demo.** Split screen. Left: ask a rival answer engine about a BSE small-cap, copy
the answer. Right: paste, `check this`. The paragraph re-renders with two ticks, one strike
with both share-count sources named, one BASIS note explaining a one-off, one honest `?`.
Click the strike: the exchange page opens. No slide needed.

**Lifecycle cost.** The grammar is stable; the witnesses ride NSE/BSE endpoints that already sit
behind circuit breakers (`services/nse_provider.py:279`, `services/provider_health.py:1-20`).
The hostile battery (`docs/redesign/verification/r15/battery/manifest.json`) becomes the
regression suite: every battery trap is a paste that must produce the right mark. Cost to keep
alive: refresh the battery each release.

**Biggest risk.** A red pen that is wrong is worse than no red pen. Consolidated vs standalone,
TTM vs FY, reported vs adjusted are all "different basis", not "wrong"; an `[X]` may only fire
when the witness is the same basis and period, names its source and as-of date, and otherwise
the mark degrades to BASIS or `?`. The default must be humility.

**Size.** M.

---

## 2. The Blind-Spot Ledger — the app writes its own limitation paragraph (NOT floor)

**User moment.** The user researches Jumbo Bag Ltd (BSE-only, nano-cap; profit CAGR 82% on
sales CAGR 7% per the battery manifest, so every ratio is source-dependent). The brief ends not
with a disclaimer but with a specific confession: "I read 8 of 112 pages of the FY26 annual
report. Pages 41-58 are scanned images with no text layer; the segment table is in there and I
did not read it. NSE lane: not applicable (BSE-only). Two figures had their citations removed
because the cited page did not support them. Depth ran at 'deep', not the 'heavy' you asked
for — wall budget." A journalist reads that and knows what the rest of the brief is worth.

**Mechanics.** Every ingredient is already computed and then dropped or scattered.
`extract_pdf_text` returns `pages_used`, `page_count`, `pages_empty`
(`sidecar/services/search/extract.py:528-537`); the announcements merge records failed lanes in
`errors` (`sidecar/models/announcements.py:56`, `services/corporate_disclosures.py:271-274`);
citecheck knows which claims it softened (`services/research/citecheck.py:12-20,216`); the
brief already carries `degradedReason` (`types/brief.ts:196`); tool timeouts and open circuit
breakers are known at dispatch (`catalog.py:1553-1563`, `services/provider_health.py`). New:
fold these into one `brief.structured["coverage"]` object per run (the raw-evidence store is
already shared per run, `services/research/deep.py:331-351`) and render one short, specific
"What I could not see" block in `brief-blocks.tsx`. Deterministic, zero LLM tokens, works on the
keyless lane.

**Why it is Jarvis.** Receipts for what was NOT read. Coding agents say "I could not run the
tests"; no finance tool says "I could not read page 41". Perplexity's reviewers complain that
"the presence of sources can create a false sense of certainty"
(`census/world/perplexity-screener.md:488-492`) — this is the antidote.

**60-second demo.** Research a small-cap whose results PDF is a scan. The brief says so, names
the pages, and links the PDF at that page so the user can read the table themselves.

**Lifecycle cost.** Near zero — it reports counters the pipeline already keeps. The only upkeep
is wiring each NEW lane's failure signal into the same object.

**Biggest risk.** Boilerplate. If it prints on every brief it becomes a disclaimer nobody reads;
it must print only non-trivial gaps, in one to four lines, with numbers.

**Size.** S.

---

## 3. The Scorecard — the first finance AI that keeps score on itself (NOT floor)

**User moment.** In October the user reopens Dhanlaxmi Bank. Before anything else the agent
says: "On 19 Sep I told you equity capital was 395 cr after the rights issue; that still holds
against the Sep-quarter filing. I also told you revenue growth was +14% — the bank's
own quarterly statements compute +6% on the same period; that was the provider's scalar and it
was wrong. My record on this name: 8 of 9 figures held." In Settings, a "Track record" page:
briefs written, figures re-checked, figures contradicted by later primary filings, broken down
by which upstream provider supplied the wrong one.

**Mechanics.** Rides the claims ledger: `extractBriefClaims` / `recordBriefClaims` read figures
off `brief.structured` metric cards with no LLM (`src/lib/brief-claims.ts:1-14`), stored as
`ResearchSpaceClaim {symbol, metric, value, statedAt}` (`types/research-space.ts:34-42`) and
surfaced as "PRIOR STATED VALUES" in the preamble (`agent_runtime.py:344-353,402`). Three
limits make it a seed, not a scorecard: it is capped at 50, scoped to a research space, and the
claim has no period / as-of / provider — so "the world moved" cannot be told apart from "I was
wrong". New: a sidecar `claims.db` (SQLite, same shape discipline as
`services/runs_store.py:55`) keyed by symbol, each claim carrying `period`, `as_of`, `provider`,
`source_url`; a deterministic re-check when a new brief for the same symbol publishes (same
metric + same period + different value = a graded miss; different period = a change, not a
miss); a read-only `track_record` capability and a small Settings page.

**Why it is Jarvis.** Memory plus receipts about itself. Trust is not a claim, it is a record.

**60-second demo.** Needs history, so the demo ships with a recorded two-month record for one
name, labelled as a recording, then does one live re-check: a fresh brief lands and one old
figure flips to "contradicted by filing dated ...", with both receipts.

**Lifecycle cost.** Grows forever unless capped per symbol and vacuumed; and the repo has no
migration story (`CREATE TABLE IF NOT EXISTS` only, `docs/CURRENT_STATE.md:849-854`) — this
store needs a schema version from day one.

**Biggest risk.** Grading unfairly in either direction. A price that moved is not an error; a
restated prior-period figure is ambiguous. Only same-period, same-basis contradictions from a
primary filing may count as a miss, and the page must show the denominator.

**Size.** M.

---

## 4. Brief Diff — ask again, see only what changed (NOT floor)

**User moment.** The user researched Viyash Scientific (ex-Sequent Scientific, renamed
2026-01-23) three weeks ago. Today they type "anything new on Viyash?". Instead of a second wall
of prose: a "Changed since 28 Aug" strip — promoter holding 52.1% -> 49.8% (new SHP, linked),
two new exchange announcements (one "Outcome of Board Meeting"), one new conflict (provider
52-week high now disagrees with exchange history), everything else collapsed as "unchanged
(14 figures)".

**Mechanics.** The brief store already carries the prior brief INTO the new run
(`src/store/brief.ts:49,165-173`) and a restored brief always lands archived, never silently
current (`brief.ts:5-9,94`), so a prior is available across relaunches. `briefFromInput`
already preserves `structured` across re-publishes (per CLAUDE.md, "research brief renders as
typed blocks"). New: a pure `diffBriefs(prior, next)` beside the other pure helpers in
`src/lib/brief-ingest.ts` (metric cards by label, sources by URL, conflicts by field), a
"changed since" block at the top of `BriefBody`, and announcements filtered to
`ts > prior.createdAt` (`Announcement.ts`, `sidecar/models/announcements.py:41`).

**Why it is Jarvis.** Memory. Every agent-native tool converged on "the unit of review is the
change, not the transcript" (`census/world/agent-native-ux.md:46-56`); finance tools still hand
you the whole document every time.

**60-second demo.** Research a name, accept a new quarter's SHP fixture, ask again: three lines
change, the rest folds away.

**Lifecycle cost.** Low; pure frontend function with unit vectors. Breaks only if metric labels
are renamed — diff on stable keys, not display labels.

**Biggest risk.** Noise: price-derived metrics change every day. Diff must separate "filing
facts" from "market-moved values" and lead with the former.

**Size.** S.

---

## 5. The Rulebook — it holds you to your own words (NOT floor in its behavioural half)

**User moment.** Months ago the user wrote three lines in plain English: "I don't buy below 50%
promoter holding. No companies with debt/equity above 1. My Fusion Finance thesis: credit costs
normalise by Q3 FY27." Today they ask the agent to add Crest Ventures to the paper portfolio.
The proposed-change card arrives with an objection attached: "You told me on 3 Aug: no
debt/equity above 1. Crest is at 1.4 (FY26 balance sheet, linked). Accept anyway?" Jarvis does
not block; he raises an eyebrow with a receipt.

**Mechanics.** Today the user's own words are invisible to the agent: `write_note` exists
(`catalog.py:1374`, applied at `src/lib/host-actions.ts:803-813`) but notes never ride the
snapshot (`src/modules/chat/context-provider.ts:99-121`) and there is no read tool. New: (a) a
"Rules" note bucket in `src/store/notes.ts` that DOES ride the snapshot, capped, and renders
into the preamble beside prior stated values (`agent_runtime.py:376-402`) — memory as a document
the user can open and edit, which is the proven form (`census/world/agent-native-ux.md:167-178`);
(b) quantitative rules compile once to the screener formula grammar that already exists —
`compile_formula` / `evaluate_formula` (`sidecar/services/screener_formula.py:441,563`), no
eval, recursive-descent — so "debt/equity above 1" is a formula evaluated against ONE symbol,
deterministically, with no LLM in the judgment; (c) the check runs at the single choke point
every mutation already passes through, the diff/accept gate (`src/store/proposed-changes.ts:92-214`),
for `portfolio_add_position` and `add_to_watchlist`; (d) qualitative theses are handed to idea 6
to be tested against new filings (that half IS the floor item).

**Why it is Jarvis.** Memory plus initiative, aimed at the user's discipline rather than at the
market. Helm's verdict on Perplexity was "retrieves, it does not reason about you"
(`census/world/perplexity-screener.md:128-134`).

**60-second demo.** Type one rule. Ask to add a stock that breaks it. The accept card objects,
quoting the rule with its date and the filing figure. Accept or decline — the user stays in
charge.

**Lifecycle cost.** Rules referencing fields the fundamentals model lacks must fail loudly at
compile time ("I cannot check this rule: no pledge data"), not silently pass. Keeping the
formula grammar's TS twin in lockstep is an existing cost (`screener_formula.py:10-13`).

**Biggest risk.** Nagging. One objection per action, never on reads, and a rule the user
overrides twice asks once whether it should be retired.

**Size.** M.

---

## 6. The Handover — the app speaks first (FLOOR: watching, stitched to the user's own book)

**User moment.** 8:40 am, lid opens. Before the user types anything: "While you were away
(14h 10m): 3 of your 11 holdings filed with the exchange. One matters — Jonjua Overseas
allotted its 7:24 bonus on 7 Sep; your 1,200 shares are now 1,550 and your cost basis per share
changed; I have NOT touched your portfolio, here is the proposed edit. Fusion Finance: board
meeting for results on Thursday. Nothing else needs you." Each line links the exchange PDF.

**Mechanics.** A laptop sleeps, so this is a catch-up-on-wake pass, not a cron. Rides
`get_announcements` (`sidecar/services/corporate_disclosures.py:265`), whose `_dedup_key`
(`:251`) is exactly the seen-set key a cursor needs; `get_results_calendar` (`:335`, fetched
today but with no surface — `services/research/disclosures.py:15-18`); `get_shareholding`
(`:366`); declared-unpaid dividends (`services/dividend_actions.py:1-16`); renames
(`services/nse_symbol_change.py:1-12`). The background-task lifecycle has a working precedent in
the warm loop — started in the lifespan and stopped in its `finally`
(`sidecar/app.py:130,142`, `services/fundamentals_warm.py:403,433`). Deterministic triage first
(exchange category + phrase list: auditor resignation, pledge, SAST, related party, rating
action, bonus/split) — zero tokens; then at most ONE budget-capped LLM pass over survivors as a
durable run (`services/run_manager.py:237`, metered by `services/budget_guard.py:87-166`). OS
notification through the plugin already registered (`src-tauri/src/lib.rs:394`), whose frontend
bridge today only drains workflow intents (`src/lib/desktop-notification.ts:1-24`). New: a
`watch.db` cursor store, a holdings+watchlist push from the renderer at launch (the portfolio is
sidecar-side already, `services/portfolio_db.py:27-34`; the watchlist is not), a handover card,
polite pacing (<=1 req/s/host). Portfolio edits arrive as proposed changes, never applied.

**Why it is Jarvis.** Initiative and watching. "Answers, it does not watch" is the benchmark's
named gap (`census/world/perplexity-screener.md:128-137`), and Vysted today ships zero alerts
(`perplexity-screener.md:523-531`).

**60-second demo.** Quit the app. A fixture announcement lands. Reopen: the app talks first, one
line, one PDF, one proposed portfolio edit waiting at the gate.

**Lifecycle cost.** The highest of the eight. NSE's cookie-dance lane and BSE's JSON API change
without notice; the triage phrase list rots; the exchange breaker must degrade the card to "I
could not check NSE since Tuesday" rather than to silence.

**Biggest risk.** Silence that looks like "nothing happened". The card must always state what it
checked, when, and which lanes failed — idea 2's ledger applied to the watcher. Second risk:
fan-out against exchanges from a user IP on every launch; cap symbols and cache per day.

**Size.** L.

---

## 7. Page-anchored receipts and the Receipt Bundle (FLOOR: receipts, extended to be publishable)

**User moment.** The brief on Elcid Investments says book value per share is 3,01,137. The user
hovers the figure: "Annual Report FY26, p. 87, line: 'Net worth ...'", clicks, and the PDF opens
at page 87. Then they export the brief to send to a sceptical friend: the bundle carries, for
every figure, the URL, the page, the quoted line, the fetch time and the SHA-256 of the bytes
Vysted actually read — so someone who does not own Vysted can check it, and a journalist can
print it.

**Mechanics.** The PDF lane already selects and records pages (`pages_used`,
`sidecar/services/search/extract.py:506`) and then flattens them into anonymous paragraphs
(`extract.py:516-518`). New: keep a `[p.N]` marker per paragraph through assembly; the evidence
audit that already judges a claim against the full extracted page text
(`services/research/citecheck.py:12-16,235`) returns the page on which it found the figure; add
`page?: number` and `quote?: string` to `BriefSource` (`types/brief.ts:230-250`, mirrored in
`sidecar/models`, same commit); open with `#page=N`. The bundle rides the existing atomic export
path (`src/lib/export-artifact.ts:1-15`) plus a manifest JSON.

**Why it is Jarvis.** Receipts, to coding-agent standard: not "source: annual report" but file,
line, hash.

**60-second demo.** Hover a number, click, land on the page. Export, open the manifest, verify a
hash on camera.

**Lifecycle cost.** Exchange attachment URLs move (the BSE `AttachLive` / `AttachHis` split is
already noted in `corporate_disclosures.py` header); the hash is what survives link rot. Page
markers cost tokens in the evidence excerpt — keep them terse.

**Biggest risk.** Scanned PDFs have no text layer, so there is no page to anchor; the receipt
must then say "scanned — figure taken from the aggregator, not this page" rather than fake an
anchor. No OCR exists in the sidecar today.

**Size.** M.

---

## 8. Audit Me — the shipped lie-detector test (NOT floor)

**User moment.** A reviewer who trusts nothing opens the command palette and runs "Trust audit".
With no API key at all, the app runs its own resolver, fundamentals and witnesses across a
bundled set of names chosen to break it — JNPR (Juniper Green Energy, listed 2026-08-06, ticker
collides with Juniper Networks), SEQUENT -> VIYASH rename, Jonjua's bonus, Elcid's six-figure
price, SIFY (an Indian company with no Indian listing: the right answer is "none") — and
publishes a report card: resolved correctly 19/24, conflicts disclosed 11, wrong-and-silent 2,
with the two failures printed in full.

**Mechanics.** The battery and its outside-truth packs already exist as build artefacts
(`docs/redesign/verification/r15/battery/manifest.json`, `battery/packs/`). New: freeze a
structural subset into a bundled fixture (identity, exchange, board, face value, scale, "has no
NSE line" — fields that do not move daily, each with `as_of`); a runner that calls the existing
handlers directly (`resolve_symbol` `catalog.py:170`, `fundamentals` `:225`,
`shareholding_pattern` `:686`) and collects the witness conflicts; a report-card block. No LLM,
so it is the one impressive thing the keyless stranger can do in the first five minutes. It is
also the regression suite for ideas 1 and 7.

**Why it is Jarvis.** Receipts about itself, run on the reader's machine. Every rival's accuracy
claim is a sentence on a landing page; this one is a button.

**60-second demo.** Fresh install, no keys. Run the audit. Watch it fail two, in red, by name.

**Lifecycle cost.** Truth packs rot — renames, delistings, new collisions. Each pack carries
`as_of`; the report states pack age and greys out anything older than two quarters; refresh is
one agent-day per release and belongs on the release checklist.

**Biggest risk.** Looks like a stunt if the failures never shrink. It only works if the numbers
in the README are the numbers the button prints.

**Size.** M.

---

## Single strongest idea: Red Pen (idea 1)

It is the only one of the eight that needs no elapsed time, no history and no explanation: a
reader watches another product's paragraph get corrected, with the exchange page one click
away. It is also the sentence made literal — Vysted is the one that checks.

Why a rival could not copy it in a month:

1. **The witnesses are scar tissue, not a feature.** Each of the seven cross-checks exists
   because a specific hostile name broke the app across R12-R15 (Gujarat Gas's rename, RBA's
   stale share count, Tilaknagar's exceptional items, PFC's declared-unpaid dividend, Bilcare's
   52-week range — the module docstrings cited above name them). A red pen with no witnesses
   is a second opinion from the same vendor feed.
2. **The supply is structural.** Perplexity's Indian numbers are a third-party vendor feed
   (`census/world/perplexity-screener.md:264-280`); a hosted product cannot cookie-dance NSE
   from a data-centre IP at scale or license its way around it in a month, while a local-first
   app fetches politely from the user's own connection as the user's own agent
   (`services/nse_provider.py:238-345`, `services/bse_provider.py:612-760`). Screener has the
   data but no agent, no API (`perplexity-screener.md:296-310`) and a per-answer meter.
3. **The incentive is inverted.** An answer engine sells confidence; shipping a tool that
   strikes through answers — its own included — attacks its own product. Vysted has no answer
   business to protect. Its brand is the disagreement.
