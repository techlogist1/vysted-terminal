# R15 Invent — ranked backlog

**Worker model:** `claude-opus-5-5[1m]` · **Date:** 2026-09-23 · **Branch:** `004-r4-experience-rebuild` · **Spec:** `tooling/PROMPT_offmachine_s2.md` §6 (JUDGE panel), single stage, no refute.

**Inputs:** 70 ideas from eight seats (bloomberg 9, retail 8, forensic 9, quant 9, hn-sceptic 9, journalist 8, sellside 9, designer 9) and the 6 Tier-A opportunities that survived the session-2 verify pass (OPP-1, 2, 3, 4, 6, 7; OPP-5 struck). **Output:** 58 ranked backlog items. Every input appears exactly once in the source index at the end; nothing was dropped silently. Machine-readable twin: `BACKLOG.json` (same data, one object per ranked item).

## How to read this

- **A row is a thing to build, not a seat's idea.** Seven seats proposed the same wake sweep and five the same thesis tripwire; ranking them separately would rank one build seven times. Duplicates are merged into the variant with the best mechanics (named `primary`), and the distinct parts of the others are listed as `absorbed`. One row (BL-02) is a derived substrate that several seats specified inside their ideas and that about twenty items stand on.
- **Size** is build days to release grade for a small agent team, tests and fixtures included, excluding the item's listed dependencies and prerequisite defect fixes. Bands: S = 2-4 days, S-M = 4-5 days, M = 5-8 days, M-L = 9-12 days, L = 12+ days.
- **Lifecycle cost** is what breaks in six months and what it costs to keep alive, carried over from the idea's own lifecycle field and merged where rows were merged.
- **Design system:** `on` uses existing R9 tokens and blocks; `on, extends it` adds one primitive or state and needs an R9 conformance review (never a reopen). No item is off the design system.
- **Plugin contract:** no item changes `types/plugin.ts`. One (BL-28) uses `contributesData` as it is.
- **Tracked-portfolio write** replaces 'order-safety surface' after the 23 Sep trading removal: does the item write the user's tracked portfolio, and through what gate. Read it against today's gate: the proposed-changes gate stages data-writes in ASK mode only; AUTO auto-applies every non-order kind, portfolio add/update/delete included (`src/store/proposed-changes.ts:113-119`, verified 2026-09-23; COD-host-actions-proposed-changes-3, admitted high); accept re-resolves the target against whichever portfolio is active (…-1); there is no undo (WLD-agent-native-ux-2); `cost_basis` is not validated (WLD-harness-tools-3). Only one ranked item writes holdings (BL-17, the Tip Ledger shadow position) and it lists those fixes as prerequisites.

## Method

Each merged item was judged on four things: **value** (moat fit across data trust, research quality, a finance-tuned agent and local-first; how much Jarvis it delivers across initiative, watching, memory and receipts; audience breadth), **leverage** (how many other items it unlocks, and which admitted census findings it closes), **cost** (days, including any new substrate) and **risk** (the chance it ships misleading, and its lifecycle rot). Tiers come first; order inside a tier is judgement, and every row states its reason in one line. Five rules decided the close calls:

1. **Trust before initiative.** Nothing that watches ships before the feed it watches is complete (BL-02 before BL-04). A watcher reading a 30-day BSE window reads 'nothing happened' for every quiet small cap.
2. **Zero-token, keyless value first.** The witnesses, the firewall, coverage honesty and page receipts cost no tokens and work for the user who has not entered a key, the user onboarding invites.
3. **Recorders start early.** Anything whose value is elapsed time (BL-08) ranks above its surfaces, because a late start can never be backfilled.
4. **Nothing writes the book before the gate is real.** Items that write the tracked portfolio wait for COD-host-actions-proposed-changes-1 and -3 and for undo (BL-19); autonomy comes after undo (BL-39).
5. **Nothing reads vendor statements for small caps before the statement lane has a correctness gate.** Statements for SME ticker collisions serve a US company's numbers (DAT-P3-1, P4-1, P5-1, P6-1, admitted critical); items that need them (BL-35, BL-44, BL-50, BL-55) carry those fixes as prerequisites.

## The spine

```
BL-02 feed ──┬─► BL-04 Watch ──┬─► BL-09 Tripwires ──► BL-32 Alerts · BL-55 Linter
             │                 ├─► BL-23 Gatekeeper exits ──► BL-28 Rule packs (+ BL-13)
             │                 └─► BL-37 Calm · BL-42 Pre-print · BL-46 Cheap paper
             ├─► BL-15 Results-day ──┬─► BL-16 Guidance ledger ──► BL-42 · BL-48 Dodge ledger
             │   (needs BL-05, 06)   ├─► BL-26 Living model ──► BL-53 Between prints · BL-47 FY+1 comps
             │                       └─► BL-44 SUE · BL-41 falsifier
             └─► BL-25 Filing clock · BL-45 Proceeds ledger
BL-01 Witnessed ──► BL-11 Proof Open · BL-21 Fig ──► BL-43 One number
BL-03 Reasons about you ──► BL-09 · BL-27 Rulebook · BL-37
BL-05 Firewall ──► BL-10 Red Pen · BL-15 unit witness · BL-36 Forkable
BL-06 Page receipts ──► BL-22 Locker ──► BL-36 · BL-54 Redline ◄── BL-31 Seven Pages
BL-08 Recorder ──► BL-14 derived series · BL-24 Exit Door ──► BL-33 Radar · BL-30 Drift · BL-50/51/52
BL-19 Undo ──► BL-39 Earned autonomy
```

## Ranked backlog

| # | Item | Tier | Size | Days | Portfolio write | Depends on | Sources |
|---|---|---|---|---|---|---|---|
| 1 | BL-01 Witnessed by default | 1 | S | 3 | none | — | designer-1 |
| 2 | BL-02 A disclosure feed you can build on | 1 | S | 3 | none | — | derived substrate |
| 3 | BL-03 Reasons about you: your position and your notes in every answer | 1 | S-M | 4 | reads | — | OPP-7 |
| 4 | BL-04 The Watch: wake sweep and a 'while you were away' card that states its blind spots | 1 | M | 8 | none | BL-02 | bloomberg-1, retail-8, hn-sceptic-6, journalist-6, OPP-1 |
| 5 | BL-05 Number firewall with a rupee scale witness | 1 | M | 8 | none | BL-06 | hn-sceptic-1, OPP-2 |
| 6 | BL-06 Page receipts | 1 | S-M | 5 | none | — | journalist-7, forensic-7, hn-sceptic-2 |
| 7 | BL-07 Coverage honesty: say what the app could not see | 1 | S-M | 4 | none | — | journalist-2, designer-6 |
| 8 | BL-08 Start recording: point-in-time EOD and fundamentals observations | 1 | S-M | 4 | none | — | quant-1 |
| 9 | BL-09 Tripwires: kill criteria compiled once, watched for free | 2 | M | 6 | none | BL-03, BL-04, BL-13 | forensic-6, hn-sceptic-5, bloomberg-9, quant-9, OPP-1 |
| 10 | BL-10 Red Pen: paste anyone's numbers, get a marked-up verdict | 2 | M | 6 | none | BL-05 | journalist-1, bloomberg-6, hn-sceptic-3 |
| 11 | BL-11 Proof Open: the first minute is a demonstration | 2 | S | 2 | none | BL-01 | designer-2 |
| 12 | BL-12 Turn receipt | 2 | S | 2 | none | — | designer-9 |
| 13 | BL-13 Cap-table X-ray: names, beneficial owners, encumbrance, holder counts, pledge trend | 2 | M | 7 | none | — | forensic-3, retail-6 |
| 14 | BL-14 Corporate-action chain | 2 | S-M | 5 | none | BL-08 | quant-6 |
| 15 | BL-15 Results-day first take (deterministic results-grid extraction) | 2 | M | 7 | none | BL-02, BL-04, BL-05, BL-06 | sellside-1 |
| 16 | BL-16 Guidance ledger: what management said against what printed | 2 | M-L | 10 | none | BL-02, BL-06, BL-15 | OPP-4, hn-sceptic-7, sellside-3, bloomberg-4 |
| 17 | BL-17 Tip Ledger | 2 | M | 8 | **writes (gate)** | BL-14 | retail-1 |
| 18 | BL-18 Brief diff: ask again, see what changed | 2 | S | 3 | none | BL-02 | journalist-4 |
| 19 | BL-19 Undo and ghost edits | 2 | M | 6 | undo only | — | designer-7 |
| 20 | BL-20 Trust bench and 'Audit me' | 2 | M | 6 | none | — | journalist-8, hn-sceptic-4, OPP-3 |
| 21 | BL-21 The Figure and the Why key | 3 | M | 6 | none | BL-01 | designer-4, OPP-3 |
| 22 | BL-22 Evidence locker | 3 | M | 6 | none | BL-06 | forensic-7, hn-sceptic-2 |
| 23 | BL-23 Gatekeeper exits | 3 | S | 3 | none | BL-02, BL-04 | forensic-1 |
| 24 | BL-24 Exit Door: can I actually get out | 3 | S-M | 4 | reads | BL-08, BL-04 | retail-3, bloomberg-2 |
| 25 | BL-25 Filing clock | 3 | S | 3 | none | BL-02 | forensic-2 |
| 26 | BL-26 Living model | 3 | M | 8 | none | BL-15 | sellside-2, sellside-3 |
| 27 | BL-27 Rulebook: it holds you to your own words | 3 | M | 6 | none | BL-03, BL-24 | journalist-5, bloomberg-5 |
| 28 | BL-28 Red-flag rule packs | 3 | M | 7 | reads | BL-04, BL-13, BL-23 | forensic-9 |
| 29 | BL-29 Track record: the app keeps score on itself and its providers | 3 | M | 6 | none | BL-15 | journalist-3, hn-sceptic-4 |
| 30 | BL-30 The number changed: drift ledger | 3 | S-M | 4 | none | BL-08, BL-14, BL-02 | quant-2, bloomberg-3 |
| 31 | BL-31 Seven Pages: annual-report reader | 3 | M | 7 | none | BL-06, BL-22 | retail-7, forensic-7 |
| 32 | BL-32 Alerts with a track record | 3 | S-M | 4 | none | BL-04, BL-09 | bloomberg-7 |
| 33 | BL-33 Operator radar | 3 | M | 6 | none | BL-08, BL-02, BL-24 | retail-2 |
| 34 | BL-34 Honesty card and trial ledger for backtests | 3 | M | 6 | none | BL-08 | quant-3 |
| 35 | BL-35 Priced in: what the market cap already assumes | 3 | S | 3 | none | BL-16, BL-26 | sellside-4 |
| 36 | BL-36 Forkable research (.vybrief) and the receipt bundle | 4 | M | 6 | none | BL-05, BL-22 | hn-sceptic-8, journalist-7 |
| 37 | BL-37 Calm protocol | 4 | M | 6 | none | BL-03, BL-04, BL-33 | retail-5 |
| 38 | BL-38 Instant cockpit | 4 | M | 5 | none | — | designer-3 |
| 39 | BL-39 Earned autonomy | 4 | S | 3 | governs gate | BL-19 | designer-8 |
| 40 | BL-40 GO bar and learned routines | 4 | S-M | 4 | none | — | bloomberg-8 |
| 41 | BL-41 Page One | 4 | S | 3 | none | BL-18, BL-35, BL-15 | sellside-8 |
| 42 | BL-42 Pre-print card and your forecast record | 4 | S-M | 5 | none | BL-04, BL-15, BL-16 | bloomberg-4 |
| 43 | BL-43 One number, one truth | 4 | S | 3 | none | BL-21 | designer-5 |
| 44 | BL-44 Surprise without analysts (SUE) | 4 | S-M | 4 | none | BL-15, BL-51 | quant-8 |
| 45 | BL-45 Proceeds ledger | 4 | S-M | 5 | none | BL-02 | sellside-9 |
| 46 | BL-46 Cheap-paper calendar | 4 | M | 6 | none | BL-04, BL-13 | forensic-4 |
| 47 | BL-47 Peer set and read-across | 4 | M | 7 | none | BL-02, BL-04, BL-26 | sellside-6 |
| 48 | BL-48 Dodge ledger and who's in the room | 4 | M | 7 | none | BL-02, BL-16 | sellside-7 |
| 49 | BL-49 User-addable MCP servers | 4 | S-M | 5 | none | — | OPP-6 |
| 50 | BL-50 Factor X-ray | 4 | S-M | 5 | reads | BL-08 | quant-7 |
| 51 | BL-51 Incubator: frozen rules with an out-of-sample record | 4 | M | 6 | none | BL-08 | quant-4 |
| 52 | BL-52 As-of screens | 4 | S | 3 | none | BL-08 | quant-1 |
| 53 | BL-53 Between the prints | 4 | M | 7 | none | BL-02, BL-26, BL-47 | sellside-5 |
| 54 | BL-54 Annual-report redline | 4 | M | 8 | none | BL-31, BL-22 | forensic-8 |
| 55 | BL-55 Accounts linter with reasoned suppressions | 5 | M | 6 | none | BL-09 | forensic-5 |
| 56 | BL-56 Personas on probation | 5 | M | 6 | none | BL-04, BL-15 | hn-sceptic-9 |
| 57 | BL-57 Rule forge: event studies from any predictive sentence | 5 | L | 14 | none | BL-08, BL-02, BL-34 | quant-5 |
| 58 | BL-58 'I noticed you bought' | 5 | S-M | 4 | reads | BL-03, BL-14 | retail-4 |

Tier totals (build days, excluding prerequisite defect fixes): Tier 1: 8 items, 39 days · Tier 2: 12 items, 68 days · Tier 3: 15 items, 79 days · Tier 4: 19 items, 98 days · Tier 5: 4 items, 30 days.

## Items in rank order

### Tier 1: Ship first: trust made visible, and the substrates everything else stands on

#### 1. BL-01 · Witnessed by default

Tier 1 · **S, 3 days** · Sources: designer-1 (primary)

**What.** Run the existing zero-token witness fan-out (ownership, growth, earnings basis, 52-week range, market cap) on the overview page through one read-only GET, and render data conflicts inline in the fundamentals cell, so a keyless user sees Yahoo's 141x-wrong institutions figure beside the BSE filing's value instead of as plain fact.

