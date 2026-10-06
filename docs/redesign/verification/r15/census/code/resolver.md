# R15 Stage 1 census — code critique: `resolver` (Symbol Resolver)

**Model:** `claude-opus-5[1m]` · **Skill:** `aposd-critique` (loaded; two personas run
sequentially in one context — **assessment independence: degraded (sequential)**,
sub-agents not dispatched under the Stage-1 read-only budget).
**Scope:** the 9 files / 2,793 LOC of the `resolver` entry in `CODE_PARTITION.json`,
all read in full. Repo read-only; the only writes are this file and
`../raw/code-resolver.json`.

---

## Tactical Tornado verdict

**Low–medium.** This is not tornado code. It is the opposite failure mode: a
*strategically* written module whose invariants were moved into prose instead of
into structure, and then enforced in one call site out of two. The module docstring
(`symbol_resolver.py:1-63`) is a genuine design document; `resolution_policy.py`
is a real single-decision-point extraction that killed a documented two-truths bug.
Nothing here looks hacked together.

The damning pattern is therefore not duplication-by-laziness but **half-applied
guards**. The author identified the "a bare ticker STRING collides across
exchanges" hazard, wrote it up in capitals at `symbol_resolver.py:869-879`, and
fixed it for the R13 enrichment join — while the R12 rename lane 80 lines earlier
(`symbol_resolver.py:797-824`) performs exactly the same ticker-string join
unguarded, and `resolution_policy._residual_tie` (`resolution_policy.py:92-95`)
asserts the opposite identity rule outright. Proven below: a BSE-only instrument
gets rewritten into an unrelated NSE company at `score 1.0` with a confident
provenance note.

