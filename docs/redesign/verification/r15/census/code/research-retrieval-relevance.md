# R15 Stage 1 census — code critique: `research-retrieval-relevance` (Research Engine: Retrieval & Relevance)

**Model:** `claude-opus-5[1m]` · **Skill:** `aposd-critique` (loaded and followed; two
personas run **sequentially in one context — assessment independence: degraded**,
sub-agents not dispatched under the Stage-1 read-only budget).
**Snapshot persistence:** skipped — the run is read-only on the repo, so nothing was
written to `.aposd/critique/`.
**Scope:** the 17 files / 3,784 LOC of the `research-retrieval-relevance` entry in
`CODE_PARTITION.json`, all read in full. `services/search/extract.py` is *not* in the
entry and was read only where it consumes this subsystem's API. Repo read-only; the
only writes are this file and `../raw/code-research-retrieval-relevance.json`.
**Proofs:** three defects (P0, P1, P2 below) and two supporting claims were executed
against `sidecar/.venv/bin/python` with stubbed transports — no network, no writes, the
operator's live app untouched.

---

## Tactical Tornado verdict

**Low as craft, high as composition.** This is emphatically not tornado code. Every
individual module is written strategically: `breaker.py` and `pacing.py` are clean
composable primitives with injected clocks; `relevance.py` opens with a real
root-cause design document (`relevance.py:1-13`) and is pure, network-free and
unit-testable end to end; `scrub.py` is a disciplined prompt-injection boundary; the
typed `SearchError.reason` (`base.py:78-99`) exists specifically so the UI can tell a
throttle from an outage. Somebody cared.

The damning pattern is **drift at the seams between those good modules**. Every
finding below lives in a join, not in a body:

- the option key the caller sends (`numResults`) is read by three of four backends and
  silently ignored by the fourth — the *preferred* one (`searxng.py:263`);
- DDG is paced by two independent throttles tuned to the same number in two files
  (`pacing.py:33`, `ddg.py:69`);
- the rotation's block-page markers (`keyless.py:75-79`) fire *after* the answer has
  already been recorded as a success (`keyless.py:163-165`);
- the `up-but-empty` cross-check was correctly identified and then implemented in the
  caller for one backend only (`web_search.py:157-165`), leaving the identical hole on
  the floor it was cross-checking *against*;
- and three module docstrings still describe an R7 routing story that no longer runs
  (`base.py:20-23`, `searxng.py:18-27`, `searxng_manager.py:40-42`).

Flags found: 15 (1 silently-ignored contract parameter, 1 over-generalised regex that
drops on-entity evidence, 1 error-defined-into-success, 1 predicate reused at two
granularities, 2 duplicated-truth pairs, 1 false hot-path comment hiding a blocking
docker probe, 1 unbounded nested retry with no deadline anywhere, 1 inverted breaker,
1 lost typed reason, 1 lossy normalization, 1 unguarded background task with a dead
logger, 1 dead-except-tests API surface, 1 unclearable sticky error, 1 twin module).
Zero temporal decomposition. Zero pass-through methods of consequence.

---

## Design principles score