**Why #1.** Highest value per day in the set: the product's one real moat (six battery-born witnesses) is hidden behind a paid LLM turn while the first page a keyless user opens shows the uncorrected number (two admitted critical findings), and one route plus one cell variant discloses it at zero tokens.

**Size.** S (2-4 days), estimated 3 days. One route over snapshot_structured, one cell variant, one 1-day cache key.

**Lifecycle cost.** Adds one consumer to witnesses that already carry their own upkeep (exchange endpoint drift, circuit breakers); a witness regression now shows on the most-visited page, which is where it should show. Exchange load per overview open is bounded by a 1-day per-symbol cache and the existing breaker.

**Design system:** on. Uses the ConflictLine data_conflict / definitional tones (brief-blocks.tsx:129-176) inside the existing FundamentalValueCell; no new visual language.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write. Read-only GET route.

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** DAT-P12-1 (critical; discloses on the overview), DAT-P14-2 (critical; discloses on the overview), DAT-S3-1 (high; discloses on the overview), DAT-P16-1 (medium), DAT-S4-2 (medium), DAT-P8-4 (medium)

**Biggest risk.** Bank and definitional conflicts fire on nearly every open and drown the signal; inline only data_conflict, show definitional pairs on hover.

**Judge notes.**
- Mechanism verified 2026-09-23: the overview renders Yahoo held_percent_insiders / held_percent_institutions directly (EquityOverviewPanel.tsx:142) while the ownership witness (ownership_check.py, which covers insiders vs promoter group and institutions) runs only inside snapshot_structured (fast.py:261), whose callers are all LLM-started research (iter.py:339,915; deep.py:1035; fast.py:622); routers/fundamentals.py imports no witness.
- The symptom is already in the register as an admitted family: DAT-P12-1 and DAT-P14-2 (critical: overview 'Insiders' 51.18% and 46.6% against exchange promoter 0% and 29.67%, served with field_meta status 'ok'), DAT-S3-1 (high), DAT-P16-1, DAT-S4-2, DAT-P8-4. The DAT-P16-1 refute confirms the research path already discloses exactly this gap as a data_conflict; the overview path never runs the witness. BL-01 is the zero-token mechanism that discloses it where the user looks. The defect lane may still choose to render the SEBI promoter-group value as the primary figure; the screener's field label (DAT-S1-2) is a separate fix.

#### 2. BL-02 · A disclosure feed you can build on

Tier 1 · **S, 3 days** · Sources: derived substrate of sellside 'Covered-Name Feed' (substrate of sellside-1,3,5,6,7,9) and the forensic 'Tape' window parameter + dual timestamps (substrate of forensic-1,2,4,6,9); also bloomberg-1, retail-8, hn-sceptic-6, journalist-6

**What.** Make the exchange announcements feed complete and routable before anything watches it: page the BSE lane by count in windows of six months or less instead of a hard 30-day page-1 request, keep SUBCATNAME and the submission / dissemination timestamps on Announcement (plus the types/data.ts mirror), retry AttachLive 404s against AttachHis, and state the window covered in the response.

**Why #2.** Every watcher, tripwire, transcript, results-day and forensic idea reads this feed, and today it returns an empty 200 for any BSE filer quiet for 30 days (JUMBO): watching a feed that silently drops history is worse than not watching, so this ships before the watcher.

**Size.** S (2-4 days), estimated 3 days. Service + model change and fixtures; no UI.

**Lifecycle cost.** BSE JSON shape and SUBCATNAME vocabulary drift (the module docstring dates its observation, corporate_disclosures.py:15-23); the window ceiling (a 12.7-month strPrevDate returned empty in the sellside probe) must be re-probed each release; one fixture per payload shape.

**Design system:** n/a. No UI.  
**Plugin contract:** untouched. Announcement lives in sidecar/models + types/data.ts, not types/plugin.ts.  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** DAT-P7-1 (high), DAT-P9-5 (medium), COD-disclosures-witnesses-10 (medium)

**Biggest risk.** Wider windows multiply requests per symbol; page by count under the existing breaker pacing, and never let a partial page read as complete.

**Judge notes.**
- Not filed as its own finding: filings older than a few weeks 404 on AttachLive and serve on AttachHis (sellside live probe), while corporate_disclosures.py:84 always builds AttachLive. The register only mentions it in passing (DAT-P13-24 notes the P13 battery trap 'bse_attachment_path_attachhis_not_attachlive'); INT-deferred-84-1 is about intermittent serving, not migration. Worth a raw finding of its own.
- DAT-P7-1 and DAT-P9-5 were admitted with the corrected mechanism: the hard 30-day window (_BSE_ANN_WINDOW_DAYS = 30, corporate_disclosures.py:88), not an NSE-first assumption.

#### 3. BL-03 · Reasons about you: your position and your notes in every answer

Tier 1 · **S-M, 4 days** · Sources: OPP-7 (primary); also: read_note capability as specified in forensic-6 (new_parts) and the WLD-harness-context-3 fix shape

**What.** When the user asks about a symbol they hold, the agent and the research brief see the position (quantity, average cost, weight in the book) and the user's own note on that symbol through a read-only, internal-only read_note capability: the local-first answer to 'it retrieves, it does not reason about you'.

**Why #3.** The cheapest broad upgrade in the set (every answer about a held name improves), it closes two admitted high findings, and it unblocks five seats' thesis and rulebook ideas that all hit the same wall: the agent can write your notes but never read them.

**Size.** S-M (4-5 days), estimated 4 days. read_note read_handler (internal-only, not MCP-projected), a per-symbol preamble line, a 'your position' line in the brief.

**Lifecycle cost.** Notes enter the prompt, so a size cap, secret-strip and an untrusted-text fence (scrub.wrap_untrusted, already used inside research) are day-one requirements; the preamble line needs a token budget as notes grow.

**Design system:** on. A 'your position' line inside the existing brief metric blocks.  
**Plugin contract:** untouched. Adds a read_handler capability; mark it internal-only so private notes do not project to the external MCP surface.  
**Tracked-portfolio write:** reads only. Reads the frontend portfolio snapshot that already rides the request (get_portfolio, agent_runtime.py:1182-1187); writes nothing.

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** WLD-agent-native-ux-1 (high), WLD-harness-context-3 (high)

**Biggest risk.** Notes can carry pasted web or Telegram text; unfenced they become an injection path into a loop that can auto-apply portfolio edits (WLD-harness-context-4). Fence notes as user data, never instructions.

**Judge notes.**
- OPP-7 verified: the preamble carries only 'Portfolio: N positions, total value' (agent_runtime.py:413-423); no research pipeline reads the position. Remaining work is as the ledger says, plus the notes read that five seats need.

#### 4. BL-04 · The Watch: wake sweep and a 'while you were away' card that states its blind spots

Tier 1 · **M, 8 days** · Sources: bloomberg-1 (primary); retail-8, hn-sceptic-6, journalist-6, OPP-1 (trigger half) (absorbed)

**What.** A per-symbol cursor sweep of announcements, results intimations and shareholding filings for holdings and watchlist on launch, wake and focus (no cron: the laptop sleeps), classified deterministically with a visible 'unclassified' bucket, ranked by category x position weight, surfaced as a card before the composer plus one preamble line, with a per-symbol coverage proof and a blind-spots line; OS notification only for material classes.

**Why #4.** This is the step from 'answers' to 'watches', which is both the benchmark's named gap and an admitted high table-stakes finding, and about fifteen ranked items are evaluations over the same tape; it ranks below BL-01 to BL-03 only because those are cheaper and it needs BL-02 first.

**Size.** M (5-8 days), estimated 8 days. Store with row cap and age vacuum (2 d); sweep route, renderer scope push and lifespan loop (2 d); classifier table and fixtures (1.5 d); coverage proof and blind spots (1 d); card and preamble line (1 d); a production intent source for the notification bridge (0.5 d).

**Lifecycle cost.** The highest of the spine items. NSE's cookie-dance lane and BSE's JSON change without notice; the classifier table rots and needs a fixture per new SUBCATNAME; per-launch fan-out from the user's IP must be capped (1 req/s/host, per-day cache). A dead lane must read 'blind since <ts> on NSE', never silence. The store needs a row cap and vacuum on day one (L5: nothing in data_cache.db has ever been deleted).

**Design system:** on. A card in the chat empty-state slot plus an optional Tape panel registered as a PanelSpec; existing tokens.  
**Plugin contract:** untouched. Adds a tape_since read_handler.  
**Tracked-portfolio write:** no write. v1 writes nothing. journalist-6's 'the bonus changed your cost basis, here is the proposed edit' waits for BL-14 and, when built, stages as a data-write that must be excluded from AUTO (COD-host-actions-proposed-changes-3) and bound to its portfolio and holding at enqueue (COD-host-actions-proposed-changes-1).

**Depends on:** BL-02  
**Prerequisite defect fixes:** none  
**Closes census findings:** WLD-T-1 (high), COD-frontend-stores-2 (high), COD-workflow-engine-5 (medium)

**Biggest risk.** Silence that reads as 'nothing happened', and alert fatigue from boilerplate small-cap filings: count routine items, list material ones, notify only material classes.

**Judge notes.**
- Scope must be pushed from the renderer. Holdings of record live in the frontend workspace blob (src/store/portfolios.ts:14-15); the sidecar portfolio_db that the forensic Tape, hn-sceptic-6 and journalist-6 call 'sidecar-side already' is a write-only ledger fed only by agent writes (COD-host-actions-proposed-changes-9, admitted).
- OPP-1's 'OS-notification sink already wired end to end' does not hold: the bridge reads useWorkflowStore, which no production code writes (COD-frontend-stores-2 and COD-workflow-engine-5, both admitted; grep 2026-09-23 finds no production writer). The OS send works; the feed is dead. The opp-ledger verify pass matched line text and marked OPP-1 held.

#### 5. BL-05 · Number firewall with a rupee scale witness

Tier 1 · **M, 8 days** · Sources: hn-sceptic-1, OPP-2 (primary)

**What.** Every numeric token in chat and brief prose is marked sourced (matches a tool-result leaf within tolerance), derived (one recognised operation over sourced leaves, CAGR included, formula on hover) or orphan (struck in chat, redacted in brief metric prose, labelled 'from model memory' when the turn had no tool calls). The grammar reads rupees (Rs / ₹, crore / lakh / lakh-crore, Cr / L, Indian grouping 1,05,130), and for any figure bound to a PDF page the page's declared unit header ('₹ in lakhs') is the scale witness. Zero tokens.

**Why #5.** It turns the benchmark's most-cited failure (a 1000x scale misread) into a stated guarantee at digit granularity, runs free on every answer, and is the grammar Red Pen and the results-day note both need; it sits at 5 only because the prose half is M-sized.

**Size.** M (5-8 days), estimated 8 days. Rupee grammar + parity vectors (1.5 d), derivation search (1.5 d), number_receipts on the stream + renderers (2 d), unit-header parser + scale witness (3 d).

**Lifecycle cost.** Tolerance tuning in the first month and new number formats; a parity vector file (as screener_formula keeps for its TS twin); a fixture list of unit-header phrasings. No network, no model.

**Design system:** on, extends it. Adds a hover underline / strike state to chat markdown and BriefBody prose; needs an R9 conformance review.  
**Plugin contract:** untouched. number_receipts rides the final stream event.  
**Tracked-portfolio write:** no write

**Depends on:** BL-06 (for the page-bound scale witness only; the prose firewall ships without it)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** False orphans on legitimate multi-step arithmetic train users to ignore the strike; recognise CAGR and common derivations and label no-tool turns 'from model memory'.

**Judge notes.**
- OPP-2's 'scale tokens are already recognised in extraction (extract.py:75,86-87)' cites _PDF_FINANCE_KEYWORDS, a page-selection keyword list, not a unit parser; no deterministic document-figure extraction exists, so the 'third witness on a shipped contract' needs a unit-header parser plus a figure-to-page binding (BL-06). The ledger's size S is about 3 of this item's 8 days.
- hn-sceptic-1 verified: company_narrative._NUMBER_RE reads $ and K/M/B/T only (company_narrative.py:64-77) and _verify_text's only route caller is routers/fundamentals.py:168.

#### 6. BL-06 · Page receipts

Tier 1 · **S-M, 5 days** · Sources: journalist-7 (page-anchor half) (primary); forensic-7 (page-provenance gap), hn-sceptic-2 (page identity through extraction) (absorbed)

**What.** Keep page identity through extract_pdf_text (it computes pages_used at extract.py:506, then flattens paragraphs), have citecheck return the page it matched, add optional page and quote to BriefSource (mirrored in sidecar/models in the same commit), and open citations at #page=N, so every figure in a brief hovers to its page and quoted line.

**Why #6.** Page-grain receipts are the floor's coding-agent idiom and the substrate every verbatim-on-page check needs (guidance ledger, AR reader, locker, scale witness); modest cost, broad leverage.

**Size.** S-M (4-5 days), estimated 5 days. Extraction change, citecheck page return, contract fields, page chip.

**Lifecycle cost.** Attachment URLs move (BL-02 retries AttachHis); page markers cost evidence tokens, keep them terse; always cite the PDF index the link opens, never the printed folio.

**Design system:** on. A page chip on the existing citation markers.  
**Plugin contract:** untouched. types/brief.ts is not Tier-1.  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Scanned PDFs have no text layer and no OCR exists in the sidecar; the receipt must say 'scanned: figure from the aggregator, not this page' rather than fake an anchor.

#### 7. BL-07 · Coverage honesty: say what the app could not see

Tier 1 · **S-M, 4 days** · Sources: journalist-2, designer-6 (primary)

**What.** A deterministic, zero-token 'What I could not see' block at the end of a brief (pages read of N, scanned pages, failed lanes, citations removed, depth downgraded) plus a 4-px coverage strip under the overview header (Price / Statements / Shareholding / Filings / Corporate actions / Estimates) fed by per-leg status, FieldMeta counts and GET /system/provider-health, which no frontend reads today.

**Why #7.** The honest limitation paragraph, written by the app itself, is the cheapest antidote to 'sources create false certainty'; it works keyless and makes the full segments trustworthy because the empty ones are labelled.

