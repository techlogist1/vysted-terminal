# R15 Census — Opportunity Ledger

**Sweep:** `OPP-LEDGER` · **Worker model:** `claude-opus-5[1m]` · **Date:** 2026-09-19
**Job:** deduplicate every opportunity surfaced by the world lane, rank it, and verify every
claimed table-stakes gap against the actual code before filing it.
Read-only: no repo file was modified except this one and `raw/world-table-stakes.json`.

## Inputs

| File | State | Opportunities carried |
|---|---|---|
| `world/perplexity-screener.md` | complete (613 ln) | O1–O8 + TS-1…TS-6 |
| `world/openbb-kite-mcp.md` | complete (478 ln) | O1–O14 + T1…T7 |
| `world/fey-tijori-trendlyne.md` | complete (704 ln) | O-1…O-12 + TSG-1…TSG-8 |
| `world/agent-native-ux.md` | complete (200 ln) | W-1…W-12 (patterns, no Vysted comparison) |
| `world/investor-asks-forums.md` | **STUB** (32 ln) | none — "PART A — Findings _(populated below)_" is empty |

Two honest notes on scope:

- **`investor-asks-forums.md` never got past its header.** The demand-side sweep (what serious
  Indian investors ask for and cannot get) contributed **nothing** to this ledger. Its header
  records real fetch blocks (ValuePickr timeout, Reddit unauthenticated-fetch block) but no
  findings. That is a hole in the evidence base, not an absence of demand — the lead should
  either re-run that sweep or discount any "nobody asked for this" reasoning.
- **`agent-native-ux.md` is not compared here.** W-1…W-12 are harness patterns whose against-the-code
  comparison is the `WORLD-COMPARE` lane's job (`world/agent-native-ux-COMPARE.md` →
  `raw/world-agent-native-ux.json`). Filing them here would duplicate that worker. Where a
  harness pattern is load-bearing for a finance opportunity below it is cited, not re-derived.

## Ranking method

Each opportunity scored on three axes, multiplied:

- **Evidence** — primary source with a quote and a date (3) · third-party review (2) · single
  snippet or inference (1).
- **Moat fit** — data trust · research quality · finance-tuned agent · local-first BYOK. Hits
  three or four (3) · two (2) · one (1).
- **Proximity** — the code exists and needs wiring (3) · one new module over shipped data (2) ·
  a new data pipeline or vendor dependency (1).

Tiers are the product, not the sum: an opportunity that scores 1 on proximity cannot buy its way
into Tier A with evidence. Size is S (days) / M (a week or two) / L (longer than this release).

---

## TIER A — build these

### OPP-1 — The trigger layer, and the thesis watcher on top of it

**Score:** evidence 3 × moat 3 × proximity 3 · **Size:** S for the trigger, M for the watcher

