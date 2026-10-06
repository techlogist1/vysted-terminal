# R15 Stage 4 — Ideation seat: `bloomberg`

**Seat:** a Bloomberg Terminal power user of 15 years — buy-side PM, lives in functions,
launchpad, alerts, MSG; knows exactly what a terminal must do before it earns desk space, and
exactly what Bloomberg itself still cannot do (`tooling/launch-args/ideate-A.json:13-15`).
**Model:** `claude-sonnet-5`. **Date:** 2026-09-23. **Mode:** read-only structural derivation,
nothing built, no new ideas.

## Provenance note (read this before the ideas)

This file did not run a fresh ideation pass. Per `PROMPT_offmachine_s2.md` §5 (`bloomberg-md`),
`docs/redesign/verification/r15/invent/ideas/bloomberg.json` already existed with no matching
`.md`; this file restructures that JSON into the same prose shape the other seats' `.md` files
use (name / user moment / mechanics / why Jarvis / 60-second demo / lifecycle cost / biggest
risk / size, plus a closing strongest-idea paragraph). Every `file:line` citation below is
carried verbatim from the JSON's `rides_on` / `new_parts` fields, written by the original
`bloomberg` seat pass on 2026-09-19 — none were reopened or re-verified this session. Every
"user moment" scene is a direct dramatisation of that idea's own `one_liner`; no mechanic, risk
or dependency appears here that is not already a field in `bloomberg.json`. Hard constraints
repeated from the original IDEATE brief and assumed throughout: lives inside the existing design
system and plugin contract, never touches the order-safety surface, never requires a hosted
backend (local-first, BYOK), buildable on top of code that already exists.

---

## bloomberg-1 · TAPE — the wake sweep · on the floor

**User moment.** Lid opens after a weekend. Before any chat, before any panel is touched, one
ranked line greets the desk: a "since you were last here" tape over every holding and watchlist
name, each line weighted by its share of the book, each carrying its filing receipt — the
Bloomberg launchpad reflex, rebuilt around exchange feeds instead of a newswire firehose.

**Mechanics.** A watermark-cursor sweep over corporate disclosures and actions already fetched by
the app — `sidecar/services/corporate_disclosures.py:265` `get_announcements` (BSE+NSE merged,
with `attachment_url`), `:335` `get_results_calendar`, `:366` `get_shareholding`, and
`sidecar/services/nse_provider.py:617` `get_corporate_actions` — run on the same background-loop
pattern as `sidecar/services/fundamentals_warm.py:191` `_sweep_loop` (lifespan-managed at
`sidecar/app.py:127-134`). It posts through the existing desktop-notification bridge
(`src/lib/desktop-notification.ts:72` `useDesktopNotificationBridge`, mounted at
`src/app/page.tsx:43`) and reads the book/watchlist from the terminal snapshot
(`src/modules/chat/context-provider.ts:217` `captureTerminalState`). New: an append-only SQLite
store with a per-(symbol, feed) cursor, row cap and age vacuum
(`sidecar/services/tape_store.py`); `POST /tape/sweep {symbols, weights, since?}` + `GET /tape`;
a deterministic category/headline classifier table with **no LLM** in the sweep; a Tape panel
(`PanelSpec`) plus a `tape_since` `read_handler` capability in `catalog.py`; a frontend trigger on
boot, `visibilitychange`, and every N minutes since the last sweep.

**Why Jarvis.** Initiative, watching, receipts: the tape is there before the user asks, it is
built from exchange feeds the app already reaches, and every line opens onto its filing.

**60-second demo.** Boot the panel with a seeded fixture spanning two feeds: the tape renders
ranked, weighted lines with a coverage badge per feed, and clicking any line opens the underlying
filing.

**Lifecycle cost.** Exchange feed shape drift or IP throttling can quietly thin what the sweep
picks up over time, with no visible symptom unless the app says so.

**Biggest risk.** A thinned or throttled sweep must never read as "nothing happened" — every tape
render shows per-feed coverage (e.g. "NSE ok, BSE failed") rather than silently going quiet.

**Size.** M.

---

## bloomberg-2 · EXIT DOOR — can I actually get out · NOT on the floor

**User moment.** A position screen carries a number Bloomberg LQA never gives you for an Indian
small-cap: days-to-exit at a stated participation rate, computed from real delivery volume — plus
an immediate alert the day a holding flips from EQ to BE/BZ (trade-for-trade) or starts locking at
circuit.

