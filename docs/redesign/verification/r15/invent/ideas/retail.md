# R15 Stage 4 — Ideation seat: `retail`

**Seat:** first-time Indian retail investor, 24. Zerodha account opened last year. Holds 9 stocks
picked from YouTube and Telegram tips. Intimidated by annual reports. Terrified of operators and
pump-and-dumps in small caps.
**Worker model:** `claude-fable-5-1` · **Date:** 2026-09-19 · **Mode:** read-only thinking, nothing built.

## What this seat sees that the other seats will not

Every benchmark in the census (Perplexity Finance, Screener, Tijori, Trendlyne) is built for someone
who already has a thesis and wants data. This user has no thesis. He has a **source** — a Telegram
channel, a YouTuber — and a **fear**. His real questions are not "what is the ROCE" but:

1. "Is the person who told me to buy this lying to me?"
2. "Is somebody playing this stock?"
3. "If it goes wrong, can I even get out?"
4. "It's down 9% today — do I panic?"
5. "I cannot read a 240-page annual report. Which pages would a grown-up read?"

None of those are answered by a chatbot with panels, and none are on the floor list. They are
answered by something that **remembers what he was told, watches what happened next, and shows the
exchange's own row as the receipt.** That is the Jarvis shape for this seat: not a smarter analyst —
a bodyguard with a ledger.

A structural fact that shapes every mechanic below (verified in code): holdings, watchlist and notes
live in the **frontend workspace blob**, not the sidecar (`src/store/portfolios.ts:1-17`,
`src/store/notes.ts:3-7`). So every "watcher" here is **wake-driven**, not a daemon: on app
open/focus the frontend hands the sidecar the symbol set and a since-cursor, and the sidecar catches
up from **exchange daily archives**, which lose nothing while a laptop sleeps
(`sidecar/services/nse_bhavcopy.py:330` `_fetch_day(day)` already fetches any past date). This is the
honest local-first answer to "a laptop that sleeps" — no hosted backend, no missed days.

Scene numbers below are **illustrative**. Real small-cap names are used as the subject of neutral
checks (several are in the R15 battery so the demos run against packs that already exist); nothing
here alleges anything about any named company.

World-claim honesty: this session's WebSearch budget was exhausted (200/200), so I made one direct
primary fetch only. Verified: Telegram Desktop chat export — "you'll get all your data accessible
offline in JSON-format or in beautifully formatted HTML" (https://telegram.org/blog/export-and-more,
27 Aug 2018). Marked `[UNVERIFIED-IN-SESSION]` wherever a world fact comes from my memory and must be
confirmed at build time. Census evidence is cited by file.

---

## retail-1 — Tip Ledger ("drop your Telegram export; here is the truth about the channel you trust")

**NOT on the floor list.**

**User moment.** Aarav follows "Multibagger Kings" (41k members). Nine holdings came from it. He
exports the channel from Telegram Desktop (JSON), drops `result.json` onto Vysted. Ninety seconds
later: *"I found 63 buy calls in 14 months. I could resolve 58 to a listed instrument. Median call:
up 11% at day 3, down 24% at day 60. 39 of 58 were BSE group X or SME names. In 31 of 58 the stock
had already risen more than 15% in the five sessions BEFORE the message — someone was in before you
were told. 5 calls I could not resolve; they are listed, not scored. Channels delete their losers,
so treat this as the flattering version."* Then the line that matters to him: *"You hold 6 of these
58. Here they are."* Tap a row → the original message text, the resolved instrument, and the
exchange's bhavcopy row for the message date and for day 60.

From then on he pastes any new tip ("BUY JUMBO BAG CMP 62 TGT 140 SL 51 — big export order coming")
and gets the same autopsy on one name, the tip is **frozen into the ledger** with the price at that
moment (so a later delete cannot erase it), and Jarvis offers: *"Don't buy it. Shadow it."* — a
phantom position in a "Tip shadow" portfolio. Sixty days later Jarvis comes back unprompted with the
result, and the channel's running score.

