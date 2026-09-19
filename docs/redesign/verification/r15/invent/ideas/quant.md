# R15 Stage 4 — Ideation seat: QUANT

**Seat:** a quant running systematic factor + event strategies on Indian equities. Cares about
point-in-time (PIT) data, survivorship, corporate-action adjustment, reproducibility, backtest
honesty, and turning any research answer into a testable rule.
**Model:** `claude-fable-5-1`. **Date:** 2026-09-19. Read-only thinking; nothing built.
Scenes use names from `r15/battery/manifest.json`; the numbers inside scenes are illustrative,
not data claims.

## The seat's one-paragraph diagnosis

The terminal already sees the whole Indian market every day and then **forgets it**. The NSE
bhavcopy (every listed equity's EOD row) is fetched once a day and cached for 7 days
(`sidecar/services/nse_bhavcopy.py:100-101`), then folded into a one-row-per-symbol table by an
`ON CONFLICT(symbol) DO UPDATE` upsert (`sidecar/services/fundamentals_store.py:122-123`,
`:473-481`; writer `sidecar/services/fundamentals_warm.py:251-295`). Yesterday is overwritten.
Backtests fill at the same bar's close that produced the signal
(`sidecar/services/backtest_engine.py:321`), run on whatever provider answered — adjusted Yahoo
(`sidecar/services/yfinance_provider.py:277`, library-default adjustment, unlabeled) or
unadjusted exchange bars — with the provider label dropped on the floor
(`sidecar/services/bar_loader.py:139-151`), and completed runs live in a 32-entry in-memory LRU
(`sidecar/services/backtest_store.py:1-12`). The `strategy_critic` agent is a sceptical prompt
with four tools and no deterministic facts to be sceptical about
(`sidecar/agents/strategy_critic.json:6`).

A chatbot answers. Jarvis **remembers what the world looked like on any given day, notices when
the record of the past is quietly edited, keeps score on your ideas after you stop looking, and
counts how many times you tortured the data.** That is a quant's definition of initiative,
watching, memory and receipts. Every idea below is a face of that.

Constraints honoured by all nine: sidecar services + catalog capabilities + additions to existing
panels (no `types/plugin.ts` change, R9 design system untouched); nothing imports or touches
`broker_base.py` / `propose_order` / the audit log; no hosted backend — every loop is idempotent
by trade date and **catches up on wake**, because the laptop sleeps.

---

## Q-1. Vintage — the terminal becomes your point-in-time tape

**User moment.** Sunday night. You ask: "run my low-P/E, high-ROE small-cap screen as it would
have looked on 1 July." Today that is impossible anywhere at retail — Screener, Tijori and
Trendlyne serve latest/restated values. Vintage answers from what *your machine saw* on 1 July,
and adds: "3 of the 41 names that passed then no longer resolve today — VIYASH was SEQUENT until
2026-01-23, one was suspended, one moved to BE series. Today's screen would have hidden them
from your backtest."

**Mechanics.** Stop overwriting. (a) `eod_bars` table: append the parsed `BhavRow`s
(`nse_bhavcopy.py:124-133`) keyed `(trade_date, symbol, series)` inside
`bhavcopy_refresh_once` (`fundamentals_warm.py:251`). The archive URL is date-addressable
(`nse_bhavcopy.py:92-95`), so a sleep gap is healed exactly on wake by walking missing dates with
the existing throttle (`_MIN_REQUEST_INTERVAL_SECONDS`, `:120`) and the existing holiday-marker
logic (`:282`, `_fetch_day` `:330`). (b) `fund_obs` table: change-data-capture on
`fundamentals_store._upsert` (`:484`) — write `(symbol, field, value, observed_at, provider)`
only when a **non-price-derived** field changes (price-driven ratios are recomputed from
`eod_bars`, never stored daily). (c) Universe membership falls out for free: "every symbol with a
row on D" is the survivorship-free universe for D. (d) Identity stitching across renames reuses
`nse_symbol_change.lookup_current(symbol, as_of)` (`nse_symbol_change.py:323` — the `as_of`
parameter already exists). (e) Surface: `as_of` parameter on `screener_run` (`catalog.py:394`)
and an "as of" chip on the screener panel; the result already carries `data_as_of`
(`screener.py:683-821`). The BSE lane already keeps an accidental raw archive, but in an OS cache
dir outside the data dir (`bse_provider.py:155-163`) — move it under `--data-dir` and index it.
New: two tables, one backfill routine, one parameter.

**Why Jarvis.** Memory (the only finance tool whose memory is the market's, not the chat's) +
receipts (every as-of value carries `observed_at` + provider + source file date).

**60-second demo.** Fresh install with a bundled 1-year `eod_bars` seed (precedent:
`screener_universes/india_fundamentals_seed.json.gz`). Run a momentum screen "as of 2026-03-31",
then "as of today", side by side; the diff column shows names that vanished, were renamed, or
changed series. Click one → the bhavcopy row for that date.

**Lifecycle cost.** ~2,700 rows/day ≈ 40 MB/yr in SQLite before compression; `fund_obs` is
kilobytes/day under CDC. Needs a size row in Settings and a "compact older than N years to
weekly" switch. Breaks when NSE changes the bhavcopy format again (it did in July 2024;
`parse_bhavcopy` `:229` already handles two formats) — a parse failure must write a visible gap
marker, never a silent empty day.

