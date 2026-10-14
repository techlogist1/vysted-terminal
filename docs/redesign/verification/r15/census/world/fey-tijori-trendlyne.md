# R15 Census — World sweep: research & monitoring competitors

Scope: Fey, Tijori Finance, Trendlyne, Tickertape, StockEdge, Koyfin, Fiscal.ai (FinChat),
TradingView AI features, Bloomberg ASKB-style assistants. What they do well for **fundamental
research and monitoring**, what they charge, and where they are weak.

Run: R15 Stage 1 (census), world lane. Model: `claude-opus-5[1m]`. Date of research: 2026-09-19.
Read-only sweep; no repo files modified except this one.

Evidence rule for this file: every claim carries a URL plus a quote or a concretely described
observation. Where a site blocked fetching, that is stated and search-snippet evidence is
labelled as such.

---

## 1. Fey (fey.com) — the design benchmark, now absorbed

**Status change that matters: Fey no longer exists as an independent product.**

`https://fey.com/features` now redirects/serves an acquisition notice rather than a feature page.
Fetched 2026-09-19; the page returned only acquisition language — "our technology, design
philosophy, and relentless focus on clarity" and "making finance feel simpler, smarter, and
genuinely better." No features, no pricing, no screener docs remained on that URL.

Acquisition confirmed: Wealthsimple announced the acquisition of Fey on **27 August 2025**
(Wealthsimple newsroom, `https://newsroom.wealthsimple.com/wealthsimple-acquires-investment-research-platform-fey`;
corroborated by BetaKit `https://betakit.com/wealthsimple-acquires-fey-to-bolster-its-investment-research-capabilities/`
and FinTech Futures `https://www.fintechfutures.com/m-a/wealthsimple-acquires-fey`). Fey was a
Montreal startup founded 2021.

**What Fey did before absorption** (search-snippet + third-party review evidence, labelled as such
because the primary feature page is gone):

- AI-powered screener driven by natural language rather than filter grids.
- Earnings-call alerts with "instant alerts and clear summaries", listen-live or catch-up.
- AI summaries of news and of 10-K/10-Q filings "highlighting risks, and strengths".
- Peer analysis for benchmarking against industry.
- Weekly Monday watchlist email digest.
- Pricing circa **$30/month**, subscription only, 7-day trial (third-party review:
  `https://websites2know.com/fey-com-review/`; treat the exact number as secondhand).

**Why this is the single most important world finding for Vysted:** the most design-forward
independent retail research terminal in the world was bought by a broker and folded into a
trading app. The niche Fey occupied — beautiful, ad-free, research-first, not a brokerage
funnel — is now **vacant**. Vysted's positioning sits directly in that hole, with the added
differentiators Fey never had (local-first, BYOK, agent-native, plugin architecture, India).

---

## 2. Tijori Finance — the India depth benchmark

Source: `https://www.tijorifinance.com/features/` (fetched 2026-09-19, rendered fine).

Feature inventory, verbatim names from the page:

*Research tools*
- "Operational Metrics" — analyse company metrics and compare against competitors
- "Stock Screener" — filter companies using natural language
- "Source" — access base data sources directly
- "Sector Data" — 20+ sectors
- "TJI Indexes" — niche sector-specific indices
- "Market Monitor" — sector performance
- "Raw Materials" — price movement tracking
- "Macro Indicators" — macro-economic datasets
- "Ideas Dashboard"
- "Company & Sector Research"

*Tracking tools*
- "Portfolio" — exposure and risk
- "Timeline" — personalised feed with exchange filings, market-share changes, tweets, news
- "Watchlist"
- "Alerts" — price/volume notifications
- "Results" — real-time quarterly results

*Data depth*: market share, revenue mix (product-wise and geography-wise), **1000+ operational
metrics free / 6000+ premium**, shareholding data, sector research, macro indicators, raw
materials.

*Pricing (from the same page)*: Free ₹0 · **Monthly ₹330** · **Yearly ₹3,500** (≈₹292/mo).
Premium adds historic data, in-depth financial comparison, **reverse DCF**, source links,
unlimited alerts and watchlists.

Two things stand out and both are directly relevant to Vysted's "data trust" moat:

1. **"Source" as a first-class feature.** Tijori sells the ability to click through to the
   underlying base data source. That is provenance-as-product. Vysted already has an FR-041
   provenance label concept in the broker reads; the world shows provenance is a *selling point*,
   not a compliance chore.
2. **Operational metrics are the differentiator, not financials.** Everyone has P/E. Tijori's
   paywall is on 6000+ operational metrics (ASP per tonne, subscriber adds, capacity utilisation)
   — the stuff you cannot derive from a standard XBRL filing. Corroborated by an independent
   review: `https://aayushbhaskar.com/tijori-finance/` describes "operational metrics, revenue mix
   breakdown by product and geography, raw material prices, supply chain links".

Tijori also ships through Zerodha's ecosystem (`https://zerodha.com/z-connect/business-updates/new-on-tijori`),
which is the distribution route an independent product does not have.

---

## 3. Trendlyne — the scores-and-checklists benchmark

Source (fetched): `https://trendlyne.com/score-details/` family plus help-desk articles.
Note: `https://trendlyne.com/features/` fetched but returned only nav chrome (a JS-rendered
page) — nav items visible were "Screeners", "Alerts", "Reports", "Baskets", "Insider Trades",
"Events Calendar", "Data Downloader", plus sections "Stocks", "Futures & Options",
"Mutual Funds", "News", "Fundamentals", "Corporate Actions", "Shareholding".
`https://trendlyne.com/subscription/pricing/` returned **HTTP 404** — pricing not fetchable at
that path; see §3.2.

### 3.1 DVM scores — the mechanic worth stealing

From Trendlyne's own help articles
(`https://help.trendlyne.com/support/solutions/articles/84000347982-what-is-the-trendlyne-dvm-score-and-how-does-it-work-`
and `https://trendlyne.com/score-details/`):

- DVM = **Durability, Valuation, Momentum**, each scored **0–100**.
- Durability "checks the quality of a company's financials, its long term performance, and the
  quality of management."
