# triage-a: rc1-vshard-0:5, gate_news only gates IN targets

Auditor: Opus, group `triage-a`. Written 07:36 IST.

- HEAD: bed3b166. The code tree equals 01015033; see `triage-a-rc1-vshard-0-4.md` for that check.
- Scratch: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-a/`.
- In-process runs use `sidecar/.venv/bin/python` with `PYTHONPATH=.` and `VYSTED_DATA_DIR=<scratch>/data-inproc`, from `sidecar/`.

## Verdict

**partial on R15-RESEARCH-001.**

- Severity: **high**. The shard said medium; RESEARCH-001 itself was critical. The reasoning is in the Severity section.
- Certification failures: 1 (baseline 0, plus 1 for this verdict).

The shard's defect class holds at HEAD, but its evidence does not. The AMAL items it called "unrelated market-wide" are on-entity. The real repro is a US ticker that is also a common English word: IT (Gartner), ON (ON Semiconductor) and ALL (Allstate).

## 1. The shard's own evidence (AMAL) is wrong

`gate_news_us.py AMAL "Amalgamated Financial Corp." NASDAQ US` with `VYSTED_REGION=US`:

```
== AMAL region=US is_india_target=False ok=True items=20 gate_kept=20 note=None
row_relevant false on 7 of 20
  OFF: ['AMAL'] | Broadcom upgraded, Ultragenyx downgraded: Wall Street's top analyst calls | Yahoo! Finance: AMAL News
  OFF: ['AMAL'] | CFO Sells Nearly 20,000 Shares of Regional Bank for More Than $960,000 | Yahoo! Finance: AMAL News
  ... (5 StockStory listicles, all "Yahoo! Finance: AMAL News")
```

With no truncation, all 20 items have source `Yahoo! Finance: AMAL News` and symbols `['AMAL']`. They all come from AMAL's own Yahoo per-symbol feed.

- `news_provider.enrich` (news_provider.py:627-628, called from news_tool.py:55-56) drops every untagged region-feed item.
- I fetched the "Broadcom upgraded ..." article. It contains an Amalgamated Financial analyst call ("Amalgamated's above-peer profitability ...").
- The "CFO Sells ..." item is the Motley Fool Form-4 story on "Amalgamated Financial Corp." CFO Jason Darby, confirmed by fetching it.
- So `row_relevant` false here is a false negative of the title-only heuristic, not an off-entity item.

## 2. The defect class does reproduce, on common-word US tickers

`news_provider._aliases` keeps any bare ticker of 2 or more characters (news_provider.py:583). `_tag_symbols` matches it case-insensitively (`:606-607`), so the word "it", "on" or "all" in any region-feed headline tags that headline.

`common_word.py` with `VYSTED_REGION=US`:

```
== IT aliases=['IT', 'gartner'] items=28 from_region_feeds=8 gate_kept=28 row_relevant_false_on_region=8
   REGION: MarketWatch.com - Top Storie | Tax-free bond yields are in a sweet spot. Get in before it's too late.
   REGION: Insider Monkey | Palantir Reveals Its AI Sovereignty Strategy And Wall Street Is Starting to Believe It
== ALL aliases=['ALL', 'allstate'] items=16 from_region_feeds=1 gate_kept=16 row_relevant_false_on_region=1
== ON aliases=['ON', 'on semiconductor'] items=30 from_region_feeds=10 gate_kept=30 row_relevant_false_on_region=3
```

Next I drove the actual DEEP researcher, `deep._run_researcher`, in-process for a US-bound Gartner target (`deep_researcher_us.py`):

- The `news` tool is the real one.
- The web leg is stubbed off.
- The LLM is a stub that captures the extraction prompt.

```
== IT (US) dim=news ok=True news_items=28 region_feed_items=8 note=None
   REACHED RESEARCHER: MarketWatch.com - Top Storie | Tax-free bond yields are in a sweet spot. Get in before it's too late.
   REACHED RESEARCHER: Insider Monkey | Palantir Reveals Its AI Sovereignty Strategy And Wall Street Is Starting to Believe It
   REACHED RESEARCHER: Insider Monkey | Cantor Fitzgerald Sees Big Upside in Securitize (SECZ): Is It Time to Buy?
   REACHED RESEARCHER: Insider Monkey | Interparfums (IPAR) Extends Cavalli Fragrance Deal Through 2046. Can it Boost Profits?
   region-feed titles present in the extraction prompt: 8