**Mechanics.** Built on data the sidecar already parses: `sidecar/services/nse_bhavcopy.py:124-133`
`BhavRow` already carries series and volume, `:98` defines `EQUITY_SERIES = EQ/BE/BZ`, and `:22`
notes the fallback `sec_bhavdata_full` file carries `DELIV` columns that are documented but not
yet parsed; the 6-hour refresh loop already runs at
`sidecar/services/fundamentals_warm.py:298` `_bhavcopy_loop`. It surfaces through the existing
book-metrics seam (`src/modules/portfolio/metrics.ts`). New: a rolling 20-session per-symbol
rollup (volume, `deliv_qty`, series, hi==lo/limit-lock flag); a `liquidity_profile` `read_handler`
capability plus a portfolio column/badge; series-flip and circuit-lock tape events; ASM/GSM list
ingestion only if a stable public file is confirmed at build time (unverified this session).

**Why Jarvis.** Watching and initiative — it flags a liquidity state change the moment it happens,
not when the user thinks to check.

**60-second demo.** Load a book with one BE-series name: the days-to-exit column shows the
degraded basis, and a series-flip fixture event fires a tape line the instant it is swept.

**Lifecycle cost.** Delivery data lives only in the fallback host; if `archives.nseindia.com`
blocks it, the feature loses its primary input over time, and BSE-only names never had an NSE
bhavcopy row to begin with.

**Biggest risk.** If the fallback host blocks, days-to-exit must degrade to a total-volume basis
and say so explicitly rather than showing a stale or misleading number; BSE-only names must be
shown as unsupported, not silently omitted.

**Size.** M.

---

## bloomberg-3 · THE NUMBER CHANGED — revision witness · NOT on the floor

**User moment.** A figure on screen today does not match what it showed last month, and no filing
in the disclosure feed explains it. Jarvis says which source drifted, shows exactly what was
displayed then, and links the filing that should have governed — a revision-history function no
current Vysted view has.

**Mechanics.** The single write choke point for fundamentals is
`sidecar/services/fundamentals_store.py:473-497` `_upsert_sql`/`_upsert`, which today does
`ON CONFLICT DO UPDATE` and overwrites (one row per symbol, `:123`); each field already carries
provenance via `sidecar/models/fundamentals.py:19` `FieldMeta` (provider + `as_of`). A change can
be cross-checked against whether a filing occurred between two observations
(`corporate_disclosures.py:265`/`:335`) or a split/bonus explains a share-count step
(`nse_provider.py:617` `get_corporate_actions`), following the same flag-never-silently-pick
discipline already used in `earnings_quality.py`, `market_cap_witness.py` and
`ownership_check.py`. It renders through `src/lib/brief-claims.ts` and
`sidecar/services/agent_runtime.py:344` `_render_prior_stated_values` (what the agent already
told the user). New: a `facts_history` table (symbol, field, value, provider, `as_of`,
`observed_at`) written only on material change and capped per symbol; a change classifier
(filing-explained / corporate-action / basis-flip / unexplained provider drift); a statement
period-hash to catch restated past periods; an "as you saw it on `<date>`" chip in `BriefBody`
plus a tape event and agent-preamble line.

**Why Jarvis.** Memory, watching and receipts together — it remembers what the user was shown and
says, with evidence, whether the world moved or the data did.

**60-second demo.** Swap a fixture field's value with no accompanying filing: the chip fires
"as you saw it on `<date>`" with the two observations and a link to what — if anything — should
have explained it.

**Lifecycle cost.** Provider values flap on rounding and currency-basis noise as a matter of
course, so the underlying data feed is a permanent source of low-grade drift the feature has to
absorb rather than eliminate.

**Biggest risk.** False alarms destroy exactly the trust this sells; v1 must whitelist
filing-anchored fields only and require two consecutive confirming observations before it speaks.

**Size.** M.

---

## bloomberg-4 · PRE-PRINT CARD and PRINT GRADE · partly on the floor (guidance-vs-delivery is floor; the pre-commit and calibration record are not)

**User moment.** The evening before a holding reports, Jarvis lays out what management guided —
verbatim quotes with page receipts — and asks the user to write their own three numbers. When the
results PDF lands, it grades print against guidance against the user's own forecast, and keeps a
running calibration record across quarters.

