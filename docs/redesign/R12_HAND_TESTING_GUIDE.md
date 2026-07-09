# Vysted Terminal — Hand-Testing Guide (R12)

Written for you coming back after weeks away, not remembering your own app. Read the three paragraphs, launch it, take the ten-minute tour, then go as deep as you like.

## What Vysted Terminal is, in three paragraphs

Vysted Terminal is a desktop finance terminal you own and run locally — a Tauri app (Rust core, Next.js UI, a Python FastAPI "sidecar" that does the data and AI work), bring-your-own-keys, no account, no cloud. It aims at Bloomberg-grade data coverage with an agent sitting in the middle of everything: you talk to it in plain language and it drives the terminal — pulls up charts, writes research briefs, configures screens, arranges panels, prepares (never places) orders. The moat is data trust: any stock you search returns complete, accurate, dense data, and the full-universe screener works cold or warm, every time, on a real IP.

The engine underneath (rebuilt in R10, made data-perfect in R11) is one resolver with India-first policy, a screener that runs the whole NSE/BSE universe, a research pipeline that stamps every figure with its basis and as-of date, and a §6.5 safety model that makes it structurally impossible for the agent to place a broker order — it can only prepare one for your review. R11 made the data inexhaustible: a fresh install on a hard-blocked IP still answers your exact IT-services screen in seconds, from a bundled seed pack plus a once-a-day exchange-direct price feed, with a circuit breaker that stops hammering a throttling provider and labels every value with its true freshness.

R12 (this run) removed the last question mark and hardened the data trust against the world. It proved the gap between R10 and now was two runs (a read-only census, then the R11 data sprint), re-verified the whole gate chain, then ran a ten-stock accuracy battery against live web sources that surfaced real defects — and fixed them: a stock that had been renamed (Gujarat Gas → Gujarat Energy) the app hadn't caught, provider growth numbers that were wrong on their own claimed basis, a research narrative that invented filing dates, an agent that couldn't reach the order-review dialog because of a classifier gap. Every one is fixed, test-pinned, and where possible re-verified live. The app you're opening is one you can release.

## How to launch it

```
cd ~/Documents/dev/vysted-terminal && pnpm tauri:dev
```