```

`_record_structured` (deep.py:474-500) then cites each of these items as its own `ResearchSource` in Gartner's brief.

## 3. RESEARCH-001's own stated repro holds

The IN path is gated. `in_gate.py`, IN-bound target with the same common-word alias:

```
IN-bound IT: items=13 kept=0 note='No on-entity news found for IT — 13 item(s) returned by the news feed were off-entity/off-topic and dropped.'
```

The shard also saw the META namesake item dropped for an IN target.

## Root cause

- `sidecar/services/research/relevance.py:637`: `if not items or not (is_india_target(target) and target.is_equity_like()): return items, None`.
- `deep.py:920-928` routes the DEEP/ULTRA news leg through this gate, so for any non-IN target, region-feed items that were alias-tagged pass ungated to extraction and to cited sources.
- The IN-only scope was inherited from the FAST gate (1682b8fb, R13 #9, written for Indian namesakes). The RESEARCH-001 port (253d842f) kept it.
- The RESEARCH-001 fix_shape reads: "Route the DEEP/ULTRA structured news leg through the same relevance.row_relevant filter ... drop off-entity items". It is not scoped to IN, and its class is `off-entity-evidence`.

## Why partial, not new_defect or duplicate

- The residual is exactly RESEARCH-001's class: region-wide blend items about other companies reach the DEEP synthesis with no relevance gate.
- The entry's stated repro (IN) holds.
- The tagging that manufactures the off-entity items is R15-DATA-030's over-match class, which is item rc1-vshard-1:2 in this group. That fix alone would not close this, because the gate is the defence-in-depth layer RESEARCH-001 asked for.
- No other register entry covers the US news leg.

## Severity

I rated it high rather than critical. On a class of US tickers, the core DEEP research flow gets off-entity evidence and cites it as sources for the target. That is shown at the evidence and source layer. I have not shown a published brief misattributing it: that needs an LLM run, a hosted lane is out of bounds, and a local 8B run would not change the class.

## Certification failures

R15-RESEARCH-001 baseline is 0:

- no clause in its register note;
- not in any batch `not_certified` list;
- no prior partial or regression verdict.

Adding this partial gives **1**.

## Fix shape

Make `gate_news` gate every equity-like bound target, not only IN ones, without dropping the target's own per-symbol-feed items. Those items are tagged by provenance: in `_tag_symbols`, `symbol in item.symbols` is true for them.

- Carry that provenance through `news_provider.enrich` into the tool payload as a boolean such as `via_symbol_feed`.
- For a non-IN target, apply `row_relevant` only to items that were tagged by text alias.
- For an IN target, keep today's full gate, which covers the namesake per-symbol feed.

## Acceptance test

In `sidecar/tests/test_research_deep.py`, feed `_run_researcher` a US-bound `ResearchTarget('IT', 'Gartner, Inc.', 'NYSE', 'equity', 1.0, 'US')` and a stub `news` result with two items:

- an own-feed item "Gartner beats estimates", source "Yahoo! Finance: IT News", with `via_symbol_feed` true;
- an alias-tagged region item "Tax-free bond yields are in a sweet spot. Get in before it's too late.", source MarketWatch, symbols `['IT']`.

Assert:

- the region item is absent from the news structured pair and from the captured extraction prompt;
- the own-feed item is kept.

Live re-proof: `PYTHONPATH=. VYSTED_REGION=US sidecar/.venv/bin/python deep_researcher_us.py IT "Gartner, Inc." NYSE US "Gartner recent news and developments"` must print `region_feed_items=0`.