**Unmet need.** Nothing anywhere in this sweep watches a user's *own* position against new
filings. Perplexity "answers, it does not watch" and "retrieves, it does not reason about you"
(https://helmterminal.dev/blog/perplexity-stock-research); its Portfolio "doesn't retain reasoning
for holdings or re-test theses against new filings" (ibid.) — and is Plaid-backed, US/Canada only
(https://www.wealthmanagement.com/artificial-intelligence/perplexity-upgrades-finance-capabilities),
so an Indian user has no book on it at all. Screener's alerts are threshold and phrase triggers
with no memory of why you own the thing. Trendlyne's are screener re-evaluations.

**Who does it badly today.** Everyone, differently: Perplexity ships scheduled *prompts* (Tasks);
Screener and Trendlyne ship *stateless* triggers; Tijori ships price/volume alerts free
(https://www.tijorifinance.com/features/). Nobody joins a written thesis to a new disclosure.

**What Vysted already has, one step away.**
- Durable detached runs with a SQLite store and metered ceilings: `sidecar/services/run_manager.py`,
  `sidecar/services/runs_store.py`, `sidecar/services/budget_guard.py`, routes at
  `sidecar/routers/runs.py:63-126`.
- A workflow engine with an OS-notification sink already wired end to end:
  `sidecar/services/workflow_nodes/builtin.py:321-336` (`action.notify_desktop`) →
  `src/store/workflow.ts:180` → `src/lib/desktop-notification.ts`.
- The India announcements feed already being fetched per researcher, PDFs and all:
  `sidecar/services/research/disclosures.py:36-40`, extraction in `sidecar/services/search/extract.py`.
- A local portfolio the agent can read and write: `portfolio_add_position`, `get_portfolio`
  (`sidecar/services/agent_tools/catalog.py:1309,946`).
- Notes the user already writes: `write_note` (`catalog.py:1374`), `src/modules/notes`.

**The missing piece is one thing: a trigger.** Every run path in the app is a POST from the UI
(`sidecar/routers/workflow.py:38`, `sidecar/routers/runs.py:63`). Build a scheduler that can start
a saved workflow or a durable run on a clock, and the first useful trigger is a phrase watch over
the announcements feed already flowing — not a price-tick subsystem. Then the differentiated
layer: a stored thesis (`write_note`) + a held position (`get_portfolio`) + a new filing →
"your Q3 thesis said margins recover on the new plant; today's filing says commissioning slipped
to Q1 — here is the paragraph." That is initiative, watching, memory and receipts in one object,
and it is a composition of four shipped subsystems.

**Table-stakes floor underneath it:** `WLD-T-1` (critical). Ship the floor first; the watcher is
what makes the floor worth having.

### OPP-2 — The ₹ lakh/crore scale witness

**Score:** 3 × 3 × 3 · **Size:** S

**Unmet need.** The benchmark's single worst documented failure: Perplexity "read a thinly covered
company's 10-K revenue without applying the 'in thousands' denominator, got the number wrong by a
factor of 1,000, and then built a confident story about a 99.8% revenue collapse"
(https://helmterminal.dev/blog/perplexity-stock-research, May 2026). Perplexity's own staff answer
financial-hallucination reports with prompt hygiene — "search domain filters", "If you're not sure,
respond with 'I don't know'" — not a check (https://community.perplexity.ai/t/financial-data-hallucinations/145).

**Who does it badly.** The whole category: a 2026 multi-model audit found hallucinated facts in up
to 41% of finance responses (https://learn.g2.com/tech-signals-ai-hallucinations-and-research).
Indian filings mix ₹ lakh / crore / million *within one document set* (standalone vs consolidated,
XBRL vs PDF, exchange filing vs annual report), so the failure is strictly easier to trigger here
than on the US 10-K where it was documented. No source tested this on Indian filings — recorded as
a high-probability extension, not a verified claim.

**One step away.** Vysted already runs **two independent numeric witnesses** with an explicit
DISCLOSE-never-substitute contract and the wiring is identical for a third:
- `sidecar/services/research/range_check.py:1-20` — 52-week range vs the app's own exchange-direct
  EOD series (nse_direct → jugaad → bse), flagging a wrong provider pair rather than replacing it.
- `sidecar/services/market_cap_witness.py:1-20` — provider market cap vs a BSE-derived,
  **non-provider** share count, explicitly to break the circularity of checking a provider against
  itself.
- Scale tokens are already recognised in extraction: `sidecar/services/search/extract.py:75,86-87`
  ("crore", "lakh"); INR already renders at ÷1e7 in `sidecar/services/research/semantics.py:603-607`.

The third witness asserts the scale unit declared in a document's header against the magnitude of
the figure extracted from it, and **flags**. This is the highest-leverage item in the entire sweep:
it converts the benchmark's most-cited failure into a stated Vysted guarantee, using a contract
that already shipped twice.

### OPP-3 — Make the trust machinery visible (disagreement card, per-figure source, benchmark page)

**Score:** 3 × 3 × 3 · **Size:** S–M

**Unmet need.** Citations are table stakes and they actively mislead: users report that "the
presence of sources can create a false sense of certainty, and if the sources are mid, outdated, or
all echoing the same assumption, the answer inherits that bias"
(https://checkthat.ai/brands/perplexity/reviews). Bloomberg set the institutional bar at
per-figure attribution — "Every AI-generated summary or answer we provide includes clear
attribution, both to the source and, where applicable, to the analyst who authored it"
(https://a-teaminsight.com/blog/bloomberg-launches-ai-powered-research-tool-for-terminal-users/) —
and ASKB "include[s] citations anchoring every figure, chart, or quote". Tijori sells raw-source
access as a **named premium feature** ("Source — access base data sources directly",
https://www.tijorifinance.com/features/). Provenance is a product, not a chore.

**Who does it badly.** Everyone ships citations on the *answer*. Nobody retail ships **disagreement
between sources** as a visible object.

**One step away — this is a render of data the pipeline already computes.** `range_check.py` and
`market_cap_witness.py` both emit a labelled divergence naming both figures and both sources into
`derive_semantics`; `sidecar/services/research/citecheck.py:216` `ensure_citation_integrity` already
strips invalid markers and softens unsupported sentences; the brief renders typed blocks with a
metric grid whose `deriveMetrics` returns `null` rather than fabricate
(`src/modules/research/brief-blocks.tsx`); `shareholding_pattern` already carries `split_source` /
`split_as_of` provenance stamps. Three deliverables, ascending cost: (a) a "two sources disagree —
here are both, as of these dates" card in `BriefBody`; (b) per-figure source attribution on the
metric cards; (c) a public benchmark page showing the exact number Perplexity got wrong by 1000×
next to Vysted's answer and the filing page it came from. Neither benchmark can copy (a) without
rebuilding their provenance.

### OPP-4 — Guidance vs delivery: the concall tracker nobody ships

**Score:** 3 × 3 × 2 · **Size:** M (L until `WLD-T-6` lands)

**Unmet need.** Trendlyne ships per-call AI summaries (https://trendlyne.com/ai-conference-calls/),
Bloomberg ships transcript Q&A, Fey shipped call summaries before it was absorbed. **Nobody diffs
what management said against what printed.** A summary blob per call is a document; "management
guided 18% margin in Q2, Q3 printed 14.2%, here is the quote from each call" is a research
artifact, and it is one join away from data that is already free and public.

**Who does it badly.** Everyone summarises calls; nobody tracks them as an object with state
across quarters.

**One step away.** `earnings_history`, `earnings_estimates`, `analyst_history` and
`corporate_announcements` (which returns investor-presentation and results PDFs as
`attachment_url`) are all shipped catalog capabilities (`catalog.py:528,537,547,655`); the research
agent already produces structured briefs via `publish_brief` (`catalog.py:1177`); the PDF lane
already reads exchange attachments (`sidecar/services/search/extract.py`). A guidance-delta brief
is a new agent prompt over shipped tools plus one stored object per call — **not** a new data
pipeline. Blocked on having the transcript at all (`WLD-T-6`); the *schedule* half is already on
the wire and merely unregistered (`WLD-T-7`).

### OPP-5 — One-click, keyless broker connect ⚠ TIER-4 ADJACENT

**Score:** 3 × 2 × 2 · **Size:** S–M · **Do not bake in: surface to the operator.**

**Unmet need.** Nobody ships a *purpose-built finance desktop app* with a broker MCP pre-wired.
The proven consumption path is "install Node, edit a JSON file, run `npx mcp-remote`"
(https://github.com/zerodha/kite-mcp-server README). Zerodha made the read-only path **free and
keyless** — "No code. Just chat.", "Read-only access.", hosted version "requires no installation or
API keys" (https://zerodha.com/products/mcp/) — while the execution path still needs the ~₹500/mo
Kite Connect subscription (https://kite.trade/forum/discussion/15015/revising-kite-connect-fees-from-2000-to-500-per-month).

**One step away.** Vysted already spawns and supervises MCP subprocesses from Rust
(`src-tauri/src/openbb_mcp.rs`, `src-tauri/src/sec_edgar_mcp.rs`) and already enforces read-only
wrapper plugins in three layers. Riding the hosted endpoint removes `api_secret` from the threat
model entirely (`sidecar/routers/brokers.py:415`, `sidecar/services/brokers/kite.py:13-17`).

**Two things the operator must weigh.** (1) This depends on `WLD-T-5` (no user-addable MCP server),
not on any §6.5 change — sequence it after. (2) Zerodha's hosted "read-only" endpoint **still
exposes** `place_gtt_order` / `modify_gtt_order` / `delete_gtt_order` per its own README while the
product page says flatly "Read-only access"; a GTT arms a trade. Vysted's gate is stricter than the
upstream it would ride, so the read-only audit must be *enforced* on that surface, never inherited.
That asymmetry is also a talking point: the largest broker's agent can arm a trade; Vysted's cannot
touch one.

### OPP-6 — User-addable MCP servers

**Score:** 3 × 2 × 3 · **Size:** M

**Unmet need.** MCP's entire premise is servers the user brings. The Indian ecosystem is already
populated and Vysted can consume none of it: Zerodha official
(https://github.com/zerodha/kite-mcp-server), Upstox ×2
(https://glama.ai/mcp/servers/adibhattar95/upstox-mcp-server), Angel One SmartAPI, Dhan, Groww,
5paisa, INDmoney, a multi-broker server (https://lobehub.com/mcp/sharuniyer-indian-broker-mcp), and
~8 screener.in scrapers (https://github.com/ronyv89/screener-mcp). Fiscal.ai charges $588/yr for a
tier that includes "REST + MCP" (https://quantbrainai.net/blog/fiscal-ai-review-jul-2026/) — the
surface is commercially validated.

**One step away.** Vysted owns the hard half already (Rust-spawned subprocess lifecycle, port-wait,
graceful degrade; `crate::wait_for_port`). What is missing is a user-config'd server list —
`sidecar/routers/mcp.py` exposes only `/mcp/status` (:28) and `/openbb-mcp/status` (:44). Turns
"add a broker" from "write a Python adapter" into "paste a URL and declare it read-only". Files
as table stakes too (`WLD-T-5`) because MCP-server-only while calling MCP the universal tool layer
is a positioning contradiction.

### OPP-7 — Portfolio-aware research (the thing a local-first app can do privately)

**Score:** 3 × 3 × 3 · **Size:** S

**Unmet need.** "It retrieves, it does not reason about you" — no awareness of position size or
thesis logic (https://helmterminal.dev/blog/perplexity-stock-research). And in India the gap is
structural, not a roadmap item: Perplexity's Portfolio is Plaid-backed and Plaid's investment
aggregation is US/Canada. **The Indian Perplexity user has free quotes, news, transcripts and an NL
screener — and no book.**

**One step away.** `get_portfolio` and `broker_portfolio` are shipped capabilities
(`catalog.py:946,911`), granular broker reads carry FR-041 provenance
(`sidecar/models/broker_reads.py`), and `portfolio_advisor.json` is one of the 14 first-party
agents (`sidecar/agents/`). Threading "your actual position and cost basis" into the research
context assembly is a prompt/context step over data Vysted already holds **locally** — which is
precisely the thing a cloud product cannot do privately, and the reason this is a moat rather than
a feature.

---

## TIER B — strong, slightly further from the code

### OPP-8 — A forensic / accounting-quality score: India's unclaimed box

**Score:** 3 × 3 × 2 · **Size:** M

No mainstream Indian retail platform ships one. Tickertape's "red flags" is volatility-and-debt
risk (https://www.strike.money/reviews/tickertape); Trendlyne's Durability is a financial-quality
composite not marketed as forensic (https://trendlyne.com/score-details/). Practitioner demand is
documented and the framing is explicit — "Traditional financial analysis is not designed to detect
deception" (https://marketsmithin.substack.com/p/spotting-forensic-red-flags-in-indian). The
classic components: CFO-vs-PAT divergence, receivable/inventory days blowout, auditor resignation,
related-party growth, contingent liabilities, **promoter pledge trend**, promoter-stake decline.

The sharpest single component is the pledge **derivative**, not the level: NSE publishes pledged
data free (https://www.nseindia.com/companies-listing/corporate-filings-pledged-data) and retail
tools all ship the level (Samco Pledge Monitor, Screener screen 3513), but the practitioner rule is
directional — "Rising pledging over 4 consecutive quarters is a red flag regardless of absolute
level" (https://hdfcsky.com/blogs/risk-radar-by-sky/promoter-pledge-creeping-above-60-percent).

*One step away:* `shareholding_pattern` already returns quarterly promoter percentages newest-first
with honest `None`s and provenance stamps (`catalog.py:686`, `sidecar/models/announcements.py:91-140`);
`corporate_announcements` already categorises auditor and related-party filings (`catalog.py:655-682`).
Missing inputs: the pledge series (`WLD-T-8`) and cash-flow-vs-PAT / working-capital-days series
(`WLD-T-4`). Highest research-quality payoff per unit of work once those two land — and the score
must disclose its inputs and refresh cadence the way Trendlyne's does, or it contradicts the
data-trust position.

### OPP-9 — Filing-grounded Q&A with no per-answer meter

**Score:** 3 × 3 × 3 · **Size:** M

Screener AI has the right product — "direct access to company filings such as annual reports and
earning calls", "No uploads", "No prompt engineering" — and the wrong economics: "around ₹10-30 per
answer" that "can even go up to ₹100 if the AI reads a lot of documents", with Screener itself
conceding "the costs of answers are quite high sometimes" (https://www.screener.in/ai/). Every
competitor meters: Trendlyne 7 MarketMind credits at ₹310/mo (https://trendlyne.com/subscription/plans/);
Fiscal.ai 10 / 300 / 500 prompts per month (https://quantbrainai.net/blog/fiscal-ai-review-jul-2026/);
TradingView a weekly allowance scaling "Free 0.25×, Essential 1×, Plus 2×, Premium 5×, Ultimate 20×";
OpenBB's free Copilot was 20 queries/day with BYOK reserved for paid (https://openbb.co/pricing/).

A price tag hanging over every question is exactly the wrong incentive for exploratory research.
*One step away:* BYOK shipped (`sidecar/services/llm/`, OS-keychain-held), `budget_guard.py` already
meters tokens/spend/wall/steps per run with a stated abort reason, and the same corpus is already
pulled (`sidecar/services/research/disclosures.py:4,36-40`). This is Screener AI's product at
Screener AI's grounding with the meter pointed at the user's own key instead of a vendor's margin —
and it is as much a **claim to make loudly** as a thing to build.

### OPP-10 — Show the query you ran, and let the user edit it

**Score:** 2 × 3 × 3 · **Size:** S

Only Bloomberg does this: when numeric analysis surfaces, ASKB "exposes the underlying BQL code for
immediate reuse in Excel or BQuant"
(https://www.aicerts.ai/news/bloomberg-askb-conversational-investment-research-beta-workflows/).
No retail product shows its work in code. *One step away:* `write_screener_filters`
(`catalog.py:1237`) and `save_screen` (`catalog.py:1416`) already exist and the agent already
authors filters; `run_custom_backtest` (`catalog.py:858`) already takes a declarative, server-parsed
rule grammar it could display verbatim. Surfacing "here is the screen the agent built — edit it" is
a UI affordance over capabilities that ship today, and it is the coding-agent receipts idiom
transplanted into finance.

### OPP-11 — Named workflows instead of open chat

**Score:** 2 × 2 × 3 · **Size:** S–M

Bloomberg productised ASKB **Workflows** as first-class objects — "pre-earnings preparation,
post-earnings analysis, or meeting prep" that "assemble a structured output in minutes". No retail
product does. *One step away:* Vysted has a workflows domain in the catalog, a durable run system
(`run_manager.py`, `routers/runs.py`), `arrange_layout` (`catalog.py:1115`) and viewport-fit-aware
cockpit templates (`src/lib/layout-templates.ts` `fitLayoutTemplate`). A "results-day prep" workflow
that arranges the cockpit, pulls `earnings_upcoming` + `analyst_history` + `corporate_announcements`
and publishes a brief is an assembly of shipped parts. Pairs naturally with OPP-1: a named workflow
is exactly what a trigger should start.

### OPP-12 — Lineage on every agent output, not just broker reads

**Score:** 2 × 3 × 3 · **Size:** S

OpenBB's governance framing, verbatim: "Entitlements apply to the agent exactly as they apply to the
user behind it"; "Every output carries data lineage"
(https://openbb.co/blog/introducing-workspace-mcp/, 2026-05-26). *One step away:* the FR-041
provenance label already rides **every broker read result** —
`sidecar/models/broker_reads.py` `BrokerReadProvenance`, inherited by the positions / holdings /
margins results — and `shareholding_pattern` already stamps `source` / `split_source` / `split_as_of`.
Generalising one base model to every tool result is a mechanical extension of a pattern proven
in-tree, and it is the substrate OPP-3's per-figure attribution renders.

### OPP-13 — Be *the* Indian finance MCP server

**Score:** 2 × 3 × 2 · **Size:** M

The finance-MCP ecosystem is explicitly US-centric — "International coverage gap: Only EODHD
explicitly addresses non-US markets; most focus on US equities"
(https://chartlibrary.io/blog/financial-mcp-servers-compared); the most-starred server covers US
Treasury, US CPI and SEC filings with no India (https://docs.financialdatasets.ai/mcp-server). Every
Indian fundamentals MCP that exists is a screener.in scraper — at least 8 of them, all fragile and
ToS-grey (§3.6 of `openbb-kite-mcp.md`), because India's best fundamental dataset has no official
API and the vendors pitch "handles the browser, proxies, anti-bot, and parsing, with updates when
Screener.in changes its markup".

*One step away:* Vysted's MCP server is shipped and catalog-projected (`sidecar/services/mcp_server.py`,
parity-tested), and the India resolver/exchange plumbing exists (`sidecar/services/nse_symbol_change.py`,
`sidecar/services/resolver_masters/regenerate_india_sectors.py`, `sidecar/services/bse_provider.py`).
A durable, exchange-and-XBRL-sourced Indian fundamentals surface is defensible in a way a ninth
scraper is not — **do not add the ninth scraper**. The role is literally unoccupied.

---

## TIER C — real, but further out or narrative-only

### OPP-14 — Segment and operational metrics
Tijori paywalls at "1000+ operational metrics free; 6000+ premium" with revenue mix by product and
geography at ₹3,500/yr (https://www.tijorifinance.com/features/); Fiscal.ai's hook is "segment-level
data (e.g., AWS revenue for AMZN as a separate screenable field)"; Screener gives 10-year Segment
Results away free. *One step away:* SEBI XBRL parsing already exists for shareholding
(`sidecar/services/bse_provider.py:617-790`) and segment reporting lives in the same filings. The
extraction machinery exists; the extraction does not. Table-stakes floor: `WLD-T-13`. Size L.
Adjacent and cheaper: Screener's real switching cost is the **fillable Excel model** — "Export data
into structured excel sheets. Create your own models" plus Custom Upload, where the user's own sheet
with formulas is remembered and re-filled (https://www.screener.in/features/). Vysted exports flat
CSV (`src/lib/csv.ts`) and that export may not even work (`WLD-T-2`).

### OPP-15 — Market-observed open interest, paired with the Greeks already computed
Angel One's SmartAPI MCP is the only surveyed Indian broker surface serving "quotes/candles/OI/Greeks"
plus margin/brokerage estimation; Kite Connect serves OI inside quotes. Vysted computes Greeks
analytically (`sidecar/routers/quant.py`, `compute_greeks` at `catalog.py:756`) and observes no OI
anywhere. Pairing computed Greeks with live OI is the F&O view no open competitor has done well, in
the market where F&O is the retail centre of gravity. Table-stakes floor: `WLD-T-12`. Size M.

### OPP-16 — Broker-entitlement real-time, exactly as TradingView withdraws it
Published three days before the sweep: free TradingView users are now on a 15-minute delay on NSE and
BSE, marked with a "D" badge, and traders are "migrating to broker-native platforms like Zerodha Kite
and Upstox that offer real-time feeds" — "fifteen minutes is long enough for the entire move to be gone
before the chart even shows it"
(https://businessupturn.com/finance/stock-market/tradingview-free-users-hit-with-a-15-minute-delay-on-nse-and-bse-data-and-how-to-switch-real-time-back-on/,
2026-09-16). The licensing economics that forced TradingView's hand **do not bind a BYOK local-first
desktop app**: the user's own broker entitlement is the licence. *One step away:* live read-only Kite
integration plus the exchange-direct history lane (`sidecar/services/research/range_check.py:5-10`).
Quotes through the connected broker session is a provider-lane addition, not an architecture change.
The freshest demand event in the sweep. Size M. (Sequences behind OPP-5.)

### OPP-17 — Positioning: the seat is empty, the licence is the stronger one, the clone burned its credibility
Narrative only, zero code, and it should be said out loud in the README and launch copy:
- **The premium research-app niche is vacant.** Fey — the design benchmark for research-first retail
  terminals — was acquired by Wealthsimple on 2025-08-27 and `fey.com/features` now serves only an
  acquisition notice (https://newsroom.wealthsimple.com/wealthsimple-acquires-investment-research-platform-fey).
  Every remaining India player is attached to a distribution business (Tickertape←Smallcase,
  Tijori←Zerodha ecosystem). An independent, ad-free, non-brokerage research terminal has no incumbent.
- **The AGPL licence is now the stricter one.** OpenBB is open-sourcing its entire suite under a
  *permissive* licence (https://openbb.co/blog/openbb-belongs-to-everyone/, 2026-08-25): a
  well-capitalised firm can close-source a fork of OpenBB and cannot do that with Vysted.
- **Read-only is alignment, not apology.** Zerodha's own hosted MCP "excludes potentially destructive
  trading operations for security" (kite-mcp-server README). Vysted's §6.5 model is stricter still
  (DB-enforced append-only audit with `RAISE(ABORT)` triggers, `PRAGMA query_only=ON` reader,
  kill-switch, no non-GET routes on read-only wrappers). Frame it as the correct default the market
  leader also chose — and note the Comet cautionary tale: a browser agent reportedly executed a
  Zerodha trade with no manual click
  (https://opentools.ai/news/perplexity-ais-comet-browser-executes-no-click-trades-on-zerodha-surprising-users).
- **BYOK has no ceiling.** Every competitor meters AI (see OPP-9). Say "unlimited research runs,
  because you pay the model provider directly."
- **The nearest clone burned its credibility.** Fincept's own coverage lists "Meme token launch
  created credibility concerns" and "API credits expire after one month"
  (https://www.solosoft.dev/post/fincept-terminal-open-source-2026/). Vysted has no token and nothing
  that expires.

### OPP-18 — A documented third-party agent protocol
OpenBB ran an AI Vendors page — third-party copilots plugging into the workspace over an SSE + POST
protocol, with a published SDK (https://openbb.co/blog/building-ai-agents-for-openbb-workspace-with-pydantic-ai/).
Vysted has `src/modules/marketplace`, `src/modules/agent-builder`, an `agents` capability on the
plugin contract (`types/plugin.ts`), and custom agents with a catalog-derived allow-list
(`sidecar/models/custom_agent.KNOWN_TOOL_IDS`). The bring-your-own-*agent* story is mostly built and
not told. Narrative + docs, small code. ⚠ Any change to `types/plugin.ts` is Tier-4.

---

## TABLE-STAKES GAPS

Things competitors or agent tools all do that Vysted lacks. **Every one below was verified against
the code in this sweep**, not carried over on trust. Raw findings: `raw/world-table-stakes.json`
(prefix `WLD-T`, 14 findings).

| id | gap | sev | verified by |
|---|---|---|---|
| WLD-T-1 | Nothing runs unattended — no alerts, schedules or triggers. The workflow engine, the OS-notification sink and the durable-run machinery all exist and only a human POST starts them | critical | `catalog.py` (51 caps, none alert-shaped); `routers/workflow.py:38`; `routers/runs.py:63`; `src/lib/desktop-notification.ts` orphaned |
| WLD-T-2 | Watchlist/portfolio **Export CSV** uses the `<a download>`+Blob path this repo's own helper documents as blocked in the webview — likely a silent dead control | high | `src/lib/export-artifact.ts:4-8` vs `src/lib/csv.ts:27-37`; callers at `WatchlistPanel.tsx:265`, `PortfolioPanel.tsx:504` |
| WLD-T-3 | The 419 `kite-session-expired` reconnect cue is emitted and never consumed — the user sees the raw slug every morning | high | `brokers.py:184-188` emits; zero `419` hits in `src/`; `BrokerReadsSection.tsx:52-53` |
| WLD-T-4 | Financial statements exist as REST routes but are not registered capabilities; the fundamentals substrate is ~40 point-in-time TTM scalars | high | `routers/fundamentals.py:177,183,189` exist; zero catalog hits; `models/fundamentals.py:46-137` |
| WLD-T-5 | No way to add an arbitrary MCP server; exactly two hardcoded subprocesses | high | zero hits for `mcp_servers\|add_mcp\|external_mcp`; `routers/mcp.py:28,44` |
| WLD-T-6 | No earnings-call transcript capability | high | zero `transcript` hits in `catalog.py`; only incidental via `research/disclosures.py:4` |
| WLD-T-7 | The India results calendar is fetched but deliberately unregistered; `earnings_upcoming` defaults to ten US mega-caps | high | `earnings_provider.py:63-76`; `research/disclosures.py:185-191` says so verbatim |
| WLD-T-8 | Promoter pledge exists only as a word in a category string | high | one grep hit repo-wide: `catalog.py:659` |
| WLD-T-9 | No bulk-deal, block-deal or SAST tracking, while the US insider equivalent ships | high | zero repo hits; `routers/disclosures.py` has 3 routes; `sec_insider_transactions` at `catalog.py:625` |
| WLD-T-10 | `shareholding_pattern` **does** return the parsed FII/DII split and its description + handler note both deny it | medium | `bse_provider.py:781-790`, `corporate_disclosures.py:469-471,507-538` vs `disclosure_tools.py:85-89`, `catalog.py:687-692` |
| WLD-T-11 | No composite score glyph — nothing in a watchlist row is triage-able or alertable | medium | no score capability in `catalog.py` |
| WLD-T-12 | No market-observed open interest and no options chain | medium | zero `open_interest` hits; Greeks computed only (`catalog.py:756`) |
| WLD-T-13 | No segment revenue or operational-metric data | medium | no segment capability; XBRL machinery exists at `bse_provider.py:617-790` |
| WLD-T-14 | Broker onboarding asks for a paid key + secret + manual token paste to deliver less than Zerodha's free keyless path ⚠ Tier-4 adjacent | medium | `brokers/kite.py:13-17`; `routers/brokers.py:415` |

### Corrections and dismissals made during verification

Three claims carried by the world sweeps did **not** survive contact with the code, and are recorded
here rather than filed:

- **"FII/DII is unparsed behind an XBRL link" (TSG-4) is wrong.** It *is* parsed, merged across
  lanes, and stamped with honest provenance (`bse_provider.py:781-790`,
  `corporate_disclosures.py:507-538`). The real defect is the opposite and worse: the tool
  description and the handler's own note tell the model the data is not there. Refiled as
  `WLD-T-10` with the corrected mechanism.
- **"No backtest-on-screen loop" (TSG-8) is not a gap for an agent-native product.** `screener_run`
  returns symbols and `run_custom_backtest` takes a `symbols` array (`catalog.py:394,858`) — the
  agent composes the two without new plumbing. Dropped; do not carry it into the register.
- **"Export is flat CSV, not a fillable Excel model" (TS-4) is a differentiator, not table stakes.**
  Folded into OPP-14. What *is* table stakes is a CSV export that actually writes a file, which is
  `WLD-T-2` and is a stronger finding than the one the sweep was looking for.

Also **not** filed as gaps, deliberately: live mid-call concall transcription (a vendor dependency —
Perplexity bought Quartr access; the after-the-fact transcript is the table-stakes half, `WLD-T-6`),
and anything touching live broker order execution (out of scope by decision).

---

## COMPETITOR WATCH

**OpenBB folded — 2026-08-25.** The reference "open-source Bloomberg" is shutting down as a company
and open-sourcing Workspace, the Open Data Platform, Copilot and the Excel add-in under a permissive
licence; the co-founder states the firm "couldn't find the product-market fit needed to build a
sustainable business" (https://openbb.co/blog/openbb-belongs-to-everyone/).
**What it changes:** (a) the "why not just use OpenBB?" objection inverts — it is now an abandoned
codebase anyone may fork, and *being maintained* is a differentiator; (b) Vysted's AGPL-3.0 +
commercial dual licence is now the stricter of the two; (c) it is a cautionary datapoint about the
shared business model, and the stated cause was PMF, not technology; (d) OpenBB had already
abandoned the *terminal* form factor for a browser workspace, so Vysted's native-desktop bet is a
deliberate contrarian position that should be defended out loud (local-first, keychain, offline),
not assumed. **Action: audit the repo's positioning docs for text that still treats OpenBB as a live
commercial incumbent.**

**Fincept Terminal — the near-identical clone.** Native desktop (C++20 + Qt6) with an embedded Python
analytics runtime, 37 BYOK AI agents, MCP tool orchestration, a drag-and-drop node editor, **16 broker
integrations including Zerodha / Angel One / Upstox / Fyers**, and **AGPL-3.0 free + a ~$10,200/yr
commercial licence** (https://www.solosoft.dev/post/fincept-terminal-open-source-2026/, 2026-05-01).
Same architecture, same licence model, same India broker set. Its own coverage lists the openings:
"Meme token launch created credibility concerns", "API credits expire after one month", "Strict
dependency requirements complicate source builds", "Not a Bloomberg replacement for professionals".
**What it changes:** the launch narrative needs an explicit differentiation position — no token,
pure BYOK with nothing to expire, a signed single-binary install, and a test-enforced safety
architecture. Depth of *India disclosure* understanding (pledge, SAST, bulk/block, FII/DII with
provenance) is the axis a 16-broker breadth play does not cover.

**Fey absorbed — 2025-08-27.** Wealthsimple acquired the design benchmark for research-first retail
terminals; `fey.com/features` now serves only an acquisition notice. The niche is vacant (OPP-17).

**Also on the board.** Perplexity Finance is free, India-live, and shipping fast (NL screener, live
Indian concall transcription via Quartr, Tasks) — but has no Indian book (Plaid is US/Canada), has a
documented 1000× filing-scale failure, and does not watch. Screener's 2026 changelog is ratio depth,
industry aggregates and data completeness — **not an agent** — which means the best Indian
fundamentals dataset is not coming after this position, but also that it stays locked in a web UI
with no official API. Koyfin, the best global dashboard, lists **no AI capability at any tier up to
$299/mo** and does not cover India (https://www.koyfin.com/pricing-llm-info/) — "agent-native +
India" is uncontested at the top of the market. Fiscal.ai is the sharpest conceptual competitor
(AI over filings and transcripts, segment KPIs, an MCP surface) and is cloud SaaS, metered at
10/300/500 prompts a month, with no India depth. TradingView shipped its agent as a **browser
extension in a side panel**, rationed by plan, and it is a technical-analysis copilot — nobody at
the mass-market tier is doing agent-first *fundamental* research. And `asymmetrica/sextant`
(TypeScript, "agent-native (MCP)", multi-asset) is a zero-star early entrant worth a periodic look.

---

## Traceability — source opportunity → ledger entry

| Source | Mapped to |
|---|---|
| PS-O1 scale witness · OB-O5 numeric-trust benchmark | OPP-2, OPP-3 |
| PS-O4 stateful watcher · PS-O6 phrase alerts · OB-O7 scheduled research · FT-O-3 free alert frequency | **OPP-1** (+ `WLD-T-1`) |
| PS-O7 trust visible · FT-O-6 provenance as product · OB-O8 lineage | OPP-3, OPP-12 |
| PS-O3 · OB-O2 keyless connect · OB-O12 daily-login tax | OPP-5 (+ `WLD-T-3`, `WLD-T-14`) |
| OB-O3 add any MCP server | OPP-6 (+ `WLD-T-5`) |
| OB-O6 portfolio-aware research | OPP-7 |
| FT-O-9 concall guidance vs delivery | OPP-4 (+ `WLD-T-6`, `WLD-T-7`) |
| FT-O-7 pledge derivative · FT-O-8 forensic score | OPP-8 (+ `WLD-T-8`) |
| PS-O5 filing-grounded QA · FT-O-2 BYOK unmetered | OPP-9 |
| FT-O-4 show the query | OPP-10 |
| FT-O-5 named workflows | OPP-11 |
| OB-O4 US-centric MCP · OB-O14 licensed India fundamentals · FT-O-12 MCP validated | OPP-13 |
| FT-O-10 operational metrics · PS-O8 industry aggregates · PS-TS-4 Excel export | OPP-14 |
| OB-O13 OI + options | OPP-15 (+ `WLD-T-12`) |
| PS-O2 broker-entitlement real-time | OPP-16 |
| FT-O-1 vacant niche · OB-O1 licence · OB-O9 stricter than Zerodha · OB-O10 credibility · FT-O-11 Koyfin vacuum | OPP-17 |
| OB-O11 third-party agent protocol | OPP-18 |

34 source opportunities → **18 deduplicated entries**. Nothing was dropped silently: every source
id above appears exactly once.