**Mechanics.**
- *Ingest:* a plain `<input type="file">` + paste box (the composer has no attachment surface today —
  `src/modules/chat/ComposerPlusMenu.tsx` has none). No Tauri config change (`dragDropEnabled:false`
  is Tier-1 and stays).
- *Extraction, regex-first:* Indian tip messages are formulaic (`CMP`, `TGT`/`TARGET`, `SL`,
  `BUY`/`ACCUMULATE`, `$`/`#` tickers). Deterministic parse handles the bulk; an LLM pass (BYOK, or
  the local lane) only for the residue. In regex-only mode the chat export never leaves the machine.
- *Resolution:* the existing resolver with its confidence bands, rename-following and enrichment —
  `sidecar/services/symbol_resolver.py:652` `resolve`, `:827` `_annotate_renamed_symbols`, the
  rename lane `sidecar/services/nse_symbol_change.py` (tips use old names; battery P10
  SEQUENT→VIYASH is exactly this). Below-band matches are listed as "unresolved", never scored.
  Agent-side this is catalog `resolve_symbol` (`sidecar/services/agent_tools/catalog.py:170`).
- *Outcome backfill:* one history fetch per distinct symbol — `sidecar/services/nse_provider.py:455`
  `get_history`, `sidecar/services/bse_provider.py:377` `get_history` (BSE-only names are where tips
  live). Corporate-action adjustment from `nse_provider.py:617` `get_corporate_actions` — without it
  a bonus reads as a crash (battery P14 JONJUA 7:24 bonus is the trap).
- *Front-run fingerprint:* pure arithmetic on the same series — return over sessions t-5..t-1, volume
  vs 20-session median (`BhavRow.volume`, `nse_bhavcopy.py:129`).
- *Claims become checks:* "big export order coming" is stored as a falsifiable claim against the
  symbol; the announcements feed (`sidecar/services/corporate_disclosures.py:265`) is checked for it
  at 30/60/90 days. This is the floor list's thesis-vs-filings idea, re-aimed at a user who has no
  thesis of his own: **the tipster's thesis is the one on trial.**
- *Shadow portfolio:* zero new storage — a named portfolio in the existing multi-portfolio store
  (`src/store/portfolios.ts:33`), added through the gated `portfolio_add_position`
  (`catalog.py:1309`, diff/accept via `src/store/proposed-changes.ts`). It is a tracking ledger, not
  an order (`sidecar/services/agent_runtime.py:165-166` already says so to the model).
- *New:* a `tips` SQLite store in the sidecar data dir (source, message ts, raw text, resolved
  instrument + band, price-at-tip, claims, outcome checkpoints); a Tip Ledger panel; a wake-time
  checkpoint job; one preamble line ("this symbol came from source X, record 2/11") beside the
  existing prior-values precedent (`agent_runtime.py:344`).

**Why it is Jarvis.** Memory (it remembers what you were told, including what the channel later
deleted), watching (it returns at day 60 without being asked), receipts (the message + the exchange
row), initiative ("you hold 6 of these").

**60-second demo.** Drop a real exported tip channel. Table fills live. Sort by "rose before the
message". Click one: message on the left, price path with the message timestamp marked on the right,
bhavcopy row as the receipt. Paste a new tip; it lands in the ledger; "shadow it" → proposed change →
accept. Cut to a seeded ledger 60 days on: notification "Your 12 Aug tip: −31%. Channel is now 2/12."

**Lifecycle cost.** Telegram's export format has been stable since 2018; low. Price-history lanes
already rot-managed (`provider_health.py`, per-path NSE breakers). The ledger grows by a few rows a
week — bounded trivially. Real cost: corporate-action adjustment correctness, forever.

**Biggest risk.** A wrong resolve produces a confident wrong verdict about a *source the user
trusts* — the most damaging possible error for this product. Mitigation is structural: band-gated
scoring, unresolved listed not guessed, every scored row shows its receipts and is user-correctable,
and the survivorship caveat is printed on the scorecard, not buried. Second risk: legal tone — the
scorecard must state arithmetic ("median day-60 return"), never adjectives ("scam").

