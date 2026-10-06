# CODE CRITIQUE — `market-data-providers-2`

APOSD critique (skill `aposd-critique`, 18 principles, two personas). Subsystem =
the READ SURFACE over the market-data providers: 9 routers, 6 model modules, 7
agent-tool handlers, 3 TS contracts (2,855 LOC actual; partition `loc` 5,925 counts
the test files too). Every core file read in full.

**Assessment independence: degraded (sequential).** No sub-agent tool in this worker's
harness, so Strategic-Thinker and Tactical-Tornado passes ran one after the other in a
single context. Per the skill's own troubleshooting row, the second pass is therefore
biased by the first; treated as one synthesis, not two votes.

**Snapshot persistence: skipped deliberately.** `.aposd/critique/` would drop untracked
files into the operator's repo mid-census. This file + `raw/code-market-data-providers-2.json`
are the census deliverables.

---

## Tactical Tornado verdict

**Medium-high.** This is not tornado code — the docstrings are unusually good, the
concurrency decisions are measured and explained (`routers/quotes.py:6-13` cites the
real ~26s→slowest-symbol number), and the `provider_registry` dispatch seam is honoured
everywhere (no router hardcodes a provider). What the tornado left behind is narrower and
more dangerous: **placeholder values that render as facts**, and **a data-identity decision
implemented once in the sidecar and silently re-implemented in the client**.

The most damning pattern: `services/sec_filings_provider.py:544-555` synthesises a
`Filing` with `form_type="10-K"` and `filed_date=datetime.now(tz=UTC).date()` when the
accession is not in the last 40 filings — the FilingViewer then labels an arbitrary
filing as a 10-K filed today. A placeholder became a rendered fact.

Red flags found: 11 (2 information leakage, 1 pass-through method with a false comment,
3 repetition clusters, 2 special-general mixtures, 3 obviousness/consistency).

---

## Design principles score

