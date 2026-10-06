# R15 Stage C: batch-29 verifier verdicts

- Verifier: a fresh-context verifier (claude-opus-5-5) on 27 Sep 2026, 11:16 to 11:35 IST.
- Target: `worktree-agent-batch-29-int@cee5dc19`. Base: `522c3246`.
- Sidecar: booted from the worktree source on `127.0.0.1:52310`, with a copy of `vysted-iso/data` and MCP on :52153/:52154.
- Local model: `llama3.1:8b` via ollama.

**Verdict: BLOCK.** Six entries are certified. R15-DATA-030 is not certified, and its commit `e7d5a628` regresses
on-entity news tagging that the base had. The other six entries do not depend on that commit. Revert or rework only
`e7d5a628`, then merge the rest.

## Chain

- `pnpm ci-local`: `CI_EXIT=0` at 54239c87 (pytest 3784 passed, 1 skipped). Smoke: `SMOKE_EXIT=0`.
- cee5dc19 is the only commit after CI, and it touches only `src/lib/host-actions.ts` and its test. The verifier re-ran:
  - vitest `host-actions.test.ts`: 115/115.
  - prettier, eslint and `tsc --noEmit`: clean.
- Focused pytest at head, 9 changed test files: 263 passed.

## Certified

### R15-RESEARCH-001 (critical)