**Size.** S-M (4-5 days), estimated 4 days. coverage object per run + brief block (2 d); strip component + coverage(symbol) selector (2 d).

**Lifecycle cost.** Near zero: it reports counters the pipeline already keeps. Each new lane or source must declare its segment and failure signal or it does not appear.

**Design system:** on, extends it. A short brief block (on) plus one new quiet strip component on existing tokens (conformance review).  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Boilerplate: print only non-trivial gaps, one to four lines, with numbers; keep the strip quiet so it does not read as a 'your data is bad' banner.

**Judge notes.**
- designer-6's demo trips the breaker with POST /system/provider-health/trip, a rig mutation route the census says should not ship in production (COD-market-data-providers-2-11, admitted low). The strip must read the GET only.

#### 8. BL-08 · Start recording: point-in-time EOD and fundamentals observations

Tier 1 · **S-M, 4 days** · Sources: quant-1 (recorder half) (primary)

**What.** Stop overwriting. Append every daily NSE and BSE bhavcopy row the app already parses and then forgets after a 7-day cache, keyed (trade_date, symbol, series); record changed non-price fundamentals fields with observed_at and provider; heal sleep gaps by walking missing trade dates on wake; write a visible gap marker when a day fails to parse. No surface yet.

**Why #8.** The only item whose value is denominated in elapsed time: every day it is not running is as-observed history no later build can recover, so the recorder ranks far above the surfaces that read it (drift, exit door, radar, incubator, as-of screens).

**Size.** S-M (4-5 days), estimated 4 days. eod_bars append in bhavcopy_refresh_once, fund_obs change-data-capture on _upsert, gap backfill, Settings size row + compaction switch; move the BSE raw archive under --data-dir (bse_provider.py:155-163).

**Lifecycle cost.** About 2,700 rows a day, roughly 40 MB a year before compression (quant estimate): a size row and a 'compact older than N years' switch on day one (L5). A bhavcopy format change (July 2024 precedent) must write a gap marker, never a silent empty day. Fundamentals are point-in-time only from install day and must be labelled 'observed since <date>'.

**Design system:** n/a. A Settings size row only.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Being read as history it is not; every consumer must carry 'observed since'.

### Tier 2: The Jarvis layer: watching, memory and receipts on the spine

#### 9. BL-09 · Tripwires: kill criteria compiled once, watched for free

Tier 2 · **M, 6 days** · Sources: forensic-6 (primary); hn-sceptic-5, bloomberg-9, quant-9, OPP-1 (thesis-watcher half) (absorbed)

**What.** The user writes exit conditions in prose in the symbol note; one LLM call selects and parameterises rules from a closed menu, each carrying its source sentence, as a proposed change; accepted tripwires are evaluated deterministically at every sweep over the tape, shareholding and results data at zero tokens, and a firing quotes the user's own sentence beside the filing page. Sentences outside the menu stay visible as reminders, never 'armed'.

**Why #9.** Five seats converged on it independently; it is the floor's thesis-versus-filings item with the model removed from the part that must never be wrong, which on a BYOK laptop that sleeps is the only honest way to watch.

**Size.** M (5-8 days), estimated 6 days. Event fields in the screener_formula FIELD set (+ TS twin), compile prompt, tripwire store, evaluator at sweep, armed/reminder UI, synonym table as data.

**Lifecycle cost.** The field vocabulary becomes a contract: stored tripwires carry a vocabulary version and fail loudly on rename; the per-event-class synonym table ('cessation' vs 'resignation') is data to tune; a dead lane must show 'blind since'.

**Design system:** on, extends it. A 'my rules' section on the symbol note with an unmistakable armed vs reminder state (new state; conformance review).  
**Plugin contract:** untouched. Extends the formula field vocabulary, not the plugin contract.  
**Tracked-portfolio write:** no write. Tripwire rows live in their own store, created through the proposed-changes gate.

**Depends on:** BL-03, BL-04, BL-13 (for pledge and holder criteria)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** False comfort: a user believes an uncheckable sentence is armed; armed vs reminder must be unmistakable.

#### 10. BL-10 · Red Pen: paste anyone's numbers, get a marked-up verdict

Tier 2 · **M, 6 days** · Sources: journalist-1 (primary); bloomberg-6, hn-sceptic-3 (absorbed)

**What.** Paste a Telegram tip, a broker note or another AI's answer: numeric tokens are extracted with the BL-05 grammar, one tool-less LLM call binds each to {symbol, metric enum, period} under a code-enforced verbatim-substring rule, and each claim runs against fundamentals, field_meta and the matching witness to return OK / CONTRADICTED (both sources named) / DIFFERENT BASIS / STALE / CANNOT CHECK. Exposed as a check_claims read_handler that auto-projects to MCP, so Claude Desktop or Cursor can use Vysted as a fact-checker.

**Why #10.** The one demo that needs no elapsed time or history (a rival's paragraph corrected with the exchange page one click away), and it turns the witness layer outward; it waits on the BL-05 grammar, which is why it is not higher.

**Size.** M (5-8 days), estimated 6 days. Labelled source map, binding call + verbatim gate, verdict engine over witnesses, composer paste/file intake (none exists), marked-up block.

**Lifecycle cost.** The metric enum and witness set grow together, and every new witness is a new verdict for free; the hostile battery becomes its regression suite and is refreshed each release.

**Design system:** on. A marked-up-text block in BriefBody.  
**Plugin contract:** untouched. check_claims read_handler projects to MCP by the catalog rule.  
**Tracked-portfolio write:** no write. Optionally files the verdict under the symbol note via write_note (a data-write through the gate), which needs COD-host-actions-proposed-changes-2 (a mode-less write_note replaces the note) fixed first.

**Depends on:** BL-05  
**Prerequisite defect fixes:** WLD-harness-context-4 (high)  
**Closes census findings:** none

**Biggest risk.** A confident CONTRADICTED on a basis mismatch (consolidated vs standalone, TTM vs FY) is worse than silence: CONTRADICTED only on same basis and period, otherwise BASIS or CANNOT CHECK. Pasted text is untrusted input; the binding call carries no host-action tools.

#### 11. BL-11 · Proof Open: the first minute is a demonstration

Tier 2 · **S, 2 days** · Sources: designer-2 (primary)

**What.** A keyless first-run step before the key form: name a company, and in about 8 s a 'What we checked' card shows each witness as agrees / disagrees, here are both / couldn't check, why, using the sidecar's own reason strings; key setup moves after it.

**Why #11.** Two days turn the accuracy claim into something a sceptic verifies in the first minute with no key, which is the positioning made visible; it is only as good as BL-01 underneath.

