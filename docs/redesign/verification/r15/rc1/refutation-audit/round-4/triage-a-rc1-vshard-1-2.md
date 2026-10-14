# triage-a: rc1-vshard-1:2, the news alias over-matches

Auditor: Opus, group `triage-a`. Written 07:40 IST.

- HEAD: bed3b166. The code tree equals 01015033.
- Own sidecar on :52420.
- Scratch: `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit4-triage-a/`.

## Verdict

**partial on R15-DATA-030.**

- Severity: **medium**, the same as the shard. It matches the refuter's final severity for DATA-030's over-match raw id COD-market-data-providers-2-14.
- Certification failures: 1 (baseline 0, plus 1 for this verdict).

## Repro at HEAD, part 1: the shard's same-name company cases

`alias_overmatch.py` runs `news_provider.build_aliases` and `_tag_symbols` in-process on a `NewsItem` from a non-per-symbol feed (`symbols=[]`):

```
RELIANCE.NS  'Reliance Power wins Bhutan project'         -> ['RELIANCE.NS']  aliases=['RELIANCE.NS', 'RELIANCE', 'reliance industries']
RELIANCE.NS  'Reliance Infrastructure plunges'            -> ['RELIANCE.NS']
RELIANCE.NS  'Reliance Communications insolvency update'  -> ['RELIANCE.NS']
LT.NS        'LT Foods Q2 profit jumps 30%'               -> ['LT.NS']      aliases=['LT.NS', 'LT', 'larsen & toubro']
ITC.NS       'ITC Hotels shares list at premium'          -> ['ITC.NS']     aliases=['ITC.NS', 'ITC', 'itc']
control RELIANCE.NS 'Reliance Industries Q2 profit rises 10%' -> ['RELIANCE.NS']
control TCS.NS 'Tata Motors PV unit demerger'             -> []
```

In the live IN region feed at 07:3x IST, none of these names happened to appear; the scan is in `region_feed.py`. So part 1 is proven on the matcher, which is deterministic code.

## Repro at HEAD, part 2: a fresh live case of the same class, on the actual `/news` route

`curl -s -H "X-Vysted-Region: US" "http://127.0.0.1:52420/news?symbols=IT&limit=50"` (IT is Gartner):

```
IT (Gartner) US /news items 28 own-feed 20 region-feed tagged IT 8
    MarketWatch.com - Top Storie | Tax-free bond yields are in a sweet spot. Get in before it's too late. | symbols ['IT']
    MarketWatch.com - Top Storie | 'She says it's just money': My friend pays for everything. ... | symbols ['IT']
    Insider Monkey | Palantir Reveals Its AI Sovereignty Strategy And Wall Street Is Starting to Believe It | symbols ['IT']
    Insider Monkey | Interparfums (IPAR) Extends Cavalli Fragrance Deal Through 2046. Can it Boost Profits? | symbols ['IT']
    Yahoo Personal Finance | What is the prime rate, and how does it affect you? | symbols ['IT']
```

The same happens for ON (10 region items) and ALL (1). Tickers such as NOW, KEY, LOW and CAT share the shape. The raw output is in `item2-4-common-word-US.txt`.

## Root cause

- `sidecar/services/news_provider.py:583` keeps every bare or suffixed ticker of 2 or more characters as a text alias.
- `:606-607` matches each alias case-insensitively with `\b...\b` over title and summary.
- As a result:
  - a bare ticker that is the leading word of another listed company's name tags that company's headlines (RELIANCE and "Reliance Power", LT and "LT Foods", ITC and "ITC Hotels");
  - a ticker that is an English word tags any headline containing the word (IT and "it", ON and "on", ALL and "all").

## Why partial on DATA-030

R15-DATA-030 is fixed. Its class is `raw-string-symbol-match`.

- The title names both halves of the defect: suffixed Indian tickers tag nothing (under-match), and single-letter tickers "tag every headline containing the article 'a'" (over-match).
- The fix_shape prescribed "require len>=2 for bare-text matches and use the company name for 1-letter tickers".
- The under-match half and the 1-letter over-match are fixed. The shard reproduced RELIANCE.NS, HDFCBANK, SBIN, BAJFINANCE and TCS.NS tagging, and A/T/F/C prose not tagging.
- The same over-match mechanism still fires for 2+ character tickers that are prose words or company-name prefixes: a raw ticker string matched case-insensitively in prose.
- The register already records this residual in DATA-030's note: "the bare-ticker alias can now also tag an unrelated same-name company's headlines (e.g. RELIANCE would also tag 'Reliance Power' ...) ... flagged for the next verifier pass".
- Because the existing entry is fixed and the residual reproduces, this is partial, not duplicate.

## Severity

Medium.

- The News panel and the `news` tool show unrelated or other-company headlines tagged to the requested symbol, with sentiment.
- The headline text names the other company, so a reader can spot most cases.
- Where the same tags feed the US DEEP research leg, that is rc1-vshard-0:5 (partial on RESEARCH-001, high).

## Certification failures

R15-DATA-030 baseline is 0:

- its note has no "certification failures so far" clause;
- it is not in any `not_certified` list;
- no audit partial or regression verdict.

Adding this partial gives **1**.

## Fix shape

In `news_provider._aliases` and `_tag_symbols`:

- Match the ticker aliases (bare and suffixed) case-sensitively, i.e. as an uppercase token. Prose "it", "on", "all" or "Reliance" then never matches a ticker.
- Keep the company-name alias case-insensitive.
- Drop the bare-ticker text alias when that ticker is the first word of a different listed company's name in the resolver masters (RELIANCE: Reliance Power and Reliance Infrastructure; LT: LT Foods; ITC: ITC Hotels). For those tickers, only the company-name alias and per-symbol-feed provenance tag.

## Acceptance test

In `sidecar/tests/test_news.py`, parametrise `_tag_symbols(item, build_aliases([sym]))` on items with `symbols=[]`:

| Symbol | Headline | Expected |
|---|---|---|
| IT | "Tax-free bond yields are in a sweet spot. Get in before it's too late." | `[]` |
| ON | "Choosing these AI-exposed college majors could dent your job prospects" | `[]` |
| RELIANCE.NS | "Reliance Power wins Bhutan project" | `[]` |
| LT.NS | "LT Foods Q2 profit jumps 30%" | `[]` |
| ITC.NS | "ITC Hotels shares list at premium" | `[]` |
| RELIANCE.NS | "Reliance Industries Q2 profit rises 10%" (control) | `['RELIANCE.NS']` |
| IT | "Gartner beats estimates" (control) | `['IT']` |

Live re-proof:

```
curl -s -H 'X-Vysted-Region: US' 'http://127.0.0.1:<port>/news?symbols=IT&limit=50' | jq '[.[] | select(.source | test("IT News") | not)] | length'
```

This must print 0. The route returns a bare JSON array.