Flags found: 9 (2 identity-by-string, 2 stage-bypass, 2 duplicated projection/
truth, 1 swallowed-error-that-isn't, 1 unbounded-lifetime cache, 1 dead second
decision surface). Zero temporal decomposition, zero pass-through variables.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|-----------|---------|----------------------|-------------|
| 1 | Strategic over tactical | **pass** | `resolution_policy.py:1-44` — the whole module exists to kill the documented three-gates/two-truths defect; `decide()` is the one decision point | Change amplification down: a threshold change is one file |
| 2 | Deep modules | **pass** | `symbol_resolver.py:652-673` — `resolve(query, region)` is 2 args over a 1,050-line, 4-stage implementation (masters → marquee → banded name → live) | Small interface, large body — the right ratio |
| 3 | Information hiding | **at-risk** | `symbol_resolver.py:919-968` `autocomplete` re-derives its own score ladder (1.0/0.95/0.9/0.8) beside `_name_score`'s band ladder (`:560-596`) | Two matching truths; a band/score change must be made twice |
| 4 | Information leakage | **violate** | `routers/resolve.py:27-54` `_instrument_payload` vs `agent_tools/resolve_symbol.py:25-41` `_instrument_dict` — the same `Instrument`→wire projection, hand-maintained twice, already drifted (`round(...,4)` vs `round(...,3)`; the `rename` block exists in one and not the other) | A new `Instrument` field is silently absent from one consumer; nothing tests the pair |
| 5 | General-purpose modules | **pass** | `symbol_resolver.py:403-445` — `is_nse_symbol`/`is_bse_symbol`/`bse_scrip_code`/`region_hint` are general dict lookups reused by 8 provider modules | One master load serves routing, gating and resolution |
| 6 | Different layer, different abstraction | **pass** | `resolution_policy.py:51-52` imports resolver types under `TYPE_CHECKING` only; the band vocabulary lives in the policy and the resolver imports it (`symbol_resolver.py:88-97`) | Genuinely avoids the circular import without duplicating constants |
| 7 | Pull complexity downward | **violate** | `agent_tools/resolve_symbol.py:70` and `agent_tools/fundamentals.py:119` call the blocking resolver **on the event loop**, while `routers/resolve.py:93` and `routers/fundamentals.py:73` `asyncio.to_thread` it and document why (`routers/resolve.py:70-72`) | Measured 300–900 ms of event-loop stall per agent name-resolve; up to 30 s on the live fallback (`yfinance 1.3.0` `Search(timeout=30, raise_errors=True)`) |
| 8 | Better together / apart | **at-risk** | `symbol_resolver.py:673` — `resolve` = `_enrich_resolution(_annotate_renamed_symbols(_resolve_masters(...)))`; enrichment (which computes the ISIN) runs *after* rename (which needs an identity check) | The ordering forecloses the one check that would make the rename lane safe |
| 9 | Define errors out of existence | **at-risk** | `symbol_resolver.py:366-376` catches only `FileNotFoundError`/`ModuleNotFoundError`; `json.JSONDecodeError` escapes an `@lru_cache`d loader, contradicting the docstring at `:313` ("a missing/garbled map degrades to `{}`") | A truncated bundled master turns every `/resolve` into a 500 (CORS-masked, per CLAUDE.md), not a degrade |
| 10 | Design it twice | **pass** | `resolution_policy.py:33-39` weighs and rejects two rival residual-tie definitions (same-symbol rows vs cross-region rows) before picking one | The alternative is written down, not just the winner |
| 11 | Comments describe non-obvious | **pass** | `symbol_resolver.py:130-143` explains *why* lead-verb stripping is safe (the substring band can never bind) — reasoning code cannot carry | Genuine unknown-unknown reduction |
| 12 | Comments first | **pass** | Every module opens with a design-history docstring (`nse_symbol_change.py:1-64` documents the live endpoint, row shape and a verbatim sample row) | The next maintainer can re-derive the parser without the network |
| 13 | Choosing names | **pass** | `BAND_EXACT_TICKER` … `BAND_FUZZY` (`resolution_policy.py:62-68`); `_DISAMBIGUATE_SCORE`, `_residual_tie` | Names carry the model |
| 14 | Modifying existing code | **violate** | `resolver_masters/enrich_nse_sectors.py:64-72` still writes the orphan `industry` key and a 4-key partial record; `tests/test_india_sector_map.py:56-86` forbids exactly that shape in the shipped file | The artifact was cleaned (D59), the producer that dirtied it was not — rerunning the documented refresh command re-introduces the defect and reds CI |
| 15 | Consistency | **violate** | `/resolve` runs rename + enrichment (`symbol_resolver.py:673`); `/resolve/autocomplete` runs neither (`:919-968`), yet `routers/resolve.py:145` projects both through the same payload builder | Proven: `autocomplete("GUJGAS")` → `GUJGASLTD.NS` (retired) while `resolve("GUJGASLTD")` → `GUJENERGY.NS`; and `isin/bse_code/industry/former_name` are always `null` on the autocomplete wire |
| 16 | Code should be obvious | **at-risk** | `symbol_resolver.py:468` `_instrument_nse(..., band: int = BAND_FUZZY)` — the default makes the *wrong* band the easy one; `autocomplete` takes it (`:952,961,965`), so an exact-ticker row ships `score=1.0, band=0` | Verified: `decide()` on an autocomplete `Instrument` returns `"disambiguate"` for a perfect ticker match |
| 17 | Design for the future | **at-risk** | `symbol_resolver.py:126-128,1033-1038` — the live LRU is size-bounded (128) but has **no TTL**; a successful *empty* result is cached for the sidecar's lifetime | A newly listed symbol stays unresolvable until the desktop app restarts |
| 18 | Performance as design | **violate** | `symbol_resolver.py:747-755` scans 2,675 NSE + 4,873 BSE + 10,365 US names per query with a `SequenceMatcher` per row (`:592-595`); `resolve()` has no memo while `_live_lookup` has an elaborate one | Measured masters-only: `"infosys"` 313 ms, `"tata steel"` 653 ms, `"hdfc bank limited results"` 897 ms — every call, never cached |

**Summary: 9 pass, 5 at risk, 4 violate (9/18 pass).**

---

## Overall impression

The acceptance model is the best-designed thing in the subsystem — one threshold,
one `decide()`, a band vocabulary that makes "a substring match can never bind"
structural rather than advisory. That part earned its complexity.

The cost is concentrated in one habit: **identity is asserted in prose and
enforced by string equality.** The instrument now carries an ISIN (R13) — the
actual global identity key — and not one identity decision uses it. The rename
lane joins on the ticker string, the residual-tie check compares ticker strings,
the enrichment join was hardened against ticker-string collision and its
sibling 80 lines up was not.