**Size.** M.

---

## retail-2 — Operator Radar (the exchange's own fingerprints, on your nine stocks, caught up on wake)

**NOT on the floor list** (the floor names pledge / deals / results-day; this is price-volume-series
forensics against a *silent* filings feed).

**User moment.** Aarav opens the laptop after four days. Before he types: *"Vertex Securities
(BSE:VERTEX): up 38% across the 4 sessions you were away, volume 9× its 20-day median, zero exchange
filings in that window, three closes locked at the upper band, and on 17 Sep the exchange moved it
to a trade-for-trade series. That combination is the shape of a stock being moved, not a stock with
news. Receipts: 4 bhavcopy rows, the empty announcements window, the series change."* No verdict, no
advice — a shape, and the rows. (Both lanes already parse the series code: NSE
`nse_bhavcopy.py:132`, BSE `bse_provider.py:238` — nothing reads a *change* in it today.)

**Mechanics.**
- The market-wide EOD ingest already exists and already loops: `sidecar/services/fundamentals_warm.py:298`
  `_bhavcopy_loop` (6h, `:52`), `:251` `bhavcopy_refresh_once`; each day's parsed rows are cached 7
  days (`nse_bhavcopy.py:100-101`). `BhavRow` already carries `series` (`nse_bhavcopy.py:132`) — an
  EQ→BE/BZ migration is a surveillance action sitting unread in data the app already parses.
- *Catch-up:* on wake, compute missing sessions since the last ingest and call `_fetch_day`
  (`nse_bhavcopy.py:330`) per day under the existing 0.75 s throttle (`:120`). BSE names ride
  `bse_provider.py:274` `_bhavcopy_for(day)`.
- *Rules are deterministic, no LLM:* (a) series migration; (b) N consecutive closes where
  close==high and change ≈ a band step (5/10/20%); (c) volume > k× 20-session median; (d) price
  +X% over 10 sessions **and** zero rows from `corporate_disclosures.get_announcements` (`:265`) in
  the window — the join nobody does: *movement with no filing*; (e) delivery collapse while price
  rises. The LLM only narrates rows that fired.
- *New:* a compact per-symbol ring (60 sessions × {close, volume, series, high, low, deliv%}) in
  SQLite for holdings + watchlist only; delivery parsing from the security-wise full bhavcopy the
  module already knows as a fallback (`nse_bhavcopy.py:22` "extra DELIV columns", URL at `:95`) —
  `BhavRow` has no delivery field today (`:124-132`); SME series are dropped today (`:98`, `:40`) and
  must be admitted for *watched* symbols since tips live there; `POST /watch/sweep {symbols, since}`
  called by the frontend on boot/focus; an ASM/GSM/ESM list lane `[UNVERIFIED-IN-SESSION: the
  exchanges publish these lists; endpoint shape to be confirmed — no surveillance, bulk/block-deal or
  price-band code exists in `nse_provider.py`/`bse_provider.py` today, grep-verified]`.

**Why it is Jarvis.** Watching and initiative, with receipts that are the exchange's own files. It
speaks first, and only when a rule fired.

**60-second demo.** Seed four sessions of archive rows for a watched name with the pattern; "open
the lid" (relaunch). The radar card is the first thing on screen; expand → four bhavcopy rows, an
announcements window showing 0 items, the series flip. Then a clean holding: "nothing fired" in one
quiet line — silence is part of the demo.

**Lifecycle cost.** NSE has already changed the bhavcopy format once (UDiFF, ~July 2024 per the
module docstring). When it changes again the radar goes blind — so "last successful ingest: N
sessions ago" must be a visible state, fed by `provider_health`, never a silent empty. BSE delivery
data lane is unknown `[UNVERIFIED-IN-SESSION]`. Holiday table upkeep already exists
(`sidecar/services/locale.py`).

**Biggest risk.** False positives on genuinely re-rating small caps would teach a nervous user to
sell winners. The wording discipline is the product: "shape", thresholds shown, rule names shown,
never "manipulated".

