# R10 Track RESOLVE — one resolver, one truth (+ metric semantics)

Branch: `worktree-agent-r10-resolve`. Read first: `verification/R10_DEFECT_CATALOGUE.md`
(E1, E8), DECISIONS D37/D38 context, the contracts commit (types/brief.ts BriefExecution/
BriefDisambiguation/BriefDerivedMetrics; research/models.py ResearchExecution).

## Files you own (exclusive)

`sidecar/services/resolution_policy.py` (new), `sidecar/services/symbol_resolver.py`,
`sidecar/services/research/target.py`, `sidecar/services/research/semantics.py` (new),
`sidecar/services/research/fast.py`, `sidecar/services/research/iter.py`,
`sidecar/services/research/deep.py`, `sidecar/services/agent_tools/resolve_symbol.py`,
`sidecar/services/agent_tools/deep_research.py`, `sidecar/config.py` (region default
line only), `src/lib/region.ts` (mirror default only),
`sidecar/services/resolver_masters/marquee_aliases.json` (new), and the matching tests
(`test_resolution_policy.py` new, `test_symbol_resolver.py`, `test_research_target.py`,
`test_research_semantics.py` new, `test_research_model_lane.py`, fast/iter/deep tests).
Do NOT touch `agent_runtime.py`, `agent_tools/research.py`, `catalog.py`, `routers/`,
frontend (except the region.ts default line) — other teams own them.

## 1. resolution_policy.py — the ONE acceptance policy

```python
ACCEPT = 0.72   # >= ACCEPT -> bound
REJECT = 0.50   # < REJECT  -> unresolved
@dataclass(frozen=True) class ResolutionDecision:
    outcome: Literal["bound","disambiguate","unresolved"]
    instrument: Instrument | None
    candidates: list[Instrument]
    reason: str
def decide(resolution: Resolution) -> ResolutionDecision
```
Delete `target.py`'s `CONFIDENCE_FLOOR`; `symbol_resolver.DISAMBIGUATION_THRESHOLD`
re-exports from here. A grep-style test pins that no second threshold constant exists.

## 2. symbol_resolver.py scoring rebuild

- `resolve(query, *, region)` keyword-required. Callers pass `config.get_region()`.
  Flip `config` default region "US"→"IN" and `src/lib/region.ts` DEFAULT_REGION in the
  SAME commit. User Settings still override.
- **Band tie-break replaces the additive bonus**: sort key
  `(band, locale_match, name_score)` where band ∈ {exact-ticker 6, marquee 5,
  name-exact 4, first-word 3, prefix 2, substring 1, fuzzy 0}. A cross-locale
  higher band ALWAYS beats a same-locale lower band. Reported confidence = raw
  name score (no inflation, no clamp hiding 0.97-vs-1.0).
- **First-token normalization**: strip trailing punctuation ("reliance," → "reliance")
  and compare against corporate-suffix-stripped names (Inc/Ltd/Limited/Corp …) so
  US "RELIANCE, INC." and NSE "Reliance Industries Limited" land in the same band and
  locale breaks the tie — IN session → NSE.
- **Whole-query fuzzy demotion (kills E1)**: the SequenceMatcher rung applies ONLY to
  queries of ≤4 words after cleaning. A longer query scores via its leading-word
  prefixes (the target.py prefix loop), never via whole-string similarity — pin the
  Phase-0 repro table as regression tests: `research Reliance` must NOT bind REFR,
  `Reliance Q4 results` must NOT bind FRLCY, `Reliance Industries Q4 FY26 results`
  must bind RELIANCE (via its 2-word prefix), `reliance industries quarterly results`
  must bind RELIANCE.
- **Marquee stage** (after exact-ticker, before fuzzy): bundled
  `marquee_aliases.json` — `reliance` → primary RELIANCE (alternatives RPOWER,
  RELINFRA as candidates), `mahindra` → primary M&M (alternatives TECHM, M&MFIN),
  `tata`/`bajaj`/`adani`/`birla` → forced `disambiguate` with curated candidate lists
  (tata: TCS TATAMOTORS TATASTEEL TATAPOWER TATACONSUM TITAN; bajaj: BAJFINANCE
  BAJAJFINSV BAJAJ-AUTO BAJAJHLDNG; adani: ADANIENT ADANIPORTS ADANIGREEN ADANIPOWER
  ADANIENSOL; birla: GRASIM ULTRACEMCO ABCAPITAL ABFRL HINDALCO). Verify every symbol
  against the NSE master at test time. Applies when region is IN or GLOBAL. The
  match key is the cleaned one-word query or the leading word of a two-word query
  whose second word is generic ("group", "stock", "share").