| # | Principle | Verdict | Evidence (file:line) | Consequence |
|---|-----------|---------|----------------------|-------------|
| 1 | Strategic over tactical | **at-risk** | `relevance.py:407-418` `_symbol_only_in_index_form` — a patch written for the KSE-100 incident, generalised to "any 2–3 digit number after the ticker" | The fix for one collision silently drops a whole class of on-entity headlines (P1) |
| 2 | Deep modules | **pass** | `base.py:112` `search(query, *, options)` is 2 args over 4 backends + rotation + breakers + pacing; `relevance.py:515` `entity_match(row, target)` over ~300 lines of scoring | Callers carry almost none of the retrieval complexity |
| 3 | Information hiding | **at-risk** | `web_search.py:141` and `:157` branch on `label is None` as a proxy for "a SearXNG lane served", explained by a prose comment at `:139-140` | `_resolve_backend`'s internal labelling convention is load-bearing control flow two functions away; a fourth lane breaks both branches silently |
| 4 | Information leakage | **violate** | `pacing.py:33` `"ddg": 3.0` vs `ddg.py:69` `_RATE_PER_MIN = 20`; `_coerce_limit` at `ddg.py:399`/`brave.py:140`/`mojeek.py:132` vs `_citation_limit` at `searxng.py:261`; `USER_AGENT` at `transport.py:33` vs `ddg.py:76`; `_host_matches` at `relevance.py:306` vs `finance.py:122` | Four copies of the same knowledge; one pair has **already drifted** into a proven defect (P0) |
| 5 | General-purpose modules are deeper | **violate** | `keyless.py:84-89` `is_low_quality` applied to a WHOLE result (`:98`) and to a single PARAGRAPH (`extract.py:219`) from one marker list | `"all rights reserved"` is correct per-paragraph and destructive per-result — proven to drop a legitimate IR row (P3) |
| 6 | Different layer, different abstraction | **at-risk** | `web_search.py:219-240` hand-rebuilds `SearchResponse`/`SearchResult`/`Citation` into a dict field by field | A new field on the dataclass is invisible to the agent until this projection is edited too; nothing tests the pair |
| 7 | Pull complexity downward | **violate** | `web_search.py:157-165` implements the up-but-empty cross-check in the CALLER for SearXNG only; the same failure inside `keyless.py:186-189` is unreachable from there | The right idea at the wrong layer — the floor it cross-checks against has the identical hole (P2) |
| 8 | Better together or better apart | **at-risk** | `brave.py` vs `mojeek.py` — 104 differing lines of ~145 after renaming engine + region param; `_clean`/`_is_organic_url`/`_node_to_result`/`_parse`/`_coerce_limit`/status branches identical | A fix to the scrape contract must be made twice and has no structural reason to stay in sync |
| 9 | Define errors out of existence | **violate** | `keyless.py:163-165` records success and `any_engine_answered=True` BEFORE `_filter_results`; `:186-189` then returns an empty SUCCESS | A soft block is defined *into* a valid "found nothing" — the opposite direction (P2, proven) |
| 10 | Design it twice | **pass** | `breaker.py` (state machine) and `pacing.py` (throttle + backoff) are separate composable primitives, not one tangled rate-limiter; `keyless.py` supersedes the bare `ddg.py` floor while both stay resolvable | Each can be reasoned about and tested alone |
| 11 | Comments describe non-obvious | **at-risk** | Rationale comments are excellent (`ddg.py:63-73`, `breaker.py:9-25`) — but `web_search.py:11-13`/`:85-86` ("an instant in-process read, no network probe"), `base.py:20-23` ("sourced from `locale_domains`") and `searxng.py:18-27` (autodetect routing) are all **false today** | The comments a maintainer trusts most are the ones that lie (P4, F12) |
| 12 | Comments first | **pass** | Every public function carries an interface comment written to the contract, not the body; `relevance.py:1-13` and `keyless.py:1-27` are genuine design docs | New readers get the *why* before the *how* |
| 13 | Choosing names | **pass** | `WEAK_MATCH_CEILING`, `_foreign_shadow`, `keyless-fallback`, `ready_base_url_detected` all create an image | Minor: `_symbol_only_in_index_form` names the KSE case, not the rule it enforces |
| 14 | Modifying existing code | **violate** | R7→R8→R9→R13 layers left behind: `registry.py:22-24` declares exa/hosted DEAD while `base.py:59-75` still carries `metadata` for the hosted cost annex and `web_search.py:237-239` still passes it through | Each generation added; none deleted or corrected the prose it invalidated |
| 15 | Consistency | **violate** | Option key (`numResults` honoured 3×, ignored 1×); citation limit (`keyless.py:169` `limit=len(results)` vs `DEFAULT_CITATION_LIMIT=8` everywhere else); timeouts (12s `ddg.py:84`, 20s `searxng.py:61`, 12s `transport.py:45`); retry shape (`ddg.py`'s own loop nested inside `keyless.py`'s) | Four conventions for one concept; the reader cannot generalise from any one backend |
| 16 | Code should be obvious | **at-risk** | `relevance.py:421-474` `_entity_signals` — 5 interacting signal paths mutating two booleans; `:407-418` needs a manual trace to see that `saw_occurrence` + early-`return False` means "ALL occurrences were index-shaped" | The two proven relevance behaviours are both invisible on a read |
| 17 | Design for the future | **violate** | `base.py:138-174` `locale_domains`/`US_DOMAINS`/`IN_DOMAINS`, `searxng.py:64-142` `detect_searxng`/`_json_capable`/`_managed_base_url`, `base.py:75` `metadata`, `breaker.py:135` `breaker_status`, `registry.py:38` `KNOWN_BACKENDS`, `scrub.py:105` `untrusted_context_message` — **zero production callers**, alive only in tests | ~150 lines of hooks for scenarios that were deleted, plus docstrings pointing at them as live |
| 18 | Performance as design | **violate** | `ATTEMPTS_PER_ENGINE=2` (`pacing.py:42`) × `_MAX_ATTEMPTS=2` (`ddg.py:60`) × 2 endpoints (`ddg.py:385`,`:393`) = 8 POSTs @ 12s for the DDG turn alone, ×3 engines; `grep -n "timeout\|wait_for\|deadline" keyless.py web_search.py` → **zero hits**. `transport.py:108` builds a fresh `AsyncClient` per fetch | No wall-clock budget bounds a single `web_search` call; worst case is minutes inside one agent tool step |

