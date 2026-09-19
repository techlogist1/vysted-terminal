# R15 Census — World sweep: Perplexity Finance & Screener.in AI

**Sweep:** `WORLD-RES` (world research, competitive/benchmark)
**Date of research:** 2026-09-19
**Method:** live web (WebSearch + WebFetch). Every claim carries a URL + quote or a concretely
described observation. Fetch failures are labelled inline.
**Scope note:** live broker order execution is deliberately out of this release — nothing below
counts it as a gap.

**Fetch blocks encountered (labelled honestly):**

- `https://www.perplexity.ai/changelog/*` — **HTTP 403 Forbidden** to WebFetch. Perplexity's own
  changelog could not be read directly; Perplexity-side claims below are sourced from press
  coverage, the CEO's own posts as quoted in press, and third-party reviews, never from the
  changelog itself.

---

## PART A — What Perplexity Finance does TODAY (Sept 2026)

### A1. India market data is live, free, and first-party-positioned

Perplexity Finance launched India coverage in Aug 2025 and has kept expanding it.

> "Perplexity Finance expands to Indian stock markets. Users will now have access to live stock
> prices, news, & latest information from BSE and NSE across Perplexity's desktop, mobile web and
> mobile apps"
> — Vikas SN (journalist), X, Aug 2025, https://x.com/tsuvik/status/1955581467368857890

marketcalls.in (2025-08-14, Rajandran R) enumerates the India surface:

> "live NSE and BSE stock quotes" … "Historical price and volume data with charts" … "Upcoming
> earnings calendars" … watchlists and sentiment meters … market context from "reliable news
> sources and filings"
> — https://www.marketcalls.in/perplexity/perplexity-finance-now-covers-indian-markets-why-traders-should-care.html

Critically, it is **free**: the same piece emphasises the data is "up-to-the-second" and available
"at no cost". That is the pricing floor Vysted competes against for quotes/news.

### A2. Live Indian earnings-call transcription + concall calendar (Aug 2025)

> "Perplexity has augmented its Finance dashboard with the ability to transcribe Indian public
> companies' quarterly earnings calls live, as well as show schedules for post-results conference
> calls." … Until then "the dashboard only showed transcripts for U.S. stocks."
> — TechCrunch, 2025-08-18,
> https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/

CEO Aravind Srinivas, as quoted in that coverage, framed the goal as adding "a lot more value to
Indian equity markets research in the coming days." The transcription rides a **Quartr**
integration (third-party vendor), paired with streaming audio, speech-to-text and structured
timestamps — see https://www.aicerts.ai/news/ai-meets-markets-perplexity-finance-brings-real-time-stock-transcripts-to-india/

**This matters for Vysted:** live concall transcription is a vendor-dependency moat, not an LLM
moat. Perplexity bought it. Screener has concall *notes* but not live transcription.

### A3. Natural-language screener, covering US **and Indian** equities

> "Natural language powered Stock Screener on Perplexity Finance."
> — Aravind Srinivas (CEO), X, Jul 2025, https://x.com/AravSrinivas/status/1948812710952796576

> "a natural-language screener for US and Indian equities"
> — Helm Terminal, "Perplexity for Stock Research in 2026",
> https://helmterminal.dev/blog/perplexity-stock-research

Interaction model: a prompt like "$10B+ market cap, $25B+ revenue, 10% YoY revenue growth, sorted
by P/E ratio" returns a filtered, column-configurable, sortable table.

### A4. Portfolio via Plaid (US/Canada only), watchlists, alerts, Tasks

> "Around March 2026, Perplexity partnered with Plaid to launch Portfolio in the US and Canada:
> connect a brokerage, get read-only aggregation of holdings and transactions with AI analysis on
> top."
> — synthesis of https://www.wealthmanagement.com/artificial-intelligence/perplexity-upgrades-finance-capabilities
> and https://helmterminal.dev/blog/perplexity-stock-research

Full 2025→2026 shipped list per Helm Terminal: "a market heatmap, an Earnings Hub, a
natural-language screener, portfolio tracking via Plaid, price alerts, and automated Tasks."
Also "insider and politician trade data" and "Tasks, which run a recurring research query on a
schedule."

**Two hard boundaries visible here:**

1. **Portfolio aggregation is US/Canada only.** Plaid does not cover Indian brokers. An Indian
   investor on Perplexity Finance has watchlists but **no real holdings/P&L context**.
2. Pricing: "The Finance hub is largely free, Pro is $20 a month, and a $200-a-month Max tier gets
   agent features first" (Helm Terminal, ibid.).

---

## PART B — Where Perplexity Finance FAILS (documented)

### B1. The unit/scale misread — confirmed, with a narrative built on top

This is the single most important documented failure for a data-trust product.

> "Perplexity read a thinly covered company's 10-K revenue without applying the 'in thousands'
> denominator, got the number wrong by a factor of 1,000, and then built a confident story about a
> 99.8% revenue collapse."
> — Helm Terminal (May 2026 four-model test: ChatGPT / Claude / Perplexity / Gemini),
> https://helmterminal.dev/blog/perplexity-stock-research

The reviewer's own emphasis: the arithmetic error was not the scary part — **the narrative on top
of it was**. The model did not flag uncertainty; it explained the fabricated collapse.

The same review's verdict on coverage depth:

> "best used for quick lookups on major, well-covered stocks. On small caps and thin coverage,
> treat every figure as an unverified starting point."