- Valuation "evaluates whether a stock is overvalued or undervalued based on its current price
  and price-to-earnings (P/E) ratio."
- Momentum "is calculated daily from over 35 technical indicators".
- Banding: "Durability scores above 55 are considered good(G) and below 35 are considered bad(B).
  Scores between 35-55 are considered neutral/Medium/Middle(M)" — i.e. a three-state G/M/B cube.
- Inputs span "market data, financials, shareholding patterns, insider trades and SAST, technical
  and fundamental ratios, broker upgrades, news/trends".
- Refresh cadence is explicit: Momentum recomputes **end of day**; Durability and Valuation revise
  "based on the company's quarterly and annual performance, as well as daily changes in ratios
  such as P/E."

Also shipped: **SWOT + checklist** — "Trendlyne's SWOT analysis provides an overview of the
strengths and weaknesses of every stock, as well as the opportunities and threats they are facing."

The design lesson: a single compact glyph (the DVM cube) that encodes three orthogonal axes at a
stated refresh cadence, with the inputs disclosed. It is legible in a list row, sortable, and
alertable. That is a *monitoring primitive*, not a research report.

### 3.2 Trendlyne pricing and plan gates

Source: `https://trendlyne.com/subscription/plans/` (fetched 2026-09-19). The `/subscription/pricing/`
path 404s; `/subscription/plans/` is the live page.

| Plan | Monthly | Annual | Scope |
|---|---|---|---|
| GuruQ | ₹310 | ₹2,190 | India |
| StratQ | annual only | ₹5,900 | India, realtime |
| Pro (Global) | ₹1,500 | ₹8,900 | India + US |
| Pro Plus (Global) | ₹2,000 | ₹11,900 | India + US + SmartOptions |

What the tiers actually gate is the striking part — **everything is metered**:

- GuruQ: "7 MarketMind AI credits", 1,758 screener parameters, daily technicals, 30 watchlists,
  150 price-target alerts, 75 active screener alerts (daily frequency), 200 annual backtests,
  monthly screener rewind.
- StratQ: "20 MarketMind AI credits", 3,512 screener parameters, 15m–monthly technicals,
  200 watchlists, 500 price-target alerts, 300 active screener alerts at 15-minute frequency,
  1,200 annual backtests, weekly screener rewind, platform walkthrough call.
- Pro Plus: "40 MarketMind AI credits", India 3,512 + USA 2,558 parameters, SmartOptions F&O
  analytics.

All plans include: "Best DVM Stocks, Forecaster, 300 stock reports/month, Real Time Alpha Alerts,
Portfolio Report, Email alerts, Superstar alerts".

Two hard observations:

1. **AI is sold in credits, and the credits are tiny.** Seven AI credits a month on the entry
   plan, forty on the ₹11,900/yr plan. An agent-native product that runs on the user's own key
   has no such ceiling. This is the clearest structural weakness in the incumbent field: their
   AI economics force rationing because they pay for inference; a BYOK local-first product does
   not.
2. **Alert *frequency* is a paid axis.** 15-minute alert evaluation is a ₹5,900/yr feature. A
   local-first desktop app that polls on the user's own machine has no marginal cost per
   evaluation.

Nav-level features observed on `https://trendlyne.com/features/` (JS-rendered; only chrome
captured, labelled as such): "Screeners", "Alerts", "Reports", "Baskets", "Insider Trades",
"Events Calendar", "Data Downloader", and sections for "Futures & Options", "Mutual Funds",
"Corporate Actions", "Shareholding". "Superstar alerts" (ace-investor portfolio change alerts)
is confirmed in the all-plans list above.

---

## 4. Tickertape — the scorecard and sentiment benchmark

**Fetch blocked.** `https://www.tickertape.in/plans` returned "Unable to verify if domain
www.tickertape.in is safe to fetch" — enterprise/network policy blocked the direct fetch.
`https://www.findmymoat.com/tools/tickertape` returned **HTTP 429**. Everything below is from
search snippets and third-party reviews and is labelled accordingly.

Feature evidence (search snippets, 2026-09-19):

- **Investment Scorecard** — "rates each stock's performance, valuation, profitability, growth,
  and risk/red flags." A five-axis card, one step beyond Trendlyne's three.
- **Red flags** as an explicit surfaced category (Pro gate).
- **Market Mood Index (MMI)** — "a sentiment indicator that reflects the overall mood of the
  market, be it fear or greed, based on multiple underlying factors." Historical MMI is Pro-gated.
- **Screener** — "200+ filters including financial, ownership, and growth metrics"; custom
  filters and custom universes are Pro.
- **Forecasts** — "analyst ratings, price forecasts, revenue and EPS forecasts" (Pro).
- **Alerts** — "custom alerts based on price movements, technical indicators, and financial
  events, with alerts receivable via email or SMS."
- Pro also adds exports, portfolio analytics, multi-account portfolios, "more than 100 key metrics".

Sources (third-party, snippet-level): `https://www.findmymoat.com/tools/tickertape`,
`https://www.strike.money/reviews/tickertape`,
`https://www.winvesta.in/blog/investors/fundamental-analysis-tools-and-screeners-2026-guide`,
`https://www.bullrun.co.in/blog/best-tickertape-alternatives-india`.

Note Tickertape is owned by Smallcase — again a research surface attached to a distribution
business, not an independent product.

**The interesting gap:** a "red flags" section and a "risk" score exist, but across every snippet
reviewed nobody describes *forensic accounting* checks (cash-flow-vs-profit divergence, receivable
days blowout, auditor change, related-party growth, contingent liabilities, promoter pledge trend).
Tickertape's "risk" is volatility-and-debt risk. Forensic/quality scoring in the Indian market is
dominated by paid institutional products, not retail terminals — see §9.

---

## 5. StockEdge — the scans-and-deals benchmark

Sources: `https://stockedge.com/pricing` and `https://blog.stockedge.com/stockedge-premium-version/`
(both fetched 2026-09-19).

Pricing, verbatim from the pricing page:

| Plan | Monthly | Annual |
|---|---|---|
| Premium | ₹399/mo | ₹1,738/yr (₹145/mo) |
| Pro | ₹1,499/mo | ₹6,946/yr (₹579/mo) |
| Club | ₹2,499/mo | ₹13,899/yr (₹1,158/mo) |

Gates, verbatim: Premium = "500+ Advanced Scans", "2 Custom Scans with Basic Downloads",
"20 Combination Scans", momentum/fundamental scoring, "Sector Rotation (Sector Level)".
Pro adds "50 Custom Scans with Advanced Downloads", "50 Combination Scans", "15+ Auto recognized
Chart Patterns", industry-level sector rotation, "Sector Analytics - Results, Shareholding".
Club adds "Stock AI", "Strategy-Backed Trading and Investment Ideas", expert query resolution,
"Daily Morning Market Report".

Feature depth from the premium blog post (verbatim): "Bullish and Bearish Technical scans"
across "Exponential Moving Averages (EMA), MACD, ADX, ATR, Bollinger Band, and Stochastic &
Parabolic SAR"; "50+ fundamental scans based on profitability, sales, PAT, EPS, and important
ratios like free cash flow, Operating cash flow, PE ratio, DE ratio"; combination scans mixing
technical + fundamental; "Readymade portfolio of more than 150 Ace Investors like Rakesh
Jhunjhunwala, Dolly Khanna, Porinju Veliyath, Vijay Kedia, R K Damani".

The **deals and ownership** stack is StockEdge's real moat (search-snippet evidence from
`https://www.strike.money/reviews/stockedge` and `https://blog.stockedge.com/exploring-my-stockedge/`):
users can "form a group of various big investors and get consolidated data of all their bulk,
block deals, and insider trades together with their latest shareholding for the last five years",
and monitor "insider activity, bulk deals, pledged shares, and promoter movements".

That is the India-specific monitoring set Vysted's peers in the US (Koyfin, Fiscal.ai) simply do
not have, because bulk/block deals and promoter pledge are SEBI-disclosure artifacts with no US
analogue. **It is table stakes for an India-first terminal.**

---

## 6. Koyfin — the global dashboard benchmark, and a striking AI vacuum