**Biggest risk.** Fundamentals are PIT only *from install day forward*; the past is
vendor-latest. Must be labeled ("observed since 2026-09-20") or it becomes the exact lie it
exists to prevent. Deep-history backfill depth of the archive hosts is unprobed.

**Size.** M.

---

## Q-2. Drift Ledger — "the number changed, and here is who changed it"

**User moment.** Monday 09:05. A quiet card: "Overnight, Yahoo revised JUMBO's trailing EPS
9.8 → 7.1 (observed 2026-09-12 vs 2026-09-19). No exchange filing in the window explains it. 2 of
your saved screens flip because of it; 1 published brief quoted the old value." Nobody tells a
retail investor when a historical data point is silently edited. This is the single most common
root of "the numbers look wrong".

**Mechanics.** Pure by-product of Q-1's `fund_obs`: a drift is a new observation for a field whose
fiscal period did not advance. Classifier: (1) a results/announcement row exists in the window
(`corporate_disclosures.get_announcements`, `corporate_disclosures.py:265`) → *explained:
new filing*; (2) a corporate action in the window (`nse_provider.get_corporate_actions`,
`nse_provider.py:617`) → *explained: share-count change*; (3) neither → *unexplained vendor
revision*. Impact join: re-evaluate the user's `SavedScreen`s (`src/store/screener.ts:69`) with
`screener_formula.evaluate_formula` (`screener_formula.py:563`) on old vs new values, and match
against the brief claims ledger (`src/lib/brief-claims.ts:47`,
`src/store/research-spaces.ts:156-173`). Scope the watch to holdings + watchlist + saved-screen
members so it costs nothing. No LLM anywhere in the detection path.

**Why Jarvis.** Watching + receipts + initiative: it audits its own suppliers on your behalf and
volunteers the result.

**60-second demo.** Replay mode over a seeded `fund_obs` with a planted revision: the card
appears, "show impact" flips a saved screen's membership live, "show receipts" opens both
observations with timestamps and providers.

**Lifecycle cost.** Noise is the killer: tolerance bands per field (rounding, FX, TTM roll) need
tuning in the first month, then a fixture suite of known-benign drifts. Near-zero runtime cost.

**Biggest risk.** False alarms on legitimate TTM rolls → users mute it. The "period did not
advance" test must be strict, and unexplained-only should be the default filter.

**Size.** S (given Q-1).

---

## Q-3. Honesty Card + Trial Ledger — the backtest lie detector that remembers your p-hacking

**User moment.** You and the agent have been iterating an RSI/SMA rule on five small caps all
evening. The 14th variant prints Sharpe 1.8. The result panel shows, above the equity curve:
"**Haircut Sharpe 0.6.** You have run 14 variants on this symbol set since Tuesday. Signals fill
at the same close that generated them (next-open fill: Sharpe 1.1). DHANBANK had a rights issue
inside the window and its bars came from an unadjusted source. Position size is 9% of median daily
volume in JUMBO. 11 closed trades — this is an anecdote."

**Mechanics.** A deterministic audit computed beside `_compute_metrics`
(`backtest_engine.py:226-288`), returned in `BacktestResult.warnings` (already rendered,
`src/modules/backtest/BacktestResultView.tsx:506`) plus a structured `honesty` block:
- **Look-ahead delta:** re-run with fills shifted to the next bar's open (today: `bar.close`,
  `backtest_engine.py:321`); report both.