First launch after a while may rebuild the Python sidecar (~a minute or two — you'll see PyInstaller output); that's normal. If the window comes up white or blank, it's the known WKWebView occlusion throttle — click the Dock tile or resize the window once and it paints. The composer's model picker should already say **OpenRouter · GLM 5.2** or **Kimi K2.6** (your funded lane). Your DeepSeek-direct balance is empty by choice — if you pick that lane and see a "balance is empty" message, that's the humanized 402, not an outage.

## The ten-minute tour (the first clicks that show the machine)

1. **A marquee research run.** In the composer, type `Research WENDT` (or any name) and send. Watch the brief build in the right panel — a FAST stamp, an "EOD AS OF" date chip, a provider chip, metric cards (price, P/E, ROE, drawdown), and a synthesis with inline `[n]` citations. Click any `$TICKER` chip in the brief to load it into the chart.
2. **The cold-then-warm screener.** Open the screener (⌘K → "Open panel" → Screener, or ask the agent "screen NSE IT services under ₹5,000 cr, P/E < 20, ROE > 15%"). It returns ~22 real rows — and even on a freshly-cleared cache with the provider throttling, it answers in seconds with a PARTIAL badge and honest freshness labels rather than hanging or lying. SAKSOFT should be in the set.
3. **The portfolio scenario.** Ask "add 5 RELIANCE, 5 INFY, and 5 TATASTEEL to my paper portfolio." The agent stages the adds; your portfolio shows three positions with correct cost bases and a real (non-zero) ₹ total — all one currency, one subtotal.
4. **One persona.** Ask "what would Buffett think of this?" on a loaded name — the copilot hands off to the Buffett value lens. Personas drive loaded panels, not just chat.

## The deep tour (surface by surface — what "correct" looks like)

- **Composer:** the model picker searches 346 models; the +menu carries context/persona/autonomy/mode; Normal/Deep/Ultra are three depth stops (Deep and Ultra escalate in place and cost more); sending morphs the send button to a stop, and you can queue the next prompt while one streams.
- **Symbol resolution:** try the ambiguous surnames — Reliance, Tata, Bajaj, Adani, Birla, Mahindra, Jindal, Godrej, L&T. Each resolves to the right listing or offers a named chooser; it never silently binds a foreign OTC ticker. **New in R12:** search "Gujarat Gas" — it now resolves to **GUJENERGY** (the July-1 rename) with a "renamed from GUJGASLTD" note, not the stale identity.
- **Research briefs:** every figure carries its basis. Drawdown ("vs 52-week high") and 52-week price change ("trailing 52 weeks") are two distinct, labeled cards — not the same number twice. Dividends reconcile declared-vs-paid. **New in R12:** growth figures now cross-check against the company's own quarterly statements — when the provider's number disagrees with the statements on the same claimed basis (common for banks), you get a Conflict Note showing both, never a silently-picked wrong number. And the narrative can no longer invent filing dates for a corporate action it can't cite.
- **Screener:** criteria path, pasted-formula path, and agent-authored path all hit one engine and return identical rows. A deliberately heavy screen completes or fails honestly, never hangs. **New in R12:** the agent now filters by sector server-side instead of sweeping everything and post-filtering (which could silently drop matches).
- **Panels:** dockview tabs, charts with indicators, watchlist, comparison cockpit, notes, code nodes. Tab-switching works; **drag-to-reorder tabs and drag palette→canvas need your hand** — no automation can synthesize those.
- **Settings:** every control reads and writes; check the Region & Locale, Keybindings, and Advanced tabs.
- **Plugins:** the marketplace and manager work; six plugins load (brokers, example, openbb-mcp, vysted-lenses, vysted-news, yfinance). Tradesa is fully removed — the plugin system is alive without it.
- **Orders (the safety showcase):** ask "buy 5 shares of RELIANCE at market." The agent PREPARES the order into a review bar reading "ROUTES TO THE CONFIRM-BEFORE-PLACE DIALOG — NOTHING IS PLACED AUTOMATICALLY." Even if you click Accept, it fails closed ("no broker adapter registered") — it structurally cannot place an order without a broker you connected yourself. That's §6.5, and it's proven live this run.
- **Error handling:** every failure — bad key (401), empty balance (402), throttle (429), network down, search-engine down, garbage symbol — renders a human sentence plus a next action, with the raw detail behind a Details toggle. No naked JSON anywhere.

## Your personal checklist (NEEDS-MANUAL-CHECK — the four things a rig can't do)

1. **In-webview drags** — reorder dockview tabs by dragging; drag a node from the editor palette onto the canvas. No rig on this Mac can synthesize a trusted drag; you have to feel these by hand.
2. **Narrow-width sweep** — drag the window down to its ~960px minimum and eyeball every panel and the Settings tabs for clipped or overlapping text. The spacing audit passes statically, but your eye is the gate.
3. **The screener throttle chips, re-shot** — R11 captured the full chip set live (PARTIAL badge, "DATA PROVIDER IS THROTTLING THIS IP", "15 LIVE · 8 MIXED", per-tier freshness). Clear your fundamentals cache and re-run the IT screen to see it fresh on your own eyes.
4. **The taste pass** — persona voices, micro-interactions, the feel of the thing. That's yours alone.

## Honest edges before you show this to the world

- **Bank growth numbers will carry Conflict Notes routinely.** yfinance's revenue-growth scalar for Indian banks rides a different revenue definition than the statements, so the cross-check flags it. That's the app being honest that the number is unusable-as-claimed, not a bug — but expect to see the note on bank briefs.
- **Provider data can be wrong and the app says so, not that it's right.** The battery found the app RIGHTER than the aggregators twice, and found provider quirks (dividend rate omitting specials, institutional-holding fields off by orders of magnitude on thin BSE microcaps) that it flags rather than fabricates. Where a figure is genuinely unavailable, you get an honest gap, not a zero.
- **The default research lane is a model choice.** DeepSeek V4 Flash sometimes refuses tool calls (a content-filter finish); glm-5.2 and kimi-k2.6 on the same key drive every tool. The app explains the refusal honestly rather than showing a raw error — but if host-actions feel flaky, switch the model, not the app.
- **Deep-research briefs run on a time budget.** A deep run winds down and synthesizes when its slice is up rather than running forever; the brief says so.