- **`_live_lookup(query, region)`**: collect all 5 quotes; under IN rank .NS/.BO
  first; score stays 0.6 — which the policy maps to `disambiguate`, never `bound`.
- **Prefix fallback** (`target.py`): `_PREFIX_WORDS = (4, 3, 2, 1)`; a 1-word prefix
  may bind only at band ≥ first-word (0.97) or exact-ticker/marquee.

## 3. target.py + consumers

`target_from_payload` consumes `ResolutionDecision`. New sentinel for disambiguation
(e.g. `ResearchDisambiguation(query, candidates)`). `resolve_target` returns
`ResearchTarget | ResearchDisambiguation | None`. Research loops (fast/iter/deep) on
disambiguation return `{"ok": True, "needs_disambiguation": True, "query": …,
"candidates": [{symbol,name,exchange,score,yahoo_symbol}], "message": "<human>"}` —
no markdown, no structured, no web spend. The `resolve_symbol` tool reply gains
`"status": "bound"|"disambiguate"|"unresolved"` with `resolved: null` unless bound.

## 4. Tier B binds the same target (deep_research.py)

In `run_research_model_brief`, BEFORE the OpenRouter call:
`resolve_target(invoke_tool, text, region=config.get_region())`.
- disambiguation → return the needs_disambiguation dict (zero HTTP spend).
- bound → prepend pin line `"Research target: {name} ({exchange}: {symbol}). Every
  claim must concern this exact listed entity."` to the prompt; after the call run
  `fast.snapshot_structured(invoke_tool, target.symbol)`; brief gets
  `symbol=target.symbol`, `structured={"resolved": resolved_payload(target), **snap}`.
- None → web-only with NO_INSTRUMENT_NOTE (today's behavior).

## 5. Execution-loop hint (contract with Team RUNTIME)

Each engine return gains ONE key, `"execution_loop"`: `gather_fast` → `"fast"`;
`run_iter_research` → `"iter"`; heavy → `"heavy"`; `run_research_model_brief` →
`"research-model"` (set it on ok results AND on `run_deep_brief`'s pass-through).
Team RUNTIME mints run_id + builds the full ResearchExecution in
`agent_tools/research.py` — you only report what ran. Do not edit research.py.

## 6. semantics.py — the metric discipline layer (E8)

Pure module, no IO. `derive_semantics(structured: dict, region: str|None) -> dict`
returning the `derived` leg `{"ok": True, "provider": "derived", "data": {...}}` per
the BriefDerivedMetrics contract (types/brief.ts): drawdown_from_high =
(52wHigh − price)/52wHigh labeled "Below 52-week high" with formula;
fifty_two_week_change re-labeled "52-week price change (Yahoo)";
dividend_yield vs dividend_per_share/price reconciled (>25% relative divergence →
a `conflicts[]` entry and NO single dividend value); revenue/earnings growth re-emitted
with basis "yoy" and metric named; market_cap vs price×shares_outstanding cross-check
(±5% else conflict). Values null when inputs missing — never fabricated.
`prompt_block(derived) -> str` renders "METRIC FACTS — use these labels and bases
verbatim; figures not listed here must be cited to a source" for synthesis prompts.
Hook ONCE in `fast.snapshot_structured` (covers fast/iter/heavy + Tier B via §4);
inject `prompt_block` into iter/heavy synthesis prompt assembly.

## Gates before you push

`ruff format && ruff check` clean; full `pytest sidecar/tests` green (update any test
the region flip or scoring rebuild legitimately changes — but a changed expectation
needs a one-line comment saying why the new truth is right); the Phase-0 repro table
pinned as tests; marquee property test (region IN ⇒ every marquee bind is IN-listed).
Commit granularly, push your branch after each green milestone.