The single biggest complexity reduction available is not a refactor: it is
**moving three invariants out of docstrings into the four lines of code that
would hold them** (rename gated on NSE membership; autocomplete routed through
the same post-stages as resolve; one shared wire projection).

---

## What's working

1. **`resolution_policy.decide()` as the sole acceptance gate** (`resolution_policy.py:99-145`,
   grep-pinned by `tests/test_resolution_policy.py:135`). Four consumers — two
   routers, two agent tools — map the same `Resolution` through the same function.
   This is a real two-truths bug that was found and structurally closed.
2. **Band-before-score ranking** (`resolution_policy.py:124`, `symbol_resolver.py:763`).
   `confidence >= ACCEPT and band >= BAND_PREFIX` makes "high score, weak evidence"
   unbindable by construction, so a 0.99 substring hit cannot silently bind. The
   additive locale bonus it replaced was a class of wrong-entity bug, not an instance.
3. **Honest degradation in the rename lane** (`nse_symbol_change.py:323-364`).
   Empty map → `None` → the resolver behaves exactly as before the lane existed;
   chain walking is bounded (`_MAX_CHAIN_HOPS = 8`) and cycle-guarded; a
   future-dated change is not applied. This is how the rest of the subsystem
   should handle unknowns.

---

## Priority issues

### [P0] The rename lane joins on the ticker string, so a BSE-only company can be answered as an unrelated NSE company at confidence 1.0

- **Principle:** 4 (information leakage) / 15 (consistency) — the same hazard is guarded once and not twice.
- **Complexity symptom:** unknown unknowns.
- **Evidence:** `services/symbol_resolver.py:797-824` (`_rename_instrument` gates only on
  `inst.region != REGION_IN`, then overwrites `exchange="NSE"` and
  `yahoo_symbol=f"{new}.NS"`), against the explicit guard for the identical
  collision class at `services/symbol_resolver.py:869-879`.