| #  | Principle | Verdict | Evidence (file:line) | Consequence |
|----|-----------|---------|----------------------|-------------|
| 1  | Strategic over tactical | at-risk | `sec_filings_provider.py:549` `form_type="10-K"` placeholder in a shipped render path; `routers/earnings.py:141` `__all__ = ["date","router"]` re-exports a dead import to dodge ruff F401 | Tactical residue inside otherwise strategic code; the lint dodge keeps a dead import alive forever |
| 2  | Deep modules | at-risk | `services/agent_tools/sec_tools.py:34-74`, `:77-110`, `:113-152` — three ~35-line bodies that are 90% envelope over one provider call | 9 shallow wrappers whose only added value is `{"ok": bool}`; cognitive load per tool ≈ its implementation |
| 3  | Information hiding | at-risk | `correctness_gate.py:76-90` `_match_key` owns "are these the same instrument"; `routers/quotes.py:85-87` returns a bare list that forces the caller to re-derive it | Change amplification: the normalisation rule now lives in Python AND in `src/modules/watchlist/api.ts:40,57` |
| 4  | General-purpose modules | pass | `routers/history.py:72`, `indicators.py:64`, `price_data.py:46` all call the same `provider_registry.get_history(symbol, timeframe, range_, asset_class)` — no per-route provider switch | One dispatch point; adding a provider touches no router |
| 5  | Different layer, different abstraction | violate | `sec_filings_provider.py:563-575` `get_filing_sections` = `get_filing(...).sections`, a pass-through whose docstring claims "a cheaper route without re-fetching the metadata row" while `get_filing:526-538` makes **both** upstream calls | Pass-through method + an actively false interface comment; `routers/sec_filings.py:127-141` publishes it as a distinct cheaper route |
| 6  | Pull complexity downward | violate | `routers/quotes.py:85-87` elides failures from a positional list, pushing the symbol-join upward to TS | The client cannot join by index and joins by spelling instead — see P1 below |
| 7  | Better together or apart | at-risk | `routers/earnings.py:68-81, 89-100, 108-119, 127-138` — one cache-read/validate/fetch/502/cache-write block, four copies | Adding stale-while-revalidate or a cache-bypass header = 4 edits |
| 8  | Define errors out of existence | violate | `routers/quotes.py:47-48` + `history.py:50-51` swallow to `freshness=None`; `ChartPanel.tsx:385` `series.freshness ?? null` then renders **no badge** | The failure default is "looks live", the unsafe direction for an FR-041 surface |
| 9  | Design it twice | at-risk | `models/sec.py:23` `FilingFormType = Literal[7 forms]`; `sec_filings_provider.py:288-291` silently `continue`s on anything else | The 7-form set was never re-designed against EDGAR's real form space (20-F, 6-K, S-1, 424B, SC 13D, 10-K/A) |
| 10 | Comments describe non-obvious | at-risk | Mostly excellent (`routers/quotes.py:6-13`, `health.py:14-22`). But `routers/news.py:63-68` documents a word-boundary guarantee the code does not deliver, and `sec_filings_provider.py:570` is false | A wrong comment is worse than none — it stops the next reader from checking |
| 11 | Comments first | pass | Every module opens with a real interface docstring stating contract + rationale, e.g. `routers/sec_filings.py:1-24`, `models/sec.py:1-10` (XBRL-as-string rationale) | Contracts were written before bodies; the XBRL precision decision is legible |
| 12 | Choosing names | pass | `_empty_series_reason` (`history.py:16`), `return_pct_window` (`compare_symbols.py:28`), `_label_freshness` (`quotes.py:30`) each create an image | Names carry the concept without a comment |
| 13 | Modifying existing code | pass | `routers/health.py:14-22` records the hardcoded-`"0.2.1"`-drifted-5-releases regression **in the code**, not only the commit | The next reader cannot re-introduce it by accident |
| 14 | Consistency | violate | Freshness labelled on 2 of 8 data routes; `EmptySeriesError` downgraded in `history.py:73` but not in its sibling `indicators.py:64`; `asyncio.gather` uses `return_exceptions=True` in `quotes.py:84` and omits it in `compare_symbols.py:142` / `market_overview.py:111`; module-level imports everywhere except `system.py:210,217,229` | Every learned pattern has a counter-example, so none can be trusted |
| 15 | Code should be obvious | at-risk | `compare_symbols.py:69,84` and `market_overview.py:90` write `except (ProviderError, Exception)` — a tuple whose first member is unreachable | Reads as two handled cases; is one blanket catch that also eats `AttributeError`/`TypeError` |
| 16 | Design for the future | at-risk | `models/sec.py:23` closed Literal; `market_overview.py:28-31` `_INDICES_BY_REGION` hardcodes US+IN with `_DEFAULT_INDICES = US` | A GLOBAL/EU user silently gets the US benchmark set labelled with their own region |
| 17 | Performance as design | pass | `routers/quotes.py:6-13` documents the measured serialisation (~26s/55 symbols) and the fan-out fix; `routers/earnings.py:36-38` domain-tuned TTLs | Design-level fix, measured, not a micro-optimisation |
| 18 | Increments are abstractions | at-risk | Phase 6 added earnings + analyst + SEC tool families; each got its own copy of the envelope (`earnings_tools.py:64-81`, `analyst_tools.py:32-49`, `sec_tools.py:34-74`) rather than one envelope abstraction | Decomposed by feature, not by abstraction boundary |

**Summary: 5 pass, 9 at risk, 4 violate (5/18 pass).**

---

## What's working

1. **The provider seam is honoured without exception.** Every OHLCV consumer in the
   subsystem — `history.py:72`, `indicators.py:64`, `price_data.py:46`,
   `compare_symbols.py:76` — enters through the same `provider_registry.get_history`
   signature. No router knows a provider name. Adding NSE/BSE/yfinance fallthrough
   changed zero router lines; that is the change-amplification win the whole design was for.

2. **Concurrency is designed, measured, and explained.** `routers/quotes.py:6-13` names
   the symptom (26s for 55 symbols), the mechanism (blocking `fast_info` on the request
   thread starving the uvicorn pool), the fix, and the precedent it mirrors. A reader
   three years out can tell whether the constraint still holds. `crypto.py:1-12` does the
   same for the ccxt round-trip and the `finally: await stream.aclose()` invariant.