**Direct fetch of `https://www.koyfin.com/pricing/` blocked** ("Unable to verify if domain
www.koyfin.com is safe to fetch"). Koyfin publishes a machine-readable pricing page at
`https://www.koyfin.com/pricing-llm-info/` which **did** fetch (2026-09-19) — that is the primary
source used below.

| Plan | Price |
|---|---|
| Free | $0 |
| Plus | $39/mo |
| Premium | $79/mo |
| Advisor Core | $209/mo |
| Advisor Pro | $299/mo |
| Teams | custom |

Verbatim gates from that page: Plus adds "company history from 2 years on Free to 10 years",
analyst estimates, filings, earnings transcripts, global dividend data, ETF screening. Premium
adds unlimited custom formulas (vs 10 on Plus), custom financial templates, custom data series,
portfolio risk metrics, hypothetical performance, short-position support. Advisor tiers add client
portfolios, model portfolios, custodian integrations, client reports.

Search-snippet corroboration for Plus (labelled as such) adds: "unlimited screening templates,
… unlimited custom dashboards, over 100k global company snapshots, … premium news, company
filings & press releases, custom news feeds, dashboard data download, … the full history of
transcripts, and advanced transcript search"
(`https://simplemarkets.io/blog/post/koyfin-review`, `https://www.trustradius.com/products/koyfin/pricing`).
Also noted: Koyfin retired the "Pro" plan — after 30 April it was no longer renewable and existing
Pro subscribers moved to Premium at the same price.

**Two findings that matter more than the pricing:**

1. **Koyfin's own pricing page mentions no AI features at all.** The fetched
   `pricing-llm-info` page lists formulas, templates, dashboards, transcripts, custodian
   integrations — and nothing resembling an AI copilot, chat, or summarisation. Alerts appear
   once, as "watchlist and portfolio alerts" on Premium. The best-regarded global retail terminal
   is, as of this fetch, **not** agent-native. That is the whole Vysted thesis, unoccupied at the
   top of the market.
2. **Koyfin does not cover India meaningfully.** Its coverage page is
   `https://www.koyfin.com/data-coverage/stocks/` (blocked from fetch, listed in search results);
   search-snippet evidence is consistent that global coverage "does not extend comprehensively to
   Indian stocks listed on NSE and BSE", and India-specific alternatives are recommended instead
   (`https://marketxls.com/blog/koyfin-alternative-excel-financial-data-analysis`). Labelled as
   snippet-level evidence — I could not fetch Koyfin's coverage page directly to confirm exchange
   lists.

---

## 7. Fiscal.ai (formerly FinChat) — the closest thing to Vysted's thesis

Direct fetch of `https://fiscal.ai/pricing` returned **HTTP 403**;
`https://www.findmymoat.com/tools/fiscal-ai` returned **HTTP 429**. Primary usable source:
`https://quantbrainai.net/blog/fiscal-ai-review-jul-2026/` (fetched 2026-09-19), a detailed
third-party review — labelled as third-party.

| Tier | Monthly | Annual |
|---|---|---|
| Free | $0 | $0 |
| Pro | $29 | $24/mo ($288/yr) |
| Max | $64 | $49/mo ($588/yr) |

**AI is metered here too**, and hard: Free **10 prompts/month**, Pro **300/month**,
Max **500/month**. Data depth is the other axis — Free 30+ companies / 5 years / 6 quarters;
Pro 100,000+ global companies / 10+ years / 20 quarters; Max 20+ years / 40 quarters, "Full depth"
KPI access.

What they got right and nobody else has: **segment-level data as a screenable field** —
"segment-level data (e.g., AWS revenue for AMZN as a separate screenable field)". The segment and
KPI data is proprietary, extracted from filings. Max tier ships **"REST + MCP"** — Fiscal.ai
already exposes an MCP server, which is precisely Vysted's "MCP as universal tool layer" bet,
validated by a commercial peer.

The review names four explicit weaknesses, verbatim: "No alternative data" (satellite, credit
card), "No order book data" or tick data, "No native backtesting engine", and no proprietary
factor models — users get "raw data — not alpha signals".

Corroborating sources (snippet-level): `https://stockpicker.tech/analysis/fiscal-ai-review`,
`https://www.euinvestinghub.com/articles/fiscal-ai-review/`,
`https://www.toolcenter.ai/en/articles/finchat-review-2026` (confirms the FinChat→Fiscal.ai
rebrand in 2025), `https://discover.oreateai.com/discover/the-true-cost-of-fiscalai-2026-pricing-and-feature-breakdown`.

**Read for Vysted:** Fiscal.ai is the sharpest competitor conceptually — AI copilot over filings
and transcripts, MCP surface, segment KPIs. It is a cloud SaaS with metered prompts, US/global
data, and no India depth surfaced anywhere in the reviews read. Vysted's differentiation against
it is exactly the three things it cannot do: **run on your own key with no prompt ceiling**, **run
locally with your own data**, and **know the Indian disclosure regime**.

---

## 8. TradingView AI — the mass-market agent, and its ceiling

Primary source: `https://www.tradingview.com/blog/en/tradingview-ai-chart-copilot-beta-57730/`
(fetched 2026-09-19).

Verbatim: AI Chart Copilot is "An AI-powered assistant that lives in your browser's side panel and
works along your TradingView charts." It gives a "technical breakdown in seconds — moving averages,
RSI, MACD, key support and resistance levels", manages alerts conversationally, retrieves "latest
news, earnings data, and fundamental metrics", and scans watchlists for setups. Delivery is a
**Chrome/Chromium browser extension**. On limits TradingView says only: "To keep it sustainable and
free, we may limit daily usage." Roadmap wording: bringing it "natively into the side panel across
all browsers and the desktop app."

Launch date **2 April 2026**, public beta (corroborated across
`https://chartwisehub.com/tradingview-ai-chart-copilot-guide/`,
`https://finestel.com/blog/tradingview-ai-chart-copilot-review/`, and the TradersPost coverage
below). TradingView also shipped, per search snippets, "AI-powered document summaries" and
"AI-powered corporate news" in early 2026.

Metering again (search-snippet evidence, `https://pineify.app/resources/blog/tradingview-ai-chart-copilot-what-it-is-how-it-works-and-what-serious-traders-need-beyond-it`
and TradersPost `https://blog.traderspost.io/article/tradingview-ai-features-chart-copilot-documents-news`
— both hosts blocked direct fetch; TradersPost returned "Unable to verify if domain … is safe to
fetch"): a weekly allowance scaling by plan — "Free 0.25×, Essential 1×, Plus 2×, Premium 5×, and
Ultimate 20×", and Pine Script authoring reserved for Essential and above. Stated limits: "It is
not an automated trading bot. It cannot execute trades… Native Chart Copilot does not generate Pine
Script code or send signals to brokers."

**Read for Vysted:** the biggest charting platform on earth shipped its agent as a *browser
extension in a side panel* — bolted on, not designed in, and still rationed by plan. It is a
technical-analysis copilot, not a fundamental-research agent. Nobody at the mass-market tier is
doing agent-first **fundamental** research.

---

## 9. Bloomberg — ASKB and the institutional bar

Bloomberg's own pages (`bloomberg.com/professional/insights/...`) were **blocked from direct fetch**
("Unable to verify if domain www.bloomberg.com is safe to fetch"). Evidence below is from
A-Team Insight (fetched successfully) plus search snippets of Bloomberg's own press announcements,
labelled accordingly.

Timeline (search-snippet evidence from Bloomberg press pages and trade coverage):
- **22 Jan 2024** — AI-Powered Earnings Call Summaries
  (`https://www.prnewswire.com/news-releases/bloomberg-launches-ai-powered-earnings-call-summaries-302040670.html`).
- **7 Apr 2025** — Document Insights, conversational Q&A over a company document
  (`https://www.bloomberg.com/company/press/bloomberg-accelerates-financial-analysis-with-gen-ai-document-insights/`).
- **16 Jun 2025 / end-2025** — Document Search & Analysis.
- **23 Feb 2026** — **ASKB**, "an agentic conversational interface for its iconic Terminal",
  controlled beta.
- **16 Apr 2026** — ASKB roadmap
  (`https://www.bloomberg.com/professional/insights/press-announcement/bloomberg-unveils-askb-roadmap-for-clients-to-augment-their-investment-process-with-agentic-ai/`).

From A-Team Insight (fetched, `https://a-teaminsight.com/blog/bloomberg-launches-ai-powered-research-tool-for-terminal-users/`)
on Document Search & Analysis — the citation model is the headline, verbatim:

> "Every AI-generated summary or answer we provide includes clear attribution, both to the source
> and, where applicable, to the analyst who authored it."

Sources spanned: "Earnings transcripts, Regulatory filings, Bloomberg News articles, Independent
analyst research, Internal notes, Annual reports, ESG disclosures." It "enables users to pose
questions in natural language and receive structured, comparative insights" and to "compare
multiple documents at once."

ASKB architecture (search-snippet evidence, `https://www.aicerts.ai/news/bloomberg-askb-conversational-investment-research-beta-workflows/`
— direct fetch returned **HTTP 503**; also `https://aimagazine.com/news/how-bloomberg-is-using-agentic-ai-for-complex-workflows`
and `https://www.thetradenews.com/bloomberg-embeds-agentic-ai-into-the-terminal/`): ASKB
"orchestrates specialized agents for search, summarization, code generation, and visualization, and
an execution planner sequences these agents"; "A controller agent merges their outputs, resolves
conflicts and formats citations"; responses "include citations anchoring every figure, chart, or
quote"; and "when numeric analysis surfaces, ASKB exposes the underlying BQL code for immediate
reuse in Excel or BQuant". **ASKB Workflows** cover named multi-step activities — "pre-earnings
preparation, post-earnings analysis, or meeting prep" — and "assemble a structured output in
minutes."

**Three things Bloomberg has established as the institutional bar, all of which Vysted can match
without a Bloomberg budget:**

1. **Citation anchored to every figure**, not to the answer as a whole.
2. **The generated query is shown and reusable** (BQL exposed for Excel/BQuant). Show your work,
   in code.
3. **Named workflows, not open chat** — "pre-earnings prep", "post-earnings analysis", "meeting
   prep" are first-class objects a user invokes, not prompts a user must compose.

---

## 10. The India-specific monitoring layer nobody has fully solved

This is the part of the world sweep with the highest signal for an India-first terminal.

**Promoter pledge.** The raw feed is public and free: NSE publishes
`https://www.nseindia.com/companies-listing/corporate-filings-pledged-data`. Retail tooling around
it is thin and crude — Samco ships a "Pledge Monitor" (`https://www.samco.in/technology/pledge-monitor`,
positioned as "full details of pledged shares by all 4000+ listed companies"), Screener.in exposes
it as a static screen (`https://www.screener.in/screens/3513/promoter-pledges/`), StockEdge bundles
it into investor-group monitoring. What nobody surfaced in this sweep is the **trend** reading that
practitioners actually use. Quoted thresholds from practitioner sources: "Any promoter pledge above
20% of total holdings is a serious red flag, and pledges above 50% are dangerous"
(`https://multibaggershares.com/forensic-accounting-red-flags-how-to-detect-financial-manipulation-in-indian-companies-before-it-destroys-your-portfolio-the-complete-fraud-detection-toolkit-for-smart-value-investors/`),
and "Rising pledging over 4 consecutive quarters is a red flag regardless of absolute level"
(`https://hdfcsky.com/blogs/risk-radar-by-sky/promoter-pledge-creeping-above-60-percent`, which also
notes a promoter pledging "over 60–70% of holdings without a clear strategic rationale is sending a
signal worth understanding"). The *derivative* — four-quarter direction — is the signal; the
*level* is what everyone ships.

**Forensic / accounting-quality scoring.** Practitioner writeups exist
(`https://marketsmithin.substack.com/p/spotting-forensic-red-flags-in-indian`;
`https://watsinfo.com/blog/corporate-governance-stock-analysis.html`) and the framing is explicit:
"Traditional financial analysis is not designed to detect deception." Tickertape ships a "red flags"
bucket inside its Investment Scorecard and Trendlyne ships SWOT + checklists, but across every
source read in this sweep **no mainstream Indian retail platform ships a forensic-accounting score**
with the classic components (CFO-vs-PAT divergence, receivable/inventory days blowout, auditor
resignation, related-party growth, contingent liabilities, pledge trend, promoter-stake decline).
One niche product markets itself in that space (`https://www.thescreener.in/pricing`) but it is not
a competitor of scale. This is the clearest unclaimed high-value box on the India board.

**Concall summaries.** Trendlyne ships AI conference-call summaries
(`https://trendlyne.com/ai-conference-calls/`, fetched — the page is a marketing landing page, so
coverage counts and paywall status are **not stated on it**; search-snippet evidence describes it as
freemium and covering NSE/BSE calls, and Trendlyne also publishes an earnings-call podcast RSS at
`https://trendlyne.com/feeds/earning-calls-podcast-rss/`). Trendlyne's own comparison page
(`https://help.trendlyne.com/support/solutions/articles/84000396310-trendlyne-vs-stockedge-vs-tickertape-vs-screener-in`
— their marketing, treated as such) claims 22 exclusive features vs the other three and admits only
two gaps: "Account Aggregator integration for Equity and MFs" and "Market Sentiment analysis".
Concall summarisation is therefore **present but shallow** in India: a summary blob per call, not a
tracked object.

**What nobody ships:** a *concall tracker* — guidance extracted per call, stored, and diffed
against the next call and against what actually printed in the results. "Management said 18% margin
in Q2; Q3 printed 14.2%; here is the quote from each call." That is a research artifact, and it is
one join away from data that is already free and public.

---

## OPPORTUNITIES FOR VYSTED

Each: what the world lacks or does badly, the evidence, and the Vysted capability it sits one step
from. Repo anchors verified read-only against `004-r4-experience-rebuild` on 2026-09-19.

**O-1 — The premium-research-app niche is literally vacant.**
Fey was the design benchmark for research-first retail terminals and was acquired by a broker on
27 Aug 2025 (`https://newsroom.wealthsimple.com/wealthsimple-acquires-investment-research-platform-fey`);
`https://fey.com/features` now serves only an acquisition notice. Every remaining India player is
owned by or attached to a distribution business (Tickertape←Smallcase, Tijori←Zerodha ecosystem per
`https://zerodha.com/z-connect/business-updates/new-on-tijori`). *One step from:* nothing to build —
this is positioning. An independent, ad-free, non-brokerage research terminal has no incumbent.

**O-2 — Every competitor meters AI; BYOK has no ceiling.**
Trendlyne: "7 MarketMind AI credits" at ₹310/mo, 40 at ₹11,900/yr
(`https://trendlyne.com/subscription/plans/`). Fiscal.ai: 10 / 300 / 500 prompts per month across
Free/Pro/Max (`https://quantbrainai.net/blog/fiscal-ai-review-jul-2026/`). TradingView: a weekly
allowance "Free 0.25×, Essential 1×, Plus 2×, Premium 5×, Ultimate 20×". *One step from:* the BYOK
key path already shipped (`sidecar/services/llm/`, keychain-backed per CLAUDE.md "BYOK secrets").
This is not a feature to build — it is a **marketing claim to make loudly**: unlimited research runs,
because you pay the model provider directly.

**O-3 — Alert *frequency* is a paid axis for cloud products and free for a desktop app.**
Trendlyne charges ₹5,900/yr for 15-minute screener-alert evaluation vs daily on the ₹2,190 plan
(same source as O-2). A local process polling on the user's own machine has zero marginal cost per
evaluation. *One step from:* **nothing exists yet** — see TSG-1. This is the single highest-leverage
new subsystem, and it converts an incumbent paywall into a Vysted giveaway.

**O-4 — Nobody shows the query they ran, except Bloomberg.**
ASKB "exposes the underlying BQL code for immediate reuse in Excel or BQuant" (search-snippet,
`https://www.aicerts.ai/news/bloomberg-askb-conversational-investment-research-beta-workflows/`).
No retail product does this. *One step from:* `write_screener_filters` and `run_custom_backtest`
already exist as catalog capabilities (`sidecar/services/agent_tools/catalog.py`), and
`save_screen` persists them. Surfacing "here is the screen the agent built, edit it" is a UI
affordance over capabilities that already ship — a show-your-work moat aligned exactly with the
stated "data trust" positioning.

**O-5 — Named workflows beat open chat.**
Bloomberg productised "pre-earnings preparation, post-earnings analysis, or meeting prep" as ASKB
Workflows that "assemble a structured output in minutes". No retail product does. *One step from:*
Vysted already has a workflow domain in the catalog, a durable detached run system
(`sidecar/services/run_manager.py`, `sidecar/routers/runs.py`) and `arrange_layout` +
`layout-templates.fitLayoutTemplate` cockpit templates. A "results-day prep" workflow that arranges
the cockpit, pulls `earnings_upcoming` + `analyst_history` + `corporate_announcements`, and publishes
a brief is an assembly of shipped parts, not new plumbing.

**O-6 — Provenance is a product, not a chore.**
Tijori sells "Source — access base data sources directly" as a named premium feature
(`https://www.tijorifinance.com/features/`); Bloomberg's differentiator quote is "Every AI-generated
summary or answer we provide includes clear attribution, both to the source and, where applicable,
to the analyst who authored it." *One step from:* the FR-041 provenance label already exists on
broker reads (`synthetic`/`mode`/`provider`, per CLAUDE.md), `shareholding_pattern` already returns
"each quarter's XBRL filing link", `corporate_announcements` already returns "attachment (PDF) URL"
per `sidecar/services/agent_tools/catalog.py:659-682`, and research already runs a citecheck
(`sidecar/services/research/citecheck.py`). The parts are there; **per-figure** attribution in
`BriefBody` (`src/modules/research/brief-blocks.tsx`) is the step.

**O-7 — The four-quarter pledge derivative, not the pledge level.**
NSE publishes pledged data free (`https://www.nseindia.com/companies-listing/corporate-filings-pledged-data`);
retail tools ship the level (Samco Pledge Monitor, Screener.in screen 3513). The practitioner rule is
directional: "Rising pledging over 4 consecutive quarters is a red flag regardless of absolute level"
(`https://hdfcsky.com/blogs/risk-radar-by-sky/promoter-pledge-creeping-above-60-percent`). *One step
from:* `corporate_announcements` already names "pledges" as a category it returns, and
`shareholding_pattern` already returns quarterly promoter percentages newest-first
(`catalog.py:659`, `catalog.py:684`). The trend computation is a derivative over data already
fetched.

**O-8 — A forensic/quality score is the unclaimed box in India.**
No mainstream Indian retail platform ships one; Tickertape's "risk/red flags" is volatility-and-debt
risk (snippet evidence, `https://www.strike.money/reviews/tickertape`), Trendlyne's Durability is a
financial-quality-and-management composite but is not marketed as forensic
(`https://help.trendlyne.com/support/solutions/articles/84000347982-...`). Practitioner demand is
documented (`https://marketsmithin.substack.com/p/spotting-forensic-red-flags-in-indian`). *One step
from:* `fundamentals`, `shareholding_pattern`, `corporate_announcements` are shipped catalog
capabilities; the missing inputs are cash-flow-vs-PAT and working-capital-days series. Highest
research-quality payoff per unit of work, and it directly serves the stated "research quality" moat.

**O-9 — Concall guidance-vs-delivery tracking exists nowhere.**
Trendlyne ships per-call AI summaries (`https://trendlyne.com/ai-conference-calls/`); Fey shipped
call summaries before acquisition; Bloomberg ships transcript Q&A. **Nobody diffs stated guidance
against what printed.** *One step from:* `earnings_history` + `earnings_estimates` +
`corporate_announcements` (which returns investor-presentation PDFs) already exist; the research
agent already produces structured briefs with `publish_brief`. A guidance-delta brief is a new agent
prompt over shipped tools, not a new data pipeline.

**O-10 — Operational metrics, not financials, are what people pay for.**
Tijori paywalls at "1000+ operational metrics for free; 6000+ for premium"; Fiscal.ai's hook is
"segment-level data (e.g., AWS revenue for AMZN as a separate screenable field)". Both treat
segment/operational data as *the* premium good. *One step from:* Vysted parses XBRL for
`shareholding_pattern` already; segment reporting is in the same filings. Not a one-week job, but
the extraction machinery exists.

**O-11 — Koyfin, the best global dashboard, has no AI and no India.**
Its own machine-readable pricing page (`https://www.koyfin.com/pricing-llm-info/`, fetched) lists no
AI capability at any tier up to $299/mo; alerts appear once as "watchlist and portfolio alerts". India
coverage is absent (snippet evidence, `https://marketxls.com/blog/koyfin-alternative-excel-financial-data-analysis`).
*One step from:* nothing — this validates that "agent-native + India" is an uncontested intersection
at the top of the market.

**O-12 — MCP as a product surface is commercially validated.**
Fiscal.ai's Max tier ships "REST + MCP" (`https://quantbrainai.net/blog/fiscal-ai-review-jul-2026/`)
— a paid competitor charges $588/yr partly for an MCP endpoint. *One step from:* Vysted's MCP server
is shipped and catalog-projected (`sidecar/services/mcp_server.py`, parity-tested by
`test_mcp_catalog_parity.py` per CLAUDE.md). This is an existing asset currently under-positioned:
it is a differentiator, not plumbing.

**Count: 12 opportunities.**

---

## TABLE-STAKES GAPS

Where this research shows Vysted is **behind** what a demanding Indian retail owner already gets
elsewhere, often for free. Repo state verified read-only on `004-r4-experience-rebuild`, 2026-09-19.

**TSG-1 — No alerts or monitoring subsystem at all. (critical for the "monitoring" half of the
product.)**
Every single competitor ships alerts as table stakes: Trendlyne "150 price target alerts / 75 active
screener alerts" on its ₹310 entry plan plus "Real Time Alpha Alerts" and "Superstar alerts" on
*all* plans (`https://trendlyne.com/subscription/plans/`); Tijori ships "Alerts — price/volume
notifications" on the free tier (`https://www.tijorifinance.com/features/`); Tickertape ships
price/technical/financial-event alerts by email and SMS; TradingView's Copilot "manages alerts
through conversation". In Vysted there is **no alert router** (`sidecar/routers/` contains no
alerts module — verified: `agents, backtest, brokers, crypto, custom_agents, disclosures, earnings,
fundamentals, health, history, indicators, llm, macro, mcp, news, plugins, portfolio, quant, quotes,
resolve, runs, safety, screener, search_status, search_tiers, sec_filings, system, workflow,
workspace`), **no alert capability** in the 51-entry catalog (`sidecar/services/agent_tools/catalog.py`
— the full id list contains no alert/notify/watch-trigger entry), and no alerts module under
`src/modules/` (the `grep -il alert` hits there are ARIA `role="alert"` banners and disclaimer
dialogs — e.g. `src/modules/broker-connect/kite-static-ip-banner.tsx`,
`src/modules/safety/DisclaimerFlow.tsx` — not a monitoring engine). A terminal you must be looking
at to learn anything is not a monitoring product.

**TSG-2 — No bulk/block-deal or insider-deal tracking.**
StockEdge lets users "form a group of various big investors and get consolidated data of all their
bulk, block deals, and insider trades together with their latest shareholding for the last five
years" (`https://www.strike.money/reviews/stockedge`,
`https://blog.stockedge.com/exploring-my-stockedge/`); Trendlyne ships "Insider Trades",
"Insider + SAST Alerts" and "Superstar alerts". Vysted has `sec_insider_transactions` — **US only**
— and its India disclosures router exposes only `/announcements`, `/results`, `/shareholding`
(`sidecar/routers/disclosures.py:44,74,95`). No bulk deals, no block deals, no SAST, no
ace-investor portfolios. This is the single most-used India monitoring surface and Vysted has none
of it.

**TSG-3 — No structured promoter-pledge data.**
Vysted's `corporate_announcements` merely lists pledge *announcements* as one announcement category
(`sidecar/services/agent_tools/catalog.py:659`); there is no pledge percentage, no history, no
threshold. Screener.in, Samco, StockEdge and Trendlyne all ship pledge tracking, and the NSE feed is
free (`https://www.nseindia.com/companies-listing/corporate-filings-pledged-data`). For an
India-first product this is a table-stakes miss, not an opportunity.

**TSG-4 — Shareholding stops at the top-level split; FII/DII is unparsed.**
Vysted's own capability description concedes it: quarterly promoter/public/employee-trust
percentages "with each quarter's XBRL filing link (**which carries the full FII/DII split**)"
(`sidecar/services/agent_tools/catalog.py:684-697`). Handing the user a link to the data is not
having the data. Trendlyne, Tickertape and StockEdge all ship parsed FII/DII quarterly series, and
StockEdge Pro sells "Sector Analytics - Results, Shareholding" (`https://stockedge.com/pricing`).

**TSG-5 — No composite scorecard glyph.**
Trendlyne's DVM (three 0–100 axes with disclosed inputs and a stated refresh cadence —
`https://trendlyne.com/score-details/`) and Tickertape's Investment Scorecard (performance,
valuation, profitability, growth, red flags) are the two most-recognised objects in Indian retail
research. Vysted's catalog has `fundamentals` returning raw ratios and no composite. Without some
sortable, list-legible, alertable summary glyph, there is no way to triage a watchlist at a glance —
and no anchor for TSG-1's alerts to fire on.