- **Proof (run against the shipped masters):** injecting one rename row for the
  BSE-only ticker `NSDL` (National Securities Depository Ltd — one of **2,481**
  BSE-only tickers, none of which NSE's `symbolchange.csv` governs) yields
  `resolve("NSDL","IN")` → `GUJENERGY / GUJARAT ENERGY LIMITED / NSE / GUJENERGY.NS`,
  `score 1.0`, note `"NSDL was renamed to GUJENERGY on NSE …"`. The docstring at
  `:793` already reasons about this collision for *US* tickers and stops one
  exchange short.
- **Why it matters:** wrong money-relevant identity presented as true, with
  provenance text that reads as evidence. Whether a live collision exists today
  depends on NSE's ~1,050-row retired-symbol list, which I did not fetch — the
  structural defect is proven, the live instance is unverified.
- **Fix:** one condition in `_rename_instrument` — `if inst.symbol not in _nse_master(): return inst`.
  A dual-listed retired symbol is in the NSE master, so the D67 BSE-row collapse is preserved.

### [P1] Two agent tools run the 300–900 ms (worst case 30 s) resolver on the event loop; the two routers do not

- **Principle:** 7 (pull complexity downward) / 15 (consistency).
- **Complexity symptom:** change amplification.
- **Evidence:** `services/agent_tools/resolve_symbol.py:70` and
  `services/agent_tools/fundamentals.py:119` call `symbol_resolver.resolve(...)`
  directly inside `async def`, dispatched by `services/agent_tools/__init__.py:67`
  (`return await handler(args)`). The sibling paths offload:
  `routers/resolve.py:93` and `routers/fundamentals.py:73` use `asyncio.to_thread`,
  and `routers/resolve.py:70-72` states the reason ("must not block the event loop").
  `symbol_resolver.py:658-660` cites the router's `to_thread` call as load-bearing.
- **Measured:** masters-only resolve of `"hdfc bank limited results"` = 897 ms CPU.
  The live rung is `yf.Search(...)` (`symbol_resolver.py:1001`) with yfinance 1.3.0
  defaults `timeout=30, raise_errors=True` and no explicit timeout passed.
- **Why it matters:** every agent "research X" stalls the whole sidecar — SSE
  streams, `/health`, the detached run manager — for ~0.6 s, or 30 s on a hung
  upstream. This is the hottest resolver path in the product.
- **Fix:** `resolution = await asyncio.to_thread(symbol_resolver.resolve, query, region)`
  in both tools; pass an explicit `timeout=` to `yf.Search`.

### [P1] `/resolve/autocomplete` bypasses the rename and enrichment stages, so the mention picker offers retired symbols and always-null identity

- **Principle:** 15 (consistency) / 3 (information hiding).
- **Complexity symptom:** cognitive load — two "resolve" surfaces with silently different semantics.
- **Evidence:** `symbol_resolver.py:673` composes `resolve` as
  `_enrich_resolution(_annotate_renamed_symbols(_resolve_masters(...)))`;
  `symbol_resolver.py:919-968` `autocomplete` calls neither. `routers/resolve.py:145`
  then projects autocomplete rows through the *same* `_instrument_payload`
  (`:27-54`), which emits `isin/bse_code/industry/former_name` — always `null` here.
- **Proof:** with the R12 finding's own rename row loaded,
  `autocomplete("GUJGAS","IN")` → `GUJGASLTD / Gujarat Gas Limited / GUJGASLTD.NS`
  while `resolve("GUJGASLTD","IN")` → `GUJENERGY.NS` with rename provenance.
  The keystroke picker is the primary UI entry point, so the user is handed the
  dead ticker and the chart loads a retired symbol.
- **Why it matters:** the whole point of the R12 lane is "never answer a stale
  symbol"; the highest-traffic surface opts out.
- **Fix:** run the returned list through `_rename_instrument` + `_enrich_instrument`
  in `autocomplete` (both are per-instrument and already written), or drop the four
  identity keys from the autocomplete payload so the wire does not promise them.

### [P2] `resolve()` re-scans 17,913 names per call with no memo, while the *live* rung has an LRU

- **Principle:** 18 (performance as design).
- **Complexity symptom:** change amplification (every consumer independently learns to avoid calling it).
- **Evidence:** `symbol_resolver.py:747-755` (three full master scans per query)
  × `_name_score`'s `SequenceMatcher` (`:592-595`) for ≤ 4-word queries; masters are
  `@lru_cache`d but results are not. Contrast the 20 lines of budget machinery for
  the network rung at `:117-128, 988-1038`.
- **Measured:** 313 ms (`"infosys"`), 653 ms (`"tata steel"`), 897 ms
  (`"hdfc bank limited results"`), 0.1 ms (exact ticker). `autocomplete` — same
  masters, no `SequenceMatcher` — is 3 ms.
- **Fix:** `@lru_cache(maxsize=2048)` on `_resolve_masters(query, region)` (pure
  over immutable masters; rename + enrichment stay outside it), cleared in
  `reset_caches_for_tests`. One line, one call-site edit.

### [P2] Identity is decided three different ways, and the ISIN that would settle it is unused

- **Principle:** 3 (information hiding) / 16 (obviousness).
- **Complexity symptom:** unknown unknowns.
- **Evidence:** `resolution_policy.py:92-95` — `_residual_tie` skips every candidate
  with `cand.symbol == best.symbol` as "the same instrument", documented at `:33-35`;
  `symbol_resolver.py:869-879` states the exact opposite for the enrichment join
  ("a ticker STRING alone … collides across exchanges", naming NSE `TCI` vs US `TCI`);
  `symbol_resolver.py:236` carries `isin` on every Indian instrument and no
  identity decision reads it.
- **Why it matters:** two modules hold contradictory definitions of "same
  instrument" and the next maintainer cannot tell which is authoritative. In
  `_residual_tie` the cross-region rule currently masks the consequence, so this
  is latent, not live — it becomes live the moment the residual-tie rule is
  relaxed or another exchange is added.
- **Fix:** make identity one predicate — `same_instrument(a, b)` comparing ISIN
  when both carry one and falling back to `(symbol, exchange)` — and have both
  the rename gate and `_residual_tie` call it. That also requires moving
  `_enrich_resolution` before `_annotate_renamed_symbols` in `symbol_resolver.py:673`.

---

## Persona walkthrough

**Tactical Tornado.** A tornado working in this file would extend the pattern that
is already easiest here: add the next lane as another top-level `_xxx_resolution`
stage wired into `_resolve_masters`'s numbered comment blocks (`symbol_resolver.py:691-774`),
give it its own score constant beside `_DISAMBIGUATE_SCORE`, project its new field
into `routers/resolve.py:27` and forget `agent_tools/resolve_symbol.py:25` — exactly
the drift already visible between those two functions (`round(...,4)` vs
`round(...,3)`, `rename` present vs absent). They would also copy
`_instrument_nse(sym, s)` from `autocomplete` (`:952`) into the new lane and inherit
the `band=BAND_FUZZY` default, shipping another instrument that lies about its own
evidence. The debt accretes at the seams, not inside the algorithm.

**Strategic Thinker.** They would not touch the band model — it is the good part.
They would spend the afternoon on three structural moves and stop: (1) one
`same_instrument(a, b)` predicate keyed on ISIN, called by both the rename gate
and `_residual_tie`, which deletes the P0 defect and the P2 contradiction at once;
(2) one `instrument_payload()` in the resolver package that both the router and the
agent tool import, which makes the P-level drift impossible rather than merely
fixed; (3) make `band` a required constructor argument by deleting the
`= BAND_FUZZY` defaults at `symbol_resolver.py:468,483,497`, forcing `autocomplete`
to state the band it actually means. Then they would ask why `autocomplete` and
`resolve` are two functions at all, given both scan the same masters and differ
only in which rungs they run.

---

## Minor observations

- `symbol_resolver.py:898-905` — `_enrich_instrument`'s four-field "did anything
  change" equality check to avoid a `dataclasses.replace` on a frozen dataclass.
  Pure ceremony; delete it and always `replace`.
- `symbol_resolver.py:86,1042` — `DISAMBIGUATION_THRESHOLD` is re-exported and in
  `__all__` with zero consumers anywhere in the tree (only the grep-test at
  `tests/test_resolution_policy.py:135` mentions the name). Dead public API that
  re-advertises the very "second threshold" the policy module exists to abolish.
- `symbol_resolver.py:250-258` — `Resolution.needs_disambiguation` re-runs the full
  `decide()` (including `_residual_tie`) per property access and has no production
  caller; only tests read it (`tests/test_symbol_resolver.py:96,115,415`,
  `tests/test_resolver_rename.py:93`). A second decision surface kept alive by its
  own tests.
- `nse_symbol_change.py:440-454` — `schedule_refresh` is called on every `/resolve`
  and `/resolve/autocomplete` request (`routers/resolve.py:91,140`) purely for its
  first-of-day side effect; the module docstring itself says the lifespan hook is
  the right home. Harmless now, but it makes two read-only GET routes the owners
  of a background download's lifecycle.
- `resolver_masters/regenerate_bse_master.py:159-163` and
  `regenerate_india_sectors.py:240` both hardcode `_MIN_ROWS = 1000` as a
  WAF-block floor. Same constant, same meaning, two files — fine today, drifts the
  day one universe legitimately shrinks.

---

## Questions to consider

- The instrument carries an ISIN now. What breaks if `same_instrument()` is ISIN-first
  and every identity decision — rename, residual tie, dedup, enrichment — routes through it?
- `autocomplete` and `resolve` scan the same three masters and differ only in which
  rungs they run and which post-stages they apply. Would one function with a
  `rungs=` argument be deeper than two functions with divergent semantics?
- The band field exists to make "how did this match" structural. Why is
  `BAND_FUZZY` a default rather than a required argument, given the one caller that
  takes the default is the one that produces exact-ticker matches?

---

## Run notes

- Target: `resolver` (9 files, 2,793 LOC) per `CODE_PARTITION.json`; all files read in full.
- Skill `aposd-critique` loaded and followed. **Assessment independence: degraded
  (sequential)** — Strategic Thinker pass completed and recorded before the Tactical
  Tornado scan; no sub-agents dispatched.
- Snapshot persistence to `.aposd/critique/` **skipped** — Stage 1 is read-only on
  the repo outside the two census output files.
- `.aposd/critique/ignore.md`: absent.
- Verification runs used `sidecar/.venv/bin/python` against the shipped masters only
  (`_live_lookup` stubbed to `[]` for the timing runs; the rename map injected via
  the existing `nse_symbol_change.set_active_map_for_tests` seam). No network, no
  process started or stopped, no repo file mutated. Temp files: none.