3. **`models/sec.py:1-10` pulls a genuinely hard decision downward.** XBRL values that
   overflow `Number.MAX_SAFE_INTEGER` are typed `str` on both sides with the reason stated
   at the top of the file, and `types/sec.ts:135-140` matches exactly. Every one of the
   three TS mirrors (`earnings.ts`, `analyst.ts`, `sec.ts`) was checked field-by-field
   against its Python model — **zero drift**, despite CLAUDE.md flagging hand-mirroring as
   a standing hazard.

---

## Priority issues

### [P0] `get_filing` fabricates filing identity — a placeholder renders as fact
- **Principle**: Define errors out of existence (#9) / Strategic over tactical (#1)
- **Evidence**: `sidecar/services/sec_filings_provider.py:544-555` —
  `form_type="10-K"`, `filed_date=datetime.now(tz=UTC).date()`, `company_name=""`;
  and `:528` `{"identifier":…, "accession_number":…, "form_type": "10-K"}` sent to the
  upstream sectioner for **every** filing. Rendered by `routers/sec_filings.py:114-124` →
  `FilingDetail` → FilingViewer.
- **Complexity symptom**: Unknown unknowns
- **Why it matters**: `get_filing` locates metadata by re-listing only the last 40 filings
  (`:536`) and filtering by accession. For any active filer that is well under a year of
  history, so opening a legitimately older filing from a search result or an agent's
  `sec_filing_content` call takes the synthetic branch and the panel shows *"10-K · filed
  today"* over a 2021 8-K. Separately, `:528` asks the upstream to section a 10-Q/8-K/DEF 14A
  against a 10-K item map, so the sections themselves may be wrong or empty with no signal.
  This is the one finding in the subsystem that puts a false, money-relevant fact on screen.
- **Fix**: Delete the synthetic `Filing`. When the accession is absent from the listing,
  raise `ProviderError("filing metadata unavailable for <accession>")` and let
  `routers/sec_filings.py:123` surface the 502 the panel already renders. Pass the real
  form type to `:528` — resolve it from the listing row first, and skip the sections call
  when it cannot be resolved.

### [P1] `/quotes` returns a list the client cannot join — IN watchlist rows render blank
- **Principle**: Pull complexity downward (#6) / Information hiding (#3)
- **Evidence**: `sidecar/services/nse_provider.py:354-360` (`bare = strip_exchange_suffix`)
  → `:524`/`:558` `Quote(symbol=bare, …)`; `sidecar/services/correctness_gate.py:76-90`
  `_match_key` strips `.NS`/`.BO` **so the mismatch passes the gate by design**;
  `sidecar/routers/quotes.py:85-87` returns a positional list with failures elided;
  `src/modules/watchlist/api.ts:40` keys the map on `quote.symbol.toUpperCase()` and `:57`
  looks it up by `entry.symbol.toUpperCase()` with no normalisation.
- **Complexity symptom**: Change amplification
- **Why it matters**: Request `RELIANCE.NS` → NSE provider returns `Quote(symbol="RELIANCE")`
  → gate passes → the quote is in the response → the TS join misses → the row shows a null
  quote forever. The panel is *not* broken (`api.ts:28` correctly degrades a missing symbol
  to `null`), which is exactly why this stays invisible: it looks like a coverage gap, not a
  join bug. `entry.symbol` is stored verbatim from `addSymbol` (`src/store/symbols.ts:53`),
  so any user who adds an IN name in its suffixed form — the form `history.py:18-22` treats
  as the canonical IN marker — gets a permanently blank row. The root cause is the contract:
  the sidecar owns instrument identity and then hands back a shape that forces the client to
  re-derive it.
- **Fix**: In `_label_freshness`'s pass (`routers/quotes.py:86`) set `result.symbol` to the
  requested spelling — the gate has already proved they are the same instrument — or add a
  `requested_symbol` field to `models/market.py:14` and join on that. One line; deletes the
  duplicated normalisation rather than mirroring `_match_key` into TypeScript.

### [P1] `GET /news?symbols=…` returns an empty list for every suffixed ticker
- **Principle**: Comments describe non-obvious (#10) / Code should be obvious (#16)
- **Evidence**: `sidecar/routers/news.py:69-74` matches `\b{re.escape(symbol)}\b` against
  title+summary; `:120` drops any item that matched nothing; `:132` returns `scored[:limit]`.
  The provider *did* fetch a dedicated per-symbol feed for it
  (`services/news_provider.py:284-290`).
- **Repro** (run, output verbatim):
  `tag("Reliance Industries Q2 profit rises 10%", "RIL beats estimates", ["RELIANCE.NS"]) -> []`
  `tag("TCS wins $1bn deal", "Tata Consultancy Services", ["TCS.NS","INFY.NS"]) -> []`
- **Complexity symptom**: Cognitive load / unknown unknowns
- **Why it matters**: `\bRELIANCE\.NS\b` cannot appear in prose. So the Yahoo per-symbol RSS
  feed is fetched, parsed, scored — and then 100% discarded by the tagger. The panel shows
  an empty news feed for the primary market of an India-first terminal, and reads as "no
  news for this stock". The same function's docstring (`:63-68`) asserts the matcher is
  careful about exactly this class of problem, which will stop the next reader from
  suspecting it.
- **Fix**: Tag against the symbol's alias set, not the request string — bare + suffixed
  form via `locale.strip_exchange_suffix` (already imported in the provider layer), plus the
  resolved company name. Then require the tag set to be non-empty before the `:120` drop.

### [P1] `FilingFormType` caps EDGAR at 7 forms; the rest vanish without a trace
- **Principle**: Design it twice (#9) / Design for the future (#17)
- **Evidence**: `sidecar/models/sec.py:23`
  `FilingFormType = Literal["10-K","10-Q","8-K","DEF 14A","3","4","5"]`;
  `sidecar/services/sec_filings_provider.py:217-236` `_coerce_form_type` returns `None` for
  anything unmapped; `:288-291` `if form_type is None: continue  # Skip exotic forms`.
  `:490-493` sends `limit` **upstream**, before the drop.
- **Complexity symptom**: Unknown unknowns
- **Why it matters**: A foreign private issuer files 20-F and 6-K and nothing else — that is
  every India ADR (Infosys, HDFC Bank, Wipro), the names this product's users care most
  about. Their filings list comes back `[]` with `ok: True`. Amended filings (`10-K/A`),
  registration statements (`S-1`, `424B4`) and ownership filings (`SC 13D`) are dropped the
  same way. Because `limit=40` is applied upstream first, even a plain US 10-K filer gets a
  quietly short list. Nothing in `FilingsListResponse` (`models/sec.py:143-151`) can say "12
  filings hidden", so neither the panel nor the agent can tell empty from filtered.
- **Fix**: Widen `form_type` to `str` on `Filing` and keep the Literal only as the *filter*
  enum on `routers/sec_filings.py:95`. Stop dropping rows at `:289`. If the closed Literal
  must stay for the panel's grouping, add `dropped_count` to `FilingsListResponse` so the
  omission is visible.

### [P2] The "never crashes the turn" invariant is held by a comment, not the structure
- **Principle**: Consistency (#15) / Define errors out of existence (#9)
- **Evidence**: `sidecar/services/agent_tools/compare_symbols.py:43-48` docstring —
  *"Always returns a dict … so the caller's `asyncio.gather` never aborts the batch"* — but
  `:142` calls `asyncio.gather(...)` **without** `return_exceptions=True`, and the
  result-building attribute reads at `:87-110` (`quote.symbol`, `fundamentals.market_cap`, …)
  sit outside every `try`. Identical shape at `market_overview.py:56` (*"never crash the
  turn"*) vs `:111-113`, with the reads at `:68-77` outside the `try`. The correct pattern
  is two files away: `routers/quotes.py:84` `return_exceptions=True`.
- **Complexity symptom**: Change amplification
- **Why it matters**: The invariant holds only while every attribute on `Quote`/`Fundamentals`
  exists. Rename or drop one field in `models/market.py` and the exception escapes
  `_compare_one`, the un-guarded `gather` propagates it, and the whole agent tool call fails —
  the exact outcome the docstring promises cannot happen. A test that mocks the provider will
  not catch it, because the mock has the fields.
- **Fix**: Add `return_exceptions=True` at `compare_symbols.py:142` and
  `market_overview.py:111-113`, and map a returned exception to the same per-symbol
  `{"symbol", "error"}` dict the handlers already produce. Structure now holds what the
  comment asserted.

---

## Persona walkthrough

**Tactical Tornado.** The tornado wrote `sec_filings_provider.py:544-555`. The listing
did not have the accession, the panel needed *something*, and `form_type="10-K"` +
`filed_date=today` made the page render. Ship. The same hand wrote
`_coerce_form_type:217-236` — a dict of the seven forms the demo needed, `.get()` returning
`None`, and `# Skip exotic forms` at `:290` to make the silent drop look deliberate. It also
wrote `routers/earnings.py:141` (`__all__ = ["date","router"]`) — the linter complained about
an unused import, so the import was exported instead of deleted. Each of these is one line
that made a red light green. Left alone, this file keeps growing its own placeholder
vocabulary: the next unmapped upstream shape gets another `continue`, the next missing field
another plausible default, and the panel keeps rendering confidently.

**Strategic Thinker.** The strategist already wrote most of this subsystem — and it shows in
`routers/quotes.py:1-13`, `models/sec.py:1-10`, `routers/health.py:14-22`, where the *reason*
survives in the code. Redesigning the two violations, the same hand would make the sidecar own
instrument identity end to end: `correctness_gate._match_key` already decides when two
spellings are one instrument, so `/quotes` should return the requested spelling and delete the
client-side join entirely (`src/modules/watchlist/api.ts:40,57` becomes a plain index join).
And it would make absence typed rather than synthetic — `FilingsListResponse` carries
`dropped_count`, `get_filing` raises instead of inventing, and `OHLCVSeries.reason`
(`models/market.py:59`, already the right idea) becomes the pattern every empty result follows
instead of the one route that got it.

---

## Minor observations

- `routers/system.py:215-233` — `POST /system/provider-health/trip` / `/reset` are
  verification-rig hooks shipped unconditionally in the production sidecar; tripping the
  Yahoo circuit degrades every downstream panel to the stale/seed basis. Raised as a raw
  finding (`COD-market-data-providers-2-11`).
- `routers/system.py:85-103` vs `:151-159` — the ollama `/api/tags` fetch, client
  construction, and `data["models"]` parse are written twice; the wire shape leaks into
  two functions.
- `routers/system.py:210, 217, 229` — `from services import provider_health` deferred inside
  three function bodies while the rest of the subsystem imports at module level.
- `routers/earnings.py:141-142` — `__all__ = ["date","router"]` keeps a genuinely unused
  `date` import alive to silence ruff F401. Delete the import instead. (Left out of the raw
  findings as cosmetic.)
- `routers/indicators.py:38-65` — no freshness label, so indicator overlays computed from
  end-of-day bars carry none of the FR-041 staleness the underlying chart shows.
- `services/agent_tools/analyst_tools.py:29` `_MAX_HISTORY_ROWS = 60` and
  `earnings_tools.py:75` `[:12]` cap silently, with `count` reporting the **capped** length —
  the model cannot tell a 60-row truncation from a company with exactly 60 rating changes.

---

## Questions to consider

- If `correctness_gate._match_key` is the single authority on "same instrument", why does any
  response leave the sidecar carrying a spelling the caller did not ask for?
- `OHLCVSeries.reason` (`models/market.py:56-59`) made one empty result honest and typed.
  What stops that from being the shape of every empty in the subsystem — empty filings list,
  empty news, empty earnings calendar?
- Nine agent tools share one envelope contract (`{ok, error}` + a row cap + provider-error
  mapping) copied nine times. Would `register_data_tool(id, fetch, shape)` be a deeper module
  than nine hand-written wrappers, or does the per-tool docstring carry enough value to justify
  the duplication?