**Mechanics.** Triggered off `sidecar/services/corporate_disclosures.py:335`
`get_results_calendar`, drawing announcement-to-PDF citations from
`sidecar/services/research/disclosures.py`, and extracting guidance text via
`sidecar/services/search/extract.py:436` `extract_pdf_text` (with `:506` `pages_used` and `:398`
`scanned_pages_note` already honest about image-only tables). Publishes through
`sidecar/services/agent_tools/catalog.py:1177` `publish_brief` and the typed blocks in
`src/modules/research/brief-blocks.tsx`, and can arrange a results-day desk via `catalog.py:1115`
`arrange_layout` and `src/lib/layout-templates.ts:402` `fitLayoutTemplate`. The guidance
extraction itself runs as a bounded durable run
(`sidecar/services/run_manager.py:237` `launch_run` + `sidecar/services/budget_guard.py:87`
`BudgetGuard`). New: an append-only expectations store, frozen once the results-announcement
timestamp exists; a guidance extractor whose every quote must be a verbatim substring of a cited
page (deterministic check, else dropped); a grade block type in `brief-blocks` (print / guided /
yours / delta); a calibration view across quarters.

**Why Jarvis.** Initiative, memory and receipts — it makes the user commit before results land and
then holds both management and the user to what was said.

**60-second demo.** Seed a results-calendar fixture one day out: the pre-print card shows guidance
quotes with page numbers, the user enters three numbers, and swapping in the results PDF renders
the grade block with print / guided / yours / delta.

**Lifecycle cost.** Small-cap results PDFs are frequently scanned images, so the print column will
routinely land on "unparsed — enter manually, see p.N" rather than an extracted figure.

**Biggest risk.** That degraded state has to be a designed, visible outcome — not treated or shown
as a failure of the feature.

**Size.** L.

---

## bloomberg-5 · MANDATE — your own compliance officer · NOT on the floor

**User moment.** A plain-text investment policy the user owns — max position, sector cap, minimum
exit-ability, pledge ceiling, no averaging down without re-underwriting — compiled to rules and
checked against every portfolio change, every drift, and every suggestion the agent itself makes.
It annotates. It never blocks. It never touches an order.

**Mechanics.** The policy lives as a scoped note in the workspace blob
(`src/store/notes.ts:8-33`), written via `sidecar/services/agent_tools/catalog.py:1374`
`write_note`. Compilation reuses the existing no-`eval` expression grammar
(`sidecar/services/screener_formula.py:441` `compile_formula` / `:563` `evaluate_formula`, TS
twin in `src/lib/screener-expr.ts`). Every mutation it can annotate already passes through the
diff/accept gate (`src/store/proposed-changes.ts:64` `EnqueueInput`), reads the book from
`src/modules/chat/context-provider.ts:217` `captureTerminalState`, and is injected into the
agent's own self-check via `sidecar/services/agent_runtime.py:376`
`_render_terminal_preamble`. New: a book-level field resolver for the formula engine
(`position_weight`, `sector_weight`, `days_to_exit`, `promoter_pct`, …); a mandate compile step
(prose → rules) shown as a diff the user accepts; breach annotations on proposed-changes cards
plus tape events for drift breaches.

**Why Jarvis.** Memory and initiative — it holds the user to a policy they wrote once, across every
future action, without ever taking the action itself.

**60-second demo.** Write two policy sentences, accept the compiled-rule diff, then feed a
fixture position change that breaches sector cap: the proposed-changes card carries a breach
annotation and a matching tape event fires.

**Lifecycle cost.** None distinct from the rule engine it reuses; the compiled-rule set is the
only long-lived artifact, and it is regenerated from the same prose source whenever it drifts.

**Biggest risk.** The LLM mis-compiles prose into a rule the user never meant; the compiled rules
must be shown verbatim and user-accepted every time, with the prose staying the source of truth.

**Size.** S-M.

---

## bloomberg-6 · RED PEN — fact-check what people send you · NOT on the floor

**User moment.** A broker note, a WhatsApp forward, a forum post is pasted or dropped in. Every
numeric claim is pinned to its verbatim span, checked against the app's own sourced data and the
filings, and returned marked verified / contradicted / stale / unverifiable with receipts —
including the lakh-vs-crore trap that catches even careful readers.

