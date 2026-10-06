# R15 Stage 4 — ideation seat `designer`

Model: `claude-opus-5-5[1m]`. Date: 2026-09-23. Read-only thinking; nothing built.

Seat: a product designer from the Linear / Superhuman / early-Bloomberg school. Tools should be
boring, correct and fast: density without chrome, every pixel either data or a way to act on data.
I judge a finance app by three things: what it proves in the first minute, whether a number can
tell you where it came from without you leaving the screen, and whether the agent's features
feel **earned** (they save a step I would have taken anyway, and they show their work) or feel like
a **demo** (they perform for a screenshot).

## 0. What I found when I opened the app as a designer

**The moat is real, and it is hidden behind a model call.** The app has a family of deterministic
witnesses that catch providers being wrong. The ownership witness caught Yahoo overstating
institutional holdings about 141x on a BSE micro-cap (8.455% vs the BSE filing's 0.06%,
`sidecar/services/ownership_check.py:9-10`, reproduced live as BOMOXY / 509470 in
`docs/redesign/verification/R13_RUN_REPORT.md:25`). There are also growth, earnings-basis,
52-week-range and market-cap witnesses. Every one of them runs **only** inside
`snapshot_structured` (`sidecar/services/research/fast.py:261-402`), and that function's only
callers are research pipelines an LLM turn starts (`sidecar/services/agent_tools/deep_research.py:750`,
`sidecar/services/research/deep.py:1035`, `sidecar/services/research/iter.py:339,915`). The plain
company page does not use them. `EquityOverviewPanel` renders Yahoo's `held_percent_institutions`
row directly (`src/modules/equity-overview/EquityOverviewPanel.tsx:141-142`), and
`sidecar/routers/fundamentals.py` has no witness import (grep: zero hits). So a keyless user, the
user onboarding explicitly invites ("It already works — no key, no account.",
`src/components/OnboardingFlow.tsx:250`), is shown the 141x-wrong number as plain fact on the
screen they look at first. The one thing no rival has only appears if you pay for tokens and ask
the right question.

**Provenance exists but is a tooltip.** R13 gave every fundamentals field a `FieldMeta`
(`sidecar/models/fundamentals.py:19-43`). The overview renders it in two ways: an always-visible
chip for withheld or unavailable fields (`EquityOverviewPanel.tsx:190-201`), which is good, and a
native `title=` hover for served fields (`EquityOverviewPanel.tsx:208-221` through
`src/components/DataTable.tsx:84-85,156-170`). A `title` tooltip takes about a second to appear,
cannot be reached from the keyboard, cannot be copied and does not exist on other panels. The
watchlist and chart carry panel-level badges (`src/modules/watchlist/WatchlistPanel.tsx:74-75`,
`src/modules/chart/ChartPanel.tsx:1424`), not per-figure ones.

**First paint waits on Python.** The cockpit layout is stored inside the sidecar
(`sidecar/services/workspace_store.py:1-12`). `restoreLastSessionOrDefault` awaits
`getSidecarBaseUrl()` before placing a single panel (`src/lib/workspace.ts:374-376,494-500`,
called from `src/components/PanelHost.tsx:166`), and that probe allows up to 120 s
(`src/lib/sidecar-client.ts:114-138`). The PyInstaller cold bind plus the MCP join takes tens of
seconds (`src/lib/use-sidecar-retry.ts:6-10`). The first impression of a "fast terminal" is a wait.

**The agent is honest about the right things, but its receipts are thrown away.** Per-turn token
usage is captured (`src/store/chat-history.ts:46-47,213-216`) and never rendered (no component
reads `.usage`). Foreground spend is hard-coded to 0 (`src/modules/chat/ChatSidebar.tsx:914-922`).
History is silently cut to the last 10 messages (`ChatSidebar.tsx:749-753`). Mutations go through
a real per-change review gate (`src/store/proposed-changes.ts:95-120`), but once accepted a change
leaves view (`src/modules/chat/ProposedChangesReview.tsx:27`) and cannot be undone. Autonomy is one
global `ask`/`auto` switch (`src/store/agent-autonomy.ts:23,37-40`).

**Design rule for every idea below:** trust is a *layout* property, not a feature. It has to
sit where the eye already is (the cell, the row, the turn), cost zero tokens by default, and
never add a panel when a mark on an existing surface will do.