**Size.** M (S for series + circuit + volume-vs-silent-filings on NSE; delivery + SME + BSE make it M).

---

## retail-3 — Exit Door ("if this goes wrong, can I actually get out?")

**NOT on the floor list.**

**User moment.** Aarav holds ₹85,000 of Toss The Coin (BSE SME). Portfolio row shows a small door
glyph, amber. Hover: *"Lot size 1,200. You hold 2 lots. Median 3 lots traded per session over the
last 20 sessions; on 7 sessions nothing traded. At 10% of volume it takes ~7 sessions to exit. In
March this stock closed locked at the lower band 6 sessions running — on those days there were no
buyers at any price."* His Tata Power row shows a green door: "0.0004% of a day's volume."

Nobody tells a beginner that an illiquid small cap is a room with a door that sometimes disappears.
This is the single number that would have stopped most tip-driven losses, and no tool in the census
ships it.

**Mechanics.** Rides the same per-symbol ring as retail-2 (volume `nse_bhavcopy.py:129`, BSE lane
`bse_provider.py:274`), joined to holdings (`src/store/portfolios.ts:23`) or Kite holdings
(`sidecar/models/broker_reads.py:77-87` via `sidecar/routers/brokers.py:225-231`, GET-only). Pure
arithmetic: days-to-exit = qty ÷ (participation × median traded [delivered, when retail-2 lands
it]); zero-volume session count; longest lower-band lock streak. *New:* the calc, a glyph column in
`src/modules/portfolio/PortfolioPanel.tsx`, an SME lot-size source `[UNVERIFIED-IN-SESSION: lot size
is not in any bundled master today]`, and one agent read capability so "can I get out of X?" is
answerable (`catalog.py`, `kind="read_handler"` — auto-projects per CLAUDE.md).

**Why it is Jarvis.** Initiative — it answers the question he did not know to ask — and receipts
(the zero-volume sessions are listed by date).

**60-second demo.** Portfolio with one SME name and one large cap. Two doors, two colours. Click the
amber one: the 20-session volume strip with empty days visible, the lock streak highlighted on the
chart (`set_chart_symbol`, `catalog.py:983`).

**Lifecycle cost.** Near zero beyond retail-2's ingest. Lot sizes change with SME price revisions —
a stale lot size must degrade to "lot size unknown", never a wrong count.

**Biggest risk.** Reads as a sell signal. It is a property of the room, not a view on the stock —
copy must say so.