**Mechanics.** A numeric verifier already exists for the app's own narrative text
(`sidecar/services/company_narrative.py:209` `_verify_text`, tolerances at `:49-50`, unverified
claims typed at `sidecar/models/fundamentals.py:185` `UnverifiedClaim`); RED PEN extends the same
discipline to arbitrary pasted text via the claim-vs-cited-source audit in
`sidecar/services/research/citecheck.py` and the independent-domain cross-check in
`sidecar/services/research/verify.py`, resolving tickers through
`sidecar/services/agent_tools/catalog.py:170` `resolve_symbol` and reading dropped PDFs through
`sidecar/services/search/extract.py:436` `extract_pdf_text`. New: a composer paste/drop intake
(none exists today) posting to `POST /redpen/check` (text or size-capped PDF bytes); claim
extraction with a mandatory verbatim-span check; a verdict table block, filed under the symbol's
note scope.

**Why Jarvis.** Receipts and memory — it turns something the user was going to half-trust on faith
into a sourced, filed verdict.

**60-second demo.** Paste a two-claim broker note: the verdict table returns one "verified" and
one "contradicted" line, each with the verbatim span, the app's own sourced figure, and the basis
compared.

**Lifecycle cost.** None beyond the verifier infrastructure it already rides on; the feature's
accuracy is bounded by how well `citecheck.py`/`verify.py` already generalise.

**Biggest risk.** A confident "contradicted" verdict on a basis mismatch (consolidated vs
standalone, TTM vs FY) is worse than silence; every verdict must name the basis it compared on,
and a mismatched basis reads as "not comparable," never "wrong."

**Size.** M.

---

## bloomberg-7 · ALRT WITH A TRACK RECORD · partly on the floor (signals are floor; the pre-arm dry-run is not)

**User moment.** Alerts written in plain English are compiled to a visible rule and dry-run
against the stored tape before arming: "this would have fired 3 times on your book — here they
are" — the noise rate Bloomberg's own ALRT function never shows the user before it starts firing.

**Mechanics.** Depends directly on bloomberg-1's `tape_store` for the event history the dry-run
replays, and reuses the same rule engine as bloomberg-5
(`sidecar/services/screener_formula.py:441`/`:563`). Persisting a user-authored rule follows the
same precedent as `sidecar/services/agent_tools/catalog.py:1416` `save_screen`, and firing rides
the already-wired OS notification path
(`sidecar/services/workflow_nodes/builtin.py:325` `action_notify_desktop` →
`src/store/workflow.ts:180` → `src/lib/desktop-notification.ts:72`). New: an alert rule store
plus a `create_alert` host action (through proposed-changes); a dry-run evaluator over tape
history that states its own honest depth (e.g. "history covers 41 days"); evaluation at sweep
time only — no cron, since cursors catch up on wake and a sleeping laptop misses nothing.

**Why Jarvis.** Watching, receipts and initiative — the rule is inspectable and tested against real
history before it is ever allowed to interrupt the user.

**60-second demo.** Write an alert sentence, dry-run it against a seeded tape showing three past
matches with receipts, then arm it and replay a fourth fixture event to see it fire.

**Lifecycle cost.** Dry-run depth is shallow on day one — the BSE announcements window is 30 days
(`corporate_disclosures.py:88`) — so the "track record" the dry-run shows only ever covers what
the tape has accumulated so far.

**Biggest risk.** If that depth is not stated plainly, the dry-run's "track record" becomes a false
comfort rather than an honest one.

**Size.** M (S once bloomberg-1 exists).

---

## bloomberg-8 · GO BAR and learned routines · NOT on the floor

**User moment.** Bloomberg muscle memory, rebuilt: `<TICKER> <FN>` parsed deterministically in
under 100 ms with no model involved, plus an agent that prints the mnemonic for what it just did
and notices the user's repeated morning sequence, offering to run it as one command next time.

**Mechanics.** Sits ahead of the existing fuzzy command-palette matcher
(`src/store/command-palette.ts:209` `buildPaletteCorpus` / `:321` `paletteFilter`), using the
same deterministic offline intent classifier already in the planner
(`sidecar/services/planner.py:167` `classify_intent`). Every function maps onto an existing host
action (`src/lib/host-actions.ts:880` `applyHostAction`), and a learned routine persists through
the existing workspace/workflow persistence path
(`src/lib/workspace.ts:541` `autosaveLayout` + the workflow store). New: a function table (SHP,
ANN, FA, RES, EXIT, TAPE, RP, …) with a ~40-line parser ahead of fuzzy match; a "next time:
`TANLA SHP`" hint line after agent turns that reduce to one function; a bounded host-action
history ring in the workspace blob plus a repeated-opener detector that offers "make this your
morning routine?".