**Direct read-across to India:** Indian filings are denominated in ₹ lakh / ₹ crore / ₹ million
inconsistently *within the same document set* (standalone vs consolidated, XBRL vs PDF, exchange
filing vs annual report). The failure mode Helm documented on a US 10-K "in thousands" header is
strictly *easier* to trigger on an Indian small-cap annual report. No source found that tests this
on Indian filings specifically — flagged as an untested-but-high-probability extension, not as a
verified claim.

### B2. Hallucinated financial data is an acknowledged, user-reported class

Perplexity's own community forum carries a thread titled **"Financial Data Hallucinations"**:
https://community.perplexity.ai/t/financial-data-hallucinations/145 — with users reporting the API
returning inaccurate/hallucinated stock prices.

Broader context, same class: a 2026 multi-model audit found hallucinated facts in up to **41%** of
finance-related AI responses across engines (https://learn.g2.com/tech-signals-ai-hallucinations-and-research).
Not Perplexity-specific; it is the category's failure rate, which is exactly the bar a
"data trust" moat has to clear.

### B3. It retrieves; it does not reason about *you*, and it does not *watch*

> "retrieves, it does not reason about you" — it summarises consensus without considering your
> specific position size, cost basis, or investment thesis.
> "answers, it does not watch" — it responds to queries rather than proactively monitoring
> positions between sessions.
> — Helm Terminal, https://helmterminal.dev/blog/perplexity-stock-research

(Perplexity's "Tasks" partially attacks the second one — a recurring scheduled research query —
but it is a scheduled *prompt*, not a monitor with state over your book.)

---

## PART C — What Screener.in / Screener AI does TODAY

### C1. Screener AI — launched 2025-07-08, document-grounded, pay-per-answer

> "intelligently reads company documents - like Annual reports and Earnings call transcripts - and
> extracts key insights and answers to your questions in seconds."
> — Screener changelog, "🚀 Introducing Screener AI", updated 2025-07-08,
> https://www.screener.in/docs/changelog/Screener-AI/

The product page (https://www.screener.in/ai/) is explicit about the positioning — it is
**filing-grounded, not search-grounded**:

> "direct access to company filings such as annual reports and earning calls"
> "No uploads — We auto-upload the relevant documents"
> "No prompt engineering — Just ask in plain English"
> "Hours of research, done in seconds"

**The pricing model is the striking part — metered, token-transparent, per-answer:**

> costs average "around ₹10-30 per answer" but "can even go up to ₹100 if the AI reads a lot of
> documents"; raw rate "₹100 per million input tokens and ₹800 per million output tokens"
> — https://www.screener.in/ai/

And they admit the problem on their own marketing page: "the costs of answers are quite high
sometimes" and they are "constantly working on new ways to reduce this cost." There are two
intelligence tiers (a standard higher-cost mode and a cheaper "General Intelligence" mode).

Premium subscribers get "₹500 AI Credits free".

### C2. Data density and the free/premium wall (primary source: screener.in/premium/)

Verbatim from https://www.screener.in/premium/ (fetched 2026-09-19):

| Capability | Hobby Investor (₹0/yr) | Active Investor (₹4,999/yr) |
|---|---|---|
| Stock alerts | 10 | 800 |
| Screen alerts | 2 | 75 |
| Phrase alerts | 2 | 50 |
| Follow companies | up to 50 | "Unlimited" |
| Quick ratios | 18 | 60 |
| Comparison columns | 15 | 55 |
| Key Insights | "20 per month" | "Unlimited" |
| AI Summaries | "10 per month" | "Unlimited" |
| Screener AI | "Free Credits worth ₹500" | credits included |
| Download results, industry filter | ✗ | ✓ |
| Multiple watchlists, priority support | ✗ | ✓ |

From https://www.screener.in/features/ (fetched 2026-09-19):

- **"10+ Years of Data"** — "Understand cyclicality of businesses by seeing their performances over
  long term"; **"Run queries on 10 to 15 years of financial data"**.
- **Schedules** — line-item breakdowns (raw materials, employee costs).
- **Segment results** — combined, 10 years.
- **"Export to Excel"** — "Export data into structured excel sheets. Create your own models", plus
  **Custom Upload**: upload your own Excel sheet with formulas/formatting and Screener fills it.
  This is the killer feature nobody else in India replicates well.
- Consolidated + standalone auto-selection; custom columns; custom ratios.
- Alerts: "Create your stock-screen once and forget"; watchlist news feeds; insider trades;
  credit-rating changes; announcements feed.
- Peer comparison, volume charts **with delivery percentages**, auto Pros/Cons checklist.
- Product prices for 9,000+ products from export/import records (10,000+ with 10y history per the
  premium page) — an unusual, genuinely differentiated dataset.

**Explicitly NOT on the features page:** API access, real-time prices, derivatives, mobile app,
call transcripts (only concall *notes* / insights).

### C3. Screener's 2026 shipping cadence (changelog, fetched 2026-09-19)

From https://www.screener.in/docs/changelog/ — the last twelve months are small, high-taste
increments, not big swings:

- **Sept 2026** — company logos beside names ("a visual cue when you move between companies");
  filter the latest-quarterly-results page **by industry**; open the exchange's F&O/derivatives
  page directly from a company page ("without searching for the company again").
- **Jul 2026** — "Enhanced Ratio Library": new return-quality and historical-valuation ratios
  (Med ROCE, Historical PBV) usable in custom screens.
- **May 2026** — Corporate Actions tab now includes **preferential issues**.
- **Apr 2026** — cash-flow statement gains **Free Cash Flow** and **CFO/OP ratio** ("how much of
  the reported profit turns into cash").
- **Mar 2026** — "Screener Insights": "Track historical trends and future estimates of critical
  industry metrics - all in one place."
- **Jan 2026** — **"Download Your Company Notes"**: "You can now export all your company notes from
  Account → Notebook → Download."

Read that list as a roadmap tell: Screener is investing in **ratio depth, industry-level
aggregates, and data completeness** — not in an agent.

### C4. Screener's documented weaknesses

From the Strike review (https://www.strike.money/reviews/screener-in, 2026):

> "Screener.in does not offer any broker integration"
> "customer support services are restricted to premium users only"
> "critical ratios and data analysis tools are missing" [at times]
> user complaint quoted: *"The support team is very bad. They are not able to fix the issue."*

Also per that review: **no technical-analysis tooling and no native mobile app** (the site is
mobile-responsive only). Coverage: 4,000+ Indian listed companies, 10+ years.

---

## PART D — What users PRAISE and COMPLAIN about

### D1. Perplexity — praised for citations, criticised for what citations hide

Praise (aggregated user reviews, G2 / CheckThat.ai — https://checkthat.ai/brands/perplexity/reviews,
https://www.g2.com/products/perplexity/reviews): inline citations on every answer make facts
verifiable; live web search beats a training cutoff; users specifically value being able to demand
**primary** sources — "transcripts and SEC filings".

The complaints are the more useful half:

- **Source quality is the ceiling.** Accuracy "is only as good as its sources, and it can sometimes
  treat low-quality forum posts like old Reddit threads as established facts or misattribute quotes
  to the wrong citations."
- **Citations manufacture false confidence.** "the presence of sources can create a false sense of
  certainty, and if the sources are mid, outdated, or all echoing the same assumption, the answer
  inherits that bias."
- **Hallucinations traced to Reddit-sourced misinformation** picked up by the retriever.

Combine D1 with B1: a wrong number, a confident narrative, and a citation next to it. That is
precisely the shape of the failure a "data trust" moat exists to prevent.

### D2. The vendor tell — Perplexity's numbers are a third-party feed

> "The platform sources its financial data from Financial Modelling Prep."
> — Wikipedia, *Perplexity AI*, https://en.wikipedia.org/wiki/Perplexity_AI

And their own developer docs disclaim it:

> "Market data may be delayed, incomplete, or unavailable for some symbols. `finance_search` is for
> informational use only…" — coverage varies by "Symbol and exchange availability", "Geographic
> regions and source data freshness".
> — https://docs.perplexity.ai/docs/agent-api/tools/finance-search (fetched 2026-09-19)

So Perplexity's India numbers are **one aggregator hop away from the exchange**, self-disclaimed as
possibly delayed/incomplete. Vysted's NSE/BSE-direct lane
(`sidecar/services/research/range_check.py:5-10` — "exchange-direct EOD history … the nse_direct →
jugaad → bse lane") is a *structurally* better provenance story, not just a different one.

### D3. Screener — praised for depth and a generous free tier, criticised for support and breadth

Praise (Strike review, 2026, https://www.strike.money/reviews/screener-in): accurate, reliable data;
simple interface usable by beginners; "highly generous and powerful free version"; "the undisputed
champion in India" for deep fundamental analysis.

Complaints, verbatim from the same review:

> "Screener.in does not offer any broker integration"
> "customer support services are restricted to premium users only"
> "critical ratios and data analysis tools are missing" [at times]
> user quote: *"The support team is very bad. They are not able to fix the issue."*

Plus: **no technical-analysis tooling, no native mobile app** (responsive site only).

### D4. Screener has NO official API — the whole ecosystem scrapes it

There is no official screener.in data API. The entire developer ecosystem is scrapers and
third-party wrappers: Apify actors (https://apify.com/solidcode/screener-in-scraper/api/cli,
https://apify.com/shashwattrivedi/screener-in/api), Parse.bot
(https://parse.bot/marketplace/fedcb439-5e37-4ca5-b7b3-2004ff71686d/screener-in-api), Spider Cloud,
Anakin, and community scrapers (https://github.com/jgera/screener.in). Anakin's pitch is explicitly
"handles the browser, proxies, anti-bot, and parsing, with updates when Screener.in changes its
markup" — i.e. the data is locked in a web UI and stays there.

**Read:** the best fundamental dataset in India is unaddressable by an agent except through
brittle scraping. An agent-native terminal that owns its own exchange-direct pipeline does not
have that dependency.

---

## PART E — The market context that changed in the last week

### E1. TradingView put NSE/BSE free users on a 15-minute delay (Sept 2026)

Published **2026-09-16**, three days before this sweep:

> Free users now see a 15-minute delay on NSE and BSE charts, marked with a "D" badge.
> "Real-time official data from the Indian exchanges carries terms and fees, and TradingView appears
> to be enforcing those terms more strictly for free accounts than it did before."
> Trader reaction: "fifteen minutes is long enough for the entire move to be gone before the chart
> even shows it" — users "migrating to broker-native platforms like Zerodha Kite and Upstox that
> offer real-time feeds."
> — https://businessupturn.com/finance/stock-market/tradingview-free-users-hit-with-a-15-minute-delay-on-nse-and-bse-data-and-how-to-switch-real-time-back-on/

This is the single most exploitable market event in this sweep. The licensing economics that forced
TradingView's hand **do not bind a BYOK local-first desktop app**: the user's own broker entitlement
is the licence. Vysted's Kite read-only integration is already the right shape for it.

### E2. Zerodha already ships an MCP — and it is read-only by design

> "Kite MCP … allows AI assistants to interact with real-world data and services" — supports Claude,
> Cursor, Windsurf, VS Code/Copilot. Exposes "current holdings, positions, account margins, P&L,
> market quotes, and trading history." **"order placement is not available except for GTT orders."**
> Auth: Kite 2FA, "Your Zerodha credentials never pass through Claude." Remote endpoint:
> `https://mcp.kite.trade/mcp`. Known limits: "Order placement, historical trade data, portfolio
> data, and some other features are currently unavailable."
> — Zerodha Z-Connect, 2025-05-20,
> https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp

And the cautionary tale attached to it: Perplexity's Comet browser was reported executing a trade on
Zerodha **with no manual click**, prompting exactly the concerns Vysted's §6.5 model was built for —
"unauthorized trades risk", "AI misinterprets instructions", demands for "clearer visibility into AI
decision-making processes and fail-safes"
(https://opentools.ai/news/perplexity-ais-comet-browser-executes-no-click-trades-on-zerodha-surprising-users).

**Two consequences for Vysted:**

1. The Perplexity↔Zerodha tie-up that was teased in Aug 2025 (Nikhil Kamath: "Absolutely, setting up
   a call for Monday…", Srinivas: "Will have something to share soon" —
   https://www.businesstoday.in/amp/latest/corporate/story/setting-up-a-call-on-monday-nikhil-kamath-and-aravind-srinivas-weigh-zerodha-perplexity-tie-up-488691-2025-08-09,
   https://www.storyboard18.com/digital/aravind-srinivas-hints-at-perplexity-zerodha-collaboration-after-india-finance-launch-78804.htm)
   **has no confirmed first-party product** in anything this sweep could find. It materialised as a
   generic MCP any assistant can use. Vysted is not locked out.
2. `mcp.kite.trade/mcp` is a *ready-made, Zerodha-blessed, read-only* portfolio surface — and Vysted
   is an MCP host. Today Vysted's Kite path is a manual `request_token` paste
   (`CLAUDE.md`, Broker & credentials; `sidecar/services/brokers/kite.py`). That is strictly worse
   UX than the flow Zerodha ships for its competitors' agents.

### E3. Perplexity's portfolio moat does NOT extend to India

Portfolio is Plaid-backed: "Portfolio pulls investment account data from Plaid, including holdings,
transactions, balances, and securities data across linked accounts" and "is built for insight and
does not place trades or move funds for a user"
(https://www.wealthmanagement.com/artificial-intelligence/perplexity-upgrades-finance-capabilities).
Plaid's investment aggregation is US/Canada. Helm Terminal describes the launch as "Portfolio in the
US and Canada" (https://helmterminal.dev/blog/perplexity-stock-research).

**So the Indian Perplexity Finance user has: free quotes, news, transcripts, a NL screener — and no
book.** Holdings-aware research is an open lane in India.

---

## RAW FINDINGS (merge shape)

```json
[
  {"raw_id":"WORLD-RES-1","title":"Perplexity misreads filing scale ('in thousands') and narrates the fabricated result","severity":"critical","area":"research","subsystem":"competitor/Perplexity Finance","repro":"May 2026 four-model test: ask Perplexity for a thinly-covered company's 10-K revenue","evidence":"https://helmterminal.dev/blog/perplexity-stock-research — \"got the number wrong by a factor of 1,000, and then built a confident story about a 99.8% revenue collapse\"","notes":"Indian filings mix lakh/crore/million within one document set — same failure is EASIER to trigger here. No source found testing it on Indian filings; flagged as untested extension, not verified."},
  {"raw_id":"WORLD-RES-2","title":"Perplexity staff answer financial hallucination reports with prompt workarounds, not fixes","severity":"high","area":"research","subsystem":"competitor/Perplexity API","repro":"sonar-reasoning-pro returned wrong prices for QBTS/CLSK/IONQ","evidence":"https://community.perplexity.ai/t/financial-data-hallucinations/145 — staff (vikvang, 2025-05-16): use \"search domain filters\", increase \"search context size\", add \"If you're not sure, respond with 'I don't know'\"; \"LLMs can sometimes return unpredictable output (hallucinations)\"","notes":"No bug confirmation, no fix timeline. The category has no architectural answer — only a discipline."},
  {"raw_id":"WORLD-RES-3","title":"Perplexity's India numbers are an aggregator hop (Financial Modeling Prep) and self-disclaimed as possibly delayed/incomplete","severity":"medium","area":"data","subsystem":"competitor/Perplexity Finance","repro":"read Perplexity's own finance_search docs","evidence":"https://en.wikipedia.org/wiki/Perplexity_AI (\"sources its financial data from Financial Modelling Prep\"); https://docs.perplexity.ai/docs/agent-api/tools/finance-search (\"Market data may be delayed, incomplete, or unavailable for some symbols\")","notes":"Provenance is Vysted's attackable surface: NSE/BSE-direct beats one-hop aggregator."},
  {"raw_id":"WORLD-RES-4","title":"Perplexity Portfolio is Plaid-backed, US/Canada only — Indian users get no holdings context","severity":"medium","area":"data","subsystem":"competitor/Perplexity Finance","repro":"try to connect an Indian broker to Perplexity Portfolio","evidence":"https://www.wealthmanagement.com/artificial-intelligence/perplexity-upgrades-finance-capabilities; https://helmterminal.dev/blog/perplexity-stock-research (\"Portfolio in the US and Canada\")","notes":"Holdings-aware research in India is an open lane."},
  {"raw_id":"WORLD-RES-5","title":"Perplexity answers, it does not watch — no stateful monitoring of a user's book","severity":"medium","area":"agent","subsystem":"competitor/Perplexity Finance","repro":"n/a — architectural","evidence":"https://helmterminal.dev/blog/perplexity-stock-research — \"retrieves, it does not reason about you\"; \"answers, it does not watch\"","notes":"'Tasks' (scheduled recurring query) is a scheduled prompt, not a monitor with state."},
  {"raw_id":"WORLD-RES-6","title":"Screener AI is metered per-answer at ₹10-100 and Screener itself calls the cost high","severity":"medium","area":"research","subsystem":"competitor/Screener AI","repro":"read screener.in/ai pricing","evidence":"https://www.screener.in/ai/ — \"around ₹10-30 per answer\"… \"can even go up to ₹100 if the AI reads a lot of documents\"; \"the costs of answers are quite high sometimes\"","notes":"A BYOK terminal where the user pays their own provider directly has no margin to defend and no per-answer meter anxiety."},
  {"raw_id":"WORLD-RES-7","title":"Screener has no official API — the whole ecosystem scrapes it","severity":"medium","area":"data","subsystem":"competitor/Screener.in","repro":"search for a screener.in API","evidence":"https://apify.com/solidcode/screener-in-scraper/api/cli; https://parse.bot/marketplace/fedcb439-5e37-4ca5-b7b3-2004ff71686d/screener-in-api; https://github.com/jgera/screener.in","notes":"India's best fundamental dataset is agent-unaddressable except by brittle scraping."},
  {"raw_id":"WORLD-RES-8","title":"Screener ships no transcripts, no real-time, no derivatives, no API, no mobile app","severity":"low","area":"data","subsystem":"competitor/Screener.in","repro":"read screener.in/features","evidence":"https://www.screener.in/features/ (concall NOTES only; Sept 2026 changelog only LINKS OUT to the exchange F&O page); https://www.strike.money/reviews/screener-in (\"does not offer any broker integration\", no TA tools, no mobile app)","notes":"Screener's Sept 2026 F&O 'feature' is a deep link, not data."},
  {"raw_id":"WORLD-RES-9","title":"TradingView moved NSE/BSE free users to 15-minute delayed data; traders migrating to broker-native feeds","severity":"high","area":"data","subsystem":"market context","repro":"open an NSE chart on a free TradingView account — 'D' badge","evidence":"https://businessupturn.com/finance/stock-market/tradingview-free-users-hit-with-a-15-minute-delay-on-nse-and-bse-data-and-how-to-switch-real-time-back-on/ (2026-09-16) — \"fifteen minutes is long enough for the entire move to be gone\"","notes":"BYOK/broker-entitlement sidesteps the licensing economics that forced this. Live demand event, 3 days old."},
  {"raw_id":"WORLD-RES-10","title":"Zerodha ships a read-only Kite MCP that Claude/Cursor/Windsurf already use — Vysted's Kite flow is a manual token paste","severity":"high","area":"lifecycle","subsystem":"broker/kite","repro":"compare mcp.kite.trade/mcp onboarding to Vysted's request_token paste","evidence":"https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp (2025-05-20) — \"order placement is not available except for GTT orders\"; \"Your Zerodha credentials never pass through Claude\". Vysted: sidecar/services/brokers/kite.py + CLAUDE.md 'Manual request_token paste is the v1 flow'","notes":"Vysted is already an MCP host. A Zerodha-blessed read-only surface exists and is better UX than what Vysted ships."},
  {"raw_id":"WORLD-RES-11","title":"Vysted has no alerts subsystem at all; both benchmarks do","severity":"high","area":"agent","subsystem":"alerts","repro":"grep the sidecar for a price/screen/phrase alert feature — none exists","evidence":"Vysted: no alert capability in sidecar/services/agent_tools/catalog.py (48 capabilities, none alert-shaped); the only 'alert' hits in src/ are ARIA roles/banners. Screener: https://www.screener.in/premium/ (10/800 stock, 2/75 screen, 2/50 phrase alerts). Perplexity: price alerts + Tasks (https://helmterminal.dev/blog/perplexity-stock-research)","notes":"Table stakes on both benchmarks. Screener's 'phrase alert' (fire when a phrase appears in a filing) is the interesting one — it is the cheapest bridge from Vysted's existing announcements feed."},
  {"raw_id":"WORLD-RES-12","title":"Vysted has no multi-year financial statements in the agent catalog; Screener screens on 10-15 years","severity":"high","area":"data","subsystem":"fundamentals/screener","repro":"ask the agent for a 10-year revenue series","evidence":"Vysted: sidecar/models/fundamentals.py:46 — ~40 POINT-IN-TIME TTM fields, no time series; income/balance/cashflow exist only as provider calls (sidecar/services/yfinance_provider.py:418,431,442) and are NOT registered capabilities in catalog.py. Screener: https://www.screener.in/features/ — \"Run queries on 10 to 15 years of financial data\", plus Schedules (line-item breakdowns) and 10-year Segment Results","notes":"Screener's moat is time depth + line-item depth. Vysted's screener prunes against a yfinance-derived store (sidecar/services/screener.py:18-36) — the same ceiling."},
  {"raw_id":"WORLD-RES-13","title":"Screener's export-to-Excel with a user's OWN template is unmatched; Vysted exports flat CSV only","severity":"medium","area":"data","subsystem":"export","repro":"compare Screener's custom-template Excel export to Vysted's CSV download","evidence":"https://www.screener.in/features/ — \"Export data into structured excel sheets. Create your own models\" + Custom Upload (upload your sheet with formulas/formatting, Screener fills it); Vysted: src/lib/csv.ts (flat RFC-4180 CSV, used by watchlist/portfolio/screener results)","notes":"This is the feature that keeps Indian analysts on Screener Premium. Also Jan 2026: notes export (Account → Notebook → Download)."},
  {"raw_id":"WORLD-RES-14","title":"Perplexity ships live Indian earnings-call transcription (Quartr); Vysted only reads transcript PDFs after the fact","severity":"medium","area":"research","subsystem":"disclosures/earnings","repro":"compare a live concall on Perplexity vs Vysted during an Indian earnings call","evidence":"https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/ (\"transcribe Indian public companies' quarterly earnings calls live\" + concall schedules); https://www.aicerts.ai/news/ai-meets-markets-perplexity-finance-brings-real-time-stock-transcripts-to-india/ (Quartr, streaming audio + STT + timestamps). Vysted: sidecar/services/research/disclosures.py:4 — transcripts arrive only as announcement attachment_url PDFs","notes":"Live transcription is a VENDOR moat, not an LLM moat. Perplexity bought Quartr access; Screener has notes only. The concall SCHEDULE half is cheap — Vysted already fetches the NSE results calendar (disclosures.py:15)."},
  {"raw_id":"WORLD-RES-15","title":"Citations create false certainty — the failure mode Vysted's cross-witness discipline is built against, but it is not marketed or surfaced as a differentiator","severity":"medium","area":"research","subsystem":"research/trust","repro":"n/a — positioning","evidence":"World: https://checkthat.ai/brands/perplexity/reviews — \"the presence of sources can create a false sense of certainty\". Vysted: sidecar/services/research/range_check.py:12-17 and sidecar/services/market_cap_witness.py:16-18 both state \"DISCLOSE, never substitute\" (D56/D66/D68); sidecar/services/research/citecheck.py:216 ensure_citation_integrity","notes":"The discipline exists in code. Nothing in the brief UI tells the user THIS is what makes the number trustworthy."}
]
```

---

## OPPORTUNITIES FOR VYSTED

Each: what the world lacks or does badly → evidence → the Vysted capability it sits **one step** from.

### O1. Scale-witness on Indian filings ("the ₹ lakh/crore trap")

**World lacks:** Perplexity read a 10-K's "in thousands" header wrong by ×1,000 and then *explained*
the resulting 99.8% collapse (https://helmterminal.dev/blog/perplexity-stock-research, May 2026).
Its own staff's answer to financial hallucination reports is prompt hygiene, not a check
(https://community.perplexity.ai/t/financial-data-hallucinations/145).

**One step from:** Vysted already runs two independent numeric witnesses with an explicit
"DISCLOSE, never substitute" contract — `sidecar/services/research/range_check.py:12-17` (52-week
range vs exchange-direct history) and `sidecar/services/market_cap_witness.py:16-18` (market cap vs
a BSE-derived, non-provider share count). The extraction lane already recognises "crore"/"lakh" as
scale tokens (`sidecar/services/search/extract.py:75,86-87`) and semantics already renders INR at
÷1e7 (`sidecar/services/research/semantics.py:603-607`). **A third witness — assert the scale unit
declared in the document header against the magnitude of the extracted figure, and flag rather than
substitute — is the same wiring contract as the two that already ship.** This is the single
highest-leverage item in this sweep: it converts the benchmark's worst documented failure into a
visible Vysted guarantee.

### O2. Broker-entitlement real-time, exactly as TradingView withdraws it

**World does badly:** as of 2026-09-16, free TradingView NSE/BSE users are on a 15-minute delay and
"migrating to broker-native platforms like Zerodha Kite and Upstox that offer real-time feeds"
(https://businessupturn.com/...tradingview-free-users-hit-with-a-15-minute-delay...). Perplexity's
own docs disclaim freshness (https://docs.perplexity.ai/docs/agent-api/tools/finance-search).

**One step from:** Vysted is BYOK with a live read-only Kite integration and an exchange-direct
history lane (`range_check.py:5-10`, nse_direct → jugaad → bse). The user's own broker entitlement
is the licence — the economics that forced TradingView's hand do not apply to a local-first desktop
app. Quotes through the connected broker session is a provider-lane addition, not an architecture
change.

### O3. Adopt `mcp.kite.trade/mcp` instead of the manual token paste

**World does badly / well:** Zerodha ships a read-only MCP (holdings, positions, margins, P&L,
quotes, trade history; "order placement is not available except for GTT orders"; credentials never
pass through the assistant) that Claude, Cursor and Windsurf already consume
(https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp).
Vysted's v1 flow is a manual `request_token` paste. Meanwhile Comet's no-click Zerodha trade shows
exactly why a §6.5-grade confirm gate is a *feature*
(https://opentools.ai/news/perplexity-ais-comet-browser-executes-no-click-trades-on-zerodha-surprising-users).

**One step from:** Vysted already spawns and hosts MCP subprocesses (`src-tauri/src/openbb_mcp.rs`,
`sidecar/*_mcp_subprocess/`) and already enforces read-only broker wrappers (three-layer audit, per
`CLAUDE.md` Plugin contract). Pointing the Kite plugin at a remote MCP whose *upstream* is read-only
strengthens the safety story rather than weakening it — and kills the worst onboarding step Vysted
has. **⚠ Tier-4 adjacent:** changing the broker surface touches §6.5 — surface to the operator, do
not bake in.

### O4. The stateful watcher neither benchmark has

**World lacks:** Perplexity "answers, it does not watch" (Helm Terminal); its Tasks are scheduled
prompts. Screener's alerts are threshold/phrase triggers with no memory of *your* thesis. Neither
knows your cost basis in India (O: Plaid is US/Canada — see E3).

**One step from:** Vysted has durable detached agent runs with SQLite state and a budget guard
(`sidecar/services/run_manager.py`, `sidecar/services/runs_store.py`, `sidecar/services/budget_guard.py`)
and a local portfolio (`portfolio_add_position` / `get_portfolio` in `catalog.py`). A run that wakes
on the announcements feed and re-checks a *stored thesis against your held position* is the
composition of three things that already exist. **This is the "Jarvis" differentiator — nobody in
this sweep has it.**

### O5. Filing-grounded Q&A without a per-answer meter

**World does badly:** Screener AI is the right idea — "direct access to company filings", "No
uploads", "No prompt engineering" — but it is metered at "₹10-30 per answer … up to ₹100", and
Screener itself concedes "the costs of answers are quite high sometimes"
(https://www.screener.in/ai/). Every answer has a price tag hanging over it, which is precisely the
wrong incentive for exploratory research.

**One step from:** Vysted is BYOK — the user pays their own provider with no reseller margin, and
`sidecar/services/budget_guard.py` already meters tokens/spend/wall/steps per run with a stated
abort reason. Vysted already pulls the same corpus (`disclosures.py:4` — "merged BSE+NSE feed with
results PDFs and earnings-call transcripts as attachment_url", 50-announcement window at
`disclosures.py:36-40`) and the PDF lane already reads them. **Screener AI's product, at Screener AI's
grounding, with the cost meter pointed at the user's own key instead of a vendor's margin.**

### O6. Phrase alerts on the announcements feed

**World does:** Screener sells "phrase alerts" (2 free / 50 premium — https://www.screener.in/premium/):
fire when a phrase appears in a company's filings. Perplexity has price alerts only.

**One step from:** Vysted already fetches 50 announcements per researcher with PDF extraction
(`disclosures.py:36-40`, `services/search/extract.py`). A phrase watch over that feed is a query over
data already flowing — and it is the cheapest possible first alert, avoiding a whole
price-tick-alerting subsystem. (See also TS-1: Vysted has no alerts at all.)

### O7. Make the trust machinery visible

**World does badly:** users praise Perplexity's citations and simultaneously report that "the
presence of sources can create a false sense of certainty" (https://checkthat.ai/brands/perplexity/reviews).
Citations are table stakes; *disagreement between sources* is not.

**One step from:** Vysted computes conflicts already — `range_check.py` and `market_cap_witness.py`
both emit a labelled divergence into `derive_semantics`, and `citecheck.ensure_citation_integrity`
(`sidecar/services/research/citecheck.py:216`) strips invalid markers and softens unsupported
sentences. The brief renders typed blocks with a metric-card grid
(`src/modules/research/brief-blocks.tsx`, `deriveMetrics` returns null rather than fabricate).
**A "two sources disagree, here are both" card is a render of data the pipeline already produces** —
and it is the one thing in this sweep that neither benchmark can copy without rebuilding their
provenance.

### O8. Industry-level aggregates, the direction Screener is actually walking

**World signal:** Screener's 2026 changelog is not chasing agents — it is adding **Screener Insights**
("Track historical trends and future estimates of critical industry metrics", Mar 2026), an
industry filter on the quarterly-results feed (Sept 2026), return-quality and historical-valuation
ratios (Jul 2026), FCF and CFO/OP (Apr 2026) — https://www.screener.in/docs/changelog/.

**One step from:** Vysted bundles BSE/NSE sector maps
(`sidecar/services/resolver_masters/regenerate_india_sectors.py`) and `market_overview` /
`screener_run` capabilities. Peer/sector aggregates over the existing fundamentals store is an
evaluation-phase addition to `sidecar/services/screener.py`, not new plumbing.

**Opportunity count: 8.**

---

## TABLE-STAKES GAPS

Where this research shows Vysted is **behind** what a demanding Indian user already gets free.

### TS-1 — No alerts of any kind (HIGH)

Screener free: 10 stock + 2 screen + 2 phrase alerts; premium 800/75/50
(https://www.screener.in/premium/). Perplexity: price alerts plus scheduled Tasks
(https://helmterminal.dev/blog/perplexity-stock-research).
**Vysted: nothing.** No alert capability among the 48 in
`sidecar/services/agent_tools/catalog.py`; the only `alert` matches in `src/` are ARIA roles and
banner components. A user cannot leave the app and be told anything. Start with O6 (phrase alerts
over the announcements feed already being fetched), not with a tick-alerting subsystem.

### TS-2 — No multi-year financial statements reachable by the agent (HIGH)

Screener free tier screens on "10 to 15 years of financial data", with Schedules (line-item
breakdowns) and 10-year Segment Results (https://www.screener.in/features/).
**Vysted's `Fundamentals` model is ~40 point-in-time TTM fields with no time series**
(`sidecar/models/fundamentals.py:46`). Income statement / balance sheet / cash flow exist as
provider functions (`sidecar/services/yfinance_provider.py:418,431,442`) but are **not registered
capabilities** — the agent cannot call them. "Show me 10 years of revenue for this company" is a
question Vysted cannot answer and a free Screener account answers instantly.

### TS-3 — Screener depth of ratios/columns (MEDIUM)

Screener free gives 18 quick ratios and 15 comparison columns; premium 60 and 55
(https://www.screener.in/premium/), plus user-defined custom ratios and custom columns
(https://www.screener.in/features/). Vysted's screener evaluates against a yfinance-derived store
(`sidecar/services/screener.py:18-36`) bounded by the ~40 `Fundamentals` fields, with a `formula`
escape hatch. The *interaction* (agent writes the filters via `write_screener_filters`) is ahead;
the *substrate* is behind.

### TS-4 — Export is flat CSV, not a fillable model (MEDIUM)

Screener: "Export data into structured excel sheets. Create your own models", plus Custom Upload —
the user uploads their own sheet with formulas and formatting and Screener remembers and fills it
(https://www.screener.in/features/); plus notes export since Jan 2026
(https://www.screener.in/docs/changelog/). Vysted ships RFC-4180 CSV only (`src/lib/csv.ts`). For the
Indian analyst who lives in a model spreadsheet, this is *the* switching cost.

### TS-5 — No concall schedule surfaced in the UI (MEDIUM)

Perplexity shows "schedules for post-results conference calls" alongside live transcription
(https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/).
Vysted *fetches* the NSE results calendar but only inside the research loop, and only for
earnings-DATE sub-questions — "the calendar has no registered tool"
(`sidecar/services/research/disclosures.py:15-18`). It is data already on the wire with no surface.
(Live transcription itself is a vendor dependency — Quartr — and is **not** claimed as table stakes.)

### TS-6 — Broker onboarding is worse than the one Zerodha ships for rivals (MEDIUM)

Zerodha's own Kite MCP gives any AI assistant read-only holdings/positions/margins/P&L with 2FA and
"credentials never pass through" the assistant
(https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp,
2025-05-20). Vysted's v1 is a manual `request_token` paste. A user who has already connected Claude
to Kite in two clicks will read Vysted's flow as a regression. **Tier-4 adjacent (§6.5 / broker
surface) — surface to the operator.**

---

## Source list (20 distinct)

1. https://helmterminal.dev/blog/perplexity-stock-research — Perplexity 2026 strengths/limits; the ×1,000 misread
2. https://techcrunch.com/2025/08/18/perplexity-now-supports-live-earnings-call-transcripts-for-indian-stocks/
3. https://www.marketcalls.in/perplexity/perplexity-finance-now-covers-indian-markets-why-traders-should-care.html (2025-08-14)
4. https://x.com/tsuvik/status/1955581467368857890 — India launch
5. https://x.com/AravSrinivas/status/1948812710952796576 — NL screener
6. https://community.perplexity.ai/t/financial-data-hallucinations/145 — hallucination thread + staff reply
7. https://docs.perplexity.ai/docs/agent-api/tools/finance-search — official data disclaimer
8. https://en.wikipedia.org/wiki/Perplexity_AI — Financial Modeling Prep vendor
9. https://www.wealthmanagement.com/artificial-intelligence/perplexity-upgrades-finance-capabilities — Plaid Portfolio
10. https://www.aicerts.ai/news/ai-meets-markets-perplexity-finance-brings-real-time-stock-transcripts-to-india/ — Quartr
11. https://checkthat.ai/brands/perplexity/reviews + https://www.g2.com/products/perplexity/reviews — user praise/complaints
12. https://learn.g2.com/tech-signals-ai-hallucinations-and-research — 41% finance hallucination audit
13. https://www.screener.in/ai/ — Screener AI product page + pricing
14. https://www.screener.in/docs/changelog/Screener-AI/ — launch, 2025-07-08
15. https://www.screener.in/docs/changelog/ — 2026 shipping cadence
16. https://www.screener.in/premium/ — free vs premium limit table
17. https://www.screener.in/features/ — feature inventory
18. https://www.strike.money/reviews/screener-in — 2026 review, cons + user quote
19. https://zerodha.com/z-connect/featured/connect-your-zerodha-account-to-ai-assistants-with-kite-mcp (2025-05-20)
20. https://businessupturn.com/finance/stock-market/tradingview-free-users-hit-with-a-15-minute-delay-on-nse-and-bse-data-and-how-to-switch-real-time-back-on/ (2026-09-16)

Supporting: https://www.businesstoday.in/amp/latest/corporate/story/setting-up-a-call-on-monday-nikhil-kamath-and-aravind-srinivas-weigh-zerodha-perplexity-tie-up-488691-2025-08-09 ·
https://www.storyboard18.com/digital/aravind-srinivas-hints-at-perplexity-zerodha-collaboration-after-india-finance-launch-78804.htm ·
https://opentools.ai/news/perplexity-ais-comet-browser-executes-no-click-trades-on-zerodha-surprising-users ·
https://apify.com/solidcode/screener-in-scraper/api/cli ·
https://parse.bot/marketplace/fedcb439-5e37-4ca5-b7b3-2004ff71686d/screener-in-api ·
https://github.com/jgera/screener.in

**Blocked / unverified, labelled:** `perplexity.ai/changelog/*` → HTTP 403 to WebFetch;
`findmymoat.com/tools/perplexity-finance` → HTTP 429. Neither is relied on for any claim above.
No source was found testing the lakh/crore scale misread on **Indian** filings specifically — O1
extends a US-filing-verified failure by analogy and says so.