Company scenes use real names from the R15 battery (`docs/redesign/verification/r15/battery/BATTERY_MANIFEST.md`).
Any figure in a scene that is not cited to a file is illustrative, not data.

---

## designer-1 — Witnessed by default: the moat on the page people actually open  *(not on the floor list)*

**User moment.** A retail investor hears about Bombay Oxygen Investments (BSE 509470) on a forum
and types it into the overview, with no key. Today the fundamentals table shows `Institutions 8.46%`
as plain fact. With this idea the cell reads `8.46%`, followed by a hairline amber tick and a
second figure right after it: `BSE SHP 0.06% · Jun-26`. There is no chat and no brief. The app
simply refuses to show one source's number alone when it holds a second source that disagrees.

**Mechanics.**
- New read-only GET route `/fundamentals/{symbol}/witnessed` that calls the existing
  `snapshot_structured` (`sidecar/services/research/fast.py:261`) and returns only its
  `derived.conflicts` and the witness legs (`ownership_exchange`, the growth-computed fields,
  `market_cap_witness`, `range_check`, `earnings_quality`; attached at `fast.py:376-402`). The
  function never raises and every witness returns `None` on failure (`ownership_check.py:19-22`),
  so the route cannot make the page worse. Zero tokens.
- `EquityOverviewPanel` fetches it as a seventh leg of its existing fan-out, after the six calls
  it already makes and without blocking them. The existing `FundamentalValueCell`
  (`EquityOverviewPanel.tsx:226-243`) gains a conflict slot that renders the second source inline
  and uses the tone that `ConflictLine` already defines for `data_conflict` vs
  `definitional_expected` (`src/modules/research/brief-blocks.tsx:129-176`, types in
  `types/brief.ts:93-108`). A definitional pair, such as "insiders ≠ promoter group", renders as a
  neutral second figure with its basis. A data conflict renders amber.
- Cache the witness result in the existing SQLite TTL cache (`sidecar/services/data_cache.py`) for
  one day per symbol, because exchange shareholding changes quarterly.
- New: one route, one cell variant, one cache key. No new witness, no new data source.

**Why Jarvis.** Receipts and initiative: the app volunteers a correction you did not ask for, in the
place you were already looking.

**60-second demo.** Keyless install. Type `509470`. The overview paints, and one second later two
cells grow a second figure with an amber tick. Hover the tick to see "Yahoo heldPercentInstitutions
vs BSE SEBI-XBRL shareholding pattern, quarter ending 2026-06-30". Then open the same company in
any other retail tool and see the single number with no warning.

**Lifecycle cost.** The witnesses already carry their own maintenance cost (exchange endpoint
drift, circuit breakers). This idea adds one consumer, so a witness regression now shows on the
most-visited page instead of a brief, which is where you want to see it. It also adds exchange
load per overview open, bounded by the one-day cache and the existing exchange circuit breaker.

**Biggest risk.** Noise. On bank names the growth witness produces definitional conflicts on
nearly every open (the R13 "bank Conflict Note noise"). If every cell grows a second number, the
signal is lost. Mitigation: only `data_conflict` gets the amber tick. Definitional pairs appear on
hover, not inline.

**Size.** S (2-3 days).

---

## designer-2 — Proof Open: the first minute is a demonstration, not a tour  *(not on the floor list)*

**User moment.** First launch. Today the welcome card says "An agent-native finance terminal" and
offers a key form (`src/components/OnboardingFlow.tsx:224-290`). Every product says it is
accurate. Instead, the first screen asks one question, "Name a company you own or are watching",
and within about eight seconds, with no key, shows a card titled **"What we checked"**: six rows,
one per witness, each saying `agrees`, `disagrees — here are both`, or `couldn't check — why`. For
Viyash Scientific (renamed from Sequent in 2026) the identity row says "Resolved VIYASH ←
formerly SEQUENT, BSE 512529". For Jonjua Overseas, 15 days after a 7:24 bonus issue, the
market-cap row either agrees or says which side has not caught up with the new share count.

**Mechanics.**
- Rides designer-1's route plus the resolver (`sidecar/routers/resolve.py:57`) and the identity
  cross-check (`sidecar/services/identity_crosscheck.py`).
