# Refutation audit round 2: R15-AGENT-053 (group surface, key rc1-verifier:11) at 4c6dfe8c (code tree; HEAD a3275f64, docs-only diff)

Verdict: **partial**. Audited 18:15-18:21 IST.

## Tree check
`git diff --name-only 4c6dfe8c HEAD | grep -v '^docs/'` printed nothing.

## Certification
- batch-10 VERDICTS.json: certified. VERDICTS.md:53 cites only the context-provider.test cases, which cover the generic otherPanels summary.
- Fix commit 2eec39a9 "generic per-source panel summaries + clickable symbols". Its --stat touches the earnings, analyst-ratings, sec, screener, macro and quant panels plus context-provider.ts. It does **not** touch src/modules/news/NewsFeedPanel.tsx. `git log 2eec39a9..HEAD -- src/modules/news/NewsFeedPanel.tsx` shows only 898e4f9f, a token swap.
- Round-1 REFUTATION_AUDIT.json: this id is absent.

## Entry's own repro, re-run at the candidate
The entry's repro has two halves. (a) Context: open Backtest/News/Equity or Earnings and ask what is on screen. (b) Clicks: "Click a symbol in an earnings row, or a symbol chip on a news item: nothing happens".

(a) plus the earnings/analyst/SEC half of (b), certified tests re-run:
`node_modules/.bin/vitest run src/modules/chat/context-provider.test.ts src/modules/earnings/EarningsCalendarPanel.test.tsx src/modules/analyst-ratings/AnalystRatingsPanel.test.tsx src/modules/sec/SecFilingsPanel.test.tsx src/modules/news/NewsFeedPanel.test.tsx -t "053|generic summary|otherPanels|loads it into the chart|symbol" --reporter=verbose`
```
 Test Files  5 passed (5)
 ✓ context-provider.test.ts > otherPanels generic summary (R15-AGENT-053) > carries a backtest AND a news publish, each as a generic summary
 ✓ EarningsCalendarPanel.test.tsx > clicking a symbol loads it into the chart without triggering the row's expand
 ✓ AnalystRatingsPanel.test.tsx > clicking the symbol header loads it into the chart (R15-AGENT-053)
 ✓ SecFilingsPanel.test.tsx > clicking the company name/identifier loads it into the chart (R15-AGENT-053)
 ✓ NewsFeedPanel.test.tsx > renders the symbol tags for each item   (render only; no click assertion)
```
The news half of (b) was driven live in a jsdom render of the real NewsFeedPanel. The scratch test is /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit2-surface/vt/news053.test.tsx and it runs under the scratch config /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit2-surface/vt/vitest.config.mts, rooted at the repo. It mocks fetchNews to return one item with symbols ["AMD"] and mocks host-actions.loadSymbolIntoChart as a spy. It then clicks the chip.
`node_modules/.bin/vitest run --config /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit2-surface/vt/vitest.config.mts`
```
REFAUDIT chip tag: SPAN role button? null inside <a> href: https://example.com/n1 onclick attr: null
REFAUDIT buttons named AMD: 0
REFAUDIT loadSymbolIntoChart calls: []
REFAUDIT chart-command changed: false equity-command changed: false
```
**The news-chip half reproduces exactly as the entry states it.** The chip is a SPAN nested inside the article <a href=item.url target=_blank>. No button carries the symbol name. A click makes no loadSymbolIntoChart call and changes neither the chart-command store nor the equity-command store. In the app, the click falls through to the anchor and opens the article.

## Verifier's refutation (rc1-verifier:11), re-run
Evidence: verifier/g2/spot-refutation-code.txt, NewsFeedPanel.tsx:118-150. Reading HEAD confirms the same code: src/modules/news/NewsFeedPanel.tsx:118-125 is the <a>, and :138-148 renders `item.symbols.map(symbol => <span ...>{symbol}</span>)`. The live render above agrees. The refutation holds.

## Why partial, not verifier_error or regression
This is not a verifier error. The news chip is named in the entry's own repro and in its fix_shape ("make rendered symbols buttons calling loadSymbolIntoChart"). It is not a regression either: NewsFeedPanel was never touched by the fix, so this half was never fixed. The rest of the entry's repro holds fixed: the context half and the earnings/analyst/SEC clicks. So the verdict is partial.
A llama3.1:8b agent run was not used. The refuted half is a renderer click handler and involves no agent tool call.

## Root cause
src/modules/news/NewsFeedPanel.tsx:138-148 renders the symbol chips as inert <span>s inside the article anchor at :118-125.

## Fix shape
Close the anchor after the title/meta block so that it wraps only the headline and the meta row. A <button> inside an <a> is invalid interactive nesting. Then render the symbol row as a sibling inside the <motion.li>, with each symbol as <button type="button" aria-label={`Load ${symbol} in chart`} onClick={() => loadSymbolIntoChart(symbol)}>. The button should keep the chip styling. Use the same host-actions import that earnings and analyst-ratings already use.

## Acceptance test
In src/modules/news/NewsFeedPanel.test.tsx, vi.mock("@/lib/host-actions") with a loadSymbolIntoChart spy. Render with newsItem({symbols:["NVDA"]}). Assert all of the following:
- `screen.getByRole("button",{name:/NVDA/})` exists.
- Its `closest("a")` is null.
- fireEvent.click on it calls loadSymbolIntoChart with "NVDA".

Live re-proof: rerun `node_modules/.bin/vitest run --config /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit2-surface/vt/vitest.config.mts` (news053.test.tsx). It must print `buttons named AMD: 1` and `loadSymbolIntoChart calls: [["AMD"]]`.

## Certification-failure count
batch not_certified lists: 0. Round-1 audit: 0. This gate: 1 (partial). **Total 1.**