**Size.** S (given retail-2's ring), M standalone.

---

## retail-4 — "I noticed you bought" (a decision journal written from holdings diffs)

**NOT on the floor list.**

**User moment.** Monday, Aarav reconnects Kite. Jarvis: *"Since Thursday: you bought 140 Dynamic
Archistructures at ₹212 and added 30 Tata Power. One line each — why?"* He types "telegram said
infra order". Jarvis files it and freezes the world as it was: price, market cap, P/E with its basis
note, promoter %, the Exit Door reading, any radar flags, the tip-ledger link. Six months later:
*"Your 14 decisions this year. The 5 you could give a reason for: +9%. The 9 you bought because
someone said so: −22%. Your best decision had the longest reason."* The receipts are about **him**.

**Mechanics.** Read-only diff of successive holdings snapshots — `GET /brokers/{id}/holdings`
(`routers/brokers.py:225-231`; `BrokerHolding` `models/broker_reads.py:77-87`); manual portfolios
(`src/store/portfolios.ts`) are the same diff source without a broker. The frozen state reuses the
deterministic claims extractor (`src/lib/brief-claims.ts:46` `extractBriefClaims`, claim shape
`types/research-space.ts:35-44`). The "why" lands in the per-symbol note
(`src/store/notes.ts:31` `appendSymbolNote`) via gated `write_note` (`catalog.py:1374`). *New:* a
`holdings_snapshots` + `decisions` store, the diff, the ask-card, a yearly review brief published
through `publish_brief` (`catalog.py:1177`). Touches no order surface: GET-only, no §6.5 ABC change,
no `place_/submit_/execute_` names (`catalog.py:1483`).

**Why it is Jarvis.** Watching (it notices an action taken outside the app), memory (the reason and
the world, frozen), initiative (it asks).

**60-second demo.** Two seeded snapshots a week apart. Launch: the ask-card appears for the new name.
Type a reason. Open the decision: frozen metric cards dated that day beside today's. Jump to the
review brief.

**Lifecycle cost.** Kite's token dies daily (~6 am IST, `docs/CURRENT_STATE.md` §3.5), so snapshots
are irregular — the diff must tolerate gaps and corporate actions (a bonus is not a "buy"; reuse
`nse_provider.py:617`). Snapshot rows: bounded, tiny.

**Biggest risk.** Nagging. One card per new name, dismissible forever per symbol, never blocking.

**Size.** M.

---

## retail-5 — Calm Protocol (red-day triage + the rules you wrote when you were calm)

**NOT on the floor list.**

**User moment.** 11:40, a holding is −9.2%. Notification: *"Jumbo Bag −9.2%. I checked five things
in the last minute. No exchange filing today. Packaging peers: 6 of 8 down, median −5.1%. Smallcap
index −3.4%. Volume 1.3× normal — not a stampede. No radar rule fired. This looks like the market,
not the company. On 12 Aug you wrote: 'I don't sell on a market-wide fall unless a filing changes
the story.' No filing changed the story."* The other branch is just as fast: *"Filing at 14:32 —
'Resignation of Statutory Auditor' [PDF p.1]. This is company-specific. Your rule says: read the
filing first. Here it is."*

**Mechanics.** Trigger: a held symbol's day change crosses a threshold during the watchlist's
existing quote poll (5 s, `docs/CURRENT_STATE.md` §3.9). Triage is a **fixed checklist run as tool
calls, not free reasoning**: `corporate_announcements` (`catalog.py:655`), sector peers from the
India-wide store (`sidecar/services/fundamentals_store.py:561` `query` + the sector map
`symbol_resolver.py:306`), `market_overview` (`catalog.py:262`), the radar ring. Delivery rides the
existing notification bridge (`src/lib/desktop-notification.ts`; sidecar node
`sidecar/services/workflow_nodes/builtin.py:325`), generalised from workflow-only intents. The rules
are a short typed list captured in onboarding for this persona (`src/store/onboarding.ts`) and
persisted in the workspace blob (the four-call-site rule in CLAUDE.md applies). *New:* the trigger,
the checklist runner, the rules field, the card.

**Why it is Jarvis.** Initiative at the exact moment a human is worst at thinking; memory of his own
words; receipts for both branches.

**60-second demo.** Force a −9% quote on a held name with a seeded peer set. Notification fires, card
shows five ticked checks each with its receipt, his own rule quoted with its date. Flip the fixture to
include an auditor-resignation filing: the card changes branch and opens the PDF.

**Lifecycle cost.** Only works while the app is open (no daemon) — must be stated, not hidden; the
wake brief (retail-8) covers the rest. Sector map staleness (`resolver_masters`) mislabels peers over
time.

**Biggest risk.** A "looks like the market" read on the day the filing lands 20 minutes later. The
card must carry its check time and re-run on the next announcements TTL (15 min,
`sidecar/routers/disclosures.py:39`).

**Size.** M.

---

## retail-6 — The Crowd Arrived (distribution detector from the shareholding filing)

**NOT on the floor list.**

**User moment.** *"Icon Facilitators: retail shareholders went from 3,100 to 27,400 in two quarters.
Over the same two quarters promoters went 71.2% → 63.9% and large non-institutional holders fell
4.1 points. You are one of roughly 24,000 people who arrived while the people who knew the company
best were leaving. Receipts: three quarterly XBRL filings."* This is the quietest and most damning
picture of a distribution phase, it is filed with the exchange every quarter, and no retail tool
draws it.

**Mechanics.** The SHP lane already fetches and parses BSE SEBI XBRL per quarter
(`sidecar/services/bse_provider.py:612` `get_shareholding`, `:694` `parse_shp_xbrl`) but reads only
the percentage concept (`:594` `_SHP_PCT_CONCEPT`); `ShareholdingPattern` has no holder-count field
(`sidecar/models/announcements.py:82-138`) and the XBRL link already rides each row (`:124`).
*New:* parse the per-category shareholder-count facts `[UNVERIFIED-IN-SESSION: concept name to be
read off a real filing]`, add optional fields (mirror in `types/` same commit), one rule, one card on
the ownership section, and surface through the existing `shareholding_pattern` capability
(`catalog.py:686`). The 4-quarter promoter/pledge *derivative* the census calls for
(`census/world/fey-tijori-trendlyne.md` O-7) drops into the same card.

**Why it is Jarvis.** Watching (quarterly, on wake) and receipts (three filings, linked).

**60-second demo.** A name with a holder-count jump: one chart, two lines crossing — holders up,
promoter down — three filing links under it.

**Lifecycle cost.** XBRL taxonomy revisions (SEBI has revised SHP formats before
`[UNVERIFIED-IN-SESSION]`) break the parse → must degrade to "count unavailable", which the
never-fabricate discipline in `announcements.py:85-88` already models. NSE-only names have no count
unless dual-listed.

**Biggest risk.** A successful IPO/re-rating also grows holders. The rule needs the *conjunction*
(holders up AND insiders down), and must show both legs.

**Size.** S–M.

---

## retail-7 — Seven Pages (the annual report, read with you, every sentence pinned to a page)

Floor-adjacent (receipts, related-party) — the seat twist is *guided reading for someone who has
never opened one*, plus memory of what he has already learned.

**User moment.** *"Viyash Scientific's annual report is 236 pages. A professional reads about seven
first. 1) p.88 — the auditor's opinion: clean, but one Key Audit Matter on receivables. 2) p.141 —
related-party transactions: ₹46 cr of purchases from a promoter entity, up from ₹12 cr. 3) p.163 —
contingent liabilities: ₹31 cr of disputed tax, 14% of net worth. …"* Each line opens the PDF at
that page. A term he has not met ("contingent liability") gets one sentence, using his own stock;
next time it does not.