- A new `ProofStep` in the existing `OnboardingFlow` state machine (`type Step`,
  `OnboardingFlow.tsx:58`) runs before `welcome`. The key paths (`CloudStep`, `LocalStep`)
  stay exactly as they are, but move after the proof, reframed as "turn on the agent that
  reasons over this".
- The "couldn't check" rows use the sidecar's own reason strings (`FieldMeta.reason`,
  `fundamentals.py:39-43`). The card never shows a check it did not run.
- New: one onboarding step and one card component. The card is reused by designer-6 as the
  coverage header.

**Why Jarvis.** Receipts. It is the trust signal a sceptic can check in under a minute, and it
works with no key, which is the product's positioning made visible.

**60-second demo.** This is the demo itself: fresh install, type a BSE-only nano-cap, and watch
six checks resolve with at least one "disagrees — here are both".

**Lifecycle cost.** Low. It shares designer-1's route. The risk is a demo that decays: if an
exchange lane breaks, the first-run card says "couldn't check" on the operator's showcase screen.
That is honest, but it hurts the first impression, so the smoke test should cover the route.

**Biggest risk.** The user types a large cap where every check agrees, and the moment looks empty.
Mitigation: an all-agree result reads as a positive receipt ("6 of 6 sources agree, here is what
was compared"), and the input suggests one BSE-only name as a starting example.

**Size.** S (2 days on top of designer-1).

---

## designer-3 — Instant Cockpit: paint the last-known world, stamped with its age  *(not on the floor list)*

**User moment.** 9:14 on a weekday. The user opens the laptop and launches the app. Today they see
a loading placeholder until Python binds (`PanelHost.tsx:166`, `workspace.ts:494-500`), which on a
cold `--onefile` boot takes tens of seconds. With Instant Cockpit, the saved layout paints in
under 200 ms: the watchlist shows yesterday's closes, the overview shows ELCIDIN's last-seen figures
correctly grouped (₹1,05,130), and every figure carries a quiet age stamp (`close 18 Sep`). As the
sidecar comes up, each value fades to live and its stamp disappears. The app is never blank, and it
never presents an old number as current.

**Mechanics.**
- Rust already exposes `get_app_data_dir` and `write_text_atomic` (`src-tauri/src/lib.rs:407-419`).
  Add one read command, `read_text_in_app_data(name)`, limited to a fixed allow-list of two file
  names. This is an ordinary Rust command, not a change to `tauri.conf.json`, the plugin contract or
  the Tier-1 files.
- File 1: a copy of the autosave layout blob. `autosaveLayout` (`workspace.ts:541`) already
  serialises it. Also write it through `write_text_atomic` so Rust can serve it before the sidecar
  exists. The sidecar stays the source of truth, because this file is only a mirror used at boot.
- File 2: `last_seen.json`, a bounded map `{symbol → {quote, key fundamentals, provider, as_of}}`
  the frontend writes on the same debounce. This is last-seen data the user was shown, not new
  persistent UI state. It respects the CLAUDE.md rule that persisted UI state rides the workspace
  blob and not localStorage, because the file lives in the app-data directory and is written by Rust.
- `restoreLastSessionOrDefault` first applies the mirror synchronously, then reconciles against
  the sidecar copy when it answers, which is the existing code path.
- Every rendered value from File 2 is wrapped in the existing `StalenessBadge` semantics
  (`src/components/DataBadges.tsx`, `live | stale | eod`), plus a new `cached` state.

**Why Jarvis.** Watching and memory. The instrument is on when you look at it, and it tells you
honestly how old each reading is.

**60-second demo.** Quit, relaunch, and hold a stopwatch. The layout and numbers are up before the
sidecar log prints its bind. Then watch values go from grey "18 Sep" to live one by one.

**Lifecycle cost.** Two-writer drift between the mirror and the sidecar layout. Mitigation: the
sidecar always wins on reconcile, and the mirror carries a version stamp. Schema changes to
`SerializedWorkspace` must keep the older-blob guard that already exists (`deserializeWorkspace`).

**Biggest risk.** A cached price is mistaken for a live one during market hours. The age stamp must
be impossible to miss: before live confirmation, a cached value renders in the tertiary tone with
its date, never in the primary tone, and it never flashes (`src/lib/use-flash-value.ts` must not
fire on the cached-to-live transition).

**Size.** M (4-5 days, including the Rust command and a reconcile test).

---

## designer-4 — The Figure, and the Why key: every number can explain itself in place  *(receipts, on the floor list; the mechanism is not)*

**User moment.** The user is looking at Jumbo Bag's overview. The manifest notes a profit CAGR of
82% on a sales CAGR of 7%, a gap that makes every derived ratio depend on the source. They put the
cursor on `P/E 38.1` and press `?`. A compact card opens on the cell itself, with no panel switch
and no LLM:

```
P/E (TTM)            38.1
= price 90.00  (BSE close 18 Sep, jugaad)
÷ EPS TTM  2.36  (yfinance info, fetched 18 Sep 14:02)
basis   reported (not adjusted) · consolidated
checks  earnings-basis witness: adjusted P/E 21.4 — one-off gain in Q1
source  [open BSE filing]   [copy as citation]
```

Press `?` again to add one line from the model, only if a key is present: "The adjusted basis is
the one to anchor on because…". The deterministic lineage always comes first, and the model only
comments on it.

**Mechanics.**
- A new design-system primitive `<Fig value meta lineage>` in `src/components/`, which wraps the
  formatting that `src/lib/format.ts` already owns (`formatMoney`, `formatPercent`, `groupDigits`,
  `format.ts:65-210`). It replaces the `title=` path (`DataTable.tsx:84-85`) with a focusable cell
  (`tabIndex=0`) that `?` and `Enter` open. The primitive is one component and the card is one
  component. Both use existing tokens, so no new visual language.
- Lineage comes from data the payload already carries: `FieldMeta` (provider, as_of, reason) and
  the witness legs from designer-1. Derived ratios gain a small `derivation` field in the sidecar
  (`{op, inputs:[field…]}`) where the service computes them. This is the one new wire field, and it
  is additive (`FieldMeta` is documented as additive, `fundamentals.py:36-37`).
- `?` is registered through the existing remappable keymap (`src/store/keybindings.ts:154-157`), so
  users can rebind it.
- Adoption order: overview fundamentals, then the brief metric cards
  (`brief-blocks.tsx`, `deriveMetrics`), then the watchlist row.

**Why Jarvis.** Receipts as UI: the receipt is part of the number, not a footnote in a different
panel.

**60-second demo.** Arrow down the fundamentals table pressing `?` on each row. Every figure answers
"who, when, how, and does anyone disagree" in place, in under 100 ms, with the network off.

**Lifecycle cost.** Every new metric needs its lineage declared, or its card says "lineage not
recorded". That is honest, but it creates pressure to keep up. A vitest can list every `<Fig>` usage
without lineage.

**Biggest risk.** `?` collides with typing in input-heavy panels. Bind it only when a `<Fig>` has
focus. The composer and inputs never see it.

**Size.** M (5 days for the primitive, the card and the overview; each additional panel is about
half a day).

---

## designer-5 — One number, one truth: the cockpit never shows two values for the same thing without saying why  *(not on the floor list)*

**User moment.** Jonjua Overseas completed a 7:24 bonus issue on 2026-09-07. The watchlist shows
the price from the quote provider, the overview shows a market cap computed from the pre-bonus share
count, and a brief published last week shows the old EPS. Today the three panels quietly disagree
and the user has to notice. With this idea, each figure that disagrees with the same figure in
another open panel gets a small link glyph. Hover it and all the sibling panels highlight their copy:
"Market cap ₹11.2 cr here (BSE share count, 18 Sep) vs ₹6.6 cr in Brief (yfinance, 11 Sep) — the
brief predates the bonus allotment."

**Mechanics.**
- A client-side figure registry, a small Zustand store in the same style as the panel-context bus
  (`src/store/panel-context.ts:38-68`), keyed by `(symbol, metric, basis)`. Every `<Fig>` from
  designer-4 registers `{value, provider, asOf, panelId}` on mount and unregisters on unmount.
- A pure comparator with the same relative/absolute tolerances the narrative verifier already uses
  (`sidecar/services/company_narrative.py:49-50`) marks disagreements. Basis-bearing metrics compare
  only like with like.
- The brief's stated values are already extracted deterministically by `extractBriefClaims`
  (`src/lib/brief-claims.ts:1-13`). They register as figures with the brief's `createdAt` as the
  as-of, so a stale brief is caught by the same mechanism.
- New: one store, one comparator, one glyph. There is no sidecar change.

**Why Jarvis.** Watching. The instrument checks itself across panels continuously, which no user
can do across six panels by eye.

**60-second demo.** Open JONJUA in the overview next to an old brief. The link glyph appears on two
figures, and hovering explains the bonus. Then refresh the brief and watch the glyph disappear.

**Lifecycle cost.** It depends on designer-4 adoption: only figures rendered through `<Fig>` take
part. The comparator's tolerance table needs care as metrics are added.

**Biggest risk.** False positives from timing. A live price 30 s newer than the overview's
snapshot is not a disagreement. Price-class metrics compare only across different as-of *days*.

**Size.** S (2-3 days, after designer-4).

---

## designer-6 — Coverage strip: say what the app cannot see, per company, before the user finds out  *(not on the floor list)*

**User moment.** Sumax Engineering listed on NSE Emerge 17 days ago, and the NSE master
structurally cannot contain it (manifest: "the NSE master holds series `EQ` and `ETF` only"). A user
opens it. Screener.in's promise is that any listed stock returns complete data. When Vysted cannot
meet that promise, the worst outcome is a panel of dashes that looks like a broken app. The
coverage strip is a single 4-px segmented bar under the overview header, one segment each for
Price · Statements · Shareholding · Filings · Corporate actions · Estimates. The segments are
filled, partial or empty, and hovering or pressing `?` names the reason and the fallback tried:
"Shareholding — not published yet (first SHP due after the quarter following listing)". "Yahoo
circuit open for 4 min (rate limited); retrying".

**Mechanics.**
- Built entirely from signals that exist: per-leg `ok/provider` on the overview fan-out
  (`EquityOverviewPanel.tsx`, six parallel calls with graceful partial failure), `FieldMeta.status`
  counts per group, the disclosure routes (`sidecar/routers/disclosures.py:44,74,95`), and the
  Yahoo circuit-breaker state at `GET /system/provider-health` (`sidecar/routers/system.py:203-211`),
  which **has no frontend consumer today** (grep over `src/`: zero hits).
- The strip reuses designer-2's "What we checked" card as its expanded view, so there is one
  component with two sizes.
- New: one strip component and one `coverage(symbol)` selector. No sidecar change beyond reading
  the existing route.

**Why Jarvis.** Honesty as initiative: the app states its blind spot before the user trips over it.

**60-second demo.** Open SUMAX, then RELIANCE. One strip is mostly empty with reasons, the other is
full. Then trip the Yahoo circuit on the isolated stack (`POST /system/provider-health/trip`, the
existing drill route) and watch three segments turn partial with "rate limited, retrying".

**Lifecycle cost.** Reason strings must stay human. When a new source is added, its segment must be
declared or it does not appear. That is a small per-source step, and it fits the marketplace data
plugin shape.

**Biggest risk.** It reads as a "your data is bad" banner and makes the product look weaker than
tools that hide gaps. The strip is 4 px and quiet by design. The goal is that users trust the full
segments because the empty ones are labelled.

**Size.** S (2 days).

---

## designer-7 — Ghost edits and ⌘Z: the agent's changes appear where they land, and every one can be undone  *(not on the floor list)*

**User moment.** The user asks: "Add the three BSE-only names from that screen to my watchlist and
note why I'm watching Naperol." Today the changes show as a list at the bottom of the chat
(`ProposedChangesReview.tsx:20-35`), away from the watchlist and notes they affect, and once
accepted they cannot be reversed (`ProposedChangesReview.tsx:27` lists only pending changes; there
is no pre-image). With ghost edits, the three rows appear *inside the watchlist* at 50% opacity with
a dashed left rule, and the note text appears in the note as a tinted insertion. `↵` on a focused
ghost accepts it, `⌫` rejects it, and `⇧↵` accepts all. Every applied change, including one applied
under AUTO, goes onto an undo stack. `⌘Z` in any panel reverses the agent's last change to that
panel, with a toast: "Removed NAPEROL note paragraph (agent, 14:02). ⌘⇧Z to redo."

**Mechanics.**
- `describeHostAction` already produces `kind/title/before/after` per change
  (`src/lib/host-actions.ts:583-865`). The `enqueue` step (`proposed-changes.ts:95-111`) gains a
  **pre-image** capture per kind: the watchlist array, the note body, the portfolio row, the screen
  filters. It is taken synchronously at accept time, before `apply` runs (`host-actions.ts:1176-1395`).
- Target panels subscribe to `pending()` filtered by their own kind and render ghosts. The
  watchlist and notes come first, because they are the two most frequent agent writes.
- An `undo` store keeps a bounded stack of `{changeId, kind, preImage, appliedAt}`. `⌘Z` routes
  through the keymap. The portfolio pre-image restores through the existing
  `/portfolio/positions` CRUD, so there is no new route.
- The review list in chat stays for batch review, now as a compact summary of the ghosts.

**Why Jarvis.** Earned trust. A capable assistant does the work in place and makes every change
reversible, so delegating is cheap. It also closes the W-3 gap that the world compare filed
(`census/world/agent-native-ux-COMPARE.md`, row W-3).

**60-second demo.** Ask for three watchlist adds and a note. The ghosts appear in place. Accept two
with `↵` and reject one with `⌫`. Switch to AUTO and ask for a portfolio row deletion, then press
`⌘Z`: the row returns with its cost basis intact.

**Lifecycle cost.** Every new data-write host action must declare a pre-image or it cannot be
proposed. That is a compile-time rule in `describeHostAction`'s switch, which is good pressure.
Ghost renderers are added per panel, currently four.

**Biggest risk.** Undo that lies. If the user edited the note after the agent did, a naive restore
wipes the user's edit. Rule: undo is refused, with a stated reason, when the target changed since
apply. This is the Claude Code "state the undo boundary" pattern (`census/world/agent-native-ux.md`
W-3).

**Size.** M (5-6 days).

---

## designer-8 — Earned autonomy: the agent asks for less permission as it proves it does not need it  *(not on the floor list)*

**User moment.** Three weeks in, the user has accepted 23 of 23 agent chart-symbol changes and 11 of
12 watchlist adds unedited, and rejected 4 of 6 note rewrites. A single quiet line appears in the
review strip: "You've accepted every chart change I proposed (23/23). Let me apply those without
asking? [Yes for charts] [Not now]". Notes stay on ask indefinitely, because the record says
they should.

**Mechanics.**
- Replace the global `ask | auto` (`src/store/agent-autonomy.ts:23,37-40`) with a per-kind map
  over the kinds `describeHostAction` already assigns: `chart | panel | watchlist | data-write |
  settings` (`host-actions.ts:583-865`). The auto-apply predicate at `proposed-changes.ts:118`
  becomes a lookup. This is the shape the census already filed as the fix for
  COD-host-actions-proposed-changes-3.
- A tally per kind of `accepted-unedited / rejected`, persisted in the workspace blob per the
  CLAUDE.md persisted-state rule (`serializeWorkspace`, `workspace.ts:234`).
- The offer fires only after at least N=10 decisions at 100% (or at least 95%) acceptance for that
  kind. It never fires for `data-write` on the portfolio, which is permanently on ask. Any single
  reject after a grant downgrades that kind back to ask, with a one-line notice.
- Settings shows the ledger as a small table: kind, record, mode. Autonomy you can read.

**Why Jarvis.** Memory and earned trust. The assistant learns what you delegate from what you do,
not from a settings page you never open.

**60-second demo.** Pre-seed a tally, trigger a chart change, see the offer, accept it. The next
chart change applies with a transcript note. Reject one watchlist add and see that kind stay on ask.

**Lifecycle cost.** Low: one map, one tally, one table. The judgement call is the thresholds, and
they belong to the operator.

**Biggest risk.** It could feel manipulative, as if the product is pushing you towards less oversight.
The offer appears once per kind, has a permanent "don't ask again", and the ledger is always
visible. It is never offered for anything that writes the tracked portfolio.

**Size.** S (2-3 days; overlaps the COD-host-actions-3 fix, so build them together).

---

## designer-9 — The turn receipt: one monospace line that says what the answer cost and what it rests on  *(not on the floor list)*

**User moment.** The user asks about Crest Ventures: "is this a real-estate company or an NBFC?".
The answer streams, and under it sits one line in tertiary monospace, nothing more:

```
5 tools · 7 sources (BSE 3, NSE 1, web 3) · 2 checks ok · 1 disagree · 18.4k tok · $0.004 · 9.2s · context 7/10 turns
```

Each segment is clickable. `1 disagree` opens the conflict line, `7 sources` lists them, and
`context 7/10` warns that the next answer will forget the first three turns. The user clicks it to
pin those turns or start a research space.

**Mechanics.**
- Every input exists. `usage` per message (`chat-history.ts:46-47`, captured at
  `ChatSidebar.tsx:914-918`, never rendered), `toolSteps` and `researchSteps` (`chat-history.ts:57,60`),
  and research wall time, which `ResearchActivity` already sums ("Researched in 6.4s · 5 steps",
  `src/modules/chat/ResearchActivity.tsx:12-14`). The history window is the literal `.slice(-10)`
  at `ChatSidebar.tsx:749-753`. Price comes from the same per-model rate table the Delegate BudgetGuard
  already meters with (`sidecar/services/budget_guard.py:57-84`, `price_per_million`), whose result
  the rail renders as cost-so-far (`src/modules/chat/AgentsRail.tsx:103-107`).
- Replace the hard-coded `spendUsd: 0` (`ChatSidebar.tsx:921`) with the priced value. The research
  LLM calls that are currently unmetered must be counted first (filed as
  COD-research-extraction-synthesis-2). Until they are, the segment reads `≥$0.004`, never a precise
  wrong number.
- New: one `TurnReceipt` component, one pure `receiptFor(message)` function, and one
  `context n/10` computation.

**Why Jarvis.** Receipts and honesty about cost and memory, the two things BYOK users worry about most
and chat products hide most.

**60-second demo.** Ask three questions and watch the receipt line tick. At `context 10/10`, the
segment turns amber and says what the next turn will drop.

**Lifecycle cost.** Near zero once the metering is right. The risk is a wrong dollar figure, and
the `≥` rule covers it.

**Biggest risk.** Line creep: people will want to add segments. The design rule is a hard cap of
one line at panel width, with segments dropping right to left.

**Size.** S (1-2 days, not counting the metering fix it depends on).

---

## What I deliberately left to other seats

Opening to a brief or wake sweep (retail-8, bloomberg TAPE), the deterministic GO bar (bloomberg),
page-anchored receipts and receipt bundles (journalist-7, forensic-7), a number firewall on LLM prose
(hn-sceptic-1), thesis tripwires (four seats have one). My ideas are the **surface layer** those
ideas render into. designer-4's `<Fig>` is where a firewall-verified digit, a page receipt or a
revision-witness flag should appear. Build the primitive once and every seat's receipt gets the
same place, the same key and the same card.

## Build order if only some of this happens

1 → 2 (the moat made visible, 4-5 days) · 9 (cheap, honest) · 4 → 5 (the primitive, then the
self-check) · 7 → 8 (reversibility before autonomy: never grant autonomy for something you cannot
undo) · 3 (largest, and the best first impression) · 6 (whenever designer-2's card exists).

## Single strongest idea: designer-1, Witnessed by default

The most valuable thing in this repository is a set of deterministic witnesses, each built from a
measured failure, that catch providers being wrong about Indian companies: 141x on institutional
ownership, a growth scalar that contradicts the company's own statements, a market cap computed
from a share count the bonus issue already changed. Today they run only after an LLM turn, which
means only for users who have paid for a key and asked for research. The page every user opens
first shows the uncorrected number. Moving the witnesses onto the overview costs one read-only route
and one cell variant, spends no tokens, and makes "data trust" something a keyless first-time user
can see in their first minute.

A rival cannot copy this in a month because the UI is the easy part. The hard part is the
witnesses underneath: a BSE SEBI-XBRL shareholding lane, exchange-direct history, a non-provider
share count, and a conflict taxonomy that separates definitional differences from data errors so
the tick means something. Those took three release rounds of live failures to build (R11-R13). A
competitor can draw an amber tick in an afternoon, but without that machinery the tick is either
always silent or always on, and users learn to ignore it within a week.