Live DEEP `_run_researcher` against the live news tool (`VYSTED_REGION=US`, the query "… recent news and
developments"):

| Target | Case | news_items | region_feed_items | in extraction prompt |
|---|---|---|---|---|
| ON Semiconductor | literal | 20 | 0 | 0 |
| IT | literal | 20 | 0 | 0 |
| ALL | literal | 15 | 0 | 0 |
| **AI (C3.ai)** | fresh | 20 | 0 | 0 |
| GE | fresh | 20 | 0 | 0 |
| META | fresh | 18 | 0 | 0 |
| BDL (IN) | original repro | 0 | 0 | 0 |
| RELIANCE (IN) | IN path | 0 | 0 | 0 |

- **Fresh class case (AI).** `/news?symbols=AI` hands 7 alias-tagged, off-entity region items to the tool: "AI-exposed
  college majors", Palantir, Accenture and others. The gate dropped all 7, and none reached the researcher.
- **In-process `row_relevant`, base → head:**
  - "Lockheed wins contract on hypersonic program" for ON: True → False.
  - "ON Semiconductor beats estimates", "C3.ai shares jump", "AMD beats estimates" and "Allstate catastrophe losses
    mount" all stay True.
- Residuals are filed as issues: an ALL-CAPS 3-character ticker still passes, and "GE beats estimates" is now
  under-included.

### R15-DATA-063 (medium)

Live, `/indicators` freshness against `/history` freshness for the same symbol:

| Case | /indicators | /history | Parity |
|---|---|---|---|
| TCS rsi (literal) | eod | eod | True |
| INFY.NS ema | eod | eod | True |
| AAPL sma | eod | eod | True |
| **HDFCBANK.NS macd** (fresh) | eod | eod | True |
| **RELIANCE.BO rsi** (fresh) | eod | eod | True |
| **BTC/USDT 1h, asset_class=crypto** (fresh) | live | live | True |
| **TCS 1h** (fresh) | eod | eod | True |

The empty series ZZZNOTREAL returns 200 with provider none and freshness None. That is the downgrade kept.

### R15-LEAD-004 (medium)

Live `/fundamentals` with `X-Vysted-Region: IN`:

- NDTV: the reason is "the exchange filings leave a quarter of the trailing year unfiled or unparsed; kept, flagged".
  "half-yearly" does not appear.
- JONJUA keeps "(a half-yearly filer)".
- TCS.NS carries no reason.

Fresh `cadence()` shapes, in-process:

| Shape | cadence() |
|---|---|
| Jan-Mar unfiled, no 6-month period | quarterly-gap |
| Oct-Mar 6-month period with Jan-Mar filed inside | quarterly |
| Complete Jul-25..Jun-26 | quarterly |
| Pure half-yearly, newest period ending March | half-yearly |
| Pure half-yearly, newest period ending September | half-yearly |
| Calendar-FY halves | half-yearly |

A recently listed filer with only 2 quarters filed gets "half-yearly". This is filed as an issue: the rule's letter
and its rationale differ, and the base behaved the same.

### R15-LIFECYCLE-020 (medium)

Fresh case, in-process against a faked Yahoo that answers 429 to every request:

1. Two user 429s: ct=2.0, circuit closed.
2. Then 10 india `fundamentals_warm` sweeps (2400 symbols) and 30 sp500 `_warm_once` cycles (506 symbols), 2436
   HTTP calls in all: circuit still closed, ct=2.0, opens_total=0. The warm 429s advanced nothing.
3. The next user 429 opens the circuit. The user fetch spent 3 HTTP calls.

Live `/system/provider-health` on the booted sidecar: yahoo open=false, ct=0.

### R15-LEAD-048 (medium)

A scratch vitest ran the fresh cases through the real `applyIntent` / `describeIntent`. It was deleted and never
committed. 7/7 passed:

- `technical` and `macro` each apply the mode (one `clear`, no `resetLayout`), and the preview reads "Switch to the …
  layout".
- `toString`, `hasOwnProperty`, `Fundamental` and `fundamental layout` each fail with the pattern named, with no reset
  and no clear.
- `macro` with no mounted layout fails "not mounted" and does not reset.

Agent side: `llama3.1:8b` given "/layout fundamental" emitted `arrange_layout {pattern:"research-cockpit"}`, which
honours the schema enum. So the chat path does not reach the host with a raw mode id on this model, and the host path
is covered by vitest.

### R15-LEAD-049 (medium)

Live results:

- `POST /screener/run {universe:"nifty50", criteria:[]}`: evaluated 50, skipped 0, "screened 50 of 50 — 0
  unavailable". TMPV is present and TATAMOTORS is absent.
- `/resolve?q=TATAMOTORS` candidates: `[TMPV, TMCV, TSLA]`, with TMPV first.
- `/quotes/TMPV.NS`: 200 (nse_direct 290.45).

Fresh class audit of every universe seed against the current masters:

- `nifty50.json`: 0 missing.
- `sp500.json`: ECHO and VMRK are missing. They are filed as an issue, because the entry's sibling audit covers only
  the retired Tata Motors ticker.
- Direct `/quotes/TATAMOTORS.NS` still returns 404. That is outside the fix_shape and is filed as an issue.

## Not certified

### R15-DATA-030 (high): regression

The literal repros pass: IT "it's", ON "On Holding", "RELIANCE POWER", "LT Foods" and "ITC Hotels" all give `[]`. Live
`/news` for IT, ON and ALL (US) now carries 0 alias-tagged region items.

**The claim fails in two ways.**

1. **Under-match regression**, in-process with base `522c3246` against head:

| Symbol | Headline | Base | Head |
|---|---|---|---|
| RELIANCE.NS | "Reliance Q2 profit jumps 9% on retail, Jio" | tagged | not tagged |
| RELIANCE.NS | "Reliance shares hit record high" | tagged | not tagged |
| MARUTI.NS | "Maruti sales rise 8% in September" | tagged | not tagged |
| META | "Meta unveils new Llama model" | tagged | not tagged |
| UBER | "Uber beats estimates on ride growth" | tagged | not tagged |

   - Live: the real TheStreet region item "Bank of America backs Meta stock after Muse surprise" is tagged `['META']`
     at base and `[]` at head. It is absent from `/news?symbols=META`.
   - Mechanism: the ticker alias is now case-sensitive, so `META` no longer matches "Meta". The name alias is the full
     multi-word master name ("meta platforms", "reliance industries"), so a short-name mention matches nothing.
   - This is the single-word-name class that got batch-28's DATA-030 fix reverted.

2. **Acronym-ticker class not fixed.** Live `/news?symbols=AI` (US) returns 7 alias-tagged, off-entity region items.
   One of them is "Choosing these AI-exposed college majors could dent your job prospects", the headline the
   acceptance pins as `[]` for ON. The research gate drops these items for DEEP, but the News panel shows them.

## Issues noticed (not in any entry's diff)

1. **ALL-CAPS 3-character tickers still pass the relevance gate.** For a non-IN 3-character common-word ticker, an
   ALL-CAPS title still scores 0.6. "ALL EYES ON THE FED…" counts for Allstate. The code marks this with a ponytail
   ceiling, and no live feed item today is all-caps.
2. **2-letter tickers are under-included for non-IN targets.** A 2-letter ticker never passes alone now. "GE beats
   estimates on jet engine demand" was relevant to GE Aerospace at base and is dropped at head.
3. **`cadence()` mislabels a recent IPO.** A recently listed quarterly filer with 2 quarters filed is labelled
   half-yearly.
4. **Direct quotes on the retired ticker give no rename hint.** `/quotes/TATAMOTORS.NS` and `/quotes/TATAMOTORS.BO`
   return 404 without pointing to TMPV.
5. **`sp500.json` has stale symbols.** It carries ECHO and VMRK, which are absent from the US master.