- **Basis check:** stop discarding `series.provider` (`bar_loader.py:151`); flag mixed
  adjusted/unadjusted baskets; cross corporate actions in-window (`nse_provider.py:617`).
- **India cost realism:** a named fee preset (STT, stamp duty, exchange + GST, brokerage) instead
  of a bare `fee_bps` (`_apply_fees`, `:199-202`); participation = size ÷ median volume from
  `eod_bars`.
- **Survivorship flag:** "universe chosen today, tested over the past" unless Q-1 `as_of` universe
  was used.
- **Trial Ledger:** persist every run to SQLite (pattern: `runs_store.py:55`) keyed by
  `hash(symbol set, date window)`; count variants; deflate the best Sharpe for the number of
  trials. This is the part nobody ships: the machine remembers how many doors you tried.
- Honest naming: the current "walk-forward" is fixed-parameter sub-period slicing
  (`backtest_engine.py:459-483`) — label it "sub-period stability".
The card is fed to `strategy_critic` as facts via `backtest_summary` (`catalog.py:843`), so its
framework (sample size, overfitting — it already asks for these in prose) finally has numbers.
Census note for the lead: the equity curve appends one point **per bar**, not per day
(`backtest_engine.py:313`, `:391-397`), and metrics annualise those points by 252
(`:249-267`) — multi-symbol runs are mis-annualised today. The card's first job is to not inherit
that.

**Why Jarvis.** Receipts + memory + the nerve to contradict its own headline number.

**60-second demo.** Run the agent's `run_custom_backtest` (`catalog.py:858`) three times with
tweaked periods; watch the trial counter climb and the haircut Sharpe fall while the raw Sharpe
rises. Toggle "next-open fills".

**Lifecycle cost.** Indian statutory charges change with budgets — the fee preset needs a dated
table and an "as of" label. The trial ledger needs a reset/segment affordance ("new hypothesis")
or it punishes honest exploration.

**Biggest risk.** Deflation maths presented with false precision. Ship it as a banded verdict
(anecdote / suggestive / robust) with the formula one click away, not a third decimal.

**Size.** M.

---

## Q-4. Incubator — freeze a rule, and the terminal keeps its out-of-sample score