**Mechanics.** The PDF lane already tracks which pages it used — `sidecar/services/search/extract.py:506`
`pages_used`, returned at `:534` — and honestly reports scanned pages (`:398`). It is capped for
results filings: 60 pages (`:65`), 15 MB (`:51`), 6 kept (`:68`). *New:* an annual-report mode that
finds sections by heading (Independent Auditor's Report / Key Audit Matters / CARO / Related Party /
Contingent Liabilities / Managerial Remuneration / Cash Flow) across the whole document and keeps
**page numbers per extracted paragraph**; an AR locator `[UNVERIFIED-IN-SESSION: BSE serves annual
reports per scrip; endpoint to confirm]`; page receipts as `url#page=N` opened via the already-granted
shell `open`; a `learnedTerms` map in the workspace blob; a DEEP-tier run so it survives a closed
chat (`sidecar/services/run_manager.py:237` `launch_run`, budget-guarded). Every quoted figure goes
through the existing citation-integrity pass (`sidecar/services/research/citecheck.py`).

**Why it is Jarvis.** Receipts at page grain; memory of the user's own vocabulary.

**60-second demo.** "Read the annual report with me." Seven cards stream in. Click card 2: the PDF
opens on p.141. Hover "related party": one-line explanation. Ask again on another stock: no
explanation — it remembers.

**Lifecycle cost.** Scanned/image reports (common in micro-caps) defeat text extraction — the
existing scanned-pages note must become "I can read 3 of your 7 pages; here is why". Token cost per
report is real on BYOK; BudgetGuard already meters it.

**Biggest risk.** A page number that is off by one destroys the receipt's credibility — PDF page
index vs printed folio. Always cite the PDF index the link opens, and verify the quoted string is on
that page before emitting.

**Size.** M.

---