**Summary: 4 pass, 6 at risk, 8 violate (4/18 pass).**

The score reads worse than the craft. Every violate is an *integration* verdict: no
single file here is badly written, and several are exemplary. What failed is the
maintenance of agreements between them across four redesign generations.

---

## What's working

1. **`relevance.py` is genuinely data-driven, not special-cased** — and its own test
   suite proves it (`tests/test_research_relevance.py:367-369` asserts the KSE gate is
   driven by `FOREIGN_MARKET_MARKERS`, not a ticker branch). The module is pure, takes
   no network and no LLM (`relevance.py:12`), so every scoring claim is cheap to falsify
   — which is exactly why P1 below was provable in four lines.
2. **The honesty plumbing is real, not decorative.** `SearchError.reason`
   (`base.py:78-99`) → per-engine notes (`keyless.py:180-184`) → `GET /search/status`
   (`search_status.py:20-23`) → "DuckDuckGo cooling down (24s)" is a complete chain from
   a 202 response to an honest UI string. Most codebases fake this with a global boolean.
3. **`breaker.py` and `pacing.py` are correctly-shaped primitives.** Injected `clock`,
   `sleeper` and `rng` (`breaker.py:53`, `pacing.py:88-89`) make the whole
   timing surface deterministic offline; `RequestQueue.acquire` stamps the *slot* time
   rather than the post-sleep clock read (`pacing.py:115-116`) — a subtle, correct
   choice with a comment explaining it.
4. **`scrub.py` fences untrusted web text before it reaches a prompt** with marker
   escaping (`scrub.py:59-67`) so a hostile page cannot close the fence. Used at every
   real ingress (`deep.py:789-795`, `verify.py:175-185`, `deep.py:611` inline titles).

---

## Priority findings

### [P0] The preferred retrieval tier silently ignores the caller's result count