**User moment.** On 20 September you save a rule ("promoter stake up QoQ, pledge zero, price above
200-DMA, exit below 50-DMA") and press **Freeze**. You forget about it. On 4 December: "Your
frozen rule has been out-of-sample for 52 sessions: 6 signals, +3.1% average against +5.4%
in-sample. It is decaying, mostly on entries after 3-day run-ups." No order was placed, proposed
or staged — it is a scorecard.

**Mechanics.** A frozen rule = `{rule_hash, frozen_at, definition}` where the definition is an
existing artefact: a screener formula (`screener_formula.compile_formula`, `:441`) or a DSL
strategy (`backtest_dsl.py`, grammar `:13-27`). A `signal_log` table is append-only using the
same trigger idiom as the audit log (`sidecar/models/audit_log.py:40-46` — copied pattern, new
file, new DB; the §6.5 files are not touched) and each row carries the hash of the previous row,
so the record is tamper-evident. Evaluation runs inside the existing daily cadence
(`_bhavcopy_loop`, `fundamentals_warm.py:298`) after Q-1 appends the day. **Sleep-proof by
construction:** an EOD rule over an archived tape is deterministic, so on wake the missed
sessions are replayed in order and stamped `replayed_on_wake`; they remain out-of-sample because
`frozen_at` precedes them and the rule hash cannot change. Entries are booked at the *next*
session's open. Naming stays outside the `place_/submit_/execute_` grep gate
(`record_signal`, `incubator_*`). Surface: an "Incubator" tab in the backtest panel; a
`incubator_status` read capability; `action.notify_desktop`
(`workflow_nodes/__init__.py:54`) for a decay alert.

**Why Jarvis.** Watching + memory + receipts. It is the only feature here whose value is
measured in elapsed wall-clock time.

**60-second demo.** Seeded rule frozen "90 days ago" on the bundled tape: in-sample vs
out-of-sample curves on one chart, the signal log with hash chain, "verify chain" → green.

**Lifecycle cost.** Rule definitions must be versioned against the evaluator: a grammar change
that alters semantics must refuse to continue an old rule rather than silently re-interpret it.
Small disk. One daily evaluation per frozen rule.

**Biggest risk.** Users read a forward record as advice. It needs the research-lab voice and no
"performance" language without n and dispersion next to it.

**Size.** M (needs Q-1's tape).

---

## Q-5. Rule Forge — every predictive sentence gets an "is that actually true?" button

**User moment.** The research brief on a small-cap says: "pledge releases have historically
preceded re-ratings." The sentence carries a small flask icon. Click: the agent proposes a precise
event definition, you accept it, and 40 seconds later: "Across NSE names with a pledge-release
disclosure since 2024: n = 23 events, 20-session market-adjusted return +2.4%, t = 1.1, hit rate
52%. **Not distinguishable from noise.** 3 events drive the whole mean — here are their filings."

**Mechanics.** An event study is the missing sibling of the bar-by-bar backtester and is far more
natural for Indian disclosure data. Events come from the merged announcement feed — each item has
category, timestamp and PDF URL (`catalog.py:655-684`, `corporate_disclosures.py:265`).
Timestamp → tradable session: after 15:30 IST books the next session's open. Returns from Q-1's
tape, market-adjusted against an index series via `bar_loader.load_bars` (`bar_loader.py:160`).
Output: CAR curve with dispersion band, n, t-stat, hit rate, top-3 contribution, and the event
list where each row links to the exchange PDF (the PDF lane already reads them,
`services/search/extract.py:49-65`). The LLM is used once, to turn a sentence into a typed
`EventSpec` that the user confirms through the existing proposed-changes gate; the study itself is
deterministic python `statistics`. Initiative: the brief renderer marks sentences containing a
predictive claim (the verifier already extracts claims, `research/verify.py:137`). An accepted
spec can be sent straight to Q-4 to be frozen. Results count toward Q-3's Trial Ledger.

**Why Jarvis.** Initiative (it challenges its own prose) + receipts (every event is a filing).

**60-second demo.** "Do board-meeting-for-results intimations filed after hours predict a gap?"
→ spec → CAR chart → click the biggest contributor → PDF opens.

**Lifecycle cost.** Announcement categories are free text and drift; the category map needs a
fixture suite and an "unclassified" bucket surfaced, not hidden. A cross-sectional announcement
archive must accrue (or be backfilled per symbol on demand) — until then n is small and the
verdict must say so.

**Biggest risk.** Whether the exchange feeds return enough cross-sectional history per category
without hammering them is unprobed; the current fetcher is per-symbol
(`nse_provider.py:575-594`). If history is thin, the honest product is "anecdote detector" for a
few months — still valuable, but must be framed that way.

**Size.** L- (M if scoped to watchlist + holdings universe first).

---

## Q-6. Action Chain — corporate-action adjustment you can audit, one receipt per factor

**User moment.** JONJUA did a 7:24 bonus with record date 2026-09-04. On the chart the price
"crashed" that morning; the P/E card, the 52-week high and a backtest stop-loss all misread it.
With the Action Chain the chart has an `as traded | adjusted` toggle, the ex-date carries a
marker, and hovering it shows: "factor 0.7742 — bonus 7:24, exchange corporate-action row, ex
2026-09-04; confirmed by an overnight discontinuity of −22.6% on normal volume."

**Mechanics.** The feed is already fetched and then thrown away for everything but dividends:
`dividend_actions.py:38-40` keeps only subjects matching `dividend` and says so ("the feed also
carries bonuses / splits / rights we ignore"). Parse bonus/split/rights subjects into a
per-symbol factor chain (`nse_provider.get_corporate_actions`, `nse_provider.py:617`), store it,
and derive adjusted series locally from Q-1's unadjusted tape — one code path, one basis, labeled.
Honest scope: only the NSE feed exists in code today; a BSE-only scrip like JONJUA needs a BSE
corporate-actions lane (new), and until then the BSE tape discontinuity
(`bse_provider.py:301`) is its only witness — shown amber.
**Second witness:** the tape itself — a close-to-prev_close discontinuity on the ex-date
(`BhavRow.prev_close`, `nse_bhavcopy.py:128`) corroborates or disputes the feed; a factor with
one witness is shown amber, never silently applied. This mirrors the repo's existing witness
idiom (`market_cap_witness.py:140`, `earnings_quality.py:158`). Consumers: chart toggle,
`bar_loader` basis (feeds Q-3's basis check), 52-week fields, Q-5 returns.

**Why Jarvis.** Receipts. "Adjusted close" stops being an article of faith in a vendor.

**60-second demo.** Load a name with a recent bonus: toggle the basis, hover the marker, open the
exchange row; then run the same backtest on both bases and watch a phantom stop-loss trade
disappear.

**Lifecycle cost.** Subject strings are free text ("Bonus 7:24", "Face Value Split From Rs 10 To
Rs 2", rights with premium) — a regex family with a fixture file of real 2026 subjects, plus an
"unparsed action" list that is visible. Rights and demergers need ratio + price and will
sometimes be unparseable; show them as unresolved.

**Biggest risk.** Exactly what `PrvsClsgPric` means on an ex-date must be verified against three
known 2026 actions before it is trusted as a witness. If it is already exchange-adjusted, the
witness is `prev_close[D] vs close[D-1]`; if not, it is the overnight gap. Either works; guessing
does not.

**Size.** S–M.

---

## Q-7. Factor X-ray — "your portfolio is one trade"

**User moment.** Six holdings, six different sectors, you feel diversified. The portfolio panel
shows a five-bar strip: "Momentum 88th percentile, Value 17th, Quality 61st, Size 9th (micro),
Low-vol 22nd. Five of six holdings are the same bet: small, expensive, recently up." Two weeks
later, unprompted: "Your book's momentum exposure crossed the 90th percentile today."

**Mechanics.** The columnar store already holds the whole India universe with the needed fields
(`fundamentals_store.py:67-99`): cross-sectional percentile ranks are one SQL window function
over `fundamentals` (`query`, `:561`). Momentum, low-vol and turnover ranks come from Q-1's tape
(12-1 return, 60-day stdev, median traded value). Holdings from `portfolio_db`
(`portfolio_db.py:27`) or the read-only broker seam (`catalog.py:911`). Exposure = weight-averaged
percentile, with coverage stated ("4 of 6 holdings have ROE"). New capability `factor_exposure`
(read handler → projects to the agent and MCP by the catalog rule). Bonus for India: the legacy
bhavcopy fallback carries delivery columns (`nse_bhavcopy.py:22-30`) that `BhavRow` drops —
delivery-percentage is a genuinely local factor no global tool has. Watching rides the same daily
loop as Q-4.

**Why Jarvis.** Initiative + watching: it tells you what you own in the language of risk, before
the drawdown does.

**60-second demo.** Paste six tickers → strip renders → ask the agent "what am I actually betting
on?" → it answers from `factor_exposure`, not from vibes → "find me two names that would pull
value above the median" → `screener_run` with rank criteria.

**Lifecycle cost.** Low. Rank definitions must be frozen and versioned (changing a definition
silently rewrites history in Q-4/Q-5). Coverage on BSE-only nano-caps is thin and must show as
"unranked", never as 50th percentile.

**Biggest risk.** Percentiles on vendor fundamentals inherit vendor errors; pair each strip with
its coverage and `data_as_of` so a bad input is visible, not laundered into a rank.

**Size.** S–M.

---

## Q-8. Surprise without analysts — SUE and drift watch for names nobody covers

*(Floor-adjacent: results-day signals. The quant twist is what makes it work for small caps.)*

**User moment.** A ₹600-crore company with zero analyst coverage files results at 18:40. Every
"earnings surprise" tool shows a blank because there is no consensus. The terminal says: "PAT ₹14.2
cr against ₹9.1 cr in the same quarter last year; standardised against its own 8-quarter history
that is a +2.3σ surprise — its largest in the record. Filed after hours: the first tradable print
is tomorrow's open. I will track the 20-session drift and tell you how this kind of surprise has
behaved in your universe."

**Mechanics.** Seasonal-random-walk SUE needs only the company's own quarterly series — no
estimates. Quarterly history exists (`catalog.py:528` `earnings_history`,
`earnings_quality.py:228`); the newest quarter comes from the results PDF already reachable
through the announcements lane (`research/disclosures.py:45-52` ranks the results filing first)
with the scale witness guarding lakh/crore misreads. Trigger: results calendar
(`corporate_disclosures.py:335`) scoped to holdings + watchlist, checked on the daily loop and on
wake. Drift tracking is a Q-4 frozen rule instantiated automatically per event; the base rate is a
Q-5 event study keyed on SUE buckets.

**Why Jarvis.** Watching + initiative, on exactly the names where the rest of the market's tooling
is blind.

**60-second demo.** Replay a past results evening on the seeded tape: the card, the σ bar against
eight quarters, the drift tracker starting the next session.

**Lifecycle cost.** PDF table extraction is the fragile joint; every extracted figure must show
its page receipt and fall back to "could not read the filing" rather than a guess. Consolidated
vs standalone must be pinned per company and never mixed across quarters.

**Biggest risk.** A mis-extracted PAT produces a confident, wrong σ. Gate SUE on two agreeing
sources (PDF + vendor quarterly once it updates) or label it "single-source, provisional".

**Size.** M.

---

## Q-9. Thesis CI — your thesis compiles into tests, and the build goes red

*(Floor-adjacent: thesis vs filings. The quant twist: no LLM at check time.)*

**User moment.** Your note on a holding says: "Owning this while OPM holds above 18%, promoters do
not pledge, and debt keeps falling." The agent proposes three assertions; you accept. A small
green "3/3" sits beside the ticker for months. After the Q2 shareholding filing: "**1/3 failing**
— promoter pledge moved 0% → 4.2% (BSE XBRL, filed 2026-10-19). Your thesis named this as a
condition."

**Mechanics.** A tripwire is a screener formula scoped to one symbol — the language, parser and
evaluator already exist and are hostile-input hardened (`screener_formula.py:441`, `:563`). The
LLM runs once, at compile time, turning prose from a note (`write_note`, `catalog.py:1374`) into
formulas the user approves through the proposed-changes gate; after that, evaluation is
deterministic and free, re-run whenever Q-1 records a new observation for a referenced field or a
new shareholding quarter lands (`corporate_disclosures.get_shareholding`, `:366`;
`bse_provider.get_shareholding`, `bse_provider.py:612`). That matters on a laptop that sleeps and a
BYOK budget: zero tokens to keep watching. Needs two or three fields the formula vocabulary lacks
today (pledge %, promoter %, QoQ deltas) — add them as fields, not as a new language.

**Why Jarvis.** Memory (it holds you to what you wrote) + watching + receipts (the failing
assertion links to the filing that failed it).

**60-second demo.** Write a two-line thesis → accept three assertions → replay a seeded
shareholding update → the badge turns red and opens the XBRL link.

**Lifecycle cost.** Low at runtime. The field vocabulary is a contract: renaming a field breaks
stored theses, so stored formulas need a version and a loud migration failure.

**Biggest risk.** Qualitative theses ("management is honest") do not compile. The compiler must
say "this part is not testable" instead of inventing a proxy.

**Size.** S–M.

---

## Dependency shape (so the lead can sequence)

`Q-1 Vintage` is the spine. `Q-2`, `Q-4`, `Q-7` (momentum/vol legs) and `Q-5` read it.
`Q-6` makes it trustworthy for returns. `Q-3` stands alone and is the cheapest credibility win.
`Q-9` stands alone apart from change triggers. Minimum coherent slice for a release:
**Q-1 + Q-3 + Q-6**, with Q-2 as the visible "it watches" moment because it is nearly free once
Q-1 exists.

## Strongest single idea: Q-1 Vintage

Because its value is denominated in **elapsed time, not code**. A rival can clone the schema in a
week; they cannot clone the six months of as-observed fundamentals, survivorship-free universe
membership and forward signal records sitting in a user's data dir — and every day they delay,
every Vysted user's tape gets one day further ahead. Hosted competitors have a structural problem
copying it: a central PIT product means storing and re-serving exchange and vendor history to
everyone, which is a licensing and cost posture they have avoided for a decade (it is why retail
PIT data for India does not exist); a local recorder re-serves nothing — it remembers what one
user's own machine already fetched. And it is the rare foundation that turns the product's
weakness into its moat: "local-first on a laptop that sleeps" stops being an apology and becomes
the reason the data is *yours*, as-of-dated, and verifiable. Everything that feels like Jarvis in
this document — the drift card, the frozen-rule scorecard, the as-of screen, the honest backtest —
is that memory, surfaced.