**TSG-6 — No concall/earnings-call transcript surface.**
Trendlyne ships AI concall summaries free-tier (`https://trendlyne.com/ai-conference-calls/`), Koyfin
Plus ships "the full history of transcripts, and advanced transcript search" at $39/mo
(`https://www.koyfin.com/pricing-llm-info/`), Fiscal.ai and Bloomberg both build their AI on
transcripts, and Fey shipped call alerts and summaries. Vysted's catalog contains no transcript
capability — `grep -in "transcript" sidecar/services/agent_tools/catalog.py` returns nothing. For a
product whose stated moat is "research quality", the highest-signal unstructured source in equity
research is absent.

**TSG-7 — No segment / operational-metric data.**
Tijori's entire paid proposition is operational metrics and product-and-geography revenue mix;
Fiscal.ai's is segment KPIs as screenable fields. Vysted has neither. Benchmarked against
screener.in this is survivable; benchmarked against Tijori (an India competitor at ₹3,500/yr) it is
the reason a serious fundamental investor keeps a second subscription.

**TSG-8 — No backtest-on-screen loop despite having both halves.**
Trendlyne sells "200 annual backtests" at ₹2,190 and "1200 annual backtests" at ₹5,900
(`https://trendlyne.com/subscription/plans/`). Vysted ships `screener_run`, `save_screen`,
`backtest_summary` and `run_custom_backtest` as separate catalog capabilities
(`sidecar/services/agent_tools/catalog.py`) — the pieces exist but no evidence in this sweep of a
"backtest this screen" path joining them. Flagged as a gap to verify in the code lane, not asserted
as broken.