**Size.** S (2-4 days), estimated 2 days. One onboarding step in the existing state machine + one card (reused as the BL-07 strip's expanded view).

**Lifecycle cost.** Low; shares BL-01's route. The demo decays if an exchange lane breaks, so add the witnessed route to the sidecar smoke test.

**Design system:** on. One onboarding step and one card on existing tokens.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-01  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** An all-agree large cap makes the moment look empty; render '6 of 6 sources agree, here is what was compared' and suggest a BSE-only example.

#### 12. BL-12 · Turn receipt

Tier 2 · **S, 2 days** · Sources: designer-9 (primary)

**What.** One tertiary monospace line under every agent turn (tools, sources by origin, checks ok / disagree, tokens, $ as a lower bound while research calls are unmetered, wall time, context n/10) with the context segment warning before the 10-message window silently drops history.

**Why #12.** Two days to show BYOK users the two things chat products hide most, cost and forgetting, and it turns an admitted defect (the silent history cut) into a stated limit.

**Size.** S (2-4 days), estimated 2 days. TurnReceipt component, pure receiptFor(message), context segment; excludes the metering fix.

**Lifecycle cost.** Near zero once metering is right; the risk is line creep, so hard-cap it at one line.

**Design system:** on. One tertiary mono line on existing tokens.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** COD-research-extraction-synthesis-2 (high; for an exact $; until then the segment reads 'at least')  
**Closes census findings:** none

**Biggest risk.** A precise-looking wrong dollar figure; always a lower bound until research calls are metered.

**Judge notes.**
- Surfaces WLD-harness-context-2 (admitted: a silent 10-message window) as a visible limit; it does not fix it.

#### 13. BL-13 · Cap-table X-ray: names, beneficial owners, encumbrance, holder counts, pledge trend

Tier 2 · **M, 7 days** · Sources: forensic-3 (primary); retail-6 (absorbed)

**What.** Parse named holders, significant beneficial owners, the three-way encumbrance / warrant / lock-in flags and per-category shareholder counts out of the SEBI shareholding XBRL the app already downloads each quarter (it reads one concept of 83 today), diff them quarter on quarter with each cell linked to its XBRL, flag the conjunction 'retail holders multiplying while promoters and large holders shrink', derive the 4-quarter pledge trend once the numeric concept is confirmed on a pledged filer, and remember holder names only across names the user touched.

**Why #13.** Promoter, pledge and holder data is the most gameable number in an Indian small-cap and the axis a 16-broker clone does not cover; the data is already on disk, so this is India-disclosure depth for the price of a parser extension, and it feeds tripwires and rule packs.

**Size.** M (5-8 days), estimated 7 days. Parser extension + one cache schema bump, additive ShareholdingPattern fields + types mirror, name normaliser, diff block, ownership card, one probe of a pledged filer.

**Lifecycle cost.** SEBI revises the SHP taxonomy every couple of years (the parser already absorbed one silent schema change, bse_provider.py:703-716): pin fixtures per taxonomy version and degrade unknown concepts to 'not parsed'. BSE-only lane; NSE-only names keep today's summary and must say so.

**Design system:** on. A diff table block in BriefBody and a card on the ownership section.  
**Plugin contract:** untouched. Additive model fields; types mirror in the same commit.  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** WLD-T-8 (high; once the pledge concept is confirmed), WLD-T-10 (medium; / COD-disclosures-witnesses-6 (fix the tool description that denies FII/DII in the same commit))

**Biggest risk.** False identity between same-name entities (PAN is not disclosed): never assert sameness, say 'same name string', show both filings.

#### 14. BL-14 · Corporate-action chain

Tier 2 · **S-M, 5 days** · Sources: quant-6 (primary)

**What.** Parse the bonus / split / rights subjects the NSE corporate-actions feed already returns (dividend_actions.py keeps only dividends) plus a new BSE CorporateAction lane for BSE-only scrips into a per-symbol factor chain, corroborate each factor against the bhavcopy ex-date discontinuity (single-witness factors shown amber, never silently applied), and derive adjusted series locally with an as-traded / adjusted toggle and a receipt per factor.

**Why #14.** It closes an admitted high data gap (JONJUA's two 2026 bonuses are invisible) and it is what stops a bonus reading as a crash in the Tip Ledger, Exit Door, drift classification and the Watch's cost-basis note.

**Size.** S-M (4-5 days), estimated 5 days. Subject parser + fixture file + visible 'unparsed action' list, BSE lane, factor store, chart toggle and ex-date markers.

**Lifecycle cost.** Subject strings are free text ('Bonus 7:24', 'Face Value Split From Rs 10 To Rs 2'); rights and demergers will sometimes be unresolvable and must show as such. PrvsClsgPric ex-date semantics must be checked against three known 2026 actions before it is trusted as a witness.

**Design system:** on. Ex-date markers and a basis toggle on the chart; canvas colours stay single-sourced in chart-theme.ts.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write. v1 is read-only. A later 'your share count / cost basis per share changed' proposal (BL-04) would be a data-write through the gate and needs COD-host-actions-proposed-changes-1 and -3 first.

**Depends on:** BL-08 (for derived series; the parser and BSE lane stand alone)  
**Prerequisite defect fixes:** none  
**Closes census findings:** DAT-P14-4 (high)

**Biggest risk.** A wrongly applied factor rewrites price history; amber until two witnesses agree.

#### 15. BL-15 · Results-day first take (deterministic results-grid extraction)

Tier 2 · **M, 7 days** · Sources: sellside-1 (primary)

**What.** When a watched name files results, locate the SEBI comparative P&L grid in the PDF, map rows to line ids with a per-archetype dictionary (lender, holding company, manufacturer), refuse to extract without a unit header (the BL-05 scale witness), label standalone vs consolidated, and publish a variance table against the prior quarter and the same quarter last year with a page receipt per cell, plus three lines of number-gated prose. Comparison with the user's own estimate arrives with BL-26.

**Why #15.** Results day is a floor item and this is the deterministic extraction the guidance ledger, the Living Model, SUE and brief falsifiers all resolve against; the vendor alternative is unsafe for exactly these names (statements for SME ticker collisions serve a US company's numbers, DAT-P3-1 and siblings, admitted critical).

**Size.** M (5-8 days), estimated 7 days. Table locator, per-archetype row matcher, unit-header refusal, results_flash read_handler, variance block, fixture corpus seed.

**Lifecycle cost.** Filers change grid layouts; SME filers under Reg 33 print half-yearly; scanned PDFs exist. A growing fixture corpus, one per new layout; about a day a quarter of upkeep across a 30-name list.

**Design system:** on. Existing metric and table brief blocks plus a variance block type.  
**Plugin contract:** untouched. results_flash read_handler.  
**Tracked-portfolio write:** no write

**Depends on:** BL-02, BL-04, BL-05, BL-06  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** The row matcher maps 'Total income' onto 'Revenue from operations' on a lender or holding company; per-archetype maps and an amber 'matched by similarity' state.

#### 16. BL-16 · Guidance ledger: what management said against what printed

Tier 2 · **M-L, 10 days** · Sources: OPP-4 (primary); hn-sceptic-7, sellside-3 (horizon drift and the haircut number), bloomberg-4 (guidance-vs-delivery half) (absorbed)

**What.** For each earnings-call transcript and investor presentation already arriving in the BSE feed (SUBCATNAME 'Earnings Call Transcript'; one de-wrapped hop for cover-letter filers), an LLM proposes guidance rows {metric, range, unit, horizon phrase, speaker, page, verbatim} that code drops unless the verbatim is on the cited page. Accepted rows resolve deterministically against printed results as HIT / MISS / PUSHED (the horizon word moved later with the range unchanged) / DROPPED (stopped being said, hn-sceptic-7's FADED), with a per-management delivered-to-guided factor shown only at n of 4 or more and a coverage line ('2 of 8 quarters readable').

**Why #16.** The floor's 'nobody shows guidance against delivery across quarters' and the single most valuable research artifact in the set, but it stands on three substrates (BL-02, BL-06, BL-15), hence 16.

**Size.** M-L (9-12 days), estimated 10 days. Transcript routing + one-hop fetch, extractor + verbatim gate, closed horizon lexicon, resolver, FADED text search, ledger block, coverage statement.

**Lifecycle cost.** Medium. Transcript formats vary; website-hosted transcripts rot (cache them via BL-22); bounded LLM extraction cost per transcript (about 30 names x 4 calls a year); many small caps hold no calls or file scans, and coverage must be stated, never implied.

**Design system:** on. A ledger / timeline block with page chips.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write. Accepted rows go to their own store through the gate.

**Depends on:** BL-02, BL-06, BL-15  
**Prerequisite defect fixes:** none  
**Closes census findings:** WLD-T-6 (medium; in part: a transcript path, not a vendor)

**Biggest risk.** An extraction invents a range management never gave (verbatim gate plus user acceptance); hedged language makes KEPT / BROKEN a judgement call, so auto-resolve only rows with a number and a horizon.

**Judge notes.**
- OPP-4's 'blocked on having the transcript at all (WLD-T-6)' no longer holds: the sellside live probe found transcripts in the BSE feed the app already calls, and the WLD-T-6 refute downgraded the finding to medium because research already routes concall questions to that feed. The real blockers are the dropped subcategory and AttachLive rot (BL-02). Size M-L, not L.

#### 17. BL-17 · Tip Ledger

Tier 2 · **M, 8 days** · Sources: retail-1 (primary)

**What.** Drop a Telegram Desktop JSON export or paste one tip: calls are regex-parsed (LLM only for residue), resolved with the resolver's confidence bands and rename lane (below-band calls listed, never scored), scored against exchange history at day 3 / 30 / 60 with corporate-action adjustment, checked for a pre-message run-up, frozen with the price at that moment so a later delete cannot erase it, and optionally shadow-tracked in a named portfolio instead of bought; a per-source scorecard carries a printed survivorship caveat.

**Why #17.** The only idea that attacks the cause of the largest retail cohort's losses rather than the symptoms, and it only works local-first (a hosted product would be publishing named tipsters' records); it is not higher because a wrong resolve is the most damaging error this product can make and it needs BL-14.

**Size.** M (5-8 days), estimated 8 days. File/paste intake (dragDropEnabled:false stays), parser, tips store, history backfill, run-up fingerprint, checkpoint job on wake, panel, shadow path.

**Lifecycle cost.** Telegram's export format has been stable since 2018 (low); the real cost is corporate-action correctness forever (BL-14) and resolver drift on renamed or colliding tickers.

**Design system:** on. A Tip Ledger panel registered as a PanelSpec; existing table and card blocks.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** WRITES, through the proposed-changes gate. The optional shadow position uses portfolio_add_position into a separate named portfolio through the proposed-changes gate (data-write). Needs COD-host-actions-proposed-changes-3 (else AUTO applies it unreviewed), -1 (else the shadow lands in whichever portfolio is active at accept time) and WLD-harness-tools-3 (validate cost_basis; here the price at the tip is known, so pass it explicitly).

**Depends on:** BL-14  
**Prerequisite defect fixes:** COD-host-actions-proposed-changes-3 (high), COD-host-actions-proposed-changes-1 (high), WLD-harness-tools-3 (high)  
**Closes census findings:** none

**Biggest risk.** A wrong resolve produces a confident wrong verdict about a source the user trusts: band-gated scoring, unresolved listed, receipts on every row, user correction, arithmetic-only wording (never 'scam').

#### 18. BL-18 · Brief diff: ask again, see what changed

Tier 2 · **S, 3 days** · Sources: journalist-4 (primary)

**What.** Re-researching a name renders a 'changed since <date>' strip at the top of the brief (new filings, flipped filing-fact metrics, new conflicts) with market-moved values separated and everything unchanged collapsed to a count, via a pure diffBriefs(prior, next) helper on stable keys.

**Why #18.** Three days of pure frontend buys 'the unit of review is the change, not the transcript' for every returning user, and it is box one of Page One.

**Size.** S (2-4 days), estimated 3 days. Pure helper + unit vectors, strip block, per-symbol last-brief file (shared with BL-41).

**Lifecycle cost.** Low: a pure frontend function; it breaks only if it diffs display labels instead of stable keys. The brief store holds one brief per panel and carries the prior only into the in-flight run (src/store/brief.ts:45-53), so a per-symbol last-brief file keeps the prior across panel reuse and relaunch.

**Design system:** on. A strip block at the top of BriefBody.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-02 (for 'announcements since the prior')  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Price-derived metrics change daily; lead with filing facts or the strip becomes the wall of prose it replaces.

#### 19. BL-19 · Undo and ghost edits

Tier 2 · **M, 6 days** · Sources: designer-7 (primary)

**What.** Capture a pre-image for every applied agent change (AUTO included), push it onto a bounded undo stack, let Cmd-Z reverse the agent's last change to a panel (refused with a reason if the user has edited the target since), and render pending changes as ghost rows and insertions inside the watchlist and notes where they land.

**Why #19.** The tracked portfolio is the one money-relevant write surface left after the trading removal and an accepted or AUTO-applied delete is unrecoverable today; reversibility has to exist before any idea that writes the book at scale or grants autonomy (BL-39).

**Size.** M (5-8 days), estimated 6 days. Per-kind pre-image capture, undo store + keymap, stale-target refusal, ghost renderers for watchlist and notes first.

**Lifecycle cost.** Every new data-write host action must declare a pre-image or it cannot be proposed (a compile-time rule in describeHostAction's switch); ghost renderers are per panel (four today).

**Design system:** on, extends it. Adds a ghost / pending state (reduced opacity, dashed rule) to panel rows; R9 conformance review, not a reopen.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** writes (restorative undo, user-initiated). Undo re-applies a holding pre-image through the existing store seams, user-initiated, with a stale-target refusal; the pre-image must be bound to {portfolioId, holdingId} (COD-host-actions-proposed-changes-1).

**Depends on:** none  
**Prerequisite defect fixes:** COD-host-actions-proposed-changes-1 (high)  
**Closes census findings:** WLD-agent-native-ux-2 (medium)

**Biggest risk.** Undo that clobbers a later user edit; refuse when the target changed since apply.

#### 20. BL-20 · Trust bench and 'Audit me'

Tier 2 · **M, 6 days** · Sources: journalist-8 (primary); hn-sceptic-4 (trust-bench half), OPP-3 (deliverable c: the public benchmark page) (absorbed)

**What.** Freeze a structural subset of the R15 hostile battery (identity, exchange, board, face value, scale, 'has no NSE line', each with as_of) into a bundled fixture; a keyless command-palette 'Trust audit' runs the existing handlers and witnesses against it and prints resolved correctly / conflicts disclosed / wrong and silent with the failures in full, and pnpm trust-bench writes the same report to a committed TRUST.md each release: the public benchmark page, failures left in.

**Why #20.** Every rival's accuracy claim is a sentence and this is a button a keyless reviewer presses in minute five, doubling as the regression suite for BL-05 and BL-10; it is marketing-shaped, so it follows the items that make the numbers better.

**Size.** M (5-8 days), estimated 6 days. Fixture freeze, runner over handlers, report-card block, script + TRUST.md writer.

**Lifecycle cost.** Real: truth packs rot (renames, delistings, new collisions). Packs carry as_of, the report greys out anything older than two quarters, and a refresh is one agent-day per release on the release checklist.

**Design system:** on. A report-card block.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** It looks like a stunt if the failures never shrink, and it hands rivals copy; it only works if the README numbers are the numbers the button prints.

### Tier 3: Differentiators on the spine

#### 21. BL-21 · The Figure and the Why key

Tier 3 · **M, 6 days** · Sources: designer-4 (primary); OPP-3 (deliverable b: per-figure attribution on metric cards) (absorbed)

**What.** A design-system <Fig> primitive replaces native title= tooltips with a focusable figure; ? opens an in-cell lineage card (inputs, provider, as-of, basis, witness verdicts, filing link, copy as citation) with no LLM, and a second ? optionally adds one model line. Adopted on overview fundamentals, then brief metric cards (OPP-3 b), then watchlist rows.

**Why #21.** It is the single surface every other seat's receipt should render into (firewall verdicts, page anchors, revision flags), and it ranks after the items that produce those receipts.

**Size.** M (5-8 days), estimated 6 days. Primitive + lineage card + overview adoption (5 d); each further panel about half a day.

**Lifecycle cost.** Every new metric must declare its lineage or its card says 'lineage not recorded'; a vitest lists Figs without lineage.

**Design system:** on, extends it. Extends the design system with one primitive and one card on existing tokens (R9 conformance review).  
**Plugin contract:** untouched. An additive derivation field on FieldMeta (documented as additive, fundamentals.py:36-37).  
**Tracked-portfolio write:** no write

**Depends on:** BL-01  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** ? collides with typing; bind it only while a Fig has focus.

#### 22. BL-22 · Evidence locker

Tier 3 · **M, 6 days** · Sources: forensic-7 (locker half) (primary); hn-sceptic-2 (persistence and revised-filing detection) (absorbed)

**What.** Persist the page text (bytes optional) of every filing the agent reads under its sha256 with fetch time and page map, pin anything cited by a saved brief, claim, tripwire or promise, open citations from disk offline, and raise 'the document changed under you' with a page-text diff when a re-fetch hashes differently.

**Why #22.** Receipts that survive the source (AttachLive URLs already rot within weeks, per the sellside probe) and the one thing a hosted product structurally will not do, keep the user's evidence offline; it underpins the guidance ledger, the redline and forkable research.

**Size.** M (5-8 days), estimated 6 days. Locker store with LRU cap and pinning, optional sha256 / fetchedAt on BriefSource, hash compare on re-visit, chip states.

**Lifecycle cost.** Disk: a few GB a year for a heavy user if bytes are kept, about 100 KB per 60-page filing as compressed text. The LRU cap and pinning are budgeted on day one (L5). Hash bytes, not text, because pypdf text drifts across versions.

**Design system:** on. The citation chip gains 'stored' and 'changed' states.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-06  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Scanned filings are stored faithfully and remain unreadable; the chip must say 'stored, not machine-readable'.

#### 23. BL-23 · Gatekeeper exits

Tier 3 · **S, 3 days** · Sources: forensic-1 (primary)

**What.** A tape class for auditor, CFO, company-secretary and independent-director exits (SUBCATNAME plus headline, no LLM); notify only on a mid-term auditor exit or two or more gatekeeper exits in 180 days; on open, the agent reads the 1-3 page resignation letter and quotes the stated reason with its page.

**Why #23.** The cheapest high-signal forensic event class once the tape exists, and a cluster inside a 180-day window across 30 names is exactly what no human holds in their head.

**Size.** S (2-4 days), estimated 3 days. Classifier classes + cluster rules + timeline card, on the Watch.

**Lifecycle cost.** SUBCATNAME vocabulary drifts: a visible unclassified bucket and a fixture-pinned classifier test. NSE's 'Updates' category is coarser, so NSE-only SME names get a weaker tape and must say so.

**Design system:** on. A timeline card.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-02, BL-04  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Alert fatigue from routine board churn; only the cluster and mid-term rules notify.

#### 24. BL-24 · Exit Door: can I actually get out

Tier 3 · **S-M, 4 days** · Sources: retail-3 (primary); bloomberg-2 (absorbed)

**What.** A per-holding liquidity glyph: days to exit at a stated participation rate from delivery volume (total volume, labelled, when delivery is unavailable), zero-volume session count, SME lot arithmetic, the longest lower-band lock streak, and a tape event the day a holding moves from EQ to BE / BZ (trade-for-trade), plus a read_handler so the agent can answer 'can I get out of X?'.

**Why #24.** The single number that would have stopped most tip-driven small-cap losses, computed from data the app already parses, and small once the recorder runs.

**Size.** S-M (4-5 days), estimated 4 days. Delivery parse from the security-wise bhavcopy fallback (BhavRow has no delivery field), calc, glyph column + hover card, read_handler.

**Lifecycle cost.** Near zero beyond the EOD ingest. Delivery columns exist only on the fallback host; if it blocks, degrade to total volume and say so. SME lot size has no bundled source (unverified) and must degrade to 'lot size unknown'. BSE-only names use the BSE bhavcopy lane.

**Design system:** on. A glyph column and hover card in the portfolio panel.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** reads only. Reads the manual tracked portfolio.

**Depends on:** BL-08, BL-04 (for the series-flip event)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** It reads as a sell signal; it is a property of the market for the stock, not a view on the company.

**Judge notes.**
- retail-3's Kite holdings read (sidecar/routers/brokers.py GET holdings, models/broker_reads.py) is on the 23 Sep trading-removal surface and is struck; the manual portfolio is sufficient.

#### 25. BL-25 · Filing clock

Tier 3 · **S, 3 days** · Sources: forensic-2 (primary)

**What.** Days from quarter end to results across quarters, filings after 21:00 or on a Friday night, rescheduled board meetings, corrigenda and late shareholding submissions, rendered as a BriefDerivedValue-shaped series (formula and basis) with every timestamp linked; colour only a monotonic drift of three or more quarters; no LLM.

**Why #25.** It measures the filer's behaviour, which no aggregator field contains, at near-zero upkeep; it sits below gatekeeper exits because the signal is slower and needs quarters of history.

**Size.** S (2-4 days), estimated 3 days. A ~150-line derivation module, one header chip + hover, a statutory-deadline constants block.

**Lifecycle cost.** Near zero: timestamps are the most stable payload fields; statutory deadlines live in one constants block with a source comment.

**Design system:** on. A header chip in the existing metric-card grid.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-02 (dual timestamps and history beyond 30 days)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Over-reading noise: show the series, never a score.

**Judge notes.**
- History depth: BSE windows must be paged at six months or less (sellside probe); whether windows older than about a year return at all is unprobed, so the clock may only see what the recorder accumulates.

#### 26. BL-26 · Living model

Tier 3 · **M, 8 days** · Sources: sellside-2 (primary); sellside-3 (apply-haircut to the model) (absorbed)

**What.** A small per-company driver model (30 lines or fewer, per-archetype template) in a local Model Store: actuals auto-filled from results filings with page receipts (BL-15), estimate changes on an append-only revision trail (reason and triggering filing), agent edits only as proposed diffs, a model_read capability so every brief compares against the user's number, and .xlsx export with live formulas through the Rust atomic-write path (not the dead <a download> path of WLD-T-2).

**Why #26.** It answers screener.in's real switching cost (the fillable Excel model) with the one file a cloud product has to ask permission for, the analyst's own model, kept local; its audience is the pro seat and it stands on BL-15.

**Size.** M (5-8 days), estimated 8 days. Model Store (lines / cells / revisions), cell references in the formula grammar, grid panel, model_read, model-edit host action, xlsx writer.

**Lifecycle cost.** Templates drift as businesses change shape (lines must be addable without breaking history); schema migrations from day one (the repo has CREATE TABLE IF NOT EXISTS only); an xlsx writer is a new sidecar dependency against the 120 MB footprint target.

**Design system:** on. A new dockview grid panel, held deliberately small under R9 density rules.  
**Plugin contract:** untouched. model_read reaches custom agents through the allow-list derivation.  
**Tracked-portfolio write:** no write. Writes the Model Store (user research data) through the gate, not the tracked portfolio.

**Depends on:** BL-15  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** A worse Excel nobody opens: do not compete on grid features; compete on filings filling actuals, reasons on revisions and the agent reading the model.

#### 27. BL-27 · Rulebook: it holds you to your own words

Tier 3 · **M, 6 days** · Sources: journalist-5 (primary); bloomberg-5 (absorbed)

**What.** A 'Rules' note bucket that rides the snapshot (capped) holds the user's policy in plain English; quantitative rules compile once (shown verbatim, user-accepted) to the no-eval formula grammar with book-level fields (position weight, sector weight, days to exit, promoter %), and every proposed portfolio add or watchlist add, including the agent's own suggestions, arrives with an objection quoting the rule, its date and the figure. It annotates; it never blocks.

**Why #27.** Discipline aimed at the user rather than the market, reusing the grammar, gate and notes the product already has; it needs BL-03 and the AUTO fix, and serves the disciplined minority.

**Size.** M (5-8 days), estimated 6 days. Rules bucket + snapshot + preamble, compile step with diff, book-level field resolver, objection on proposed-change cards.

**Lifecycle cost.** Rules referencing fields the model lacks must fail loudly at compile time; the formula TS twin stays in lockstep (an existing cost); a rule overridden twice asks once whether to retire it.

**Design system:** on. An objection line on proposed-change cards.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write. It annotates portfolio proposals at the gate, which only works if data-writes actually stop there, i.e. after COD-host-actions-proposed-changes-3 (AUTO auto-applies data-writes today, so the objection would arrive after the fact).

**Depends on:** BL-03, BL-24 (days-to-exit field)  
**Prerequisite defect fixes:** COD-host-actions-proposed-changes-3 (high)  
**Closes census findings:** none

**Biggest risk.** Nagging and mis-compiled rules: one objection per action, never on reads, compiled rules shown verbatim.

#### 28. BL-28 · Red-flag rule packs

Tier 3 · **M, 7 days** · Sources: forensic-9 (primary)

**What.** Detection-as-code for Indian small-cap governance: small readable rule files describing event sequences over the tape (for example rating downgrade, then CFO exit, then results delayed), each citing the regulator order it was distilled from, evaluated privately against the user's holdings and returning 'steps matched' with a filing per step, never a verdict. A first-party pack of about 12 rules reviewed line by line by the operator, and a CI lint (schema, citation present, a fixture that fires).

**Why #28.** The strongest long-run moat in the forensic set (a hosted platform cannot publish 'matches a fraud pattern' about a listed company, a local evaluator publishes nothing), but it is only as good as the tape and event classes under it and carries the highest reputational risk of any rule-based item.

**Size.** M (5-8 days), estimated 7 days. Rule schema + validator, windowed sequence matcher, pack loader, matched-rules block, CI lint (engine S-M); the starter pack is careful writing.

**Lifecycle cost.** The corpus is the asset and the liability: review, versioning, deprecation. Event-class vocabulary changes must be additive or packs break.

**Design system:** on. A 'matched rules' block with per-step receipts.  
**Plugin contract:** uses the contract as-is. Third-party packs ship through contributesData as a DataSource of kind 'custom'; a dedicated 'rules' kind would change types/plugin.ts (Tier-4). Do not add it.  
**Tracked-portfolio write:** reads only. Evaluates against holdings; writes nothing.

**Depends on:** BL-04, BL-13, BL-23  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** A rule reads as an accusation: observable sequences only, primary citations, steps matched, never a verdict; the operator reviews the first pack.

**Judge notes.**
- The seat's moat argument 'AGPL + the plugin contract' is stale: on 23 Sep the core was relicensed to PolyForm Strict 1.0.0 (commit 0c63d46) and CONTRIBUTING.md closed contributions. types/plugin.ts is now Apache-2.0, so third-party packs can still ship as plugins, but a community corpus lives outside the repo.

#### 29. BL-29 · Track record: the app keeps score on itself and its providers

Tier 3 · **M, 6 days** · Sources: journalist-3 (primary); hn-sceptic-4 (in-app conflict-ledger half) (absorbed)

**What.** Persist every figure the agent states (period, as-of, provider, source) and every witness conflict by provider and segment in a local ledger; re-check deterministically when a new brief for the same symbol publishes (same metric and period with a different value is a graded miss, a different period is a change); the agent answers 'how far should I trust your market cap on SME names' from its own measured history. A read-only track_record capability and a Settings page.

**Why #29.** 'I have been wrong about this before' is the least chatbot-like sentence an assistant can say, and it upgrades the capped, source-less claims ledger into memory with provenance; mid-ranked because the value accrues over months.

**Size.** M (5-8 days), estimated 6 days. claims + conflict ledger store with schema version, re-check on publish, capability, Settings table, preamble line.

**Lifecycle cost.** Grows forever unless capped per symbol and aged out; needs a schema version from day one (there is no migration story in the repo).

**Design system:** on. A Settings table and one preamble line.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-15 (primary filings to grade against; optional)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Grading unfairly in either direction: only same-period, same-basis contradictions from a primary filing count as a miss, and the page shows the denominator.

#### 30. BL-30 · The number changed: drift ledger

Tier 3 · **S-M, 4 days** · Sources: quant-2 (primary); bloomberg-3 (absorbed)

**What.** From the fund_obs recorder (BL-08), classify every change to a filing-anchored field as explained by a filing, explained by a corporate action, a basis flip, or an unexplained vendor revision (with a statement period-hash to catch restated past periods), show which saved screens and published brief claims flip because of it, and put an 'as you saw it on <date>' chip on the brief.

**Why #30.** The most common root of 'the numbers look wrong' made visible, nearly free once the recorder runs, but it needs weeks of observations before it can say anything.

**Size.** S-M (4-5 days), estimated 4 days. Classifier, impact join over saved screens and claims, drift card, fixture suite of benign drifts.

**Lifecycle cost.** Noise is the killer: per-field tolerance bands (rounding, FX, TTM roll) tuned in the first month, then a fixture suite of known-benign drifts; unexplained-only by default; two consecutive confirming observations before it speaks.

**Design system:** on. A drift card and a chip on the brief.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-08, BL-14, BL-02  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** False alarms on TTM rolls get it muted.

#### 31. BL-31 · Seven Pages: annual-report reader

Tier 3 · **M, 7 days** · Sources: retail-7 (primary); forensic-7 (section-seek deep-read half) (absorbed)

**What.** A section-seek reader that finds the auditor's report, key audit matters, CARO, related-party, contingent-liability, managerial-remuneration and cash-flow sections anywhere in a 250-page annual report (the lane reads 60 pages and keeps 6 today, extract.py:65,68, so the back of an AR is unreachable), reads a few pages around each heading, pins every finding to a PDF page with the quote verified on that page, and explains a new term once per user, as a durable budget-guarded run.

**Why #31.** It reaches the pages a forensic reader reads first and a beginner never finds, and it is the substrate of the AR redline; mid-ranked because the locator is unverified and scanned ARs are common in the target names.

**Size.** M (5-8 days), estimated 7 days. Section locator + targeted deep read that leaves the global cap alone, AR locator, learnedTerms in the workspace blob (four-call-site rule), seven-card output.

**Lifecycle cost.** Heading conventions vary and drift; per-report BYOK token cost is real; the per-scrip AR locator endpoint is unverified.

**Design system:** on. Seven cards with page chips.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-06, BL-22 (optional)  
**Prerequisite defect fixes:** COD-research-extraction-synthesis-2 (high; so the budget ceiling can fire on research LLM calls)  
**Closes census findings:** none

**Biggest risk.** An off-by-one page (PDF index vs printed folio) destroys the receipt; scanned micro-cap reports must say 'I can read 3 of your 7 pages'.

#### 32. BL-32 · Alerts with a track record

Tier 3 · **S-M, 4 days** · Sources: bloomberg-7 (primary)

**What.** Alerts written in plain English compile to a visible rule and are dry-run against the stored tape before arming ('this would have fired 3 times on your book, here they are', with the tape's honest depth stated), then evaluate at sweep time only.

**Why #32.** It shows the noise rate Bloomberg's ALRT never shows, cheaply once tripwires exist; it ranks after tripwires because it is the generic version of the same engine.

**Size.** S-M (4-5 days), estimated 4 days. Alert rule store + create_alert proposed change + dry-run evaluator, on the tripwire engine.

**Lifecycle cost.** Dry-run depth is shallow on day one and must be stated; it deepens only as the tape accumulates.

**Design system:** on  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-04, BL-09  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** An unstated shallow history becomes false comfort.

#### 33. BL-33 · Operator radar

Tier 3 · **M, 6 days** · Sources: retail-2 (primary)

**What.** On wake, catch up missed sessions from the exchange daily archives and run deterministic shape rules on held and watched names (series migration to trade-for-trade, upper-band lock streaks, volume above k times the median, price moves with a silent filings feed, delivery collapsing while price rises) with the bhavcopy rows and the empty announcements window as receipts; the LLM only narrates rules that fired.

**Why #33.** It makes the join nobody does (movement with no filing) on data the app already ingests, for the user most exposed to operators; it sits below Exit Door because its failure mode (a false alarm on a winner) costs the user money.

**Size.** M (5-8 days), estimated 6 days. Rules over the recorded session data, delivery parse, SME series admitted for watched symbols; an ASM/GSM lane only if an endpoint is confirmed.

**Lifecycle cost.** NSE has changed the bhavcopy format once already; 'last successful ingest N sessions ago' must be visible through provider_health; the BSE delivery lane is unknown.

**Design system:** on. A radar card.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-08, BL-02, BL-24  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** False positives on genuine re-ratings teach a nervous user to sell winners: 'shape, thresholds and rows', never 'manipulated'.

#### 34. BL-34 · Honesty card and trial ledger for backtests

Tier 3 · **M, 6 days** · Sources: quant-3 (primary)

**What.** Every backtest ships a deterministic audit (the fill delta against next-open, since fills happen at the signal bar's close today; the provider and adjustment basis that bar_loader currently discards; a dated India fee preset; volume participation; a survivorship flag; n) plus a persisted count of variants tried on the symbol set that deflates the headline Sharpe into a banded verdict (anecdote / suggestive / robust), fed to strategy_critic as facts.

**Why #34.** The cheapest credibility win for the backtest audience and it contradicts its own headline number, but backtesting is peripheral to the research-first positioning and a critical metrics defect must be fixed under it first.

**Size.** M (5-8 days), estimated 6 days. Honesty block, trial ledger store, fee preset, critic wiring; excludes the COD-backtest-1 fix.

**Lifecycle cost.** Statutory charges change with budgets (a dated fee table with an as-of label); the trial ledger needs a 'new hypothesis' reset or it punishes honest exploration.

**Design system:** on. An honesty block in BacktestResultView.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-08 (for participation)  
**Prerequisite defect fixes:** COD-backtest-1 (critical; admitted critical: multi-symbol metrics mis-annualised per bar)  
**Closes census findings:** none

**Biggest risk.** Deflation maths with false precision: a banded verdict with the formula one click away.

#### 35. BL-35 · Priced in: what the market cap already assumes

Tier 3 · **S, 3 days** · Sources: sellside-4 (primary)

**What.** A deterministic reverse DCF (an implied-ROE form for lenders and holding companies by sector rule) states the growth and margin the current market cap implies at a user-visible cost of equity, beside 5-year history, guidance (BL-16) and the user's model (BL-26), as a full sensitivity grid: never a target price, rating or 'undervalued'.

**Why #35.** Three days for the question a PM pays for, but its history column reads exactly the statement data the census found serving a different company on SME ticker collisions (admitted critical), so it waits behind that fix.

**Size.** S (2-4 days), estimated 3 days. Solver + implied-ROE variant, priced_in read_handler, grid block, Settings default.

**Lifecycle cost.** Low: deterministic maths over existing fields; it breaks only if the fundamentals contract changes.

**Design system:** on. A sensitivity-grid block.  
**Plugin contract:** untouched. priced_in read_handler projects to MCP.  
**Tracked-portfolio write:** no write

**Depends on:** BL-16 (guidance column; optional, v1 ships the history column alone), BL-26 (model column; optional)  
**Prerequisite defect fixes:** DAT-P3-1 (critical), DAT-P4-1 (critical), DAT-P5-1 (critical), DAT-P6-1 (critical)  
**Closes census findings:** none

**Biggest risk.** False precision and the look of regulated research (SEBI RA regulations: unverified seat knowledge); always the whole grid, never a single cell.

### Tier 4: Later: narrower audience, heavier, or composed of items above

#### 36. BL-36 · Forkable research (.vybrief) and the receipt bundle

Tier 4 · **M, 6 days** · Sources: hn-sceptic-8 (primary); journalist-7 (receipt-bundle half) (absorbed)

**What.** A thin versioned bundle (structured legs, execution record, number receipts, locker hashes, per-figure URL / page / quote / fetch time, tool trace, no secrets since the key never persists) that any install can Verify by deterministic replay and re-hash at zero tokens: one format for sharing, for re-verifying your own old work, and for the redacted diagnostics bundle behind 'the numbers look wrong'.

**Why #36.** It answers lifecycle question L3 (no redacted diagnostics bundle exists) and makes research portable, but it sits on the firewall and the locker.

**Size.** M (5-8 days), estimated 6 days. Envelope + format_version, export and import through the Rust atomic path (never <a download>, WLD-T-2), verify replay, report block.

**Lifecycle cost.** A file format is a forever promise: keep it a thin envelope with a format_version; replay breaks when a provider dies, and the verify report names the leg that no longer reproduces.

**Design system:** on. Export / import actions and a verify-report block.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-05, BL-22  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Most retail users never share a file; it has to pay for itself as the diagnostics bundle.

#### 37. BL-37 · Calm protocol

Tier 4 · **M, 6 days** · Sources: retail-5 (primary)

**What.** When a holding falls hard during the watchlist's quote poll, run a fixed five-check triage as tool calls (filing today, sector peers, index, volume, radar), say 'market' or 'company' with receipts and check times, quote back the selling rule the user wrote when calm, and re-run on the next announcements TTL.

**Why #37.** Initiative at the moment a human thinks worst, but it fires only while the app is open during market hours and it composes pieces that rank above it.

**Size.** M (5-8 days), estimated 6 days. Drop trigger, deterministic checklist runner, rules field, triage card, notification intent.

**Lifecycle cost.** Only while the app is open (no daemon), which must be stated; sector-map staleness mislabels peers over time.

**Design system:** on. A triage card.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-03, BL-04, BL-33 (optional)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** A 'looks like the market' read minutes before a filing lands: the card carries its check time and re-runs.

#### 38. BL-38 · Instant cockpit

Tier 4 · **M, 5 days** · Sources: designer-3 (primary)

**What.** Mirror the autosave layout and a bounded last-seen value map into the app-data dir through a Rust read command (a two-name allow-list) so the cockpit paints in under 200 ms before the sidecar binds, each cached figure stamped with its age in a tertiary tone until it fades to live, never flashing.

**Why #38.** The best first impression of a fast terminal, but two admitted high defects stand between it and the screen, and fixing those alone captures most of the win.

**Size.** M (5-8 days), estimated 5 days. Rust read command, mirror writes on the autosave debounce, 'cached' freshness state, sidecar-wins reconcile.

**Lifecycle cost.** Two-writer drift between the mirror and the sidecar (the sidecar always wins; a version stamp); SerializedWorkspace changes must keep the older-blob guard.

**Design system:** on, extends it. Adds a 'cached' freshness state to StalenessBadge (conformance review).  
**Plugin contract:** untouched. An ordinary Rust command; tauri.conf.json is not touched.  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** COD-rust-core-1 (high), COD-workspace-layout-3 (high)  
**Closes census findings:** none

**Biggest risk.** A cached price read as live during market hours.

**Judge notes.**
- Blocked by two admitted high defects: setup() joins both MCP port-waits on the main thread, freezing the window for about 35 s on every cold boot (COD-rust-core-1), so nothing can paint early; and autosave is not gated on restore (COD-workspace-layout-3), so the mirror would copy a partial blob.

#### 39. BL-39 · Earned autonomy

Tier 4 · **S, 3 days** · Sources: designer-8 (primary)

**What.** Replace the global ask / auto switch with per-kind autonomy and a persisted accept / reject tally; after a clean record (for example 23 of 23 chart changes) the agent offers once to stop asking for that kind, downgrades on the first reject, shows the ledger in Settings, and never offers for writes to the tracked portfolio.

**Why #39.** Nearly free once the AUTO whitelist fix lands and good design, but the fix carries the value and the tally is polish; never grant autonomy for something you cannot undo, so it follows BL-19.

**Size.** S (2-4 days), estimated 3 days. Per-kind map, tally in the workspace blob, offer line, Settings table; build together with the COD-hapc-3 whitelist.

**Lifecycle cost.** Low: one map, one tally, one table; the thresholds are the operator's call.

**Design system:** on. One offer line and a Settings table.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** governs the gate itself. Tracked-portfolio data-writes are permanently excluded from auto-apply; this is the per-kind whitelist COD-host-actions-proposed-changes-3 asks for, plus a record.

**Depends on:** BL-19  
**Prerequisite defect fixes:** COD-host-actions-proposed-changes-3 (high)  
**Closes census findings:** none

**Biggest risk.** It can read as the product nudging you toward less oversight: offered once per kind, a permanent 'don't ask', a visible ledger.

#### 40. BL-40 · GO bar and learned routines

Tier 4 · **S-M, 4 days** · Sources: bloomberg-8 (primary)

**What.** '<TICKER> <FN>' parsed deterministically in under 100 ms ahead of the fuzzy palette (SHP, ANN, FA, RES, EXIT, TAPE and so on, each mapped to an existing host action), a 'next time: TANLA SHP' hint after agent turns that reduce to one function, and a bounded host-action history that offers to bind a repeated morning sequence as one routine.

**Why #40.** Real speed for power users at zero tokens, but it serves the terminal-native minority and the routine-learning half carries nag risk.

**Size.** S-M (4-5 days), estimated 4 days. Function table, ~40-line parser, hint line, history ring + repeat detector.

**Lifecycle cost.** A small versioned function vocabulary; adding a function is a data change.

**Design system:** on. A parse-preview line in the palette.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** none  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Mnemonic collisions with real NSE symbols: ticker-first grammar and a visible parse preview.

#### 41. BL-41 · Page One

Tier 4 · **S, 3 days** · Sources: sellside-8 (primary)

**What.** Every brief opens with three boxes (what changed since the last brief on this symbol, BL-18; what is priced in, BL-35; one dated falsifier that resolves against a future filing) with background folded away, and a deterministic filler score (sentences with no number, entity or date) fed back once into the research loop.

**Why #41.** A composition of items that rank above it, worth doing once those exist.

**Size.** S (2-4 days), estimated 3 days. Three-box renderer, falsifier field (additive in types/brief.ts), filler scorer.

**Lifecycle cost.** The heuristic needs tuning as the research agent's style drifts; unresolvable falsifiers must expire honestly.

**Design system:** on. A three-box renderer on existing blocks.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-18, BL-35, BL-15 (falsifier resolution)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** A crude filler metric punishes useful qualitative context: it demotes and reports, never deletes; the rewrite round costs an extra LLM call (off in FAST).

#### 42. BL-42 · Pre-print card and your forecast record

Tier 4 · **S-M, 5 days** · Sources: bloomberg-4 (pre-commit and calibration half) (primary)

**What.** The evening before a holding reports (wake-driven), lay out what management guided with page receipts and ask the user for three numbers; freeze them once the results announcement exists and grade print against guidance against the user, keeping a calibration record across quarters.

**Why #42.** It makes the user commit before the print and keeps score on them, which is memory with teeth, but everything it shows comes from BL-15 and BL-16.

**Size.** S-M (4-5 days), estimated 5 days. Expectations store (frozen at the results timestamp), grade block, calibration view.

**Lifecycle cost.** Scanned results PDFs mean the print column often reads 'unparsed, enter manually, see p.N', which must be a designed state.

**Design system:** on. A grade block (print / guided / yours / delta).  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-04, BL-15, BL-16  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** A degraded print column presented as a failure.

#### 43. BL-43 · One number, one truth

Tier 4 · **S, 3 days** · Sources: designer-5 (primary)

**What.** A client-side figure registry keyed by (symbol, metric, basis) that every <Fig> and every extracted brief claim registers into; when two open panels disagree beyond tolerance, both get a link glyph explaining why (for example a brief that predates JONJUA's bonus).

**Why #43.** Cheap once <Fig> exists and it catches exactly the stale-brief-after-a-bonus case, but it only covers what BL-21 has adopted.

**Size.** S (2-4 days), estimated 3 days. Registry store, pure tolerance comparator, glyph + sibling highlight.

**Lifecycle cost.** Only figures rendered through <Fig> take part; the tolerance table needs care as metrics are added.

**Design system:** on. A link glyph and sibling highlight.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-21  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** False positives from timing skew; price-class metrics compare only across different as-of days.

#### 44. BL-44 · Surprise without analysts (SUE)

Tier 4 · **S-M, 4 days** · Sources: quant-8 (primary)

**What.** Seasonal-random-walk standardised earnings surprise from the company's own 8-quarter history (no consensus needed), triggered by results for holdings and watchlist, with an after-hours-aware first tradable session and a two-source gate (filing PDF plus vendor quarterly) or a 'single-source, provisional' label.

**Why #44.** Surprise for exactly the names nobody covers, but it is a statistic on top of BL-15 and only as clean as the quarterly history under it.

**Size.** S-M (4-5 days), estimated 4 days. SUE computation + sigma bar, trigger on results, two-source gate, basis pinning per company.

**Lifecycle cost.** PDF table extraction is the fragile joint (BL-15's fixtures); consolidated vs standalone pinned per company.

**Design system:** on. A sigma-bar card.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-15, BL-51 (optional drift tracker)  
**Prerequisite defect fixes:** DAT-P3-1 (critical), DAT-P4-1 (critical), DAT-P5-1 (critical), DAT-P6-1 (critical)  
**Closes census findings:** none

**Biggest risk.** A mis-extracted PAT yields a confident wrong sigma; the vendor quarterly second source is itself unreliable on SME ticker collisions.

#### 45. BL-45 · Proceeds ledger

Tier 4 · **S-M, 5 days** · Sources: sellside-9 (primary)

**What.** Parse the quarterly Monitoring Agency Reports and Reg 32 deviation statements small caps already file into a per-issue ledger (object, promised, deployed, deviation, agency comments) with a monotonic-cumulative check, and flag stalled or reallocated objects and growth in 'general corporate purposes'.

**Why #45.** It watches a filing nobody reads and, with the cheap-paper calendar, closes the capital-raise loop; narrower audience than the items above.

**Size.** S-M (4-5 days), estimated 5 days. Table parsers + fixtures, proceeds table, one user-accepted objects extraction per issue, stalled-object card.

**Lifecycle cost.** Few formats, slow-changing regulation and a quarterly cadence: the cheapest parser here to keep alive.

**Design system:** on. A ledger block.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-02  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Cumulative vs quarterly column confusion (a monotonicity check blocks the row); sub-threshold issues have no monitoring agency and must say so.

#### 46. BL-46 · Cheap-paper calendar

Tier 4 · **M, 6 days** · Sources: forensic-4 (primary)

**What.** When a company allots preferential shares or warrants, extract allottees, price and per-tranche lock-in dates from the filing once (a durable budget-bounded run), let the user accept them through the gate, then raise the unlock at T-30 and T-7 with the page; cross-check open entries against the SHP XBRL lock-in and warrant flags (BL-13).

**Why #46.** The micro-cap supply-overhang event given a date: high value for the forensic seat, narrow for everyone else.

**Size.** M (5-8 days), estimated 6 days. Extraction prompt + schema, calendar table on the tape, one proposed-change kind, supply-events strip.

**Lifecycle cost.** Extraction is the only LLM step and it is human-accepted once; scanned allotment letters become 'could not read, enter manually'; lock-in dates are always read, never computed from ICDR rules.

**Design system:** on. A supply-events strip on the portfolio panel.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write. Calendar rows live in their own store through the gate.

**Depends on:** BL-04, BL-13  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Multi-tranche allotments and partly-paid warrants make 'the' date plural: per-tranche rows.

#### 47. BL-47 · Peer set and read-across

Tier 4 · **M, 7 days** · Sources: sellside-6 (primary)

**What.** A user-owned typed value chain per covered name (peer, customer, supplier, parent, subsidiary) seeded from the local sector columns, driving a comps table over up to about 15 names from the local store (compare_symbols caps at 4) and a quote-or-nothing read-across card when any node files results, a transcript or a monthly update.

**Why #47.** Watching beyond your own names is how sell-side finds its best calls and the comps table alone is broadly useful; the read-across half is pro-seat.

**Size.** M (5-8 days), estimated 7 days. Edge table, peer_comps handler, structured footnotes, read-across card with verbatim gate.

**Lifecycle cost.** Edges go stale (an annual review prompt); taxonomy differs across sources, which is why edges are user-owned.

**Design system:** on. A comps table and a read-across card.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-02, BL-04, BL-26 (for FY+1 columns)  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Read-across noise: typed edges only, and a card that finds nothing relevant is filed silently.

#### 48. BL-48 · Dodge ledger and who's in the room

Tier 4 · **M, 7 days** · Sources: sellside-7 (primary)

**What.** Pair each analyst question with management's answer in transcripts, label ANSWERED / DEFLECTED by deterministic features with the rule shown, track repeat deflections across calls, write a pre-meeting question bank when an Analyst / Investor Meet intimation is filed, and chart the roster of firms asking questions each quarter as a discovery or abandonment signal.

**Why #48.** A genuinely new signal (the institutional-discovery roster) that no Indian tool tracks, but it serves the corporate-access seat and needs transcript coverage that is thin on small caps.

**Size.** M (5-8 days), estimated 7 days. Speaker-turn parser + fixtures, firm alias list, answer-feature scorer, roster table, intimation parser.

**Lifecycle cost.** Moderator phrasing varies; the firm alias list needs upkeep; about one fixture per new transcript format.

**Design system:** on. A Q&A table and a roster sparkline.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write. The question bank lands in notes via write_note (a data-write), which needs COD-host-actions-proposed-changes-2 fixed first.

**Depends on:** BL-02, BL-16  
**Prerequisite defect fixes:** COD-host-actions-proposed-changes-2 (high)  
**Closes census findings:** none

**Biggest risk.** Labelling a legitimate no-guidance answer as a dodge: the rule is shown, the cross-call pattern outweighs any single label, and the user can dismiss a label with a reason.

#### 49. BL-49 · User-addable MCP servers

Tier 4 · **S-M, 5 days** · Sources: OPP-6 (primary)

**What.** A user-configured MCP server list over the generic McpClient that already exists (mcp_client.py:218), each server declared read-only by the user and its tool output fenced as untrusted, so adding a filings or data server is paste-a-URL rather than write-an-adapter.

**Why #49.** Extensibility is in the DNA and the client half is built, but the remaining evidence is ToS-grey scrapers and it opens a new injection path, so it waits behind the fence.

**Size.** S-M (4-5 days), estimated 5 days. Config store + settings UI + spawn/connect + fence; excludes the fence and AUTO fixes it depends on.

**Lifecycle cost.** Third-party servers change tool schemas without notice; the app cannot audit a remote server's read-only claim the way it audits in-tree wrappers (inspect.getmembers and router.routes), so enforcement is the fence plus no host-action tools reachable from their output.

**Design system:** on. A settings list.  
**Plugin contract:** untouched. Untouched if built as sidecar configuration; do not model it as a plugin capability (Tier-4).  
**Tracked-portfolio write:** no write. No direct writes, but third-party tool text entering the main loop can steer portfolio writes under AUTO today, so it must land after the fence and the AUTO whitelist.

**Depends on:** none  
**Prerequisite defect fixes:** WLD-harness-context-4 (high), COD-host-actions-proposed-changes-3 (high)  
**Closes census findings:** WLD-T-5 (medium)

**Biggest risk.** A new prompt-injection path into a loop that can still auto-apply portfolio deletes.

**Judge notes.**
- Its evidence thinned twice after the ledger was written: the broker servers were struck by the 23 Sep removal, and the WLD-T-5 refute downgraded the gap to medium ('universal tool layer' means MCP as a server; nothing promises consuming user-added servers). The surviving motivating examples are screener.in scrapers, which OPP-13 in the same ledger says not to add.

#### 50. BL-50 · Factor X-ray

Tier 4 · **S-M, 5 days** · Sources: quant-7 (primary)

**What.** Cross-sectional percentile ranks (value, quality, momentum, size, low volatility, delivery %) over the whole local India store give each holding and the book a factor-exposure strip with stated coverage and data_as_of, a factor_exposure capability, and a daily watch when an exposure crosses an extreme.

**Why #50.** 'Your portfolio is one trade' is a real insight, but percentiles over vendor fundamentals inherit the statement-lane defects and the momentum and volatility legs need months of recorded EOD.

**Size.** S-M (4-5 days), estimated 5 days. Rank computation with frozen versioned definitions, capability, strip, threshold watch.

**Lifecycle cost.** Rank definitions frozen and versioned; thin BSE-only coverage renders 'unranked', never the 50th percentile.

**Design system:** on. An exposure strip on the portfolio panel.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** reads only. Reads the manual tracked portfolio.

**Depends on:** BL-08  
**Prerequisite defect fixes:** DAT-P3-1 (critical), DAT-P4-1 (critical), DAT-P5-1 (critical), DAT-P6-1 (critical)  
**Closes census findings:** none

**Biggest risk.** Ranks launder vendor errors into confident percentiles.

**Judge notes.**
- The seat's broker_portfolio read (catalog.py:911) is on the trading-removal surface and is struck; the manual portfolio is sufficient.

#### 51. BL-51 · Incubator: frozen rules with an out-of-sample record

Tier 4 · **M, 6 days** · Sources: quant-4 (primary)

**What.** Freeze a saved screen or DSL rule; the terminal evaluates it every session on the recorded tape (replaying missed days on wake, stamped replayed_on_wake) into an append-only, hash-chained signal log in a new database and reports in-sample vs out-of-sample decay. It scores; it never proposes or places anything.

**Why #51.** Its value is measured in wall-clock months and it serves the systematic seat; the recorder it needs ranks high precisely so this can exist later.

**Size.** M (5-8 days), estimated 6 days. Frozen-rule store, append-only signal log (trigger idiom copied into a new DB; the §6.5 audit-log files are not touched), wake replay, Incubator tab.

**Lifecycle cost.** Rule definitions versioned against the evaluator: a semantics change must refuse to continue an old rule; one evaluation per rule per day; small disk.

**Design system:** on. An Incubator tab in the backtest panel.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-08  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** A forward record read as advice: n and dispersion beside every number.

#### 52. BL-52 · As-of screens

Tier 4 · **S, 3 days** · Sources: quant-1 (surface half) (primary)

**What.** An as_of parameter on screener_run and an 'as of' chip on the screener panel answer 'run my screen as it looked on 1 July' from what this machine observed, with a survivorship-free universe (every symbol with a row that day) and rename stitching through nse_symbol_change.lookup_current(symbol, as_of).

**Why #52.** The surface is cheap but has nothing to show until the recorder has months of history, so it ranks far below the recorder.

**Size.** S (2-4 days), estimated 3 days. Parameter + chip + labelling; worthless until BL-08 has months of data.

**Lifecycle cost.** Labelled 'observed since <date>' or it becomes the lie it exists to prevent; compaction policy from BL-08.

**Design system:** on. A chip.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-08  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Users assume vendor history is point-in-time; label every result.

#### 53. BL-53 · Between the prints

Tier 4 · **M, 7 days** · Sources: sellside-5 (primary)

**What.** A quarter-to-date nowcast from monthly dispatch releases, business updates and order-win filings: a user-accepted extraction spec per filer runs deterministically each month, compared with the model's quarter estimate as a required-run-rate bar, with order inflow summed onto the last stated order book for book-to-bill.

**Why #53.** Unique (no other seat nowcasts), but it stands on the Model Store and the peer set and carries standing curation cost.

**Size.** M (5-8 days), estimated 7 days. Tallies table, schema-once extraction with a re-confirm state, rupee amount parser with unit witness, QTD card.

**Lifecycle cost.** Per-filer specs break when a PR team redesigns the release (the re-confirm state), about an hour a month of curation across 30 names; many small caps file nothing between prints.

**Design system:** on. A QTD card.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-02, BL-26, BL-47  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** A false read-across when a supplier's mix shifts: user-owned edge weights, and it never writes the model.

#### 54. BL-54 · Annual-report redline

Tier 4 · **M, 8 days** · Sources: forensic-8 (primary)

**What.** A git diff for the notes to accounts: locate the auditor's report, the related-party note and contingent liabilities in this year's and last year's annual report, produce deterministic difflib hunks first, let the LLM only label materiality while quoting both sides verbatim, and show both pages side by side; any empty page in a section marks it unreadable.

**Why #54.** The coding-agent idiom transplanted whole onto the document aggregators cannot normalise, but it is the heaviest reader item and the most exposed to scanned-PDF garbage.

**Size.** M (5-8 days), estimated 8 days. Held to three sections on BL-31 and BL-22: locator, hunk generator, materiality prompt, diff block, run recipe.

**Lifecycle cost.** Heading conventions vary; table-heavy notes diff badly as text (layout retry); a 'section not found, open at the notes index' fallback.

**Design system:** on. A typed diff block in BriefBody.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-31, BL-22  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Scanned ARs and fused table cells produce garbage hunks that look like findings.

### Tier 5: Parked: blocked, gutted by the scope change, or not worth the risk now

#### 55. BL-55 · Accounts linter with reasoned suppressions

Tier 5 · **M, 6 days** · Sources: forensic-5 (primary)

**What.** Classic forensic checks as rule ids with their inputs shown (CFO/PAT, receivable and inventory days, other-income share, cash vs book tax, CWIP ageing, profit without sales) instead of a score; the user suppresses a finding with a written reason and an accepted level, and the rule re-fires quoting that reason when the gap widens (OPP-8 delivered as inspectable rules).

**Why #55.** PARKED: a strong design, but its inputs for the target names are either not agent-reachable (WLD-T-4) or a different company's numbers (DAT-P3-1 family, admitted critical); do not build ahead of the statement lane.

**Size.** M (5-8 days), estimated 6 days. Once unblocked: rule format + ~10 rules, statement-field resolver, lint block, suppression UI, lint_accounts capability.

**Lifecycle cost.** Rules are versioned data; the cost is statement coverage for micro-caps.

**Design system:** on. A lint block.  
**Plugin contract:** untouched. lint_accounts read_handler.  
**Tracked-portfolio write:** no write

**Depends on:** BL-09 (shared rule engine)  
**Prerequisite defect fixes:** WLD-T-4 (high), DAT-P3-1 (critical), DAT-P4-1 (critical), DAT-P5-1 (critical), DAT-P6-1 (critical)  
**Closes census findings:** none

**Biggest risk.** 'no-data' everywhere on exactly the names it is for; a rule with missing inputs must report no-data, never pass.

#### 56. BL-56 · Personas on probation

Tier 5 · **M, 6 days** · Sources: hn-sceptic-9 (primary)

**What.** Every persona and custom agent ends with one falsifiable, dated statement about reported fundamentals (never price or buy / sell); it resolves deterministically on wake, and the persona header carries a Brier and calibration record, refusing to show a score under n = 10.

**Why #56.** PARKED: a clever answer to 'twelve billionaire cosplay prompts', but it gives the user nothing usable for months and carries optics risk; Page One's falsifier (BL-41) captures the same discipline for the research agent itself.

**Size.** M (5-8 days), estimated 6 days. Validated forecast tail, forecasts store + resolver with VOID expiry, calibration view, header line.

**Lifecycle cost.** Small-cap resolution coverage is thin; unresolved forecasts expire as VOID; months of small n.

**Design system:** on. A persona header line.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-04, BL-15  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** The optics of 'predictions' in a finance app.

#### 57. BL-57 · Rule forge: event studies from any predictive sentence

Tier 5 · **L, 14 days** · Sources: quant-5 (primary)

**What.** A predictive sentence in a brief gets a flask button: the LLM drafts a typed EventSpec once, the user approves it, and a deterministic event study over exchange disclosures returns CAR, n, t-stat, hit rate, top-3 contribution and the filing behind every event, usually concluding 'not distinguishable from noise'.

**Why #57.** PARKED: intellectually the most honest research feature in the quant set, but L-sized on an unprobed data dependency; revisit once the recorder and the feed have accrued history.

**Size.** L (12+ days), estimated 14 days. Event-study engine, EventSpec + approval, category map + fixtures, accruing cross-sectional announcement archive, capability.

**Lifecycle cost.** Announcement categories drift (a category map with an unclassified bucket and fixtures); a cross-sectional announcement archive has to accrue.

**Design system:** on. A CAR chart block.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** no write

**Depends on:** BL-08, BL-02, BL-34  
**Prerequisite defect fixes:** none  
**Closes census findings:** none

**Biggest risk.** Cross-sectional history per category is unprobed and the current fetcher is per-symbol; with thin history it is an anecdote detector for months.

#### 58. BL-58 · 'I noticed you bought'

Tier 5 · **S-M, 4 days** · Sources: retail-4 (primary)

**What.** When a holding appears in the tracked portfolio, ask one line of 'why', freeze the world at that moment (price, basis-noted P/E, promoter %, exit-door reading, radar flags), and come back months later with a review of reasons given against returns.

**Why #58.** PARKED: the trading removal took its watching half, and the surviving decision journal is a nice-to-have.

**Size.** S-M (4-5 days), estimated 4 days. Manual-portfolio variant only: ask-card, frozen snapshot, periodic review brief.

**Lifecycle cost.** A tiny bounded store; corporate actions must never read as a buy (BL-14).

**Design system:** on. An ask-card and a review brief.  
**Plugin contract:** untouched  
**Tracked-portfolio write:** reads only. Reads holdings; writes the 'why' into the symbol note via write_note (a data-write), which needs COD-host-actions-proposed-changes-2.

**Depends on:** BL-03, BL-14  
**Prerequisite defect fixes:** COD-host-actions-proposed-changes-2 (high)  
**Closes census findings:** none

**Biggest risk.** Nagging: one card per new name, dismissible forever.

**Judge notes.**
- The seat's core mechanism, diffing successive read-only broker holdings snapshots (GET /brokers/{id}/holdings), is on the 23 Sep trading-removal surface. What survives is the manual portfolio, where the user enters the holding in-app, so the 'noticed' moment collapses to 'ask when you add it'.

## Candidates (unranked)

Items below did not go through the Stage 2 seat/judge process above. They are
raw candidates for the Stage E judge panel to rank on its next pass; nothing
here has a tier, a rank, or build authority yet.

#### Candidate · Filing watcher: System 1 triage in front of the BYOK model

Unranked · **Source:** R15 scope change 2 groundwork,
`docs/redesign/verification/r15/laya/BACKLOG_ENTRY.md` (full design, licence,
Windows-route note, groundwork/dataset detail and the measured verdict below)
and `docs/redesign/verification/r15/laya/VERDICT.md` (measurement detail and
critic corrections). Verification evidence only — no code from this groundwork
ships in this release.

**What.** A local triage pass in front of the BYOK model in the ingestion path
(not the chat path): score every NSE/BSE corporate announcement, pledge
change, bulk/block deal and rating action against the user's holdings,
watchlist and written thesis, and wake the BYOK model only for item shapes
that already look decision-relevant. Every surfaced item carries a receipt: a
direct link to the source filing page. The five source feeds already exist in
the sidecar (`corporate_disclosures.py`, `analyst_ratings_extended.py`); the
triage/watch layer over them does not.

**Measured verdict (this groundwork's own MEASURE pass, not a build result).**
Not worth fine-tuning for this release; case for later mixed. Gate P/R per
noul task, `composer_intent` accuracy vs majority, ECE before/after, p50/p99,
peak/steady RSS and the current-path comparison, each with its file pointer,
are in `docs/redesign/verification/r15/laya/BACKLOG_ENTRY.md` §"Verdict".
Headline: zero-shot beats majority on `composer_intent` (0.630 vs 0.333) but
loses to the sidecar's existing $0 regex heuristic (0.815); on
`holding_relevance` the best operating point ties the majority-class rate
exactly (no discrimination); `entity_match` is the one bright spot (max-F1
0.855 vs 0.71 majority) but the current heuristic is competitive on an
admittedly unfair adapted input (0.74 vs 0.77). A post-hoc calibration
temperature fit made ECE worse on both noul tasks, not better.

**Size.** Not estimated by this pass — no fine-tuning, training-set build, or
integration work has been scoped; §3 of the source doc sketches a fine-tune +
calibration + opt-in-setting plan but nothing here should be read as a size
estimate.

**Lifecycle cost.** Unscoped. The source doc notes a temperature fit must be
redone per inference backend (MLX on Apple silicon vs a PyTorch/ONNX Windows
route, since `laya-mlx` has no Windows/CUDA backend) — see
`docs/redesign/verification/r15/laya/BACKLOG_ENTRY.md` §5.

**Design system:** n/a. No UI shipped by this groundwork.
**Plugin contract:** untouched.
**Tracked-portfolio write:** reads only, in the design sketch — no code exists.

**Depends on:** the five existing disclosure/rating feeds (already shipped,
see `docs/redesign/verification/r15/laya/BACKLOG_ENTRY.md` §2); a real
training set built from actual web-row inputs for `entity_match` if pursued
(the groundwork dataset used markdown passages, a shape mismatch against the
sidecar's own `entity_match` input).
**Prerequisite defect fixes:** none identified.
**Closes census findings:** none — this candidate was not run against the
census.

**Biggest risk.** The measured zero-shot checkpoint loses to a free existing
heuristic on the one task (`composer_intent`) that already has a fast working
path, and ties majority-class on `holding_relevance`; fine-tuning is
unvalidated (base-checkpoint literature cited in
`docs/redesign/verification/r15/laya/PACKAGE_VERIFICATION.md` claims #13/#14
says a fine-tune is needed to clear this bar, not just zero-shot use).

## Defect fixes this backlog depends on

These are census findings (admitted by refute) that must land in the defect lane before, or with, the items that list them. They are not backlog items.

| Finding | Severity | Blocks |
|---|---|---|
| COD-backtest-1 | critical | BL-34 |
| COD-host-actions-proposed-changes-1 | high | BL-17, BL-19 |
| COD-host-actions-proposed-changes-2 | high | BL-48, BL-58 |
| COD-host-actions-proposed-changes-3 | high | BL-17, BL-27, BL-39, BL-49 |
| COD-research-extraction-synthesis-2 | high | BL-12, BL-31 |
| COD-rust-core-1 | high | BL-38 |
| COD-workspace-layout-3 | high | BL-38 |
| DAT-P3-1 | critical | BL-35, BL-44, BL-50, BL-55 |
| DAT-P4-1 | critical | BL-35, BL-44, BL-50, BL-55 |
| DAT-P5-1 | critical | BL-35, BL-44, BL-50, BL-55 |
| DAT-P6-1 | critical | BL-35, BL-44, BL-50, BL-55 |
| WLD-T-4 | high | BL-55 |
| WLD-harness-context-4 | high | BL-10, BL-49 |
| WLD-harness-tools-3 | high | BL-17 |

## Census findings the backlog closes

| Finding | Severity | Closed by |
|---|---|---|
| COD-disclosures-witnesses-10 | medium | BL-02 |
| COD-frontend-stores-2 | high | BL-04 |
| COD-workflow-engine-5 | medium | BL-04 |
| DAT-P12-1 | critical | BL-01 |
| DAT-P14-2 | critical | BL-01 |
| DAT-P14-4 | high | BL-14 |
| DAT-P16-1 | medium | BL-01 |
| DAT-P7-1 | high | BL-02 |
| DAT-P8-4 | medium | BL-01 |
| DAT-P9-5 | medium | BL-02 |
| DAT-S3-1 | high | BL-01 |
| DAT-S4-2 | medium | BL-01 |
| WLD-T-1 | high | BL-04 |
| WLD-T-10 | medium | BL-13 |
| WLD-T-5 | medium | BL-49 |
| WLD-T-6 | medium | BL-16 |
| WLD-T-8 | high | BL-13 |
| WLD-agent-native-ux-1 | high | BL-03 |
| WLD-agent-native-ux-2 | medium | BL-19 |
| WLD-harness-context-3 | high | BL-03 |

## Corrections the judge made to its inputs

Each was checked against the code at current HEAD or against an admitted refute verdict; none had been carried into the opportunity ledger or the seat files.

- **OPP-1** (BL-04). 'OS-notification sink already wired end to end' does not hold: src/lib/desktop-notification.ts reads useWorkflowStore, which no production code writes (COD-frontend-stores-2, COD-workflow-engine-5, both admitted; grep 2026-09-23). The OS send works; the feed is dead. The verify pass matched line text and marked OPP-1 held.
- **OPP-2** (BL-05). The cited 'scale tokens already recognised in extraction (extract.py:75,86-87)' are _PDF_FINANCE_KEYWORDS, a page-selection list, not a unit parser. No deterministic document-figure extraction exists, so the witness needs a unit-header parser and a figure-to-page binding (BL-06). Folded into BL-05.
- **OPP-4** (BL-16). 'Blocked on having the transcript at all (WLD-T-6)' is superseded: the sellside live probe found transcripts in the BSE feed the app already calls (SUBCATNAME 'Earnings Call Transcript'), and the WLD-T-6 refute downgraded it to medium. The blockers are the dropped subcategory and AttachLive rot (BL-02). Size M-L, not L.
- **OPP-6** (BL-49). After the broker examples were struck, the WLD-T-5 refute also downgraded the gap to medium (a generic McpClient exists, mcp_client.py:218; 'universal tool layer' means MCP as a server). The surviving examples are screener.in scrapers, which OPP-13 says not to add. Ranked 49.
- **forensic Tape, hn-sceptic-6, journalist-6** (BL-04). 'The portfolio is sidecar-side already (portfolio_db)' is wrong: holdings of record live in the workspace blob (src/store/portfolios.ts:14-15), and the sidecar /portfolio/positions ledger is write-only, fed only by agent writes (COD-host-actions-proposed-changes-9, admitted). Watch scope must be pushed from the renderer.
- **retail-3, retail-4, quant-7** (BL-24, BL-58, BL-50). Broker reads they cite (Kite holdings via routers/brokers.py, GET /brokers/{id}/holdings, broker_portfolio at catalog.py:911) are on the 23 Sep trading-removal surface and are struck. retail-3 and quant-7 survive on the manual portfolio; retail-4 loses its core and is parked.
- **forensic-9** (BL-28). The 'AGPL + plugin contract' moat argument is stale: the core was relicensed to PolyForm Strict 1.0.0 on 23 Sep (commit 0c63d46) and contributions are closed; types/plugin.ts is Apache-2.0, so third-party packs still ship as plugins.
- **designer-6** (BL-07). Its demo trips the breaker via POST /system/provider-health/trip, a rig mutation route the census says should not ship (COD-market-data-providers-2-11). The strip reads the GET only.

## Unfiled defects the seats surfaced (for the lead's register)

The judge stage emits no raw findings. This one looks like register material and has no raw finding of its own today.

- **BSE AttachLive 404s for filings older than a few weeks; AttachHis serves them** (BL-02; suggested high (the research PDF lane reads dead links for every BSE filing older than a few weeks)). sidecar/services/corporate_disclosures.py:84 always builds AttachLive; sellside live probe (10 and 17 Aug 2026 filings: 404 on AttachLive, 200 PDF on AttachHis). The register only mentions it in passing (DAT-P13-24 cites the P13 battery trap bse_attachment_path_attachhis_not_attachlive); INT-deferred-84-1 is about intermittent serving, not migration.

## Source index: every input and where it landed

| Input | Backlog item | Rank | Role | Note |
|---|---|---|---|---|
| bloomberg-1 | BL-04 | 4 | primary |  |
| bloomberg-2 | BL-24 | 24 | absorbed | Same idea as retail-3; its series-flip event rides BL-04. |
| bloomberg-3 | BL-30 | 30 | absorbed | Revision witness = the drift ledger; its 'as you saw it' chip lands there. |
| bloomberg-4 | BL-42 | 42 | primary | Split: the guidance-vs-delivery half is absorbed by BL-16; the pre-commit and calibration record is BL-42. |
| bloomberg-5 | BL-27 | 27 | absorbed | Mandate and Rulebook are the same mechanism. |
| bloomberg-6 | BL-10 | 10 | absorbed | Red Pen (three seats). |
| bloomberg-7 | BL-32 | 32 | primary |  |
| bloomberg-8 | BL-40 | 40 | primary |  |
| bloomberg-9 | BL-09 | 9 | absorbed | Kill criteria = tripwires (five seats). |
| retail-1 | BL-17 | 17 | primary |  |
| retail-2 | BL-33 | 33 | primary |  |
| retail-3 | BL-24 | 24 | primary | Kite-holdings dependency struck (trading removal). |
| retail-4 | BL-58 | 58 | primary | Broker-diff core struck (trading removal); manual variant parked. |
| retail-5 | BL-37 | 37 | primary |  |
| retail-6 | BL-13 | 13 | absorbed | Holder counts + conjunction rule ride the SHP XBRL parser extension. |
| retail-7 | BL-31 | 31 | primary |  |
| retail-8 | BL-04 | 4 | absorbed | The card-before-composer surface of the Watch. |
| forensic-1 | BL-23 | 23 | primary |  |
| forensic-2 | BL-25 | 25 | primary |  |
| forensic-3 | BL-13 | 13 | primary |  |
| forensic-4 | BL-46 | 46 | primary |  |
| forensic-5 | BL-55 | 55 | primary | Parked: blocked on the statement lane. |
| forensic-6 | BL-09 | 9 | primary | Its read_note prerequisite lands in BL-03. |
| forensic-7 | BL-22 | 22 | primary | Split: page-provenance gap -> BL-06; section-seek reader -> BL-31; locker -> BL-22. |
| forensic-8 | BL-54 | 54 | primary |  |
| forensic-9 | BL-28 | 28 | primary |  |
| quant-1 | BL-08 | 8 | primary | Split: the recorder is BL-08 (tier 1); the as-of screen surface is BL-52. |
| quant-2 | BL-30 | 30 | primary |  |
| quant-3 | BL-34 | 34 | primary |  |
| quant-4 | BL-51 | 51 | primary |  |
| quant-5 | BL-57 | 57 | primary | Parked. |
| quant-6 | BL-14 | 14 | primary |  |
| quant-7 | BL-50 | 50 | primary | broker_portfolio dependency struck (trading removal). |
| quant-8 | BL-44 | 44 | primary |  |
| quant-9 | BL-09 | 9 | absorbed | Thesis CI = tripwires. |
| hn-sceptic-1 | BL-05 | 5 | primary |  |
| hn-sceptic-2 | BL-22 | 22 | absorbed | Split: page identity through extraction -> BL-06; persistence + revised-filing detection -> BL-22. |
| hn-sceptic-3 | BL-10 | 10 | absorbed | Claim Checker = Red Pen. |
| hn-sceptic-4 | BL-20 | 20 | absorbed | Split: trust bench -> BL-20; in-app conflict ledger -> BL-29. |
| hn-sceptic-5 | BL-09 | 9 | absorbed | Tripwires. |
| hn-sceptic-6 | BL-04 | 4 | absorbed | Its coverage proof and blind-spots line are a required part of the Watch. |
| hn-sceptic-7 | BL-16 | 16 | absorbed | Promise ledger + FADED = the guidance ledger. |
| hn-sceptic-8 | BL-36 | 36 | primary |  |
| hn-sceptic-9 | BL-56 | 56 | primary | Parked. |
| journalist-1 | BL-10 | 10 | primary |  |
| journalist-2 | BL-07 | 7 | primary | Co-primary with designer-6. |
| journalist-3 | BL-29 | 29 | primary |  |
| journalist-4 | BL-18 | 18 | primary |  |
| journalist-5 | BL-27 | 27 | primary |  |
| journalist-6 | BL-04 | 4 | absorbed | The Handover = the Watch; its cost-basis proposal waits for BL-14 and the gate fixes. |
| journalist-7 | BL-06 | 6 | primary | Split: page anchors -> BL-06; receipt-bundle manifest -> BL-36. |
| journalist-8 | BL-20 | 20 | primary |  |
| sellside-1 | BL-15 | 15 | primary |  |
| sellside-2 | BL-26 | 26 | primary |  |
| sellside-3 | BL-16 | 16 | absorbed | Split: horizon drift + haircut number -> BL-16; apply-haircut-to-model -> BL-26. |
| sellside-4 | BL-35 | 35 | primary |  |
| sellside-5 | BL-53 | 53 | primary |  |
| sellside-6 | BL-47 | 47 | primary |  |
| sellside-7 | BL-48 | 48 | primary |  |
| sellside-8 | BL-41 | 41 | primary |  |
| sellside-9 | BL-45 | 45 | primary |  |
| designer-1 | BL-01 | 1 | primary |  |
| designer-2 | BL-11 | 11 | primary |  |
| designer-3 | BL-38 | 38 | primary |  |
| designer-4 | BL-21 | 21 | primary |  |
| designer-5 | BL-43 | 43 | primary |  |
| designer-6 | BL-07 | 7 | primary | Co-primary with journalist-2. |
| designer-7 | BL-19 | 19 | primary |  |
| designer-8 | BL-39 | 39 | primary |  |
| designer-9 | BL-12 | 12 | primary |  |
| OPP-1 | BL-04 | 4 | absorbed | Split: trigger layer -> BL-04; thesis watcher -> BL-09. 'Sink wired end to end' corrected (bridge has no production feeder). |
| OPP-2 | BL-05 | 5 | primary | Co-primary with hn-sceptic-1; proximity claim corrected (no unit parser exists). |
| OPP-3 | BL-21 | 21 | absorbed | Split: (a) already shipped (ConflictLine, brief-blocks.tsx:129-176); (b) per-figure attribution -> BL-21; (c) public benchmark page -> BL-20. |
| OPP-4 | BL-16 | 16 | primary | Transcript blocker corrected (transcripts already in the BSE feed). |
| OPP-6 | BL-49 | 49 | primary | Evidence thinned by the trading removal and the WLD-T-5 refute. |
| OPP-7 | BL-03 | 3 | primary |  |

## Excluded

- **OPP-5** (struck 2026-09-23 by the opp-ledger verify pass). One-click keyless broker connect: its whole subject is connecting a broker, which the operator's 23 Sep decision removed from the product. Not ranked.