**Why Jarvis.** Memory and initiative — it learns the user's own repeated pattern and offers to
compress it, rather than making the user re-teach the terminal every morning.

**60-second demo.** Type `TANLA SHP` in the command bar: it resolves in one deterministic parse
with a visible preview, and after three mornings of the same three-step sequence the terminal
offers to bind it to one routine.

**Lifecycle cost.** The function table is a small, versioned vocabulary; adding a function is a
data change, not a parser rewrite.

**Biggest risk.** Mnemonic collisions with real ticker symbols (an NSE symbol that reads like a
function code); a ticker-first grammar with the function in second position, plus a visible parse
preview, avoids a silent misroute.

**Size.** S-M.

---

## bloomberg-9 · KILL CRITERIA — the thesis that can be falsified · on the floor

**User moment.** Every position carries a thesis, the three KPIs that prove it, and the explicit
conditions under which the user sells. The view held at write time is frozen, and every sweep
tests the stated conditions against new filings; tripping one produces the exact page that
tripped it.

**Mechanics.** The thesis lives in the per-symbol note scope alongside the existing claims ledger
(`src/store/notes.ts` + `types/research-space.ts:34` `ResearchSpaceClaim`, capped at 50, `:86`),
using the same deterministic claim-capture path as `src/lib/brief-claims.ts` and
`sidecar/services/agent_runtime.py:344`. Evaluation rides bloomberg-1's sweep and bloomberg-5's
rule engine directly, with criteria such as promoter-trend read from
`sidecar/services/corporate_disclosures.py:366` `get_shareholding` and results conditions read
from results PDFs via `extract.py:436`. New: a thesis card (thesis / KPIs / kill criteria) as a
structured block inside the symbol note; a freeze-at-write snapshot (price, claims, sources) —
noting `Holding` has no opened-date field today (`src/store/portfolios.ts:23`); criteria
evaluation at sweep time with a "tripped" event carrying its receipt, plus a post-mortem on exit.

**Why Jarvis.** Memory, watching and receipts together — the thesis the user wrote is the thing
that later gets tested against reality, not a note that quietly ages out of relevance.

**60-second demo.** Write a thesis with one kill criterion tied to promoter shareholding, freeze
it, then feed a fixture shareholding update that breaches it: a "tripped" event fires with the
exact filing page attached.

**Lifecycle cost.** None distinct from the substrate it rides on (bloomberg-1's tape,
bloomberg-5's rule engine); its own footprint is one structured block per symbol note.

**Biggest risk.** Qualitative criteria ("management credibility breaks") cannot be evaluated
deterministically; those stay as prompts Jarvis raises for human judgement with the evidence
attached, and are never auto-tripped.

**Size.** M.

---

## Dependency shape (so the lead can sequence)

Per each idea's own `rides_on` field: bloomberg-1 (TAPE) is the substrate two other ideas name
directly — bloomberg-7's dry-run replays its `tape_store` event history, and bloomberg-9's sweep
evaluation rides it together with bloomberg-5's rule engine. bloomberg-5 (MANDATE) is itself a
dependency of bloomberg-9. bloomberg-2, -3, -4, -6 and -8 stand on existing sidecar/frontend
seams independently of the other bloomberg ideas.

## Single strongest idea: bloomberg-1, TAPE

It is the only idea in this set two others explicitly build on (bloomberg-7's dry-run, bloomberg-9's
kill-criteria sweep), which makes it the spine rather than one feature among nine. Its own
mechanics keep it cheap to keep alive: the classifier is deterministic and carries **no LLM**, so
watching a full book costs zero BYOK tokens on every sweep — the idea that turns "local-first on a
laptop that sleeps" (a hard constraint on every idea in this seat, not a limitation unique to this
one) from an apology into the reason the tape is the user's own, current, and free to run as often
as the terminal wakes. Everything else in this set that reads as Jarvis rather than a chatbot with
panels — the alert that has already been tested against history, the thesis that gets checked
against new filings without being asked — is that same tape, evaluated a different way.