---

## Raw findings (merge format)

The table-stakes gaps above, in the census raw-finding shape. Opportunities are not findings and
are deliberately not encoded here. Prefix `WRS` = World sweep, Research.

```json
[
{"raw_id":"WRS-1","title":"No alerts or monitoring subsystem exists at all","severity":"critical","area":"agent","subsystem":"monitoring/alerts","repro":"List sidecar/routers/ and the 51-entry capability catalog; no alert, notify, or trigger surface appears. src/modules/ has no alerts module.","evidence":"sidecar/routers/ (no alerts module); sidecar/services/agent_tools/catalog.py (51 _cap entries, none alert-related); https://trendlyne.com/subscription/plans/ ships 150 price-target + 75 screener alerts on the Rs310 entry plan; https://www.tijorifinance.com/features/ ships alerts on the FREE tier","notes":"Monitoring is half the stated product. Every competitor treats alerts as table stakes, two of them on free tiers. Also blocks TSG-5: a scorecard has nothing to fire on."},
{"raw_id":"WRS-2","title":"No bulk/block deal, SAST, or India insider-deal tracking","severity":"high","area":"data","subsystem":"india-disclosures","repro":"sidecar/routers/disclosures.py exposes only /announcements, /results, /shareholding. sec_insider_transactions is US-only.","evidence":"sidecar/routers/disclosures.py:44,74,95; catalog id list has sec_insider_transactions but no India deals equivalent; https://www.strike.money/reviews/stockedge ('consolidated data of all their bulk, block deals, and insider trades together with their latest shareholding for the last five years')","notes":"Most-used India monitoring surface; StockEdge Premium is Rs1738/yr."},
{"raw_id":"WRS-3","title":"Promoter pledge exists only as an announcement category, not as data","severity":"high","area":"data","subsystem":"india-disclosures","repro":"corporate_announcements lists 'pledges' among announcement categories; no pledge percentage, history, or threshold anywhere.","evidence":"sidecar/services/agent_tools/catalog.py:659; free source at https://www.nseindia.com/companies-listing/corporate-filings-pledged-data; peers: https://www.samco.in/technology/pledge-monitor, https://www.screener.in/screens/3513/promoter-pledges/","notes":"Feed is free and public. Practitioner signal is the 4-quarter direction, not the level (https://hdfcsky.com/blogs/risk-radar-by-sky/promoter-pledge-creeping-above-60-percent)."},
{"raw_id":"WRS-4","title":"Shareholding stops at top-level split; FII/DII left unparsed behind an XBRL link","severity":"high","area":"data","subsystem":"india-disclosures","repro":"Call shareholding_pattern: it returns promoter/public/employee-trust percentages plus a link to the XBRL that 'carries the full FII/DII split'.","evidence":"sidecar/services/agent_tools/catalog.py:684-697 (self-described); peers ship parsed FII/DII series - https://stockedge.com/pricing ('Sector Analytics - Results, Shareholding')","notes":"The capability's own docstring concedes the gap. Handing the user a link is not having the data."},
{"raw_id":"WRS-5","title":"No composite scorecard glyph for watchlist triage","severity":"medium","area":"ui","subsystem":"research/watchlist","repro":"fundamentals returns raw ratios; no composite score capability exists in the catalog.","evidence":"sidecar/services/agent_tools/catalog.py (no score capability); https://trendlyne.com/score-details/ (DVM: three 0-100 axes, disclosed inputs, stated refresh cadence); Tickertape Investment Scorecard per https://www.strike.money/reviews/tickertape","notes":"The two most-recognised objects in Indian retail research. Without one there is no list-legible triage and no anchor for alerts."},
{"raw_id":"WRS-6","title":"No earnings-call / concall transcript surface","severity":"high","area":"research","subsystem":"earnings","repro":"grep -in transcript sidecar/services/agent_tools/catalog.py returns nothing.","evidence":"sidecar/services/agent_tools/catalog.py (no transcript capability); https://trendlyne.com/ai-conference-calls/ (free-tier AI concall summaries); https://www.koyfin.com/pricing-llm-info/ ('the full history of transcripts, and advanced transcript search' at $39/mo)","notes":"Highest-signal unstructured source in equity research, absent from a product whose stated moat is research quality. Fiscal.ai and Bloomberg both build their AI on transcripts."},
{"raw_id":"WRS-7","title":"No segment revenue or operational-metric data","severity":"medium","area":"data","subsystem":"fundamentals","repro":"No segment or operational-metric capability in the catalog; fundamentals returns valuation ratios and a profile only.","evidence":"sidecar/services/agent_tools/catalog.py (fundamentals cap, ~line 226); https://www.tijorifinance.com/features/ ('1000+ operational metrics free; 6000+ premium', revenue mix by product and geography at Rs3500/yr); https://quantbrainai.net/blog/fiscal-ai-review-jul-2026/ (segment data as a screenable field)","notes":"This is the reason a serious fundamental investor keeps a second subscription. XBRL machinery already exists for shareholding."},
{"raw_id":"WRS-8","title":"Screener and backtest capabilities exist but no evidence of a backtest-this-screen path","severity":"low","area":"code","subsystem":"screener/backtest","repro":"screener_run, save_screen, backtest_summary and run_custom_backtest are separate catalog entries; no joining path observed in this read-only sweep.","evidence":"sidecar/services/agent_tools/catalog.py (four separate _cap entries); https://trendlyne.com/subscription/plans/ sells 200/1200 annual backtests as a paid axis","notes":"Flagged to VERIFY in the code lane, not asserted broken - this sweep did not open the screener or backtest module source."}
]
```

---

## Method notes and honest limits

- Sources consulted: 30+ distinct URLs; 12 fetched successfully as primary or near-primary sources.
- **Fetch blocked** (enterprise/network policy, error text quoted in-section): `www.tickertape.in`,
  `www.koyfin.com` (main site; the `pricing-llm-info` path did resolve), `www.bloomberg.com`,
  `blog.traderspost.io`. **HTTP errors:** `fiscal.ai/pricing` 403, `findmymoat.com` 429 (twice),
  `trendlyne.com/subscription/pricing/` 404, `aicerts.ai` 503, `screener.in` socket hang up.
  Every claim resting on those is labelled snippet-level in the text above.
- `trendlyne.com/features/` is JS-rendered; only nav chrome was captured and is reported as such.
- Prices are as advertised on the dates fetched and typically carry promotional discounts
  (Trendlyne "BESTPLAN", StockEdge "GANESHA"); treat them as list prices, not net.
- Live broker order execution is deliberately out of scope for this release and is **not** counted
  as a gap anywhere in this document.
- No repo file was modified other than this one. No process started or stopped. No GUI interaction.