**Principle:** Information Leakage (#4) / Consistency (#15).
**Complexity symptom:** Change amplification — one wire knowledge (`the options key`)
lives in four files and has already drifted.
**Evidence:** `web_search.py:198` sends `{"numResults": n, ...}`. `ddg.py:401`,
`brave.py:142` and `mojeek.py:134` each read `opts.get("maxResults", opts.get("numResults"))`.
`searxng.py:263` reads `opts.get("maxResults")` **only** — and `searxng.py:205` never caps
`results` at all, only citations.
**Proven:**

```
SearxngBackend.search("q", options={"numResults": 3, ...}) -> 40 results, 8 citations
ddg._coerce_limit({"numResults": 3})     = 3
searxng._citation_limit({"numResults": 3}) = None   # -> DEFAULT_CITATION_LIMIT = 8
```

**Why it matters:** SearXNG is the tier the product actively pushes users to set up
(the whole "Unlimited (Local)" flow, `searxng_manager.py:1-11`). On that tier the agent
asking for 3 results gets every row the instance returned — commonly 30–50 — straight
into the model's context via `web_search.py:223-232`, while the brief recorder still
only sees 8 citations (`deep.py:604`). Ask for 20 and you get 8. The *worse* tier
honours the contract; the better one does not.
**Fix:** delete `_citation_limit` and the three `_coerce_limit` copies; put one
`result_limit(options)` helper in `base.py` next to `DEFAULT_CITATION_LIMIT`, and slice
`results` with it in `searxng.py:205` as the other three already do.

### [P1] A ticker followed by a 2–3 digit number scores 0 and is dropped as off-entity

**Principle:** Strategic over Tactical (#1) / Code Should Be Obvious (#16).
**Complexity symptom:** Unknown unknowns — the drop is silent and invisible on a read.
**Evidence:** `relevance.py:407-418` `_symbol_only_in_index_form` returns True when
*every* bounded occurrence of the symbol is followed by `[\s-]?\d{2,3}` — written for
`KSE-100`, but `\s` and a bare 2–3 digit number match ordinary headline grammar.
`relevance.py:440-441` then discards the symbol signal entirely.
**Proven** (target `BAJFINANCE` / "Bajaj Finance Limited" / NSE / IN, on a moneycontrol URL):

```
"BAJFINANCE 200 DMA breakout as stock nears record"  -> 0.0   DROPPED
"BAJFINANCE breakout as stock nears record"          -> 1.0   kept
"INFY 1500 target: brokerages raise view"            -> 0.0   DROPPED
```

**Why it matters:** the symbol path is the *only* anchor whenever the ticker is not a
prefix of the company name (`BAJFINANCE`/Bajaj Finance, `M&M`/Mahindra, `INFY`/Infosys),
and "TICKER <number>" is the dominant shape of Indian price-target, DMA, crore-order and
level headlines. This is the exact class of on-entity evidence the research product
exists to retrieve, and it is dropped before it can become a source (`deep.py:611`) or
count toward coverage (`deep.py:624`). Note `MATCH_FLOOR` is never reached, so the row
does not even survive as a weak citation.
**Fix:** require the index shape to be a *hyphenated or contiguous* suffix
(`[-]?\d{2,3}` without `\s`, or assert the whole token `kse-100`/`kse100`), and gate the
whole check behind `_foreign_shadow(text_lc, host)` — the marker that made it necessary.

### [P2] An HTTP-200 block page is recorded as a healthy empty answer and resets the breaker

**Principle:** Define Errors Out of Existence (#9) / Pull Complexity Downward (#7).
**Complexity symptom:** Unknown unknowns — the failure is indistinguishable from success
at every layer above.
**Evidence:** `keyless.py:161-176` — `breaker.record_success()` (`:163`) and
`any_engine_answered = True` (`:164`) both execute **before** `_filter_results` (`:165`)
runs the block-page markers. `keyless.py:186-189` then returns
`SearchResponse(results=[], ...)` — an `ok: True` empty answer, not the typed
`rate_limited` error built four lines below. The markers at `keyless.py:75-79`
(`"verify you are a human"`, `"are you a robot"`, `"unusual traffic"`, `"access denied"`)
exist precisely to identify blocks.
**Proven** (single-engine rotation fed one 200 result whose text is a CAPTCHA
interstitial):

```
returned SearchResponse  results: 0  backend: keyless
ddg breaker state after a pure block page: closed   failures: 0
```

**Why it matters:** two harms compound. (a) The breaker never trips for a soft block, so
the engine is hammered at full rotation rate indefinitely — the one failure mode
`breaker.py` was written for. (b) The run reports "found nothing" instead of
"rate-limited", which is the honesty regression `SEARCH_REASON_RATE_LIMITED` exists to
prevent, and it is invisible to the up-but-empty cross-check in `web_search.py:157`
because that branch is gated on `label is None` (SearXNG only) — the floor being
cross-checked *against* has the same hole.
**Fix:** move `_filter_results` above `record_success`; when an engine's rows are
non-empty but filter to zero, call `breaker.record_failure()` and note
`"blocked (challenge page)"` rather than `"no results"`, and do not set
`any_engine_answered`.

### [P3] The quality filter drops legitimate results on a copyright footer

**Principle:** General-Purpose Modules Are Deeper (#5).
**Complexity symptom:** Change amplification — one marker list must satisfy two
granularities it cannot both serve.
**Evidence:** `keyless.py:80` `"all rights reserved"` in `LOW_QUALITY_MARKERS`;
`keyless.py:98` applies `is_low_quality` to the **whole** `title + snippet` of a result;
`extract.py:219` applies the same predicate to a **single paragraph**.
**Proven:**

```
SearchResult(title="Route Mobile Q2 FY25 results",
             snippet="Consolidated revenue rose 9%. (c) 2025 Route Mobile Limited. All rights reserved.")
_filter_results([row], set()) == []    # dropped
```

**Why it matters:** SERP snippets routinely splice a page footer onto real content, and
investor-relations pages — the highest-tier evidence this product ranks for
(`finance.py:138-140` `TIER_PRIMARY`) — are the worst offenders. Dropping a primary
source because it carries a copyright line inverts the source hierarchy, and the drop is
silent: the row never reaches `relevance.py` to be scored or logged.
**Fix:** split the list — keep `"all rights reserved"` (and other footer noise) in the
paragraph-level list `extract.py` consumes; leave only genuine interstitial markers
(`"verify you are a human"`, `"unusual traffic"`, `"access denied"`) in the
result-level list, and make block markers a *failure* signal per P2 rather than a filter.

### [P4] The hot path's "no network probe" is false — the first search of every process can block on docker

**Principle:** Comments Describe Non-Obvious (#11) / Performance as Design (#18).
**Complexity symptom:** Cognitive load + unknown unknowns — the comment actively
misdirects the next reader away from the cost.
**Evidence:** `web_search.py:11-13` ("an instant in-process `ready_base_url()` read, no
network probe") and `web_search.py:85-86` ("an instant in-process read (no network probe
on the hot path)") describe the call at `web_search.py:88`, which is
`ready_base_url_detected()` — `searxng_manager.py:337-354`, whose first invocation
per process `await`s a full `refresh()`: `docker version` (15s budget,
`searxng_manager.py:91`), `docker inspect`, `docker port`, and a 5s HTTP health probe
(`:97`). The 124-timeout path (`:148-153`) is reachable when dockerd is wedged.
Additionally `searxng_manager.py:348-349` sets `_hot_path_detected = True` **before** the
await, so a concurrent first search returns the stale `None` and floors to keyless while
the derivation is still in flight.
**Why it matters:** the first `web_search` of every sidecar launch — i.e. the first
research run the user ever sees after an app start — can stall tens of seconds inside a
single agent tool step with no progress signal, and the comment tells anyone profiling
it to look elsewhere. The concurrency race means the very run that paid for the
derivation may not benefit from it.
**Fix:** correct both comments; kick the one-shot derivation off at app lifespan startup
(the sidecar already has one, per `CLAUDE.md`'s `run_manager.shutdown()` rule) and keep
the hot path on the pure `ready_base_url()` read the comments already promise. If it must
stay lazy, set `_hot_path_detected` after the await and guard with the existing
`self._lock`.

---

## Minor observations

- `searxng_manager.py:62` declares `_log = logging.getLogger(__name__)` and **never uses
  it** — the entire docker pull/run/health state machine emits no log line. Combined with
  the unguarded `asyncio.create_task(self.setup())` at `:483` (only `CancelledError` is
  caught, `:491`) an `OSError` from `write_settings` (`:531`, while `pick_port` on the
  very next line *is* guarded at `:532-536`) strands the task with an unretrieved
  exception and no trace.
- `registry.py:54` and `:63-65` declare a `searxng_url` parameter both builders ignore —
  pass-through variables surviving the exa/hosted deletion.
- `relevance.py:306-307` `_host_matches` re-implements `finance.py:122-124` `_matches`
  line for line, in a module that already imports `finance` (`relevance.py:20`).
- `keyless.py:169` passes `limit=len(results)` to `normalize_results_to_citations`,
  opting out of `DEFAULT_CITATION_LIMIT` that every other backend accepts.
- `ddg.py:391` takes a second token from the global bucket for the Lite fallback, so a
  single DDG search consumes two of the ~20/min budget.

---

## Persona walkthrough

**Tactical Tornado walkthrough.** If the Tornado owned this code, the next incident
would be patched exactly the way `_symbol_only_in_index_form` (`relevance.py:407-418`)
was: a live collision (KSE-100) gets a regex written against the observed string, dropped
into the scoring path, and covered by a test asserting the *incident* is fixed
(`tests/test_research_relevance.py:293-306`). The regex's blast radius — every headline
where a number follows a ticker — is never enumerated because the test that would have
caught it was never written. Repeat that four times and `relevance.py` becomes an
incident museum: `_FILING_TITLE_RX`, `_SEO_TITLE_PATTERNS`, `CRYPTO_HOSTS`,
`FOREIGN_MARKET_MARKERS` are already four incident-shaped constants, each individually
defensible. The other Tornado tell is `web_search.py:141` and `:157`: two branches keyed
on `label is None` with a comment explaining the invariant. The third lane will be added
by copying the second branch, and the comment will be copied with it.

**Strategic Thinker walkthrough.** The redesign is small and mostly deletion. One
`SearchOptions` shape in `base.py` (limit, region, category) replaces `_coerce_limit`
×3 + `_citation_limit` and closes P0 structurally — a backend that ignores the limit
would no longer compile. `_resolve_backend` returns a typed
`ResolvedLane(backend, lane: "searxng"|"floor")` instead of a nullable label, and both
`web_search.py:141`/`:157` branch on `lane`, so the invariant lives in the type rather
than in a comment. `_filter_results` moves above `record_success` in `keyless.py` and
returns `(kept, blocked_count)`, so a challenge page is a breaker failure and a typed
`rate_limited` error rather than an empty success — which in turn makes the caller-side
cross-check at `web_search.py:157-165` redundant and deletable, pulling that complexity
down into the rotation where the evidence lives. Finally `base.py:138-174`,
`searxng.py:64-142`, `base.py:75` and the three docstrings that point at them get
deleted, not maintained. Net: fewer lines, one option contract, one lane discriminator,
one place where "this engine failed" is decided.

---

## Questions to consider

- `Citation` (`base.py:45-57`) exists to be a thinner `SearchResult`, but `deep.py:604`
  prefers citations over results — so `published_at` and `source` are discarded for every
  web source, on the one tier (SearXNG, `searxng.py:246`) that actually supplies a
  publication date. For a research product whose value is recency, is the thin shape
  earning its existence, or should `_record_web` read `results` and drop `Citation`?
- The floor's "rotate to cross-check before declaring found-nothing" doctrine
  (`keyless.py:173-176`) is the same idea as the SearXNG cross-check
  (`web_search.py:147-165`). If both are the same rule, should there be one
  `cross_check_empty(primary, floor)` seam rather than two implementations at two layers?
- `_entity_signals` (`relevance.py:421-474`) returns two booleans that five code paths
  mutate. Would returning the *evidence* (which anchor fired, in which field, at what
  length) make the two proven behaviours — and the next one — visible in a log line
  instead of requiring a reproduction script?