## retail-8 — While You Were Away (the app opens to a brief, not a blank composer)

Floor item (signals stitched to holdings), done the way a sleeping laptop demands, and the delivery
surface for retail-1/2/4/5/6.

**User moment.** Lid opens after a long weekend. *"4 days, 9 holdings, 11 exchange filings. Ten are
routine (newspaper ads, trading-window closures, a duplicate share certificate). One matters: Tata
Power board meets 24 Sep to consider results — your first results day as a holder; I'll prep you the
evening before. Also: your 12 Aug tip hit its 30-day mark (−14%), and one radar flag (details)."*

**Mechanics.** A per-symbol last-seen cursor in the workspace blob (none exists today —
grep-verified). On boot/focus the frontend requests announcements per holding
(`sidecar/routers/disclosures.py:44`, 15-min TTL `:39`), keeps `ts > cursor`
(`sidecar/models/announcements.py:41`), and triages **deterministically first** — the research lane
already owns results/presentation headline regexes (`sidecar/services/research/disclosures.py:50,61`)
and the results calendar (`:185`, which census TS-5 notes has no UI surface). The LLM writes one
line only for items that survive the routine filter. Empty-state chips
(`src/modules/chat/SuggestionChips.tsx:29`) are replaced by the brief when there is one. *New:* the
cursor, the routine-filing classifier, the brief card, the "prep me the evening before" scheduled
intent (wake-driven: fires on the first open inside the window).

**Why it is Jarvis.** Initiative and watching, honestly bounded by when the machine was awake.

**60-second demo.** Set the cursor back 5 days on a populated portfolio; relaunch. The brief renders
before any input; "10 routine" expands to show it really did read them; the one that matters opens
its PDF.

**Lifecycle cost.** The BSE announcements window is 30 days (`corporate_disclosures.py:88`) and the
feed limit is 50 (`:71`) — an absence longer than that silently loses BSE items unless the brief says
"I can only see back 30 days on BSE". Exchange category labels drift; the routine filter needs a
visible "unclassified" bucket rather than guessing.

**Biggest risk.** Filing a material item under "routine". Bias the filter to over-surface, and show
the routine list collapsed, never hidden.

**Size.** S–M.

---

## Strongest idea: retail-1, the Tip Ledger

It is the only idea here that attacks the *cause* of this user's losses rather than their symptoms.
Everything else protects him after he has bought; this one changes who he listens to. And the demo
is visceral in a way no metric card is: he watches the channel he trusts get arithmetic done to it,
with the exchange's rows as receipts, in ninety seconds, on his own laptop.

Why a rival cannot copy it in a month:

1. **It only works local-first.** A hosted product would have to ingest users' private chat exports
   and would, in effect, be publishing performance records of named tipsters — a privacy problem and
   a defamation/regulatory one. A local tool doing private arithmetic for one user publishes nothing.
   Vysted's architecture is the permission slip.
2. **Tips live exactly where rivals' data breaks.** BSE group X, SME, renamed, freshly listed,
   ticker-colliding names — the R15 battery is a list of them (P2 DAL resolves to Delta Air Lines on
   the open web; P10 SEQUENT→VIYASH). The resolver bands, rename lane, exchange-direct history and
   corporate-action handling took R11–R15 to harden; a scorecard built on a vendor feed will score
   the wrong company and not know it. The census already records the benchmark misreading small-cap
   filings by ×1000 (`census/world/perplexity-screener.md` B1).
3. **It needs watching, and the benchmark "answers, it does not watch"** (same file, B3). The day-60
   return requires something that comes back at day 60.
4. **The value is the user's own accumulating memory** — including what channels later delete. It
   compounds monthly and cannot be exported to a competitor.
5. **Incentives.** The India incumbents are attached to broking distribution
   (`census/world/fey-tijori-trendlyne.md` O-1). A feature whose headline output is "don't act on
   this" is one they are structurally unlikely to ship.

Build order if only three ship: retail-1, retail-2 (whose ring also powers retail-3), retail-8 (the
surface the other two speak through).
